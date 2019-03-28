# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
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

import ast

import monasca_setup.agent_config
import monasca_setup.detection


class HttpCheck(monasca_setup.detection.ArgsPlugin):
    """Setup an http_check according to the passed in args.
       Despite being a detection plugin this plugin does no detection and will be a noop without
       arguments.
       Expects space separated arguments, the required argument is url. Optional parameters include:
       disable_ssl_validation and match_pattern.

       You could provide Keystone configuration for all services when
       for example you want to monitor different OpenStack instance.
       Using monasca-setup, you can pass in space separated arguments with
       --detection_args, or the shortcut -a.

       monasca-setup -d HttpCheck --detection_args \
         "keystone_url=http://192.168.10.6/identity \
          keystone_project=proj \
          keystone_project_domain=Default \
          keystone_user=usr \
          keystone_user_domain=Default \
          keystone_password=pass \
          url=https://192.168.10.6"

       NOTE: keystone_project_domain and keystone_user_domain are required
       for Keystone V3. They are used to convey the project's domain name and
       user's domain name respectively.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        self.available = self._check_required_args(['url'])

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        # No support for setting headers at this time
        instance = self._build_instance(['url', 'timeout', 'username', 'password',
                                         'match_pattern', 'disable_ssl_validation',
                                         'name', 'use_keystone', 'collect_response_time'])

        init_config = None
        if 'keystone_url' in self.args:
            init_config = {'keystone_config': self._build_instance([
                'keystone_url',
                'keystone_project',
                'keystone_project_domain',
                'keystone_user',
                'keystone_user_domain',
                'keystone_password'],
                add_dimensions=False)}

        # Normalize any boolean parameters
        for param in ['use_keystone', 'collect_response_time']:
            if param in self.args:
                instance[param] = ast.literal_eval(self.args[param].capitalize())
        # Set some defaults
        if 'collect_response_time' not in instance:
            instance['collect_response_time'] = True
        if 'name' not in instance:
            instance['name'] = self.args['url']

        # Configure http check wide Keystone settings
        if init_config and ('keystone_config' in init_config):
            if 'keystone_project' in init_config['keystone_config']:
                init_config['keystone_config']['project_name'] = init_config['keystone_config']\
                    .pop('keystone_project')
            if 'keystone_project_domain' in init_config['keystone_config']:
                init_config['keystone_config']['project_domain_name'] = \
                    init_config['keystone_config'].pop('keystone_project_domain')
            if 'keystone_user' in init_config['keystone_config']:
                init_config['keystone_config']['username'] = init_config['keystone_config']\
                    .pop('keystone_user')
            if 'keystone_user_domain' in init_config['keystone_config']:
                init_config['keystone_config']['user_domain_name'] = \
                    init_config['keystone_config'].pop('keystone_user_domain')
            if 'keystone_password' in init_config['keystone_config']:
                init_config['keystone_config']['password'] = init_config['keystone_config']\
                    .pop('keystone_password')

        config['http_check'] = {'init_config': init_config, 'instances': [instance]}
        return config
