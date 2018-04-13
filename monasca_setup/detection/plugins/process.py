# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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

import json
import logging
import yaml

import six

import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection.utils import find_process_cmdline

log = logging.getLogger(__name__)


class ProcessCheck(monasca_setup.detection.Plugin):
    """Setup a process check according to the passed in JSON string or YAML config file path.

       A process can be monitored by process_names or by process_username, or by both if
       the process_config list contains both dictionary entries. Pass in the dictionary containing
       process_names when watching process by name.  Pass in the dictionary containing process_user
       name and dimensions with component when watching process by username. Watching by
       process_username is useful for groups of processes that are owned by a specific user.
       For process monitoring by process_username the component dimension is required since it is
       used to initialize the instance name in process.yaml.

       service and component dimensions are recommended to distinguish multiple components per
       service.  The component dimensions will be defaulted to the process name when it is not
       input when monitoring by process_names.
       exact_match is optional and defaults to false, meaning the process name search string can
       be found within the process name.
       exact_match can be set to true if the process_names search string should match the process
       name.

       Pass in a YAML config file path:
       monasca-setup -d ProcessCheck -a "conf_file_path=/home/stack/myprocess.yaml"

       or

       Pass in a JSON string command line argument:
       Using monasca-setup, you can pass in a json string with arguments --detection_args_json,
       or the shortcut -json.

       Monitor by process_names:
       monasca-setup -d ProcessCheck -json \
         '{"process_config":[{"process_names":["monasca-notification","monasca-api"],
         "dimensions":{"service":"monitoring"}}]}'

       Specifiy one or more dictionary entries to the process_config list:
       monasca-setup -d ProcessCheck -json \
         '{"process_config":[
            {"process_names":["monasca-notification","monasca-api"],
             "dimensions":{"service":"monitoring"}},
            {"process_names":["elasticsearch"],
             "dimensions":{"service":"logging"},"exact_match":"true"},
            {"process_names":["monasca-thresh"],
             "dimensions":{"service":"monitoring","component":"thresh"}}]}'

       Monitor by process_username:
       monasca-setup -d ProcessCheck -json \
         '{"process_config":[{"process_username":"dbadmin",
           "dimensions":{"service":"monitoring","component":"vertica"}}]}'

       Can specify monitoring by both process_username and process_names:
       monasca-setup -d ProcessCheck -json \
         '{"process_config":[{"process_names":["monasca-api"],
           "dimensions":{"service":"monitoring"}},
                             {"process_username":"mon-api",
                              "dimensions":{"service":"monitoring","component":"monasca-api"}}]}'

    """
    def __init__(self, template_dir, overwrite=False, args=None, **kwargs):
        self.process_config = []
        self.valid_process_names = []
        self.valid_usernames = []
        if 'process_config' in kwargs:
            self.process_config = kwargs['process_config']

        super(ProcessCheck, self).__init__(template_dir, overwrite, args)

    def _get_config(self):
        self.conf_file_path = None
        if self.args:
            self.conf_file_path = self.args.get('conf_file_path', None)
        if self.conf_file_path:
            self._read_config(self.conf_file_path)

    def _read_config(self, config_file):
        log.info("\tUsing parameters from config file: {}".format(config_file))
        with open(config_file) as data_file:
            try:
                data = yaml.safe_load(data_file)
                if 'process_config' in data:
                    self.process_config = data['process_config']
                else:
                    log.error("\tInvalid format yaml file, missing key: process_config")
            except yaml.YAMLError as e:
                exception_msg = (
                    "Could not read config file. Invalid yaml format detected. {0}.".format(e))
                raise Exception(exception_msg)

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        self._get_config()

        for process_item in self.process_config:
            if 'dimensions' not in process_item:
                process_item['dimensions'] = {}
            if 'process_names' in process_item:
                found_process_names = []
                not_found_process_names = []
                for process_name in process_item['process_names']:
                    if find_process_cmdline(process_name) is not None:
                        found_process_names.append(process_name)
                    else:
                        not_found_process_names.append(process_name)

                # monitoring by process_names
                if not_found_process_names:
                    log.info(
                        "\tDid not discover process_name(s): {0}.".format(
                            ",".join(not_found_process_names)))
                if found_process_names:
                    process_item['found_process_names'] = found_process_names
                    if 'exact_match' in process_item:
                        if isinstance(process_item['exact_match'], six.string_types):
                            process_item['exact_match'] = (
                                process_item['exact_match'].lower() == 'true')
                    else:
                        process_item['exact_match'] = False
                    self.valid_process_names.append(process_item)

            if 'process_username' in process_item:
                if 'component' in process_item['dimensions']:
                    self.valid_usernames.append(process_item)
                else:
                    log.error("\tMissing required component dimension, when monitoring by "
                              "process_username: {}".format(process_item['process_username']))

        if self.valid_process_names or self.valid_usernames:
            self.available = True

    def _monitor_by_process_name(
            self,
            process_name,
            exact_match=False,
            detailed=True,
            dimensions=None):
        config = monasca_setup.agent_config.Plugins()
        instance = {'name': process_name,
                    'detailed': detailed,
                    'exact_match': exact_match,
                    'search_string': [process_name],
                    'dimensions': {}}
        # default component to process name if not given
        if dimensions:
            instance['dimensions'].update(dimensions)
            if 'component' not in dimensions:
                instance['dimensions']['component'] = process_name
        else:
            instance['dimensions']['component'] = process_name
        config['process'] = {'init_config': None, 'instances': [instance]}
        return config

    def _monitor_by_process_username(self, process_username, detailed=True, dimensions=None):
        config = monasca_setup.agent_config.Plugins()
        instance = {'name': dimensions['component'],
                    'detailed': detailed,
                    'username': process_username,
                    'dimensions': {}}
        if dimensions:
            instance['dimensions'].update(dimensions)
        config['process'] = {'init_config': None, 'instances': [instance]}
        return config

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()

        # Watch by process_names
        for process in self.valid_process_names:
            log.info("\tMonitoring by process_name(s): {0} "
                     "for dimensions: {1}.".format(",".join(process['found_process_names']),
                                                   json.dumps(process['dimensions'])))
            for process_name in process['found_process_names']:
                config.merge(self._monitor_by_process_name(process_name=process_name,
                                                           dimensions=process['dimensions'],
                                                           exact_match=process['exact_match']))

        # Watch by process_username
        for process in self.valid_usernames:
            log.info(
                "\tMonitoring by process_username: {0} "
                "for dimensions: {1}.".format(
                    process['process_username'], json.dumps(
                        process['dimensions'])))
            config.merge(
                self._monitor_by_process_username(
                    process_username=process['process_username'],
                    dimensions=process['dimensions']))
        return config

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        return True
