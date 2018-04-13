# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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

"""Check the performance counters from SQL Server.

"""
import traceback

from monasca_agent.collector.checks import AgentCheck


ALL_INSTANCES = 'ALL'
VALID_METRIC_TYPES = ('gauge', 'rate')


class SQLServer(AgentCheck):
    METRICS = [
        ('sqlserver.buffer.cache_hit_ratio', 'gauge', 'Buffer cache hit ratio'),
        ('sqlserver.buffer.page_life_expectancy', 'gauge', 'Page life expectancy'),
        ('sqlserver.stats.batch_requests', 'gauge', 'Batch Requests/sec'),
        ('sqlserver.stats.sql_compilations', 'gauge', 'SQL Compilations/sec'),
        ('sqlserver.stats.sql_recompilations', 'gauge', 'SQL Re-Compilations/sec'),
        ('sqlserver.stats.connections', 'gauge', 'User connections'),
        ('sqlserver.stats.lock_waits', 'gauge', 'Lock Waits/sec', '_Total'),
        ('sqlserver.access.page_splits', 'gauge', 'Page Splits/sec'),
        ('sqlserver.stats.procs_blocked', 'gauge', 'Processes Blocked'),
        ('sqlserver.buffer.checkpoint_pages', 'gauge', 'Checkpoint pages/sec')
    ]

    def __init__(self, name, init_config, agent_config):
        AgentCheck.__init__(self, name, init_config, agent_config)

        # Load any custom metrics from conf.d/sqlserver.yaml
        for row in init_config.get('custom_metrics', []):
            if row['type'] not in VALID_METRIC_TYPES:
                self.log.error('%s has an invalid metric type: %s' % (row['name'], row['type']))
            self.METRICS.append((row['name'], row['type'], row['counter_name'],
                                 row.get('instance_name', ''), row.get('tag_by', None)))

        # Cache connections
        self.connections = {}

    @staticmethod
    def _conn_key(host, username, password, database):
        """Return a key to use for the connection cache.

        """
        return '%s:%s:%s:%s' % (host, username, password, database)

    @staticmethod
    def _conn_string(host, username, password, database):
        """Return a connection string to use with adodbapi.

        """
        conn_str = 'Provider=SQLOLEDB;Data Source=%s;Initial Catalog=%s;' % (host, database)
        if username:
            conn_str += 'User ID=%s;' % (username)
        if password:
            conn_str += 'Password=%s;' % (password)
        if not username and not password:
            conn_str += 'Integrated Security=SSPI;'
        return conn_str

    def check(self, instance):
        try:
            import adodbapi
        except ImportError:
            raise Exception("Unable to import adodbapi module.")

        host = instance.get('host', '127.0.0.1;1433')
        username = instance.get('username')
        password = instance.get('password')
        database = instance.get('database', 'master')
        conn_key = self._conn_key(host, username, password, database)
        dimensions = self._set_dimensions(None, instance)

        if conn_key not in self.connections:
            try:
                conn_str = self._conn_string(host, username, password, database)
                conn = adodbapi.connect(conn_str)
                self.connections[conn_key] = conn
            except Exception:
                cx = "%s - %s" % (host, database)
                raise Exception("Unable to connect to SQL Server for instance %s.\n %s"
                                % (cx, traceback.format_exc()))

        conn = self.connections[conn_key]
        cursor = conn.cursor()
        self._fetch_metrics(cursor, dimensions)

    def _fetch_metrics(self, cursor, custom_dimensions):
        """Fetch the metrics from the sys.dm_os_performance_counters table.

        """
        for metric in self.METRICS:
            # Normalize all rows to the same size for easy of use
            if len(metric) == 3:
                metric = metric + ('', None)
            elif len(metric) == 4:
                metric = metric + (None,)

            mname, mtype, counter, instance_n, tag_by = metric

            # For "ALL" instances, we run a separate method because we have
            # to loop over multiple results and tag the metrics
            if instance_n == ALL_INSTANCES:
                try:
                    self._fetch_all_instances(metric, cursor, custom_dimensions)
                except Exception:
                    self.log.exception('Unable to fetch metric: %s' % mname)
                    self.log.warn('Unable to fetch metric: %s' % mname)
            else:
                try:
                    cursor.execute("""
                        select cntr_value
                        from sys.dm_os_performance_counters
                        where counter_name = ?
                        and instance_name = ?
                    """, (counter, instance_n))
                    (value,) = cursor.fetchone()
                except Exception:
                    self.log.exception('Unable to fetch metric: %s' % mname)
                    self.log.warn('Unable to fetch metric: %s' % mname)
                    continue

                # Save the metric
                metric_func = getattr(self, mtype)
                metric_func(mname, value, dimensions=custom_dimensions)

    def _fetch_all_instances(self, metric, cursor, dimensions):
        mname, mtype, counter, instance_n, tag_by = metric
        cursor.execute("""
            select instance_name, cntr_value
            from sys.dm_os_performance_counters
            where counter_name = ?
            and instance_name != '_Total'
        """, (counter,))
        rows = cursor.fetchall()

        for instance_name, cntr_value in rows:
            value = cntr_value
            dimensions.update({tag_by: instance_name.strip()})
            metric_func = getattr(self, mtype)
            metric_func(mname, value, dimensions=dimensions)
