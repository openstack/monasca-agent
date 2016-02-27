# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

import monasca_agent.collector.checks as checks
from monasca_agent.common.util import timeout_command

VSQL_PATH = '/opt/vertica/bin/vsql'


class Vertica(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Vertica, self).__init__(name, init_config, agent_config)

    @staticmethod
    def _get_config(instance):
        user = instance.get('user', 'mon_api')
        password = instance.get('password', 'password')
        service = instance.get('service', '')
        timeout = int(instance.get('timeout', 3))

        return user, password, service, timeout

    def check(self, instance):
        user, password, service, timeout = self._get_config(instance)

        dimensions = self._set_dimensions({'component': 'vertica', 'service': service}, instance)

        value = self._connect_health(user, password, timeout)
        self.gauge('vertica.db.connection_status', value, dimensions=dimensions)

    def _connect_health(self, user, password, timeout):
        output = timeout_command(
            [VSQL_PATH, "-U", user, "-w", password, "-c", "select version();"], timeout)
        if (output is not None) and ('Vertica Analytic Database' in output):
            # healthy
            return 0
        else:
            return 1
