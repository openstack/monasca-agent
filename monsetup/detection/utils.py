""" Util functions to assist in detection.
"""
import psutil

from monsetup import agent_config


def find_process_cmdline(search_string):
    """Simple function to search running process for one with cmdline containing
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


def watch_process(search_strings, service=None):
    """Takes a list of process search strings and returns a Plugins object with the config set.
        This was built as a helper as many plugins setup process watching
    """
    config = agent_config.Plugins()
    parameters = {'name': search_strings[0],
                  'search_string': search_strings}

    # If service parameter is set in the plugin config, add the service dimension which
    # will override the service in the agent config
    if service:
        parameters['dimensions'] = {'service': service}

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


def service_api_check(name, url, pattern, service=None):
    """Setup a service api to be watched by the http_check plugin."""
    config = agent_config.Plugins()
    parameters = {'name': name,
                  'url': url,
                  'match_pattern': pattern,
                  'timeout': 10,
                  'use_keystone': True}

    # If service parameter is set in the plugin config, add the service dimension which
    # will override the service in the agent config
    if service:
        parameters['dimensions'] = {'service': service}

    config['http_check'] = {'init_config': None,
                            'instances': [parameters]}

    return config
