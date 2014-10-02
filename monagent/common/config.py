import ConfigParser
import os
import itertools
import logging
import logging.config
import logging.handlers
import string
import sys
import glob
import inspect
import traceback
import re
import imp
from optparse import OptionParser, Values
from cStringIO import StringIO
from version import __version__

import yaml


try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

# project
from util import get_os
from monagent.collector.jmxfetch import JMXFetch, JMX_COLLECT_COMMAND

# CONSTANTS
AGENT_CONF = "agent.conf"
DEFAULT_CHECK_FREQUENCY = 15  # seconds
DEFAULT_STATSD_FREQUENCY = 2  # seconds
DEFAULT_STATSD_BUCKET_SIZE = 10  # seconds
LOGGING_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_CONFIG_DIR = '/etc/monasca/agent'
DEFAULT_LOG_DIR = '/var/log/monasca/agent'

log = logging.getLogger(__name__)
windows_file_handler_added = False


class PathNotFound(Exception):
    pass


def get_parsed_args():
    parser = OptionParser()
    parser.add_option('-c', '--clean', action='store_true', default=False, dest='clean')
    parser.add_option('-v', '--verbose', action='store_true', default=False, dest='verbose',
                      help='Print out stacktraces for errors in checks')

    try:
        options, args = parser.parse_args()
    except SystemExit:
        # Ignore parse errors
        options, args = Values({'clean': False}), []
    return options, args


def get_version():
    return __version__


def skip_leading_wsp(f):
    "Works on a file, returns a file-like object"
    return StringIO("\n".join(map(string.strip, f.readlines())))


def _windows_commondata_path():
    """Return the common appdata path, using ctypes
    From http://stackoverflow.com/questions/626796/\
    how-do-i-find-the-windows-common-application-data-folder-using-python
    """
    import ctypes
    from ctypes import wintypes, windll

    _SHGetFolderPath = windll.shell32.SHGetFolderPathW
    _SHGetFolderPath.argtypes = [wintypes.HWND,
                                 ctypes.c_int,
                                 wintypes.HANDLE,
                                 wintypes.DWORD, wintypes.LPCWSTR]

    path_buf = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
    return path_buf.value


def _windows_config_path():
    common_data = _windows_commondata_path()
    path = os.path.join(common_data, 'Datadog', AGENT_CONF)
    if os.path.exists(path):
        return path
    raise PathNotFound(path)


def _windows_confd_path():
    common_data = _windows_commondata_path()
    path = os.path.join(common_data, 'Datadog', 'conf.d')
    if os.path.exists(path):
        return path
    raise PathNotFound(path)


def _windows_checksd_path():
    if hasattr(sys, 'frozen'):
        # we're frozen - from py2exe
        prog_path = os.path.dirname(sys.executable)
        checksd_path = os.path.join(prog_path, '..', 'checks_d')
    else:

        cur_path = os.path.dirname(__file__)
        checksd_path = os.path.join(cur_path, '../collector/checks_d')

    if os.path.exists(checksd_path):
        return checksd_path
    raise PathNotFound(checksd_path)


def _unix_config_path():
    path = os.path.join(DEFAULT_CONFIG_DIR, AGENT_CONF)
    if os.path.exists(path):
        return path
    elif os.path.exists('./%s' % AGENT_CONF):
        return './%s' % AGENT_CONF
    raise PathNotFound(path)


def _unix_confd_path():
    path = os.path.join(DEFAULT_CONFIG_DIR, 'conf.d')
    if os.path.exists(path):
        return path
    raise PathNotFound(path)


def _unix_checksd_path():
    # Unix only will look up based on the current directory
    # because checks_d will hang with the other python modules
    cur_path = os.path.dirname(os.path.realpath(__file__))
    checksd_path = os.path.join(cur_path, '../collector/checks_d')

    if os.path.exists(checksd_path):
        return checksd_path
    raise PathNotFound(checksd_path)


def _is_affirmative(s):
    return s.lower() in ('yes', 'true', '1')


