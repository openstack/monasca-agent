# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import re
import subprocess
import sys
import traceback

import monasca_agent.collector.checks as checks

GAUGE = "gauge"
RATE = "rate"

STATUS_VARS = {
    'Connections': ('mysql.net.connections', RATE),
    'Max_used_connections': ('mysql.net.max_connections', GAUGE),
    'Open_files': ('mysql.performance.open_files', GAUGE),
    'Table_locks_waited': ('mysql.performance.table_locks_waited', GAUGE),
    'Threads_connected': ('mysql.performance.threads_connected', GAUGE),
    'Innodb_data_reads': ('mysql.innodb.data_reads', RATE),
    'Innodb_data_writes': ('mysql.innodb.data_writes', RATE),
    'Innodb_os_log_fsyncs': ('mysql.innodb.os_log_fsyncs', RATE),
    'Innodb_buffer_pool_size': ('mysql.innodb.buffer_pool_size', RATE),
    'Slow_queries': ('mysql.performance.slow_queries', RATE),
    'Questions': ('mysql.performance.questions', RATE),
    'Queries': ('mysql.performance.queries', RATE),
    'Com_select': ('mysql.performance.com_select', RATE),
    'Com_insert': ('mysql.performance.com_insert', RATE),
    'Com_update': ('mysql.performance.com_update', RATE),
    'Com_delete': ('mysql.performance.com_delete', RATE),
    'Com_insert_select': ('mysql.performance.com_insert_select', RATE),
    'Com_update_multi': ('mysql.performance.com_update_multi', RATE),
    'Com_delete_multi': ('mysql.performance.com_delete_multi', RATE),
    'Com_replace_select': ('mysql.performance.com_replace_select', RATE),
    'Qcache_hits': ('mysql.performance.qcache_hits', RATE),
    'Innodb_mutex_spin_waits': ('mysql.innodb.mutex_spin_waits', RATE),
    'Innodb_mutex_spin_rounds': ('mysql.innodb.mutex_spin_rounds', RATE),
    'Innodb_mutex_os_waits': ('mysql.innodb.mutex_os_waits', RATE),
    'Created_tmp_tables': ('mysql.performance.created_tmp_tables', RATE),
    'Created_tmp_disk_tables': ('mysql.performance.created_tmp_disk_tables', RATE),
    'Created_tmp_files': ('mysql.performance.created_tmp_files', RATE),
    'Innodb_row_lock_waits': ('mysql.innodb.row_lock_waits', RATE),
    'Innodb_row_lock_time': ('mysql.innodb.row_lock_time', RATE),
    'Innodb_current_row_locks': ('mysql.innodb.current_row_locks', GAUGE),
}


