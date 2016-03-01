# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

""" Util functions to assist in detection.
"""
import logging
import subprocess
from subprocess import CalledProcessError
from subprocess import PIPE
from subprocess import Popen

import psutil

from monasca_setup import agent_config

log = logging.getLogger(__name__)


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
        try:
            if search_string in ' '.join(process.cmdline()):
                return process
        except psutil.NoSuchProcess:
            continue

    return None


def find_process_name(pname):
    """Simple function to search running process for one with pname.
    """
    for process in psutil.process_iter():
        try:
            if pname == process.name():
                return process
        except psutil.NoSuchProcess:
            continue

    return None


def find_addr_listening_on_port(port):
    """Return the IP address which is listening on the specified TCP port."""
    for conn in psutil.net_connections(kind='tcp'):
        if conn.laddr[1] == port and conn.status == psutil.CONN_LISTEN:
            return conn.laddr[0].lstrip("::ffff:")


def watch_process(search_strings, service=None, component=None,
                  exact_match=True, detailed=True, process_name=None):
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

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


def watch_process_by_username(username, process_name, service=None, component=None, detailed=True):
    """Takes a user and returns a Plugins object with the config set for a process check by user.
        This was built as a helper as many plugins setup process watching.
    """
    config = agent_config.Plugins()

    parameters = {'name': process_name,
                  'detailed': detailed,
                  'username': username}

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


def watch_file_size(directory_name, file_names, file_recursive,
                    service=None, component=None):
    """Takes a directory, a list of files, recursive flag and returns a
        Plugins object with the config set.
    """
    config = agent_config.Plugins()
    parameters = {'directory_name': directory_name,
                  'file_names': file_names,
                  'recursive': file_recursive}

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['file_size'] = {'init_config': None,
                           'instances': [parameters]}
    return config


def watch_directory(directory_name, service=None, component=None):
    """Takes a directory name and returns a Plugins object with the config set.
    """
    config = agent_config.Plugins()
    parameters = {'directory': directory_name}

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['directory'] = {'init_config': None,
                           'instances': [parameters]}
    return config


def service_api_check(name, url, pattern,
                      use_keystone=True, service=None, component=None):
    """Setup a service api to be watched by the http_check plugin.
    """
    config = agent_config.Plugins()
    parameters = {'name': name,
                  'url': url,
                  'match_pattern': pattern,
                  'timeout': 10,
                  'use_keystone': use_keystone}

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