def get_config_path(cfg_path=None, os_name=None):
    # Check if there's an override and if it exists
    if cfg_path is not None and os.path.exists(cfg_path):
        return cfg_path

    if os_name is None:
        os_name = get_os()

    # Check for an OS-specific path, continue on not-found exceptions
    bad_path = ''
    if os_name == 'windows':
        try:
            return _windows_config_path()
        except PathNotFound as e:
            if len(e.args) > 0:
                bad_path = e.args[0]
    else:
        try:
            return _unix_config_path()
        except PathNotFound as e:
            if len(e.args) > 0:
                bad_path = e.args[0]

    # Check if there's a config stored in the current agent directory
    path = os.path.realpath(__file__)
    path = os.path.dirname(path)
    if os.path.exists(os.path.join(path, AGENT_CONF)):
        return os.path.join(path, AGENT_CONF)

    # If all searches fail, exit the agent with an error
    sys.stderr.write(
        "Please supply a configuration file at %s or in the directory where the Agent is currently deployed.\n" %
        bad_path)
    sys.exit(3)


def get_config(parse_args=True, cfg_path=None, options=None):
    if parse_args:
        options, _ = get_parsed_args()

    # General config
    agent_config = {
        'check_freq': DEFAULT_CHECK_FREQUENCY,
        'monstatsd_interval': DEFAULT_STATSD_FREQUENCY,
        'monstatsd_agregator_bucket_size': DEFAULT_STATSD_BUCKET_SIZE,
        'monstatsd_normalize': 'yes',
        'monstatsd_port': 8125,
        'forwarder_url': 'http://localhost:17123',
        'hostname': None,
        'listen_port': None,
        'version': get_version(),
        'watchdog': True,
        'additional_checksd': DEFAULT_CONFIG_DIR + '/checks_d/',
    }

    monstatsd_interval = DEFAULT_STATSD_FREQUENCY
    monstatsd_agregator_bucket_size = DEFAULT_STATSD_BUCKET_SIZE

    # Config handling
    try:
        # Find the right config file
        path = os.path.realpath(__file__)
        path = os.path.dirname(path)

        config_path = get_config_path(cfg_path, os_name=get_os())
        config = ConfigParser.ConfigParser()
        config.readfp(skip_leading_wsp(open(config_path)))

        # bulk import
        for option in config.options('Main'):
            agent_config[option] = config.get('Main', option)

        #
        # Core config
        #

        # FIXME unnecessarily complex

        # Extra checks_d path
        # the linux directory is set by default
        if config.has_option('Main', 'additional_checksd'):
            agent_config['additional_checksd'] = config.get('Main', 'additional_checksd')
        elif get_os() == 'windows':
            # default windows location
            common_path = _windows_commondata_path()
            agent_config['additional_checksd'] = os.path.join(common_path, 'Datadog', 'checks_d')

        # Concerns only Windows
        if config.has_option('Main', 'use_web_info_page'):
            agent_config['use_web_info_page'] = config.get(
                'Main', 'use_web_info_page').lower() in ("yes", "true")
        else:
            agent_config['use_web_info_page'] = True

        # local traffic only? Default to no
        agent_config['non_local_traffic'] = False
        if config.has_option('Main', 'non_local_traffic'):
            agent_config['non_local_traffic'] = config.get(
                'Main', 'non_local_traffic').lower() in ("yes", "true")

        if config.has_option('Main', 'check_freq'):
            try:
                agent_config['check_freq'] = int(config.get('Main', 'check_freq'))
            except Exception:
                pass

        # Disable Watchdog (optionally)
        if config.has_option('Main', 'watchdog'):
            if config.get('Main', 'watchdog').lower() in ('no', 'false'):
                agent_config['watchdog'] = False

        # monstatsd config
        monstatsd_defaults = {
            'monstatsd_port': 8125,
            'monstatsd_interval': monstatsd_interval,
            'monstatsd_agregator_bucket_size': monstatsd_agregator_bucket_size,
            'monstatsd_normalize': 'yes',
        }
        for key, value in monstatsd_defaults.iteritems():
            if config.has_option('Main', key):
                agent_config[key] = config.get('Main', key)
            else:
                agent_config[key] = value

        # Forwarding to external statsd server
        if config.has_option('Main', 'statsd_forward_host'):
            agent_config['statsd_forward_host'] = config.get('Main', 'statsd_forward_host')
            if config.has_option('Main', 'statsd_forward_port'):
                agent_config['statsd_forward_port'] = int(config.get('Main', 'statsd_forward_port'))

        # normalize 'yes'/'no' to boolean
        monstatsd_defaults['monstatsd_normalize'] = _is_affirmative(
            monstatsd_defaults['monstatsd_normalize'])

        # Optional config
        # FIXME not the prettiest code ever...
        if config.has_option('Main', 'use_mount'):
            agent_config['use_mount'] = _is_affirmative(config.get('Main', 'use_mount'))

        if config.has_option('Main', 'autorestart'):
            agent_config['autorestart'] = _is_affirmative(config.get('Main', 'autorestart'))

        try:
            filter_device_re = config.get('Main', 'device_blacklist_re')
            agent_config['device_blacklist_re'] = re.compile(filter_device_re)
        except ConfigParser.NoOptionError:
            pass

        if config.has_option('datadog', 'ddforwarder_log'):
            agent_config['has_datadog'] = True

        # Dogstream config
        if config.has_option("Main", "dogstream_log"):
            # Older version, single log support
            log_path = config.get("Main", "dogstream_log")
            if config.has_option("Main", "dogstream_line_parser"):
                agent_config["dogstreams"] = ':'.join(
                    [log_path, config.get("Main", "dogstream_line_parser")])
            else:
                agent_config["dogstreams"] = log_path

        elif config.has_option("Main", "dogstreams"):
            agent_config["dogstreams"] = config.get("Main", "dogstreams")

        if config.has_option("Main", "nagios_perf_cfg"):
            agent_config["nagios_perf_cfg"] = config.get("Main", "nagios_perf_cfg")

        if config.has_section('WMI'):
            agent_config['WMI'] = {}
            for key, value in config.items('WMI'):
                agent_config['WMI'][key] = value

        if config.has_option("Main", "limit_memory_consumption") and \
                config.get("Main", "limit_memory_consumption") is not None:
            agent_config["limit_memory_consumption"] = int(
                config.get("Main", "limit_memory_consumption"))
        else:
            agent_config["limit_memory_consumption"] = None

        if config.has_option("Main", "skip_ssl_validation"):
            agent_config["skip_ssl_validation"] = _is_affirmative(
                config.get("Main", "skip_ssl_validation"))

        agent_config['Api'] = get_mon_api_config(config)

    except ConfigParser.NoSectionError as e:
        sys.stderr.write('Config file not found or incorrectly formatted.\n')
        sys.exit(2)

    except ConfigParser.ParsingError as e:
        sys.stderr.write('Config file not found or incorrectly formatted.\n')
        sys.exit(2)

    except ConfigParser.NoOptionError as e:
        sys.stderr.write(
            'There are some items missing from your config file, but nothing fatal [%s]' % e)

    # Storing proxy settings in the agent_config
    agent_config['proxy_settings'] = get_proxy(agent_config)

    return agent_config


