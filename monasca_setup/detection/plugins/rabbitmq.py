import logging
import urllib2


import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

rabbit_conf = '/root/.rabbitmq.cnf'
rabbitmq_api_url = 'http://localhost:15672/api'


class RabbitMQ(monasca_setup.detection.Plugin):

    """Detect RabbitMQ daemons and setup configuration to monitor them.

        This plugin needs user/pass info for rabbitmq setup, this is
        best placed in /root/.rabbit.cnf.  You can also specify exchanges
        and rabbitmq nodes that you want to monitor in a format such as
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

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(['rabbitmq-server']))
        log.info("\tWatching the rabbitmq-server process.")

        # Attempt login, requires either an empty root password from localhost
        # or relying on a configured /root/.rabbit.cnf
        if self.dependencies_installed():
            log.info(
                "\tUsing client credentials from {:s}".format(rabbit_conf))
            # Read the rabbitmq config file to extract the needed variables.
            client_section = False
            rabbit_user = 'guest'
            rabbit_pass = 'guest'
            try:
                with open(rabbit_conf, "r") as confFile:
                    for row in confFile:
                        if "[client]" in row:
                            client_section = True
                            pass
                        if client_section:
                            if "user=" in row:
                                rabbit_user = row.split("=")[1].strip()
                            if "password=" in row:
                                rabbit_pass = row.split("=")[1].strip()
                            if "exchanges=" in row:
                                rabbit_exchanges = row.split("=")[1].strip()
                            if "queues=" in row:
                                rabbit_queues = row.split("=")[1].strip()
                            if "nodes=" in row:
                                rabbit_nodes =row.split("=")[1].strip()
            except IOError:
                log.warn("\tI/O error reading {:s} only basic process watching enabled".format(rabbit_conf))
                return config

            url = rabbitmq_api_url + '/aliveness-test/%2F'
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None,
                                      rabbitmq_api_url,
                                      rabbit_user,
                                      rabbit_pass)
            handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            opener = urllib2.build_opener(handler)

            response = None
            try:
                request = opener.open(url)
                response = request.read()
                request.close()
                if '{"status":"ok"}' in response:
                    config['rabbitmq'] = {'init_config': None, 'instances':
                                          [{'name': rabbitmq_api_url,
                                            'rabbitmq_api_url': rabbitmq_api_url,
                                            'rabbitmq_user': rabbit_user,
                                            'rabbitmq_pass': rabbit_pass,
                                            'queues': [x.strip() for x in rabbit_queues.split(',')],
                                            'exchanges': [x.strip() for x in rabbit_exchanges.split(',')],
                                            'nodes': [x.strip() for x in rabbit_nodes.split(',')]}]}
                else:
                    log.warn('Unable to access the RabbitMQ admin URL;' +
                             ' the RabbitMQ plugin is not configured.' +
                             ' Please correct and re-run monasca-setup.')
            except urllib2.HTTPError, e:
                log.error('Error code %s received when accessing %s' % (e.code, url) +
                          ' RabbitMQ plugin is not configured.')
        else:
            log.error('\tThe RabbitMQ management console is not installed or unavailable.' +
                      ' RabbitMQ plugin is not configured.')

        return config

    def dependencies_installed(self):
        # ensure the rabbit management api is available
        try:
            urllib2.urlopen(rabbitmq_api_url).read()
        except urllib2.URLError:
            return False

        return True
