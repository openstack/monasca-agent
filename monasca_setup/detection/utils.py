# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 SUSE Linux GmbH
# Copyright 2017 OP5 AB

""" Util functions to assist in detection.
"""
import argparse
import logging
import os
import pwd
import subprocess
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen

from oslo_config import cfg

from monasca_agent.common.psutil_wrapper import psutil
from monasca_setup import agent_config

log = logging.getLogger(__name__)

_DEFAULT_AGENT_USER = 'mon-agent'
_DETECTED_AGENT_USER = None

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
    """Simple function to search running process for one with cmdline
    containing search_string.
    """
    for process in psutil.process_iter():
        try:
            process_cmdline = ' '.join(process.as_dict(['cmdline'])['cmdline'])
            if (search_string in process_cmdline and
               'monasca-setup' not in process_cmdline):
                return process
        except psutil.NoSuchProcess:
            continue

    return None


def find_process_name(pname):
    """Simple function to search running process for one with pname.
    """
    for process in psutil.process_iter():
        try:
            if pname == process.as_dict(['name'])['name']:
                return process
        except psutil.NoSuchProcess:
            continue

    return None


def find_process_service(sname):
    """Simple function to call systemctl (service) to check if a service is running.
    """
    try:
        subprocess.check_call(['service', sname, 'status'], stdout=PIPE, stderr=PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

    return False


def find_addrs_listening_on_port(port, kind='inet'):
    """Return the list of IP addresses which are listening
    on the specified port.
    """
    listening = []
    for connection in psutil.net_connections(kind):
        if (connection.status == psutil.CONN_LISTEN and
                connection.laddr[1] == int(port)):
            listening.append(connection.laddr[0])
    return listening


def find_addr_listening_on_port_over_tcp(port):
    """Return the IP address which is listening on the specified TCP port."""
    ip = find_addrs_listening_on_port(port, 'tcp')
    if ip:
        return ip[0].lstrip("::ffff:")


def get_agent_username():
    """Determine the user monasca-agent runs as"""

    global _DETECTED_AGENT_USER

    # Use cached agent user in subsequent calls
    if _DETECTED_AGENT_USER is not None:
        return _DETECTED_AGENT_USER

    # Try the owner of agent.yaml first
    try:
        uid = os.stat('/etc/monasca/agent/agent.yaml').st_uid
    except OSError:
        uid = None

    if uid is not None:
        _DETECTED_AGENT_USER = pwd.getpwuid(uid).pw_name
        return _DETECTED_AGENT_USER

    # No agent.yaml, so try to find a running monasca-agent process
    agent_process = find_process_name('monasca-agent')

    if agent_process is not None:
        _DETECTED_AGENT_USER = agent_process.username()
        return _DETECTED_AGENT_USER

    # Fall back to static agent user
    log.warn("Could not determine monasca-agent service user, falling "
             "back to %s" % _DEFAULT_AGENT_USER)
    _DETECTED_AGENT_USER = _DEFAULT_AGENT_USER
    return _DETECTED_AGENT_USER


def load_oslo_configuration(from_cmd, in_project,
                            for_opts, of_prog=None):
    """Loads configuration of an OpenStack project.

    for_opts should be a :py:class:`list` containing dictionaries
    with keys as expected by :py:class:meth:`cfg.ConfigOpts.register_opt`::

        >>> for_opts = [
        >>>     {'opt': cfg.StrOpt('region_name')},
        >>>     {'opt': cfg.StrOpt('username'), 'group': 'keystoneauth'},
        >>>     {'opt': cfg.StrOpt('password'), 'group': 'keystoneauth'},
        >>> ]

    Example::

        >>> nova_proc = find_process_name('nova-compute')
        >>> proc_cmd = nova_proc.as_dict(['cmdline'])['cmdline']
        >>> load_oslo_configuration(
        >>>     from_cmd=proc_cmd,
        >>>     in_project='nova',
        >>>     for_opts=for_opts
        >>> )

    which will load three [region_name, username and password] settings from
    Nova configuration regardless of where those
    settings are actually defined.

    :param from_cmd: cmdline of a process, used also to retrieve arguments
    :type from_cmd: list[basestring]
    :param in_project: the project name as defined in its oslo setup
    :type in_project: basestring
    :param for_opts: list of dict containing options to look for inside config
    :type for_opts: list[dict]
    :param of_prog: program name within the project [optional]
    :type of_prog: basestring
    :return: oslo configuration object
    :rtype: oslo_config.cfg.CONF
    """

    conf_holder = cfg.ConfigOpts()
    for no in for_opts:
        conf_holder.register_opt(**no)

    # NOTE(trebskit) we need to remove everything from the beginning
    # of the cmd arg list that is not an argument of the application
    # we want to get configuration from, i.e.;
    # /usr/bin/python, /usr/bin/python3
    # and next actual binary of the program
    # /usr/local/bin/nova-compute
    # NOTE(tobiajo) Just keep built-in options for oslo.config
    args = []
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-file')
    parser.add_argument('--config-dir')
    namespace, _ = parser.parse_known_args(from_cmd[2:])
    if namespace.config_file:
        args.append('--config-file')
        args.append(namespace.config_file)
    if namespace.config_dir:
        args.append('--config-dir')
        args.append(namespace.config_dir)

    conf_holder(
        args=args,
        project=in_project,
        prog=of_prog
    )

    return conf_holder


def watch_process(search_strings, service=None, component=None,
                  exact_match=True, detailed=True, process_name=None, dimensions=None):
    """Takes a list of process search strings and returns a Plugins object with the config set.
        This was built as a helper as many plugins setup process watching
    """
    config = agent_config.Plugins()

    # Fallback to default process_name strategy if process_name is not defined
    process_name = process_name if process_name else search_strings[0]
    parameters = {'name': process_name,
                  'detailed': detailed,
                  'exact_match': exact_match,
                  'search_string': search_strings}

    dimensions = _get_dimensions(service, component, dimensions)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


def watch_process_by_username(username, process_name, service=None,
                              component=None, detailed=True, dimensions=None):
    """Takes a user and returns a Plugins object with the config set for a process check by user.
        This was built as a helper as many plugins setup process watching.
    """
    config = agent_config.Plugins()

    parameters = {'name': process_name,
                  'detailed': detailed,
                  'username': username}

    dimensions = _get_dimensions(service, component, dimensions)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


def watch_file_size(directory_name, file_names, file_recursive=False,
                    service=None, component=None, dimensions=None):
    """Takes a directory, a list of files, recursive flag and returns a
        Plugins object with the config set.
    """
    config = agent_config.Plugins()
    parameters = {'directory_name': directory_name,
                  'file_names': file_names,
                  'recursive': file_recursive}

    dimensions = _get_dimensions(service, component, dimensions)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['file_size'] = {'init_config': None,
                           'instances': [parameters]}
    return config


def watch_directory(directory_name, service=None, component=None, dimensions=None):
    """Takes a directory name and returns a Plugins object with the config set.
    """
    config = agent_config.Plugins()
    parameters = {'directory': directory_name}

    dimensions = _get_dimensions(service, component, dimensions)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['directory'] = {'init_config': None,
                           'instances': [parameters]}
    return config


def service_api_check(name, url, pattern, use_keystone=True,
                      service=None, component=None, dimensions=None):
    """Setup a service api to be watched by the http_check plugin.
    """
    config = agent_config.Plugins()
    parameters = {'name': name,
                  'url': url,
                  'match_pattern': pattern,
                  'timeout': 10,
                  'use_keystone': use_keystone}

    dimensions = _get_dimensions(service, component, dimensions)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['http_check'] = {'init_config': None,
                            'instances': [parameters]}
    return config


def _get_dimensions(service, component, dimensions=None):
    if dimensions is None:
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