def set_win32_cert_path():
    """In order to use tornado.httpclient with the packaged .exe on Windows we
    need to override the default ceritifcate location which is based on the path
    to tornado and will give something like "C:\path\to\program.exe\tornado/cert-file".

    If pull request #379 is accepted (https://github.com/facebook/tornado/pull/379) we
    will be able to override this in a clean way. For now, we have to monkey patch
    tornado.httpclient._DEFAULT_CA_CERTS
    """
    if hasattr(sys, 'frozen'):
        # we're frozen - from py2exe
        prog_path = os.path.dirname(sys.executable)
        crt_path = os.path.join(prog_path, 'ca-certificates.crt')
    else:
        cur_path = os.path.dirname(__file__)
        crt_path = os.path.join(cur_path, 'packaging', 'monasca-agent', 'win32',
                                'install_files', 'ca-certificates.crt')
    import tornado.simple_httpclient
    log.info("Windows certificate path: %s" % crt_path)
    tornado.simple_httpclient._DEFAULT_CA_CERTS = crt_path


def get_proxy(agent_config, use_system_settings=False):
    proxy_settings = {}

    # First we read the proxy configuration from agent.conf
    proxy_host = agent_config.get('proxy_host', None)
    if proxy_host is not None and not use_system_settings:
        proxy_settings['host'] = proxy_host
        try:
            proxy_settings['port'] = int(agent_config.get('proxy_port', 3128))
        except ValueError:
            log.error('Proxy port must be an Integer. Defaulting it to 3128')
            proxy_settings['port'] = 3128

        proxy_settings['user'] = agent_config.get('proxy_user', None)
        proxy_settings['password'] = agent_config.get('proxy_password', None)
        proxy_settings['system_settings'] = False
        log.debug("Proxy Settings: %s:%s@%s:%s" %
                  (proxy_settings['user'], "*****", proxy_settings['host'], proxy_settings['port']))
        return proxy_settings

    # If no proxy configuration was specified in agent.conf
    # We try to read it from the system settings
    try:
        import urllib
        proxies = urllib.getproxies()
        proxy = proxies.get('https', None)
        if proxy is not None:
            try:
                proxy = proxy.split('://')[1]
            except Exception:
                pass
            px = proxy.split(':')
            proxy_settings['host'] = px[0]
            proxy_settings['port'] = px[1]
            proxy_settings['user'] = None
            proxy_settings['password'] = None
            proxy_settings['system_settings'] = True
            if '@' in proxy_settings['host']:
                creds = proxy_settings['host'].split('@')[0].split(':')
                proxy_settings['user'] = creds[0]
                if len(creds) == 2:
                    proxy_settings['password'] = creds[1]

            log.debug("Proxy Settings: %s:%s@%s:%s" % (
                proxy_settings['user'], "*****", proxy_settings['host'], proxy_settings['port']))
            return proxy_settings

    except Exception as e:
        log.debug(
            "Error while trying to fetch proxy settings using urllib %s. Proxy is probably not set" %
            str(e))

    log.debug("No proxy configured")

    return None


