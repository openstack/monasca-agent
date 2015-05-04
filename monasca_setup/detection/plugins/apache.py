import logging
import urllib2


import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

apache_conf = '/root/.apache.cnf'
DEFAULT_APACHE_URL = 'http://localhost/server-status?auto'


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

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monasca_setup.detection.find_process_cmdline('apache2') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(['apache2']))
        log.info("\tWatching the apache webserver process.")

        error_msg = '\n\t*** The Apache plugin is not configured ***\n\tPlease correct and re-run monasca-setup.'
        # Attempt login, requires either an empty root password from localhost
        # or relying on a configured /root/.apache.cnf
        if self.dependencies_installed():
            log.info(
                "\tAttempting to use client credentials from {:s}".format(apache_conf))
            # Read the apache config file to extract the needed variables.
            client_section = False
            apache_url = None
            apache_user = None
            apache_pass = None
            try:
                with open(apache_conf, "r") as confFile:
                    for row in confFile:
                        if "[client]" in row:
                            client_section = True
                            pass
                        if client_section:
                            if "url=" in row:
                                apache_url = row.split("=")[1].strip()
                            if "user=" in row:
                                apache_user = row.split("=")[1].strip()
                            if "password=" in row:
                                apache_pass = row.split("=")[1].strip()
            except IOError:
                log.info("\tUnable to read {:s}".format(apache_conf))
                log.info("\tWill try to setup Apache plugin using defaults.")

            if not apache_url:
                apache_url = DEFAULT_APACHE_URL

            opener = None
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

            response = None
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
            except urllib2.URLError, e:
                log.error('\tError {0} received when accessing url {1}.'.format(e.reason, apache_url) +
                          '\n\tPlease ensure the Apache web server is running and your configuration ' +
                          'information in /root/.apache.cnf is correct.' + error_msg)
            except urllib2.HTTPError, e:
                log.error('\tError code {0} received when accessing {1}'.format(e.code, apache_url) + error_msg)
        else:
            log.error('\tThe dependencies for Apache Web Server are not installed or unavailable.' + error_msg)

        return config

    def dependencies_installed(self):
        # No real dependencies to check
        return True
