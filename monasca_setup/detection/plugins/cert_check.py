# (C) Copyright 2016 Hewlett Packard Enterprise Development LP

import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

CA_CERTS = "/etc/ssl/certs/ca-certificates.crt"
CIPHERS = "HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5"
DEFAULT_TIMEOUT = 1.0
DEFAULT_COLLECT_PERIOD = 3600


class CertificateCheck(monasca_setup.detection.ArgsPlugin):
    """Setup a https certification check according to the passed in args.

       Outputs one metric: https.cert_expire_days which is the number of
       days until the certificate expires

       Despite being a detection plugin, this plugin does no detection and
       will be a NOOP without arguments.  Expects one argument, 'urls'
       which is a comma-separated list of urls
       Examples:

       monasca-setup -d CertificateCheck -a "urls=https://ThisCloud.example:8070"
       These arguments are optional:
       ca_certs: file containing the certificates for Certificate Authorities
                 default is CA_CERTS
       ciphers: list of ciphers to check
                default is CIPHERS
       collect_period: Integer time in seconds between outputting the metric.
                       Since the metric is in days, it makes sense to output
                       it at a slower rate. The default is once per hour
       timeout: Float time in seconds before timing out the connect to the url.
                Increase if needed for very slow servers, but making this too
                long will increase the time this plugin takes to run if the
                server for the url is down. The default is 1.0 seconds
    """

    def _detect(self):
        """Run detection, set self.available True if urls are detected
        """
        self.available = self._check_required_args(['urls'])

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = monasca_setup.agent_config.Plugins()
        instances = []
        init_config = {'ca_certs': CA_CERTS,
                       'ciphers': CIPHERS,
                       'timeout': DEFAULT_TIMEOUT,
                       'collect_period': DEFAULT_COLLECT_PERIOD}
        if 'ca_certs' in self.args:
            init_config['ca_certs'] = self.args['ca_certs']
        if 'ciphers' in self.args:
            init_config['ciphers'] = self.args['ciphers']
        if 'timeout' in self.args:
            timeout = float(self.args['timeout'])
            if timeout <= 0.0:
                log.error('Invalid timeout value %s, ignoring' %
                          self.args['timeout'])
            else:
                init_config['timeout'] = timeout
        if 'collect_period' in self.args:
            collect_period = int(self.args['collect_period'])
            init_config['collect_period'] = collect_period
        for url in self.args['urls'].split(','):
            url = url.strip()
            # Allow comma terminated lists
            if not url:
                continue
            log.info("\tAdding SSL Certificate expiration check for {}".format(url))
            instance = self._build_instance([])
            instance.update({'url': url, 'name': url})
            instances.append(instance)

        config['cert_check'] = {'init_config': init_config,
                                'instances': instances}

        return config
