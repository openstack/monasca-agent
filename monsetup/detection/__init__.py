"""Classes and utilities for detection of running resources to be monitored.
    Detection classes should be platform independent
"""
import psutil

from monsetup import agent_config


class Plugin(object):
    """Abstract class implemented by the mon-agent plugin detection classes
    """
    # todo these should include dependency detection

    def __init__(self, template_dir, overwrite=True):
        self.available = False
        self.template_dir = template_dir
        self.dependencies = ()
        self.overwrite = overwrite
        self._detect()

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        raise NotImplementedError

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        raise NotImplementedError

    def dependencies_installed(self):
        """return True if dependencies are installed
        """
        raise NotImplementedError

    @property
    def name(self):
        """Return _name if set otherwise the class name"""
        if '_name' in self.__dict__:
            return self._name
        else:
            return self.__class__.__name__


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


def watch_process(search_strings):
    """Takes a list of process search strings and returns a Plugins object with the config set.
        This was built as a helper as many plugins setup process watching
    """
    config = agent_config.Plugins()
    config['process'] = {'init_config': None,
                         'instances': [{'name': search_strings[0], 'search_string': search_strings}]}
    return config

def service_api_check(name, url, pattern):
    """Setup a service api to be watched by the http_check plugin."""
    config = agent_config.Plugins()
    config['http_check'] = {'init_config': None,
                            'instances': [{'name': name,
                                           'url': url,
                                           'match_pattern': pattern,
                                           'timeout': 10,
                                           'use_keystone': True}]}
    return config