def get_confd_path(osname):
    bad_path = ''
    if osname == 'windows':
        try:
            return _windows_confd_path()
        except PathNotFound as e:
            if len(e.args) > 0:
                bad_path = e.args[0]
    else:
        try:
            return _unix_confd_path()
        except PathNotFound as e:
            if len(e.args) > 0:
                bad_path = e.args[0]

    cur_path = os.path.dirname(os.path.realpath(__file__))
    cur_path = os.path.join(cur_path, 'conf.d')

    if os.path.exists(cur_path):
        return cur_path

    raise PathNotFound(bad_path)


def get_checksd_path(osname):
    if osname == 'windows':
        return _windows_checksd_path()
    else:
        return _unix_checksd_path()


def get_win32service_file(osname, filename):
    # This file is needed to log in the event viewer for windows
    if osname == 'windows':
        if hasattr(sys, 'frozen'):
            # we're frozen - from py2exe
            prog_path = os.path.dirname(sys.executable)
            path = os.path.join(prog_path, filename)
        else:
            cur_path = os.path.dirname(__file__)
            path = os.path.join(cur_path, filename)
        if os.path.exists(path):
            log.debug("Certificate file found at %s" % str(path))
            return path

    else:
        cur_path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(cur_path, filename)
        if os.path.exists(path):
            return path

    return None


def check_yaml(conf_path):
    f = open(conf_path)
    try:
        check_config = yaml.load(f.read(), Loader=Loader)
        assert 'init_config' in check_config, "No 'init_config' section found"
        assert 'instances' in check_config, "No 'instances' section found"

        valid_instances = True
        if check_config['instances'] is None or not isinstance(check_config['instances'], list):
            valid_instances = False
        else:
            for i in check_config['instances']:
                if not isinstance(i, dict):
                    valid_instances = False
                    break
        if not valid_instances:
            raise Exception(
                'You need to have at least one instance defined in the YAML file for this check')
        else:
            return check_config
    finally:
        f.close()


