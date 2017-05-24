# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import re
import subprocess
import sys

import monasca_agent.collector.checks as checks
from monasca_agent.common.psutil_wrapper import psutil
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

        #
        # Normalize the load averages by number of cores
        # so the metric is useful for alarming across
        # hosts with varying core numbers
        #
        num_cores = psutil.cpu_count(logical=True)

        self.gauge('load.avg_1_min',
                   round((float(load[0]) / num_cores), 3),
                   dimensions=dimensions)
        self.gauge('load.avg_5_min',
                   round((float(load[1]) / num_cores), 3),
                   dimensions=dimensions)
        self.gauge('load.avg_15_min',
                   round((float(load[2]) / num_cores), 3),
                   dimensions=dimensions)

        log.debug("Collected 3 load metrics (normalized by {} cores)".format(num_cores))
