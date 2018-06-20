# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from six.moves import urllib

from monasca_setup import agent_config
from monasca_setup.detection.plugin import Plugin
from monasca_setup.detection.utils import find_addrs_listening_on_port
from monasca_setup.detection.utils import find_process_cmdline
from monasca_setup.detection.utils import service_api_check
from monasca_setup.detection.utils import watch_directory
from monasca_setup.detection.utils import watch_file_size
from monasca_setup.detection.utils import watch_process
from monasca_setup.detection.utils import watch_process_by_username


log = logging.getLogger(__name__)


class ServicePlugin(Plugin):
    """Base class implemented by the monasca-agent plugin detection classes for OpenStack Services.
    Detection plugins inheriting from this class can easily setup up processes to be watched and
    a http endpoint to be checked.

    This class covers Process, HTTP endpoints, Directory, and File monitoring.  It is primarily
    used for monitoring OpenStack components.
    Note: There are existing default detection plugins for http_check.py, directory.py, and
    file_size.py that only require configuration.

    A process can be monitored by process_names or by process_username. Pass in the process_names
    list argument when watching process by name.  Pass in the process_username argument and
    component_name arguments when watching process by username. Watching by username is useful for
    groups of processes that are owned by a specific user.
    For process monitoring by process_username the component_name is required since it is used to
    initialize the instance name in process.yaml.  component_name is optional for monitoring by
    process_name and all other checks.

    An http endpoint connection can be checked by passing in the service_api_url and optional
    search_pattern parameters.
    The http check can be skipped by specifying the argument 'disable_http_check'

    Directory size can be checked by passing in a directory_names list.

    File size can be checked by passing in a file_dirs_names list where each directory name item
    includes a list of files.
    example: 'file_dirs_names': [('/var/log/monasca/api', ['monasca-api'])]

    Note: service_name and component_name are optional (except component_name is required with
    process_username) arguments used for metric dimensions by all checks.
    """

    def __init__(self, kwargs):
        self.service_name = kwargs['service_name']
        self.process_names = kwargs.get('process_names')
        self.process_username = kwargs.get('process_username', None)
        self.component_name = kwargs.get('component_name', None)
        self.file_dirs_names = kwargs.get('file_dirs_names')
        self.directory_names = kwargs.get('directory_names')
        self.service_api_url = kwargs.get('service_api_url')
        self.search_pattern = kwargs.get('search_pattern')
        # overwrite is currently not used with this class, make optional until we remove it.
        overwrite = kwargs.get('overwrite', False)
        template_dir = kwargs['template_dir'],
        if 'args' in kwargs:
            args = kwargs['args']
            if isinstance(args, str):
                try:
                    # Turn 'service_api_url=url' into
                    # dict {'service_api_url':'url'}
                    args_dict = dict(
                        [item.split('=') for item in args.split()])
                    # Allow args to override all of these parameters
                    if 'process_names' in args_dict:
                        self.process_names = args_dict['process_names'].split(',')
                    if 'process_username' in args_dict:
                        self.process_username = args_dict['process_username']
                    if 'component_name' in args_dict:
                        self.component_name = args_dict['component_name']
                    if 'file_dirs_names' in args_dict:
                        self.file_dirs_names = args_dict['file_dirs_names']
                    if 'directory_names' in args_dict:
                        self.directory_names = args_dict['directory_names'].split(',')
                    if 'service_api_url' in args_dict:
                        self.service_api_url = args_dict['service_api_url']
                    if 'search_pattern' in args_dict:
                        self.search_pattern = args_dict['search_pattern']
                    if 'overwrite' in args_dict:
                        overwrite = args_dict['overwrite']
                    if 'template_dir' in args_dict:
                        template_dir = args_dict['template_dir']
                except Exception:
                    log.exception('Error parsing detection arguments')

        super(ServicePlugin, self).__init__(template_dir, overwrite, kwargs.get('args'))

    def _detect(self):
        """Run detection.

        """
        self.found_processes = []
        if self.process_names:
            for process in self.process_names:
                if find_process_cmdline(process) is not None:
                    self.found_processes.append(process)
            if len(self.found_processes) > 0:
                self.available = True
        if self.process_username and self.component_name:
            self.available = True
        if self.file_dirs_names:
            self.available = True
        if self.directory_names:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()
        if self.found_processes:
            log.info("\tMonitoring by process_name(s): {0} "
                     "for service: {1}.".format(",".join(self.found_processes), self.service_name))
            for process in self.found_processes:
                # Watch the service processes
                component_name = self.component_name if self.component_name else process
                config.merge(watch_process(search_strings=[process], service=self.service_name,
                                           component=component_name, exact_match=False))

        if self.process_username:
            log.info("\tMonitoring by process_username: {0} for "
                     "service: {1}.".format(self.process_username, self.service_name))
            config.merge(watch_process_by_username(username=self.process_username,
                                                   process_name=self.component_name,
                                                   service=self.service_name,
                                                   component=self.component_name))
        if self.file_dirs_names:
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
                    log.info(
                        "\tMonitoring the size of files {0} in the "
                        "directory {1}.".format(
                            ", ".join(
                                str(name) for name in file_names),
                            file_dir))
                config.merge(
                    watch_file_size(
                        directory_name=file_dir,
                        file_names=file_names,
                        file_recursive=file_recursive,
                        service=self.service_name,
                        component=self.component_name))

        if self.directory_names:
            for dir_name in self.directory_names:
                log.info("\tMonitoring the size of directory {0}.".format(
                    dir_name))
                config.merge(
                    watch_directory(
                        directory_name=dir_name,
                        service=self.service_name,
                        component=self.component_name))

        # Skip the http_check if disable_http_check is set
        if self.args is not None and self.args.get('disable_http_check', False):
            self.service_api_url = None
            self.search_pattern = None

        if self.service_api_url and self.search_pattern:
            # Check if there is something listening on the host/port
            parsed = urllib.parse.urlparse(self.service_api_url)
            host, port = parsed.netloc.split(':')
            listening = find_addrs_listening_on_port(port)

            if len(listening) > 0:
                # If not listening on localhost or ips then use another local ip
                if host == 'localhost' and len(
                        set(['127.0.0.1', '0.0.0.0', '::', '::1']) & set(listening)) == 0:
                    new_url = list(parsed)
                    new_url[1] = listening[0] + ':' + port
                    api_url = urllib.parse.urlunparse(new_url)
                else:
                    api_url = self.service_api_url

                # Setup an active http_status check on the API
                log.info("\tConfiguring an http_check for the {0} API.".format(self.service_name))
                config.merge(service_api_check(name=self.service_name + '-api',
                                               url=api_url,
                                               pattern=self.search_pattern,
                                               use_keystone=True,
                                               service=self.service_name,
                                               component=self.component_name))
            else:
                log.info("\tNo process found listening on {0} ".format(port) +
                         "skipping setup of http_check for the {0} API." .format(self.service_name))

        return config

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        return True
