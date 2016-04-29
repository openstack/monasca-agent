# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

import logging

from monasca_agent.common.util import timeout_command
import monasca_setup.agent_config
import monasca_setup.detection
from monasca_setup.detection.utils import find_process_name
from monasca_setup.detection.utils import watch_process_by_username

log = logging.getLogger(__name__)

VERTICA_CONF = '/root/.vertica.cnf'
VSQL_PATH = '/opt/vertica/bin/vsql'
VERTICA_SERVICE = 'vertica'
CONNECTION_TIMEOUT = 3


class Vertica(monasca_setup.detection.Plugin):

    """Detect Vertica process running and DB connection status

        This plugin needs the Vertica username, password.
        The other arguments are optional.
        There are two ways to provide this, either by a file placed in
        /root/.vertica.cnf or by passing the following arguments:
            - user
            - password
            - service   (optional)
            - timeout   (optional - timeout for connection attempt in seconds)
        /root/.vertica.cnf in a format such as
        [client]
            user = user1
            password = yourpassword
            service = monitoring
            timeout = 3
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
            self.user = 'mon_api'
            self.password = 'password'
            self.service = VERTICA_SERVICE
            self.timeout = CONNECTION_TIMEOUT

            self._read_config(VERTICA_CONF)
        else:
            self.user = self.args.get('user', 'mon_api')
            self.password = self.args.get('password', 'password')
            self.service = self.args.get('service', VERTICA_SERVICE)
            self.timeout = self.args.get('timeout', CONNECTION_TIMEOUT)

    def _connection_test(self):
        """Attempt to connect to Vertica DB to verify credentials.
        :return: bool status of the test
        """
        log.info("\tVertica connection test.")
        output = timeout_command(
            [VSQL_PATH, "-U", self.user, "-w", self.password, "-c", "select version();"], self.timeout)
        if (output is not None) and ('Vertica Analytic Database' in output):
            return True
        else:
            return False

    def _read_config(self, config_file):
        """Read the configuration setting member variables as appropriate.
        :param config_file: The filename of the configuration to read and parse
        """
        # Read the Vertica config file to extract the needed variables.
        client_section = False
        try:
            with open(config_file, "r") as conf:
                for row in conf:
                    if "[client]" in row:
                        client_section = True
                        log.info("\tUsing client credentials from {:s}".format(config_file))
                        continue
                    if client_section:
                        if "user" in row:
                            self.user = row.split("=")[1].strip()
                        if "password" in row:
                            self.password = row.split("=")[1].strip()
                        if "vsql_path" in row:
                            self.vsql_path = row.split("=")[1].strip()
                        if "service" in row:
                            self.service = row.split("=")[1].strip()
                        if "timeout" in row:
                            self.timeout = int(row.split("=")[1].strip())
        except IOError:
            log.warn('Unable to open Vertica config file {0}. '
                     'Using default credentials to try to connect.'.format(VERTICA_CONF))

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
                                   'timeout': self.timeout}
                config['vertica'] = {'init_config': None, 'instances': [instance_config]}
            else:
                exception_msg = 'Unable to connect to the Vertica DB. ' \
                                'The Vertica plugin is not configured. ' \
                                'Please correct and re-run monasca-setup.'
                log.error(exception_msg)
                raise Exception(exception_msg)
        except Exception:
            exception_msg = 'Error configuring the Vertica check plugin'
            log.error(exception_msg)
            raise Exception(exception_msg)

        return config

    def dependencies_installed(self):
        return True
