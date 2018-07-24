import errno
import os
import sys

import monasca_agent.collector.checks as checks

from collections import defaultdict


class StubRing(object):
    # this is a stub ring class which is used as a mock out point when
    # unit testing this check plugin as swift is a run time dependency, but
    # don't necessary want it installed for all tests.
    pass


try:
    from swift.common.ring import Ring
    swift_loaded = True
except ImportError:
    Ring = StubRing
    swift_loaded = False

NO_SWIFT_ERROR_EXIT = 1


def get_ring_and_datadir(path):
    """:param path: path to ring

    :returns: a tuple, (ring, datadir)
    """
    ring_name = os.path.basename(path).split('.')[0]
    if '-' in ring_name:
        datadir, policy_index = ring_name.rsplit('-', 1)
    else:
        datadir, policy_index = ring_name, None
    datadir += 's'
    if policy_index:
        datadir += '-{}'.format(policy_index)

    return Ring(path), ring_name, datadir


class SwiftHandoffs(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config, instances=None):
        super(SwiftHandoffs, self).__init__(name, init_config, agent_config,
                                            instances)
        global swift_loaded
        if not swift_loaded:
            self.log.error('Swift python module not found. The python swift '
                           'module is a runtime dependency')
            sys.exit(NO_SWIFT_ERROR_EXIT)

    def check(self, instance):
        device_root = instance.get('devices', '/srv/node')
        if not os.path.exists(device_root) or not os.path.isdir(device_root):
            self.log.error('devices must exist or be a directory')
            return None

        ring_path = instance.get('ring')
        if not ring_path or not os.path.exists(ring_path) \
                or not os.path.isfile(ring_path):
            self.log.error('ring must exist')
            return None

        granularity = instance.get('granularity', 'server').lower()
        if granularity not in ('server', 'device'):
            self.log.error("granularity must be either 'server' or 'drive'")
            return None

        ring, ring_name, datadir = get_ring_and_datadir(ring_path)

        dev2parts = defaultdict(set)
        for replica, part2dev in enumerate(ring._replica2part2dev_id):
            for part, device_id in enumerate(part2dev):
                dev2parts[ring.devs[device_id]['device']].add(part)

        # print dev2parts
        primary_count = defaultdict(int)
        handoffs = defaultdict(set)
        device_dirs = os.listdir(device_root)
        for device_dir in device_dirs:
            parts_dir = os.path.join(device_root, device_dir, datadir)
            try:
                parts = os.listdir(parts_dir)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    continue
                else:
                    raise
            for part in parts:
                if not part.isdigit():
                    continue
                part = int(part)
                if part in dev2parts[device_dir]:
                    primary_count[device_dir] += 1
                else:
                    handoffs[device_dir].add(part)

        dimensions = {u'ring': ring_name, u'service': u'swift'}
        dimensions = self._set_dimensions(dimensions, instance)
        if granularity == 'server':
            self.gauge(u'swift.partitions.primary_count',
                       sum(primary_count.values()), dimensions)
            self.gauge('swift.partitions.handoff_count',
                       sum(map(len, handoffs.values())), dimensions)
        else:
            for device in device_dirs:
                dimensions['device'] = device
                self.gauge(u'swift.partitions.primary_count',
                           primary_count[device], dimensions)
                self.gauge('swift.partitions.handoff_count',
                           len(handoffs[device]), dimensions)