def load_check_directory(agent_config):
    ''' Return the initialized checks from checks_d, and a mapping of checks that failed to
    initialize. Only checks that have a configuration
    file in conf.d will be returned. '''
    from monagent.collector.checks import AgentCheck

    initialized_checks = {}
    init_failed_checks = {}

    osname = get_os()
    checks_paths = [glob.glob(os.path.join(agent_config['additional_checksd'], '*.py'))]

    try:
        checksd_path = get_checksd_path(osname)
        checks_paths.append(glob.glob(os.path.join(checksd_path, '*.py')))
    except PathNotFound as e:
        log.error(e.args[0])
        sys.exit(3)

    try:
        confd_path = get_confd_path(osname)
    except PathNotFound as e:
        log.error(
            "No conf.d folder found at '%s' or in the directory where the Agent is currently deployed.\n" %
            e.args[0])
        sys.exit(3)

    # Start JMXFetch if needed
    JMXFetch.init(confd_path, agent_config, get_logging_config(),
                  DEFAULT_CHECK_FREQUENCY, JMX_COLLECT_COMMAND)

    # For backwards-compatability with old style checks, we have to load every
    # checks_d module and check for a corresponding config OR check if the old
    # config will "activate" the check.
    #
    # Once old-style checks aren't supported, we'll just read the configs and
    # import the corresponding check module
    for check in itertools.chain(*checks_paths):
        check_name = os.path.basename(check).split('.')[0]
        if check_name in initialized_checks or check_name in init_failed_checks:
            log.debug(
                'Skipping check %s because it has already been loaded from another location', check)
            continue
        try:
            check_module = imp.load_source('checksd_%s' % check_name, check)
        except Exception as e:
            traceback_message = traceback.format_exc()

            # Let's see if there is a conf.d for this check
            conf_path = os.path.join(confd_path, '%s.yaml' % check_name)
            if os.path.exists(conf_path):
                # There is a configuration file for that check but the module can't be imported
                init_failed_checks[check_name] = {'error': e, 'traceback': traceback_message}
                log.exception('Unable to import check module %s.py from checks_d' % check_name)
            else:  # There is no conf for that check. Let's not spam the logs for it.
                log.debug('Unable to import check module %s.py from checks_d' % check_name)
            continue

        check_class = None
        classes = inspect.getmembers(check_module, inspect.isclass)
        for _, clsmember in classes:
            if clsmember == AgentCheck:
                continue
            if issubclass(clsmember, AgentCheck):
                check_class = clsmember
                if AgentCheck in clsmember.__bases__:
                    continue
                else:
                    break

        if not check_class:
            log.error('No check class (inheriting from AgentCheck) found in %s.py' % check_name)
            continue

        # Check if the config exists OR we match the old-style config
        conf_path = os.path.join(confd_path, '%s.yaml' % check_name)
        if os.path.exists(conf_path):
            try:
                check_config = check_yaml(conf_path)
            except Exception as e:
                log.exception("Unable to parse yaml config in %s" % conf_path)
                traceback_message = traceback.format_exc()
                init_failed_checks[check_name] = {'error': e, 'traceback': traceback_message}
                continue
        elif hasattr(check_class, 'parse_agent_config'):
            # FIXME: Remove this check once all old-style checks are gone
            try:
                check_config = check_class.parse_agent_config(agent_config)
            except Exception as e:
                continue
            if not check_config:
                continue
            d = [
                "Configuring %s in agent.conf is deprecated." % (check_name),
                "Please use conf.d. In a future release, support for the",
                "old style of configuration will be dropped.",
            ]
            log.warn(" ".join(d))

        else:
            log.debug('No conf.d/%s.yaml found for checks_d/%s.py' % (check_name, check_name))
            continue

        # Look for the per-check config, which *must* exist
        if not check_config.get('instances'):
            log.error("Config %s is missing 'instances'" % conf_path)
            continue

        # Init all of the check's classes with
        init_config = check_config.get('init_config', {})
        # init_config: in the configuration triggers init_config to be defined
        # to None.
        if init_config is None:
            init_config = {}

        instances = check_config['instances']
        try:
            try:
                c = check_class(check_name, init_config=init_config,
                                agent_config=agent_config, instances=instances)
            except TypeError as e:
                # Backwards compatibility for checks which don't support the
                # instances argument in the constructor.
                c = check_class(check_name, init_config=init_config,
                                agent_config=agent_config)
                c.instances = instances
        except Exception as e:
            log.exception('Unable to initialize check %s' % check_name)
            traceback_message = traceback.format_exc()
            init_failed_checks[check_name] = {'error': e, 'traceback': traceback_message}
        else:
            initialized_checks[check_name] = c

        # Add custom pythonpath(s) if available
        if 'pythonpath' in check_config:
            pythonpath = check_config['pythonpath']
            if not isinstance(pythonpath, list):
                pythonpath = [pythonpath]
            sys.path.extend(pythonpath)

        log.debug('Loaded check.d/%s.py' % check_name)

    log.info('initialized checks_d checks: %s' % initialized_checks.keys())
    log.info('initialization failed checks_d checks: %s' % init_failed_checks.keys())
    return {'initialized_checks': initialized_checks.values(),
            'init_failed_checks': init_failed_checks,
            }


