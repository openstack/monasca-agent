import logging
import urllib2

import monasca_setup.agent_config
import monasca_setup.detection


log = logging.getLogger(__name__)

# Defaults
rabbit_conf = '/root/.rabbitmq.cnf'
rabbitmq_api_url = 'http://localhost:15672/api'


class RabbitMQ(monasca_setup.detection.Plugin):
    """Detect RabbitMQ daemons and setup configuration to monitor them.

        This plugin needs user/pass info for rabbitmq setup. There are two
        ways to provide it, either by a file placed in /root/.rabbit.cnf or
        by specifying the following arguments:
            - api_url
            - user
            - password
            - queues
            - nodes
            - exchanges
        queues, exchanges and nodes are a comma separated list and are optional

        The file at /root/.rabbit.cnf should have this format:
        [client]
            user = guest
            password = guest
            nodes=rabbit@localhost, rabbit2@domain
            exchanges=nova, cinder, neutron
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('rabbitmq-server') is not None:
            self.available = True

    def _get_config(self):
        """Set the configuration to be used for connecting to rabbitmq
        :return:
        """
        # Set defaults and read config or use arguments
        if self.args is None:
            self.api_url = rabbitmq_api_url
            self.user = 'guest'
            self.password = 'guest'
            self.queues = None
            self.nodes = None
            self.exchanges = None

            self._read_config(rabbit_conf)
        else:
            self.api_url = self.args.get('api_url', rabbitmq_api_url)
            self.user = self.args.get('user', 'guest')
            self.password = self.args.get('password', 'guest')
            self.queues = self.args.get('queues')
            self.nodes = self.args.get('nodes')
            self.exchanges = self.args.get('exchanges')

    def _login_test(self):
        """Attempt to log into the rabbitmq admin api to verify credentials.
        :return: bool status of the test
        """
        url = self.api_url + '/aliveness-test/%2F'
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None,
                                  self.api_url,
                                  self.user,
                                  self.password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)

        request = opener.open(url)
        response = request.read()
        request.close()
        if '{"status":"ok"}' in response:
            return True
        else:
            return False

    def _read_config(self, config_file):
        """Read the configuration setting member variables as appropriate.
        :param config_file: The filename of the configuration to read and parse
        """
        # Read the rabbitmq config file to extract the needed variables.
        client_section = False
        with open(config_file, "r") as conf:
            for row in conf:
                if "[client]" in row:
                    client_section = True
                    log.info("\tUsing client credentials from {:s}".format(config_file))
                    pass
                if client_section:
                    if "api_url=" in row:
                        self.api_url = row.split("=")[1].strip()
                    if "user=" in row:
                        self.user = row.split("=")[1].strip()
                    if "password=" in row:
                        self.password = row.split("=")[1].strip()
                    if "exchanges=" in row:
                        self.exchanges = row.split("=")[1].strip()
                    if "queues=" in row:
                        self.queues = row.split("=")[1].strip()
                    if "nodes=" in row:
                        self.nodes = row.split("=")[1].strip()

    @staticmethod
    def _split_list(to_split):
        return [x.strip() for x in to_split.split(',')]

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(['rabbitmq-server']))
        log.info("\tWatching the rabbitmq-server process.")

        try:
            self._get_config()
            if self._login_test():
                instance_config = {'name': self.api_url,
                                   'rabbitmq_api_url': self.api_url,
                                   'rabbitmq_user': self.user,
                                   'rabbitmq_pass': self.password}
                if self.queues is not None:
                    instance_config['queues'] = self._split_list(self.queues)
                if self.exchanges is not None:
                    instance_config['exchanges'] = self._split_list(self.exchanges)
                if self.nodes is not None:
                    instance_config['nodes'] = self._split_list(self.nodes)

                config['rabbitmq'] = {'init_config': None, 'instances': [instance_config]}
            else:
                log.warn('Unable to access the RabbitMQ admin URL;' +
                         ' the RabbitMQ plugin is not configured.' +
                         ' Please correct and re-run monasca-setup.')
        except Exception:
            log.exception('Error configuring the RabbitMQ check plugin')

        return config

    def dependencies_installed(self):
        return True
