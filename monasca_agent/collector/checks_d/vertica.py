# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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

import monasca_agent.collector.checks as checks
from monasca_agent.common.util import timeout_command

LICENSE_STATUS_QUERY = "SELECT COALESCE(" \
                       "(SELECT usage_percent * 100 " \
                       "FROM v_catalog.license_audits " \
                       "WHERE audited_data ='Total' " \
                       "ORDER BY audit_start_timestamp " \
                       "DESC LIMIT 1), 0) license_usage_percent;"

NODE_METRICS_QUERY = "SELECT node_state " \
                     "FROM NODES " \
                     "WHERE node_name = '{0}';"

PROJECTION_METRICS_QUERY = "SELECT projection_name, wos_used_bytes, ros_count, " \
                           "COALESCE(tuple_mover_moveouts, 0) tuple_mover_moveouts, " \
                           "COALESCE(tuple_mover_mergeouts, 0) tuple_mover_mergeouts " \
                           "FROM projection_storage " \
                           "LEFT JOIN (SELECT projection_id, " \
                           "SUM(case when operation_name = " \
                           "'Moveout' then 1 else 0 end) tuple_mover_moveouts, " \
                           "SUM(case when operation_name = " \
                           "'Mergeout' then 1 else 0 end) tuple_mover_mergeouts " \
                           "FROM tuple_mover_operations " \
                           "WHERE node_name = '{0}' and is_executing = 't' " \
                           "GROUP BY projection_id) tm " \
                           "ON projection_storage.projection_id = tm.projection_id " \
                           "WHERE node_name = '{0}';"

RESOURCE_METRICS_QUERY = "SELECT COALESCE(request_queue_depth, 0) request_queue_depth, " \
                         "wos_used_bytes, " \
                         "COALESCE(resource_request_reject_count, 0) resource_rejections, " \
                         "COALESCE(disk_space_request_reject_count, 0) disk_space_rejections " \
                         "FROM resource_usage " \
                         "WHERE node_name = '{0}';"

RESOURCE_POOL_METRICS_QUERY = "SELECT pool_name, memory_size_actual_kb, " \
                              "memory_inuse_kb, running_query_count, " \
                              "COALESCE(rejection_count, 0) rejection_count " \
                              "FROM resource_pool_status " \
                              "LEFT JOIN (" \
                              "SELECT pool_id, COUNT(*) rejection_count " \
                              "FROM resource_rejections " \
                              "WHERE node_name = '{0}' " \
                              "GROUP BY pool_id) rj " \
                              "ON resource_pool_status.POOL_OID = rj.POOL_ID " \
                              "WHERE node_name = '{0}'"


