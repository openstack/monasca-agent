import commands
import types
import logging
import re

import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)

class SwiftRecon(checks.AgentCheck):

    GAUGES = [
            "storage.used",
            "storage.free",
            "storage.capacity"
            ]

    def swift_recon(self, params):
        command = 'swift-recon'

        if 'swift_recon' in self.init_config:
            command = self.init_config['swift_recon']

        status, result = commands.getstatusoutput(command + " " + params)
        return result

    diskusage = {}
    def get_diskusage (self):
        if not self.diskusage:
            result = self.swift_recon("--diskusage")
            for line in result.splitlines():
                m = re.match(r'Disk usage: space (\w+): (\d+) of (\d+)', line)
                if m:
                    if m.group(1) == 'used':
                        self.diskusage['used'] = long(m.group(2))
                        self.diskusage['capacity'] = long(m.group(3))
                    elif m.group(1) == 'free':
                        self.diskusage['free'] = long(m.group(2))
                else:
                    continue
        return self.diskusage

    def storage(self, value):
        self.get_diskusage()
        if value in self.diskusage:
            return self.diskusage[value]

    def storage_free(self):
        return self.storage('free')

    def storage_used(self):
        return self.storage('used')

    def storage_capacity(self):
        return self.storage('capacity')

    def check(self, instance):
        dimensions = self._set_dimensions(None, instance)

        for metric in self.GAUGES:
            log.debug("Checking metric {0}".format(metric))

            value = eval("self." + metric.replace(".", "_")+"()")

            assert type(value) in (types.IntType, types.LongType, types.FloatType)

            metric = metric + '_bytes'
            metric = self.normalize(metric.lower(), 'swift.cluster')
            log.debug("Sending {0}={1}".format(metric, value))
            self.gauge(metric, value, dimensions=dimensions)
