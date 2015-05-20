import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class HttpCheck(monasca_setup.detection.ArgsPlugin):
    """ Setup an http_check according to the passed in args.
        Despite being a detection plugin this plugin does no detection and will be a noop without arguments.
        Expects space seperated arguments, the required argument is url. Optional parameters include:
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
        log.info("\tEnabling the http_check plugin for {url}".format(**self.args))

        # No support for setting headers at this time
        instance = self._build_instance(['url', 'timeout', 'username', 'password', 'match_pattern',
                                         'disable_ssl_validation'])
        instance['name'] = self.args['url']
        instance['collect_response_time'] = True

        config['http_check'] = {'init_config': None, 'instances': [instance]}

        return config