class Vertica(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Vertica, self).__init__(name, init_config, agent_config)
        self._last_connection_status = 1

    @staticmethod
    def _get_config(instance):
        user = instance.get('user')
        password = instance.get('password')
        service = instance.get('service')
        node_name = instance.get('node_name')
        timeout = int(instance.get('timeout'))

        return user, password, service, node_name, timeout

    def check(self, instance):
        user, password, service, node_name, timeout = self._get_config(instance)

        dimensions = self._set_dimensions({'component': 'vertica', 'service': service}, instance)
        query = self._build_query(node_name)

        results, connection_status = self._query_database(user, password, timeout, query)

        if connection_status != 0:
            self.gauge('vertica.connection_status', 1, dimensions=dimensions)
            self._last_connection_status = 1
        else:
            if self._last_connection_status > 0:
                # report successful connection status when last status not success
                self.gauge('vertica.connection_status', 0, dimensions=dimensions)
            self._last_connection_status = 0
            results = results.split('\n')

            # Database metrics
            self._report_license_status(results[0], dimensions)

            # Node metrics
            dimensions['node_name'] = node_name

            self._report_node_status(results[1], dimensions)

            self._report_resource_metrics(results[2], dimensions)

            self._report_projection_metrics(results[3], dimensions)

            self._report_resource_pool_metrics(results[4], dimensions)

    def _query_database(self, user, password, timeout, query):
        stdout, stderr, return_code = timeout_command(["/opt/vertica/bin/vsql",
                                                       "-U", user, "-w",
                                                       password, "-A", "-R",
                                                       "|", "-t", "-F", ",", "-x"],
                                                      timeout,
                                                      command_input=query)
        if return_code == 0:
            # remove trailing newline
            stdout = stdout.rstrip()
            return stdout, 0
        else:
            self.log.error(
                "Error querying vertica with return code of {0} and error {1}".format(
                    return_code, stderr))
            return stderr, 1

    def _build_query(self, node_name):
        query = ''
        query += LICENSE_STATUS_QUERY
        query += NODE_METRICS_QUERY.format(node_name)
        query += RESOURCE_METRICS_QUERY.format(node_name)
        query += PROJECTION_METRICS_QUERY.format(node_name)
        query += RESOURCE_POOL_METRICS_QUERY.format(node_name)
        return query

    def _results_to_dict(self, results):
        return [dict(entry.split(',') for entry in dictionary.split('|'))
                for dictionary in results.split('||')]

    def _report_node_status(self, results, dimensions):
        result = self._results_to_dict(results)
        node_status = result[0]['node_state']
        status_metric = 0 if node_status == 'UP' else 1
        self.gauge(
            'vertica.node_status',
            status_metric,
            dimensions=dimensions,
            value_meta=result[0])

    def _report_projection_metrics(self, results, dimensions):
        results = self._results_to_dict(results)
        projection_metric_name = 'vertica.projection.'
        for result in results:
            projection_dimensions = dimensions.copy()
            projection_dimensions['projection_name'] = result['projection_name']
            # when nothing has been written, wos_used_bytes is empty.
            # Needs to convert it to zero.
            if not result['wos_used_bytes']:
                result['wos_used_bytes'] = '0'
            self.gauge(projection_metric_name + 'wos_used_bytes', int(result['wos_used_bytes']),
                       dimensions=projection_dimensions)
            self.gauge(projection_metric_name + 'ros_count',
                       int(result['ros_count']), dimensions=projection_dimensions)
            self.rate(projection_metric_name + 'tuple_mover_moveouts',
                      int(result['tuple_mover_moveouts']), dimensions=projection_dimensions)
            self.rate(projection_metric_name + 'tuple_mover_mergeouts',
                      int(result['tuple_mover_mergeouts']), dimensions=projection_dimensions)

    def _report_resource_metrics(self, results, dimensions):
        results = self._results_to_dict(results)
        resource_metric_name = 'vertica.resource.'
        resource_metrics = results[0]
        for metric_name, metric_value in resource_metrics.items():
            if metric_name in ['resource_rejections', 'disk_space_rejections']:
                self.rate(
                    resource_metric_name +
                    metric_name,
                    int(metric_value),
                    dimensions=dimensions)
            else:
                if metric_name == 'wos_used_bytes' and not metric_value:
                    # when nothing has been written, wos_used_bytes is empty.
                    # Needs to convert it to zero.
                    metric_value = '0'
                self.gauge(
                    resource_metric_name +
                    metric_name,
                    int(metric_value),
                    dimensions=dimensions)

    def _report_resource_pool_metrics(self, results, dimensions):
        results = self._results_to_dict(results)
        resource_pool_metric_name = 'vertica.resource.pool.'
        for result in results:
            resource_pool_dimensions = dimensions.copy()
            resource_pool_dimensions['resource_pool'] = result['pool_name']
            self.gauge(resource_pool_metric_name + 'memory_size_actual_kb',
                       int(result['memory_size_actual_kb']), dimensions=resource_pool_dimensions)
            self.gauge(resource_pool_metric_name + 'memory_inuse_kb',
                       int(result['memory_inuse_kb']), dimensions=resource_pool_dimensions)
            self.gauge(resource_pool_metric_name + 'running_query_count',
                       int(result['running_query_count']), dimensions=resource_pool_dimensions)
            self.rate(resource_pool_metric_name + 'rejection_count', int(result['rejection_count']),
                      dimensions=resource_pool_dimensions)

    def _report_license_status(self, results, dimensions):
        results = self._results_to_dict(results)
        license_status = results[0]
        self.gauge('vertica.license_usage_percent', float(license_status['license_usage_percent']),
                   dimensions=dimensions)
