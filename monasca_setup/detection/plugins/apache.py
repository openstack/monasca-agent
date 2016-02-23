# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import urllib2


import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

# Process name is apache2 on Debian derivatives, on RHEL derivatives it's httpd
APACHE_PROCESS_NAMES = ('apache2', 'httpd')
DEFAULT_APACHE_CONFIG = '/root/.apache.cnf'
DEFAULT_APACHE_URL = 'http://localhost/server-status?auto'
CONFIG_ARG_KEYS = set(["url", "user", "password"])


class Apache(monasca_setup.detection.Plugin):

    """Detect Apache web server daemons and setup configuration to monitor them.

        This plugin needs user/pass info for apache if security is setup on the web server,
        this is best placed in /root/.apache.cnf in a format such as
        [client]
            url=http://localhost/server-status?auto
            user=guest
            password=guest
        If this file is not provided, the plugin will attempt to connect without security
        using a default URL.
    """

    def __init__(self, *args, **kwargs):
        self._apache_process_name = 'apache2'
        super(Apache, self).__init__(*args, **kwargs)

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        for proc_name in APACHE_PROCESS_NAMES:
            if monasca_setup.detection.find_process_cmdline(proc_name) is not None:
                self._apache_process_name = proc_name
                self.available = True

    def _read_apache_config(self, config_location):
        # Read the apache config file to extract the needed variables.
        client_section = False
        apache_url = None
        apache_user = None
        apache_pass = None
        try:
            with open(config_location, "r") as config_file:
                for row in config_file:
                    if "[client]" in row:
                        client_section = True
                        continue
                    if client_section:
                        if "url=" in row:
                            apache_url = row.split("=")[1].strip()
                        if "user=" in row:
                            apache_user = row.split("=")[1].strip()
                        if "password=" in row:
                            apache_pass = row.split("=")[1].strip()
        except IOError:
            log.warn("\tUnable to read {:s}".format(config_location))

        return apache_url, apache_user, apache_pass

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(
            [self._apache_process_name], 'apache'))
        log.info("\tWatching the apache webserver process.")

        error_msg = '\n\t*** The Apache plugin is not configured ***\n\tPlease correct and re-run monasca-setup.'
        # Attempt login, requires either an empty root password from localhost
        # or relying on a configured /root/.apache.cnf
        if self.dependencies_installed():
            # If any of the exact keys are present, use them.
            if self.args and self.args.viewkeys() & CONFIG_ARG_KEYS:
                log.info("Attempting to use credentials from command args")
                apache_url = self.args.get("url", None)
                apache_user = self.args.get("user", None)
                apache_pass = self.args.get("password", None)
            elif self.args and self.args.get("apache_config_file"):
                config_file = self.args.get("apache_config_file")
                apache_url, apache_user, apache_pass = self._read_apache_config(config_file)
            else:
                apache_url, apache_user, apache_pass = self._read_apache_config(DEFAULT_APACHE_CONFIG)

            if not apache_url:
                log.warn("No url specified, using default url {:s}".format(DEFAULT_APACHE_URL))
                apache_url = DEFAULT_APACHE_URL

            if apache_user and apache_pass:
                password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                password_mgr.add_password(None,
                                          apache_url,
                                          apache_user,
                                          apache_pass)
                handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            else:
                if 'https' in apache_url:
                    handler = urllib2.HTTPSHandler()
                else:
                    handler = urllib2.HTTPHandler()

            opener = urllib2.build_opener(handler)

            try:
                request = opener.open(apache_url)
                response = request.read()
                request.close()
                if 'Total Accesses:' in response:
                    instance_vars = {'name': apache_url, 'apache_status_url': apache_url}
                    if apache_user and apache_pass:
                        instance_vars.update({'apache_user': apache_user,
                                              'apache_password': apache_pass})
                    config['apache'] = {'init_config': None, 'instances': [instance_vars]}
                    log.info("\tSuccessfully setup Apache plugin.")
                else:
                    log.warn('Unable to access the Apache server-status URL;' + error_msg)
            except urllib2.URLError as e:
                log.error('\tError {0} received when accessing url {1}.'.format(e.reason, apache_url) +
                          '\n\tPlease ensure the Apache web server is running and your configuration ' +
                          'information is correct.' + error_msg)
            # TODO(Ryan Brandt) this exception code is unreachable, will be caught by superclass URLError above
            except urllib2.HTTPError as e:
                log.error('\tError code {0} received when accessing {1}'.format(e.code, apache_url) + error_msg)
        else:
            log.error('\tThe dependencies for Apache Web Server are not installed or unavailable.' + error_msg)

        return config

    def dependencies_installed(self):
        # No real dependencies to check
        return True
