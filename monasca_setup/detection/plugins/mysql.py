import logging

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

mysql_conf = '/root/.my.cnf'


class MySQL(monasca_setup.detection.Plugin):

    """Detect MySQL daemons and setup configuration to monitor them.

        This plugin needs user/pass infor for mysql setup, this is
        best placed in /root/.my.cnf in a format such as
        [client]
            user = root
            password = yourpassword
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        if monasca_setup.detection.find_process_name('mysqld') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        # First watch the process
        config.merge(monasca_setup.detection.watch_process(['mysqld']))
        log.info("\tWatching the mysqld process.")

        # Attempt login, requires either an empty root password from localhost
        # or relying on a configured /root/.my.cnf
        if self.dependencies_installed():  # ensures MySQLdb is available
            import MySQLdb
            import _mysql_exceptions
            try:
                MySQLdb.connect(read_default_file=mysql_conf)
            except _mysql_exceptions.MySQLError:
                pass
            else:
                log.info(
                    "\tUsing client credentials from {:s}".format(mysql_conf))
                # Read the mysql config file to extract the needed variables.
                # While the agent mysql.conf file has the ability to read the
                # /root/.my.cnf file directly as 'defaults_file,' the agent
                # user would likely not have permission to do so.
                client_section = False
                my_user = None
                my_pass = None
                try:
                    with open(mysql_conf, "r") as confFile:
                        for row in confFile:
                            # If there are any spaces in confFile, remove them
                            row = row.replace(" ", "")
                            if client_section:
                                if "[" in row:
                                    break
                                if "user=" in row:
                                    my_user = row.split("=")[1].rstrip()
                                if "password=" in row:
                                    my_pass = row.split("=")[1].rstrip().strip("'")
                            if "[client]" in row:
                                client_section = True
                    config['mysql'] = {'init_config': None, 'instances':
                                       [{'name': 'localhost', 'server': 'localhost', 'port': 3306,
                                         'user': my_user, 'pass': my_pass}]}
                except IOError:
                    log.error("\tI/O error reading {:s}".format(mysql_conf))
                    pass

            # Try logging in as 'root' with an empty password
            if 'mysql' not in config:
                try:
                    MySQLdb.connect(host='localhost', port=3306, user='root')
                except _mysql_exceptions.MySQLError:
                    pass
                else:
                    log.info("\tConfiguring plugin to connect with user root.")
                    config['mysql'] = {'init_config': None, 'instances':
                                       [{'name': 'localhost', 'server': 'localhost', 'user': 'root',
                                         'port': 3306}]}

        if 'mysql' not in config:
            log.warn('Unable to log into the mysql database;' +
                     ' the mysql plugin is not configured.')

        return config

    def dependencies_installed(self):
        try:
            import MySQLdb
        except ImportError:
            return False

        return True
