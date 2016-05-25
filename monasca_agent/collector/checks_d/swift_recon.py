import logging
import json
import re
import subprocess
import types

import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)


class SwiftRecon(checks.AgentCheck):

    GAUGES = [
        "storage.used",
        "storage.free",
        "storage.capacity",
        "md5.ring.matched",
        "md5.ring.not_matched",
        "md5.ring.errors",
        "md5.ring.all",
        "md5.swiftconf.matched",
        "md5.swiftconf.not_matched",
        "md5.swiftconf.errors",
        "md5.swiftconf.all",
        "container_updater.sweep_time",
        "object_updater.sweep_time",
    ]

    def prepare(self):
        self.diskusage = {}
        self.md5 = {}

    def swift_recon(self, *params):
        executable = 'swift-recon'
        if 'swift_recon' in self.init_config:
            executable = self.init_config['swift_recon']

        cmd = " ".join((executable, " ".join(params)))
        pipe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                universal_newlines=True)
        out = "".join(pipe.stdout.readlines())
        return out

    def swift_recon_json(self, *params):
        # call swift-recon in verbose mode
        output = self.swift_recon("-v", *params)

        # look for verbose output containing the raw JSON documents received
        # from the storage nodes
        result = {}
        for line in output.splitlines():
            m = re.match(r'^-> https?://([a-zA-Z0-9-.]+)\S*\s(.*)', line)
            if m:
                hostname, json_str = m.group(1), m.group(2).replace("'", '"')
                result[hostname] = json.loads(json_str)
        return result

    ############################################################################
    # helpers for parsing output of swift-recon

    def get_diskusage(self):
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

    def get_md5(self):
        if not self.md5:
            result = self.swift_recon("--md5")
            kind = 'undef'
            for line in result.splitlines():
                m = re.match(r'.* Checking ([\.a-zA-Z0-9_]+) md5sum', line)
                if m:
                    kind = m.group(1).replace(".", "")
                    self.md5[kind] = {}
                    continue
                pattern = (r"(\d+)/(\d+) hosts matched, (\d+) error\[s\] "
                           "while checking hosts")
                m = re.match(pattern, line)
                if m:
                    self.md5[kind]['matched'] = int(m.group(1))
                    self.md5[kind]['not_matched'] = (int(m.group(2)) -
                                                     int(m.group(1)))
                    self.md5[kind]['errors'] = int(m.group(3))
                    self.md5[kind]['all'] = (self.md5[kind]['matched'] +
                                             self.md5[kind]['not_matched'] +
                                             self.md5[kind]['errors'])
                else:
                    continue
        return self.md5

    def get_updater_sweeps(self, server_type):
        data = self.swift_recon_json(server_type, "--updater")
        result = {}
        for hostname in data:
            result[hostname] = data[hostname][server_type + "_updater_sweep"]
        return result

    ############################################################################
    # helpers for accessing parsed output of swift-recon

    def storage(self, value):
        self.get_diskusage()
        if value in self.diskusage:
            return self.diskusage[value]

    def consistency(self, kind, value):
        self.get_md5()
        if kind in self.md5:
            if value in self.md5[kind]:
                return self.md5[kind][value]

    ############################################################################
    # one method for each exposed metric

    # storage capacity

    def storage_free(self):
        return self.storage('free')

    def storage_used(self):
        return self.storage('used')

    def storage_capacity(self):
        return self.storage('capacity')

    # configuration consistency

    def md5_ring_matched(self):
        return self.consistency('ring', 'matched')

    def md5_ring_not_matched(self):
        return self.consistency('ring', 'not_matched')

    def md5_ring_errors(self):
        return self.consistency('ring', 'errors')

    def md5_ring_all(self):
        return self.consistency('ring', 'all')

    def md5_swiftconf_matched(self):
        return self.consistency('swiftconf', 'matched')

    def md5_swiftconf_not_matched(self):
        return self.consistency('swiftconf', 'not_matched')

    def md5_swiftconf_errors(self):
        return self.consistency('swiftconf', 'errors')

    def md5_swiftconf_all(self):
        return self.consistency('swiftconf', 'all')

    # eventual consistency 1: updater sweep timings

    def container_updater_sweep_time(self):
        return self.get_updater_sweeps('container')

    def object_updater_sweep_time(self):
        return self.get_updater_sweeps('object')

    ############################################################################
    # collect metrics

    def check(self, instance):
        self.prepare()
        dimensions = self._set_dimensions(None, instance)

        for metric in self.GAUGES:
            log.debug("Checking metric {0}".format(metric))

            value = eval("self." + metric.replace(".", "_") + "()")

            if metric.startswith('storage'):
                metric = metric + '_bytes'
            metric = self.normalize(metric.lower(), 'swift.cluster')

            # value may be a dictionary with values by storage node...
            if isinstance(value, dict):
                for hostname in value:
                    self.submit_gauge(metric, hostname, value[hostname], dimensions)
            else:
                self.submit_gauge(metric, None, value, dimensions)

    def submit_gauge(self, metric, hostname, value, dimensions):
        assert(type(value) in (types.IntType, types.LongType,
                               types.FloatType))

        if hostname:
            dim = dimensions.copy()
            dim["storage_node"] = hostname
            log.debug("Sending {0}={1} for storage node {2}".format(metric, value, hostname))
        else:
            dim = dimensions
            log.debug("Sending {0}={1}".format(metric, value))

        self.gauge(metric, value, dimensions=dim)
