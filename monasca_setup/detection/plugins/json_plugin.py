# (c) Copyright 2016 Hewlett Packard Enterprise Development LP
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

from monasca_setup import agent_config
import monasca_setup.detection
import os


VAR_CACHE_DIR = '/var/cache/monasca_json_plugin'


class JsonPlugin(monasca_setup.detection.ArgsPlugin):
    """Detect if /var/cache/monasca_json_plugin exists

    This builds a config for the json_plugin. This detects if
    /var/cache/monasca_json_plugin exists and if so,
    builds a configuration for it.

    Users are free to add their own configs.
    """
    def __init__(self, template_dir, overwrite=True, args=None):
        super(JsonPlugin, self).__init__(
            template_dir, overwrite, args)

    def _detect(self):
        self.available = False
        if os.path.isdir(VAR_CACHE_DIR):
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return."""
        config = agent_config.Plugins()
        config['json_plugin'] = {'init_config': None,
                                 'instances': [{'name': VAR_CACHE_DIR,
                                                'metrics_dir': VAR_CACHE_DIR}]}

        return config

    def dependencies_installed(self):
        """Return True if dependencies are installed."""
        return True
