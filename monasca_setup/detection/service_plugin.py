# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

import logging
import psutil
import urlparse

from plugin import Plugin

from monasca_setup import agent_config
from monasca_setup.detection.utils import find_process_cmdline
from monasca_setup.detection.utils import service_api_check
from monasca_setup.detection.utils import watch_directory
from monasca_setup.detection.utils import watch_file_size
from monasca_setup.detection.utils import watch_process

log = logging.getLogger(__name__)


class ServicePlugin(Plugin):
    """Base class implemented by the monasca-agent plugin detection classes for OpenStack Services.
        Detection plugins inheriting from this class can easily setup up processes to be watched and
        a http endpoint to be checked.

        The http check can be skipped by specifying the argument 'disable_http_check'
    """

    def __init__(self, kwargs, **kws):
        combi = dict(kwargs)
        combi.update(kws)
        self.service_name = combi['service_name']
        args = combi.get('args')
        if isinstance(args, str):
            combi.update(dict(item.split('=') for item in args.split()))

        self.process_names = ServicePlugin._get_list_arg(combi, 'process_names')
        self.file_dirs_names = combi.get('file_dirs_names') or []
        self.directory_names = ServicePlugin._get_list_arg(combi, 'directory_names')
        self.service_api_url = combi.get('service_api_url')
        self.search_pattern = combi.get('search_pattern')
        overwrite = combi['overwrite']
        template_dir = combi['template_dir'],

        super(ServicePlugin, self).__init__(template_dir, overwrite, args)

    @staticmethod
    def _get_list_arg(combi, name):
        rv = combi.get(name)
        if isinstance(rv, str):
            return rv.split(',')
        elif isinstance(rv, list):
            return rv
        elif rv is None:
            return []
        raise TypeError("{0} is not a list".format(name))

    def _detect(self):
        """Run detection.

        """
        self.found_processes = [p for p in self.process_names
                                if find_process_cmdline(p)]
        self.available = (self.found_processes or self.file_dirs_names or self.directory_names)

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()
        for process in self.found_processes:
            # Watch the service processes
            log.info("\tMonitoring the {0} {1} process.".format(process, self.service_name))
            config.merge(watch_process([process], self.service_name, process, exact_match=False))

        for file_dir_name in self.file_dirs_names:
            # Watch file size
            file_dir = file_dir_name[0]
            file_names = file_dir_name[1]
            if len(file_dir_name) == 3:
                file_recursive = file_dir_name[2]
            else:
                file_recursive = False
            if file_names == ['*']:
                log.info("\tMonitoring the size of all the files in the "
                         "directory {0}.".format(file_dir))
            else:
                log.info("\tMonitoring the size of files {0} in the "
                         "directory {1}.".format(", ".join(str(name) for name in file_names), file_dir))
            config.merge(watch_file_size(file_dir, file_names,
                                         file_recursive, self.service_name))

        for dir_name in self.directory_names:
            log.info("\tMonitoring the size of directory {0}.".format(
                dir_name))
            config.merge(watch_directory(dir_name, self.service_name))

        # Skip the http_check if disable_http_check is set
        if self.args is not None and self.args.get('disable_http_check', False):
            self.service_api_url = None
            self.search_pattern = None

        if self.service_api_url and self.search_pattern:
            log.info("\tConfiguring an http_check for the {0} API.".format(self.service_name))
            api_url = self.check_listening(self.service_api_url)
            if api_url:
                config.merge(service_api_check(self.service_name + '-api',
                                               api_url,
                                               self.search_pattern,
                                               use_keystone=True,
                                               service=self.service_name))

        return config

    def check_listening(self, endpoint):
        # Check there is something listening on the host/port
        parsed = urlparse.urlparse(self.service_api_url)
        host, port = parsed.netloc.split(':')
        listening = [c.laddr[0] for c in psutil.net_connections()
                     if c.status == psutil.CONN_LISTEN and c.laddr[1] == int(port)]
        if not listening:
            log.info("\tNo process found listening on {0} "
                     "skipping setup of http_check.".format(port))
            return None

        # If not listening on localhost or ips then use another local ip
        if host == 'localhost' and not set(['127.0.0.1', '0.0.0.0', '::', '::1']) & set(listening):
            new_url = list(parsed)
            new_url[1] = listening[0] + ':' + port
            return urlparse.urlunparse(new_url)
        else:
            return endpoint

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        return True