#
# logging

def get_log_date_format():
    return "%Y-%m-%d %H:%M:%S %Z"


def get_log_format(logger_name):
    if get_os() != 'windows':
        return '%%(asctime)s | %%(levelname)s | %s | %%(name)s(%%(filename)s:%%(lineno)s) | %%(message)s' % logger_name
    return '%(asctime)s | %(levelname)s | %(name)s(%(filename)s:%(lineno)s) | %(message)s'


def get_syslog_format(logger_name):
    return '%s[%%(process)d]: %%(levelname)s (%%(filename)s:%%(lineno)s): %%(message)s' % logger_name


def get_logging_config(cfg_path=None):
    system_os = get_os()
    if system_os != 'windows':
        logging_config = {
            'log_level': None,
            'collector_log_file': DEFAULT_LOG_DIR + '/collector.log',
            'forwarder_log_file': DEFAULT_LOG_DIR + '/forwarder.log',
            'monstatsd_log_file': DEFAULT_LOG_DIR + '/monstatsd.log',
            'jmxfetch_log_file': DEFAULT_LOG_DIR + '/jmxfetch.log',
            'log_to_event_viewer': False,
            'log_to_syslog': True,
            'syslog_host': None,
            'syslog_port': None,
        }
    else:
        windows_log_location = os.path.join(_windows_commondata_path(), 'Mon', 'logs', 'agent.log')
        jmxfetch_log_file = os.path.join(_windows_commondata_path(), 'Mon', 'logs', 'jmxfetch.log')
        logging_config = {
            'log_level': None,
            'agent_log_file': windows_log_location,
            'jmxfetch_log_file': jmxfetch_log_file,
            'log_to_event_viewer': False,
            'log_to_syslog': False,
            'syslog_host': None,
            'syslog_port': None,
        }

    config_path = get_config_path(cfg_path, os_name=system_os)
    config = ConfigParser.ConfigParser()
    config.readfp(skip_leading_wsp(open(config_path)))

    if config.has_section('handlers') or config.has_section(
            'loggers') or config.has_section('formatters'):
        if system_os == 'windows':
            config_example_file = "https://github.com/DataDog/dd-agent/blob/master/packaging/datadog-agent/win32/install_files/datadog_win32.conf"
        else:
            config_example_file = "https://github.com/DataDog/dd-agent/blob/master/datadog.conf.example"

        sys.stderr.write("""Python logging config is no longer supported and will be ignored.
            To configure logging, update the logging portion of 'agent.conf' to match:
             '%s'.
             """ % config_example_file)

    for option in logging_config:
        if config.has_option('Main', option):
            logging_config[option] = config.get('Main', option)

    levels = {
        'CRITICAL': logging.CRITICAL,
        'DEBUG': logging.DEBUG,
        'ERROR': logging.ERROR,
        'FATAL': logging.FATAL,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'WARNING': logging.WARNING,
    }
    if config.has_option('Main', 'log_level'):
        logging_config['log_level'] = levels.get(config.get('Main', 'log_level'))

    if config.has_option('Main', 'log_to_syslog'):
        logging_config['log_to_syslog'] = config.get(
            'Main', 'log_to_syslog').strip().lower() in ['yes', 'true', 1]

    if config.has_option('Main', 'log_to_event_viewer'):
        logging_config['log_to_event_viewer'] = config.get(
            'Main', 'log_to_event_viewer').strip().lower() in ['yes', 'true', 1]

    if config.has_option('Main', 'syslog_host'):
        host = config.get('Main', 'syslog_host').strip()
        if host:
            logging_config['syslog_host'] = host
        else:
            logging_config['syslog_host'] = None

    if config.has_option('Main', 'syslog_port'):
        port = config.get('Main', 'syslog_port').strip()
        try:
            logging_config['syslog_port'] = int(port)
        except Exception:
            logging_config['syslog_port'] = None

    if config.has_option('Main', 'disable_file_logging'):
        logging_config['disable_file_logging'] = config.get(
            'Main', 'disable_file_logging').strip().lower() in ['yes', 'true', 1]
    else:
        logging_config['disable_file_logging'] = False

    return logging_config


