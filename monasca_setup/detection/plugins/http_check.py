# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

import ast

import monasca_setup.agent_config
import monasca_setup.detection


class HttpCheck(monasca_setup.detection.ArgsPlugin):
    """Setup an http_check according to the passed in args.
       Despite being a detection plugin this plugin does no detection and will be a noop without arguments.
       Expects space separated arguments, the required argument is url. Optional parameters include:
       disable_ssl_validation and match_pattern.
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

        # Normalize any boolean parameters
        for param in ['use_keystone', 'collect_response_time']:
            if param in self.args:
                instance[param] = ast.literal_eval(self.args[param].capitalize())
        # Set some defaults
        if 'collect_response_time' not in instance:
            instance['collect_response_time'] = True
        if 'name' not in instance:
            instance['name'] = self.args['url']

        config['http_check'] = {'init_config': None, 'instances': [instance]}

        return config
