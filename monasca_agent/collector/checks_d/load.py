# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import psutil
import re
import subprocess
import sys

import monasca_agent.collector.checks as checks
import monasca_agent.common.util as util

log = logging.getLogger(__name__)


class Load(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Load, self).__init__(name, init_config, agent_config)

    def check(self, instance):
        """Capture load stats

        """

        dimensions = self._set_dimensions(None, instance)

        if util.Platform.is_linux():
            try:
                loadAvrgProc = open('/proc/loadavg', 'r')
                uptime = loadAvrgProc.readlines()
                loadAvrgProc.close()
            except Exception:
                log.exception('Cannot extract load using /proc/loadavg')
                return

            uptime = uptime[0]  # readlines() provides a list but we want a string

        elif sys.platform in ('darwin', 'sunos5') or sys.platform.startswith("freebsd"):
            # Get output from uptime
            try:
                uptime = subprocess.Popen(['uptime'],
                                          stdout=subprocess.PIPE,
                                          close_fds=True).communicate()[0]
            except Exception:
                log.exception('Cannot extract load using uptime')
                return

        # Split out the 3 load average values
        load = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]

        dimensions = self._set_dimensions(None)

        self.gauge('load.avg_1_min',
                   float(load[0]),
                   dimensions=dimensions)
        self.gauge('load.avg_5_min',
                   float(load[1]),
                   dimensions=dimensions)
        self.gauge('load.avg_15_min',
                   float(load[2]),
                   dimensions=dimensions)

        log.debug('Collected 3 load metrics')