def initialize_logging(logger_name):
    global windows_file_handler_added
    try:
        logging_config = get_logging_config()

        logging.basicConfig(
            format=get_log_format(logger_name),
            level=logging_config['log_level'] or logging.INFO,
        )

        # set up file loggers
        if get_os() == 'windows' and not windows_file_handler_added:
            logger_name = 'agent'
            windows_file_handler_added = True

        log_file = logging_config.get('%s_log_file' % logger_name)
        if log_file is not None and not logging_config['disable_file_logging']:
            # make sure the log directory is writeable
            # NOTE: the entire directory needs to be writable so that rotation works
            if os.access(os.path.dirname(log_file), os.R_OK | os.W_OK):
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=LOGGING_MAX_BYTES, backupCount=1)
                formatter = logging.Formatter(get_log_format(logger_name), get_log_date_format())
                file_handler.setFormatter(formatter)

                root_log = logging.getLogger()
                root_log.addHandler(file_handler)
            else:
                sys.stderr.write("Log file is unwritable: '%s'\n" % log_file)

        # set up syslog
        if logging_config['log_to_syslog']:
            try:
                from logging.handlers import SysLogHandler

                if logging_config['syslog_host'] is not None and logging_config[
                        'syslog_port'] is not None:
                    sys_log_addr = (logging_config['syslog_host'], logging_config['syslog_port'])
                else:
                    sys_log_addr = "/dev/log"
                    # Special-case macs
                    if sys.platform == 'darwin':
                        sys_log_addr = "/var/run/syslog"

                handler = SysLogHandler(address=sys_log_addr, facility=SysLogHandler.LOG_DAEMON)
                handler.setFormatter(
                    logging.Formatter(get_syslog_format(logger_name), get_log_date_format()))
                root_log = logging.getLogger()
                root_log.addHandler(handler)
            except Exception as e:
                sys.stderr.write("Error setting up syslog: '%s'\n" % str(e))
                traceback.print_exc()

        # Setting up logging in the event viewer for windows
        if get_os() == 'windows' and logging_config['log_to_event_viewer']:
            try:
                from logging.handlers import NTEventLogHandler
                nt_event_handler = NTEventLogHandler(
                    logger_name,
                    get_win32service_file(
                        'windows',
                        'win32service.pyd'),
                    'Application')
                nt_event_handler.setFormatter(
                    logging.Formatter(get_syslog_format(logger_name), get_log_date_format()))
                nt_event_handler.setLevel(logging.ERROR)
                app_log = logging.getLogger(logger_name)
                app_log.addHandler(nt_event_handler)
            except Exception as e:
                sys.stderr.write("Error setting up Event viewer logging: '%s'\n" % str(e))
                traceback.print_exc()

    except Exception as e:
        sys.stderr.write("Couldn't initialize logging: %s\n" % str(e))
        traceback.print_exc()

        # if config fails entirely, enable basic stdout logging as a fallback
        logging.basicConfig(
            format=get_log_format(logger_name),
            level=logging.INFO,
        )

    # re-get the log after logging is initialized
    global log
    log = logging.getLogger(__name__)


def get_mon_api_config(config):
    mon_api_config = {'is_enabled': False,
                      'url': '',
                      'project_name': '',
                      'username': '',
                      'password': False,
                      'use_keystone': True,
                      'keystone_url': '',
                      'dimensions': None,
                      'max_buffer_size': 1000,
                      'backlog_send_rate': 5}

    if config.has_option("Main", "dimensions"):
        # parse comma separated dimensions into a dimension list
        try:
            dim_list = [dim.split(':') for dim in config.get('Main', 'dimensions').split(',')]
            mon_api_config['dimensions'] = {key.strip(): value.strip() for key, value in dim_list}
        except ValueError:
            mon_api_config['dimensions'] = {}

    if config.has_section("Api"):
        options = {"url": config.get,
                   "project_name": config.get,
                   "username": config.get,
                   "password": config.get,
                   "use_keystone": config.getboolean,
                   "keystone_url": config.get,
                   "max_buffer_size": config.getint,
                   "backlog_send_rate": config.getint}

        for name, func in options.iteritems():
            if config.has_option("Api", name):
                mon_api_config[name] = func("Api", name)

    return mon_api_config
