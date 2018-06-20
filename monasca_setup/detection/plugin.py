# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

"""Classes for detection of running resources to be monitored.

    Detection classes should be platform independent
"""
import ast
import logging
import sys

log = logging.getLogger(__name__)


class Plugin(object):
    """Abstract class for the monasca-agent plugin detection."""

    def __init__(self, template_dir, overwrite=True, args=None):
        self.available = False
        self.template_dir = template_dir
        self.dependencies = ()
        self.overwrite = overwrite
        if args is not None and isinstance(args, str):
            try:
                # Turn 'hostname=host type=ping' to dictionary
                # {'hostname': 'host', 'type': 'ping'}
                self.args = dict([a.split('=') for a in args.split()])
            except Exception:
                log.exception('Error parsing detection arguments')
                sys.exit(1)
        elif isinstance(args, dict):
            self.args = args
        else:
            self.args = None
        self._detect()

    def _detect(self):
        """Run detection.

        Set self.available True if the service is detected.
        """
        raise NotImplementedError

    def build_config(self):
        """Build the config as a Plugins object and return."""
        raise NotImplementedError

    def build_config_with_name(self):
        """Build the config and then add 'built_by' field.

           Build the config and then add 'built_by' field to each instance in
           the config.

           built_by is set to the plugin name

           :return: An agent_config.Plugins object
        """
        conf = self.build_config()
        if conf is None:
            return None
        for plugin_type in conf.values():
            for inst in plugin_type['instances']:
                inst['built_by'] = self.__class__.__name__
        return conf

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        raise NotImplementedError

    @staticmethod
    def literal_eval(testval):
        """Return a literal boolean value if applicable

        """
        if 'false' in str(testval).lower() or 'true' in str(testval).lower():
            return ast.literal_eval(str(testval).capitalize())
        else:
            return testval

    @property
    def name(self):
        """Return _name if set otherwise the class name.

        """
        if '_name' in self.__dict__:
            return self._name
        else:
            return self.__class__.__name__