class MySql(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(MySql, self).__init__(name, init_config, agent_config)
        self.mysql_version = {}
        self.greater_502 = {}

    @staticmethod
    def get_library_versions():
        try:
            import pymysql
            version = pymysql.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"PyMySQL": version}

    def check(self, instance):
        host, port, user, password, mysql_sock, ssl_ca, ssl_key, ssl_cert, defaults_file, \
            options = self._get_config(
                instance)
        self.ssl_options = {}
        if ssl_ca is not None:
            self.ssl_options['ca'] = ssl_ca
        if ssl_key is not None:
            self.ssl_options['key'] = ssl_key
        if ssl_cert is not None:
            self.ssl_options['cert'] = ssl_cert
        dimensions = self._set_dimensions({'component': 'mysql', 'service': 'mysql'}, instance)

        if not defaults_file:
            if not (mysql_sock or host):
                raise Exception("Mysql socket or host is required.")
            elif not user:
                raise Exception("Mysql user is required for connecting to socket or host.")

        db = self._connect(host, port, mysql_sock, user, password, defaults_file)

        # Metric collection
        self._collect_metrics(host, db, dimensions, options)
        self._collect_system_metrics(host, db, dimensions)
        db.close()

    @staticmethod
    def _get_config(instance):
        host = instance.get('server', '')
        user = instance.get('user', '')
        port = int(instance.get('port', 0))
        password = instance.get('pass', '')
        mysql_sock = instance.get('sock', '')
        ssl_ca = instance.get('ssl_ca', None)
        ssl_key = instance.get('ssl_key', None)
        ssl_cert = instance.get('ssl_cert', None)
        defaults_file = instance.get('defaults_file', '')
        options = instance.get('options', {})

        return host, port, user, password, mysql_sock, ssl_ca, ssl_key, ssl_cert, \
            defaults_file, options

    def _connect(self, host, port, mysql_sock, user, password, defaults_file):
        try:
            import pymysql
        except ImportError:
            raise Exception(
                "Cannot import PyMySQl module. Check the instructions "
                "to install this module at https://pypi.org/project/PyMySQL/")

        if defaults_file != '':
            db = pymysql.connect(read_default_file=defaults_file)
        elif mysql_sock != '':
            db = pymysql.connect(host=host,
                                 unix_socket=mysql_sock,
                                 user=user,
                                 passwd=password,
                                 ssl=self.ssl_options)
        elif port:
            db = pymysql.connect(host=host,
                                 port=port,
                                 user=user,
                                 passwd=password,
                                 ssl=self.ssl_options)
        else:
            db = pymysql.connect(host=host,
                                 user=user,
                                 passwd=password,
                                 ssl=self.ssl_options)
        self.log.debug("Connected to MySQL")

        return db

    def _collect_metrics(self, host, db, dimensions, options):
        cursor = db.cursor()
        cursor.execute("SHOW /*!50002 GLOBAL */ STATUS;")
        results = dict(cursor.fetchall())
        self._rate_or_gauge_statuses(STATUS_VARS, results, dimensions)
        cursor.close()
        del cursor

        # Compute InnoDB buffer metrics
        # Be sure InnoDB is enabled
        if 'Innodb_page_size' in results:
            page_size = self._collect_scalar('Innodb_page_size', results)
            innodb_buffer_pool_pages_total = self._collect_scalar(
                'Innodb_buffer_pool_pages_total', results)
            innodb_buffer_pool_pages_free = self._collect_scalar(
                'Innodb_buffer_pool_pages_free', results)
            innodb_buffer_pool_pages_total = innodb_buffer_pool_pages_total * page_size
            innodb_buffer_pool_pages_free = innodb_buffer_pool_pages_free * page_size
            innodb_buffer_pool_pages_used = (innodb_buffer_pool_pages_total -
                                             innodb_buffer_pool_pages_free)

            self.gauge("mysql.innodb.buffer_pool_free",
                       innodb_buffer_pool_pages_free, dimensions=dimensions)
            self.gauge("mysql.innodb.buffer_pool_used",
                       innodb_buffer_pool_pages_used, dimensions=dimensions)
            self.gauge("mysql.innodb.buffer_pool_total",
                       innodb_buffer_pool_pages_total, dimensions=dimensions)

        if 'galera_cluster' in options and options['galera_cluster']:
            value = self._collect_scalar('wsrep_cluster_size', results)
            self.gauge('mysql.galera.wsrep_cluster_size', value, dimensions=dimensions)

        if 'replication' in options and options['replication']:
            # get slave running form global status page
            slave_running = self._collect_string('Slave_running', results)
            if slave_running is not None:
                if slave_running.lower().strip() == 'on':
                    slave_running = 1
                else:
                    slave_running = 0
                self.gauge("mysql.replication.slave_running", slave_running, dimensions=dimensions)
            self._collect_dict(GAUGE,
                               {"Seconds_behind_master": "mysql.replication.seconds_behind_master"},
                               "SHOW SLAVE STATUS",
                               db,
                               dimensions=dimensions)

    def _rate_or_gauge_statuses(self, statuses, dbResults, dimensions):
        for status, metric in statuses.items():
            metric_name, metric_type = metric
            value = self._collect_scalar(status, dbResults)
            if value is not None:
                if metric_type == RATE:
                    self.rate(metric_name, value, dimensions=dimensions)
                elif metric_type == GAUGE:
                    self.gauge(metric_name, value, dimensions=dimensions)

    def _version_greater_502(self, db, host):
        # show global status was introduced in 5.0.2
        # some patch version numbers contain letters (e.g. 5.0.51a)
        # so let's be careful when we compute the version number
        if host in self.greater_502:
            return self.greater_502[host]

        greater_502 = False
        try:
            mysql_version = self._get_version(db, host)
            self.log.debug("MySQL version %s" % mysql_version)

            major = int(mysql_version[0])
            minor = int(mysql_version[1])
            patchlevel = int(re.match(r"([0-9]+)", mysql_version[2]).group(1))

            if (major, minor, patchlevel) > (5, 0, 2):
                greater_502 = True

        except Exception as exception:
            self.log.warn(
                "Cannot compute mysql version, assuming older than 5.0.2: %s" %
                str(exception))

        self.greater_502[host] = greater_502

        return greater_502

    def _get_version(self, db, host):
        if host in self.mysql_version:
            return self.mysql_version[host]

        # Get MySQL version
        cursor = db.cursor()
        cursor.execute('SELECT VERSION()')
        result = cursor.fetchone()
        cursor.close()
        del cursor
        # Version might include a description e.g. 4.1.26-log.
        # See http://dev.mysql.com/doc/refman/4.1/en/information-functions.html#function_version
        version = result[0].split('-')
        version = version[0].split('.')
        self.mysql_version[host] = version
        return version

    def _collect_scalar(self, key, dict):
        return self._collect_type(key, dict, float)

    def _collect_string(self, key, dict):
        return self._collect_type(key, dict, str)

    def _collect_type(self, key, dict, the_type):
        self.log.debug("Collecting data with %s" % key)
        if key not in dict:
            self.log.debug("%s returned None" % key)
            return None
        self.log.debug("Collecting done, value %s" % dict[key])
        return the_type(dict[key])

    def _collect_dict(self, metric_type, field_metric_map, query, db, dimensions):
        """Query status and get a dictionary back.

        Extract each field out of the dictionary
        and stuff it in the corresponding metric.

        query: show status...
        field_metric_map: {"Seconds_behind_master": "mysqlSecondsBehindMaster"}
        """
        try:
            cursor = db.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            if result is not None:
                for field in field_metric_map.keys():
                    # Get the agent metric name from the column name
                    metric = field_metric_map[field]
                    # Find the column name in the cursor description to identify the column index
                    # http://www.python.org/dev/peps/pep-0249/
                    # cursor.description is a tuple of (column_name, ..., ...)
                    try:
                        col_idx = [d[0].lower() for d in cursor.description].index(field.lower())
                        if result[col_idx] is not None:
                            if metric_type == GAUGE:
                                self.gauge(metric, float(result[col_idx]), dimensions=dimensions)
                            elif metric_type == RATE:
                                self.rate(metric, float(result[col_idx]), dimensions=dimensions)
                            else:
                                self.gauge(metric, float(result[col_idx]), dimensions=dimensions)
                        else:
                            self.log.debug("Received value is None for index %d" % col_idx)
                    except ValueError:
                        self.log.exception("Cannot find %s in the columns %s" %
                                           (field, cursor.description))
            cursor.close()
            del cursor
        except Exception:
            self.log.warn("Error while running %s\n%s" % (query, traceback.format_exc()))
            self.log.exception("Error while running %s" % query)

    def _collect_system_metrics(self, host, db, dimensions):
        pid = None
        # The server needs to run locally, accessed by TCP or socket
        if host in ["localhost", "127.0.0.1"] or db.port == int(0):
            pid = self._get_server_pid(db)

        if pid:
            self.log.debug("pid: %s" % pid)
            # At last, get mysql cpu data out of procfs
            try:
                # See http://www.kernel.org/doc/man-pages/online/pages/man5/proc.5.html
                # for meaning: we get 13 & 14: utime and stime, in clock ticks and convert
                # them with the right sysconf value (SC_CLK_TCK)
                proc_file = open("/proc/%d/stat" % pid)
                data = proc_file.readline()
                proc_file.close()
                fields = data.split(' ')
                ucpu = fields[13]
                kcpu = fields[14]
                clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])

                # Convert time to s (number of second of CPU used by mysql)
                # It's a counter, it will be divided by the period, multiply by 100
                # to get the percentage of CPU used by mysql over the period
                self.rate("mysql.performance.user_time", int(
                    (float(ucpu) / float(clk_tck)) * 100), dimensions=dimensions)
                self.rate("mysql.performance.kernel_time", int(
                    (float(kcpu) / float(clk_tck)) * 100), dimensions=dimensions)
            except Exception:
                self.log.warn("Error while reading mysql (pid: %s) procfs data\n%s" %
                              (pid, traceback.format_exc()))

    def _get_server_pid(self, db):
        pid = None

        # Try to get pid from pid file, it can fail for permission reason
        pid_file = None
        try:
            cursor = db.cursor()
            cursor.execute("SHOW VARIABLES LIKE 'pid_file'")
            pid_file = cursor.fetchone()[1]
            cursor.close()
            del cursor
        except Exception:
            self.log.warn("Error while fetching pid_file variable of MySQL.")

        if pid_file is not None:
            self.log.debug("pid file: %s" % str(pid_file))
            try:
                f = open(pid_file)
                pid = int(f.readline())
                f.close()
            except IOError:
                self.log.debug("Cannot read mysql pid file %s" % pid_file)

        # If pid has not been found, read it from ps
        if pid is None:
            try:
                if sys.platform.startswith("linux"):
                    ps = subprocess.Popen(['ps',
                                           '-C',
                                           'mysqld',
                                           '-o',
                                           'pid'],
                                          stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]
                    pslines = ps.decode('utf-8').strip().split('\n')
                    # First line is header, second line is mysql pid
                    if len(pslines) == 2 and pslines[1] != '':
                        pid = int(pslines[1])
            except Exception:
                self.log.exception("Error while fetching mysql pid from ps")

        return pid
