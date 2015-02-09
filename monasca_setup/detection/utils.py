""" Util functions to assist in detection.
"""
import psutil
import subprocess

from monasca_setup import agent_config
from subprocess import Popen, PIPE, CalledProcessError

# check_output was introduced in python 2.7, function added
# to accommodate python 2.6
try:
    check_output = subprocess.check_output
except AttributeError:
    def check_output(*popenargs, **kwargs):
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = Popen(stdout=PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd)
        return output


def find_process_cmdline(search_string):
    """Simple function to search running process for one with cmdline containing.
    """
    for process in psutil.process_iter():
        for arg in process.cmdline():
            if arg.find(search_string) != -1:
                return process

    return None


def find_process_name(pname):
    """Simple function to search running process for one with pname.
    """
    for process in psutil.process_iter():
        if pname == process.name():
            return process

    return None


def find_addr_listening_on_port(port):
    """Return the IP address which is listening on the specified TCP port."""
    for conn in psutil.net_connections(kind='tcp'):
        if conn.laddr[1] == port and conn.status == psutil.CONN_LISTEN:
            return conn.laddr[0].lstrip("::ffff:")


def watch_process(search_strings, service=None, component=None, exact_match=True, detailed=False):
    """Takes a list of process search strings and returns a Plugins object with the config set.
        This was built as a helper as many plugins setup process watching
    """
    config = agent_config.Plugins()
    parameters = {'name': search_strings[0],
                  'detailed': detailed,
                  'exact_match': exact_match,
                  'search_string': search_strings}

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


def service_api_check(name, url, pattern, service=None, component=None):
    """Setup a service api to be watched by the http_check plugin.
    """
    config = agent_config.Plugins()
    parameters = {'name': name,
                  'url': url,
                  'match_pattern': pattern,
                  'timeout': 10,
                  'use_keystone': True}

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['http_check'] = {'init_config': None,
                            'instances': [parameters]}

    return config


def _get_dimensions(service, component):
    dimensions = {}
    # If service parameter is set in the plugin config, add the service dimension which
    # will override the service in the agent config
    if service:
        dimensions.update({'service': service})

    # If component parameter is set in the plugin config, add the component dimension which
    # will override the component in the agent config
    if component:
        dimensions.update({'component': component})

    return dimensions
