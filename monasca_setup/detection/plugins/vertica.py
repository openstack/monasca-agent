# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

import logging

from monasca_agent.common.util import timeout_command
import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection.utils import find_process_name
from monasca_setup.detection.utils import watch_process_by_username

log = logging.getLogger(__name__)

VERTICA_SERVICE = 'vertica'
CONNECTION_TIMEOUT = 3
SERVICE = 'vertica'
USER = 'monitor'
USER_PASSWORD = 'password'


class Vertica(monasca_setup.detection.Plugin):

    """Detect Vertica process running and DB connection status

        This plugin has the following options (each optional) that you can pass in via command line:
            - user      (optional - user to connect with) - Defaults to monitor user
            - password  (optional - password to use when connecting) - Defaults to password
            - service   (optional - dimensions service to be set for the metrics coming out of the plugin)
            - timeout   (optional - timeout for vertica connection in seconds) - Defaults to 3 second
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if (find_process_name('vertica') is not None and find_process_name(
                'spread') is not None):
            self.available = True

    def _get_config(self):
        """Set the configuration to be used for connecting to Vertica
        :return:
        """
        # Set defaults and read config or use arguments
        if self.args is None:
            self.user = USER
            self.password = USER_PASSWORD
            self.service = VERTICA_SERVICE
            self.timeout = CONNECTION_TIMEOUT
        else:
            self.user = self.args.get('user', USER)
            self.password = self.args.get('password', USER_PASSWORD)
            self.service = self.args.get('service', VERTICA_SERVICE)
            self.timeout = int(self.args.get('timeout', CONNECTION_TIMEOUT))

    def _connection_test(self):
        """Attempt to connect to Vertica DB to verify credentials.
        :return: bool status of the test
        """
        log.info("\tVertica connection test.")
        stdout, stderr, return_code = timeout_command(
            ["/opt/vertica/bin/vsql", "-U", self.user, "-w", self.password, "-t", "-A", "-c",
             "SELECT node_name FROM current_session"], self.timeout)
        # remove trailing newline
        stdout = stdout.rstrip()
        if return_code == 0:
            self.node_name = stdout
            return True
        else:
            log.error("Error querying vertica with return code of {0} and the error {1}".format(return_code, stderr))
            return False

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        try:
            self._get_config()
            config.merge(watch_process_by_username('dbadmin', 'vertica', self.service, 'vertica'))
            log.info("\tWatching the vertica processes.")
            if self._connection_test():
                log.info("\tBuilding vertica config.")
                instance_config = {'name': 'localhost',
                                   'user': self.user,
                                   'password': self.password,
                                   'service': self.service,
                                   'node_name': self.node_name,
                                   'timeout': self.timeout}
                config['vertica'] = {'init_config': None, 'instances': [instance_config]}
            else:
                exception_msg = 'Unable to connect to the Vertica DB. ' \
                                'The Vertica plugin is not configured. ' \
                                'Please correct and re-run monasca-setup.'
                log.error(exception_msg)
                raise Exception(exception_msg)
        except Exception as e:
            exception_msg = 'Error configuring the Vertica check plugin - {0}'.format(e)
            log.error(exception_msg)
            raise Exception(exception_msg)

        return config
