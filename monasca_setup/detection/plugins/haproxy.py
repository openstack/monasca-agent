import logging
import os
import re

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)


class HAProxy(monasca_setup.detection.Plugin):
    """Detect HAProxy daemon and setup configuration to monitor.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if monasca_setup.detection.find_process_cmdline('haproxy') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        log.info("\tEnabling HAProxy process watching")

        config.merge(monasca_setup.detection.watch_process(['haproxy'], exact_match=False))
        if monasca_setup.detection.find_process_cmdline('keepalived') is not None:
            config.merge(monasca_setup.detection.watch_process(['keepalived'], exact_match=False))

        proxy_cfgfile = '/etc/haproxy/haproxy.cfg'
        if os.path.exists(proxy_cfgfile):
            # parse the config file looking for the stats section and pulling out url/user/pass
            with open(proxy_cfgfile, 'r') as pcfg:
                proxy_cfg = pcfg.read()

            url = None
            user = None
            password = None
            for line in proxy_cfg.splitlines():
                if line.startswith('listen'):
                    listen_match = re.search('^listen.*stats\S*\s(.*)', line)
                    if listen_match is None:
                        continue
                    listen_socket = listen_match.group(1).split(':')
                    if listen_socket[0] == '':
                        host = 'localhost'
                    else:
                        host = listen_socket[0]
                    port = listen_socket[1]
                    url = 'http://{0}:{1}'.format(host, port)
                if url is not None and line.strip().startswith('stats auth'):
                    auth = re.search('stats auth\s(.*)', line).group(1).split(':')
                    user = auth[0]
                    password = auth[1]

            if url is None:
                log.warn('Unable to parse haproxy config for stats url, skipping HAProxy check plugin configuration')
            else:
                log.info('Enabling the HAProxy check plugin')
                instance_config = {'name': url, 'url': url, 'status_check': False, 'collect_aggregates_only': True,
                                   'collect_status_metrics': False}
                if user is not None:
                    instance_config['username'] = user
                if password is not None:
                    instance_config['password'] = password
                config['haproxy'] = {'init_config': None, 'instances': [ instance_config ]}

        return config

    def dependencies_installed(self):
        return True
