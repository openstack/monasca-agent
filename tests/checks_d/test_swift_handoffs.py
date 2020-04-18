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

from unittest import mock
import unittest
from collections import defaultdict
from tempfile import mkdtemp
import shutil
import os
from array import array

from monasca_agent.collector.checks_d import swift_handoffs


class FakeLogger(object):
    def __init__(self):
        self.log = {'error': [],
                    'warning': []}

    def _write_msg(self, msg, key):
        self.log[key].append(msg)

    def error(self, msg):
        self._write_msg(msg, 'error')

    def warning(self, msg):
        self._write_msg(msg, 'warning')

    def get_loglines(self, key):
        return self.log[key]


class MockSwiftHandoffs(swift_handoffs.SwiftHandoffs):
    def __init__(self):
        swift_handoffs.swift_loaded = True
        super(MockSwiftHandoffs, self).__init__(
            name='swift_handoffs',
            init_config={},
            instances=[],
            agent_config={}
        )
        self.log = FakeLogger()
        self.reset_gauge()

    def gauge(self, key, value, dimensions, *args, **kwargs):
        self.gauge_called = True
        self.gauge_calls[key].append(value)
        for k, v in dimensions.items():
            self.dimensions[k].add(v)

    def reset_gauge(self):
        self.gauge_called = False
        self.gauge_calls = defaultdict(list)
        self.dimensions = defaultdict(set)


class MockRing(object):
    def __init__(self, *args):
        self.devs = [
            {u'device': u'sdb1', u'id': 0, u'ip': u'127.0.0.1',
             u'meta': u'', u'port': 6010, u'region': 1,
             u'replication_ip': u'127.0.0.1', u'replication_port': 6010,
             u'weight': 1.0, u'zone': 1},
            {u'device': u'sdb2', u'id': 1, u'ip': u'127.0.0.1',
             u'meta': u'', u'port': 6010, u'region': 1,
             u'replication_ip': u'127.0.0.1', u'replication_port': 6010,
             u'weight': 1.0, u'zone': 1},
            {u'device': u'sdb3', u'id': 2, u'ip': u'127.0.0.2',
             u'meta': u'', u'port': 6010, u'region': 1,
             u'replication_ip': u'127.0.0.2', u'replication_port': 6010,
             u'weight': 1.0, u'zone': 1},
            {u'device': u'sdb4', u'id': 3, u'ip': u'127.0.0.2',
             u'meta': u'', u'port': 6010, u'region': 1,
             u'replication_ip': u'127.0.0.2', u'replication_port': 6010,
             u'weight': 1.0, u'zone': 1}]

        self._replica2part2dev_id = [
            array('H', [3, 0, 2, 1, 2, 3, 0, 1, 3, 3, 0, 1, 2, 1, 0, 2]),
            array('H', [0, 2, 1, 3, 1, 0, 2, 3, 0, 0, 2, 3, 1, 3, 2, 1]),
            array('H', [2, 1, 3, 0, 3, 2, 1, 0, 2, 2, 1, 0, 3, 0, 1, 3])]


class SwiftHandoffsTest(unittest.TestCase):
    def setUp(self):
        super(SwiftHandoffsTest, self).setUp()
        self.swift_handoffs = MockSwiftHandoffs()
        self.tmpdir = mkdtemp()
        self.datadir = os.path.join(self.tmpdir, 'datadir')
        self.ring = os.path.join(self.tmpdir, 'object.ring.gz')
        os.mkdir(self.datadir)
        os.mknod(self.ring)
        self.expected_dev2part = {
            u'sdb1': {0, 1, 3, 5, 6, 7, 8, 9, 10, 11, 13, 14},
            u'sdb2': {1, 2, 3, 4, 6, 7, 10, 11, 12, 13, 14, 15},
            u'sdb3': {0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 14, 15},
            u'sdb4': {0, 2, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15}}

        self.expected_handoffs = {
            u'sdb1': {2, 4, 12, 15},
            u'sdb2': {0, 5, 8, 9},
            u'sdb3': {3, 7, 11, 13},
            u'sdb4': {1, 6, 10, 14}}

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @mock.patch('monasca_agent.collector.checks_d.swift_handoffs.Ring',
                MockRing)
    def test_get_ring_and_datadir(self):
        def do_test(path, expected_ringname, expected_datadir):
            _ring, name, datadir = swift_handoffs.get_ring_and_datadir(path)
            self.assertEqual(name, expected_ringname)
            self.assertEqual(datadir, expected_datadir)

        for prefix in ('/etc/swift/{}', './{}', 'some/other/loc/{}'):
            test_cases = (
                (prefix.format('object.ring.gz'), 'object', 'objects'),
                (prefix.format('object-1.ring.gz'), 'object-1', 'objects-1'),
                (prefix.format('object-2.ring.gz'), 'object-2', 'objects-2'),
                (prefix.format('object-50.ring.gz'), 'object-50', 'objects-50'),
                (prefix.format('container.ring.gz'), 'container', 'containers'),
                (prefix.format('account.ring.gz'), 'account', 'accounts'))
            for path, ex_ringname, ex_datadir in test_cases:
                do_test(path, ex_ringname, ex_datadir)

    def test_check_missing_options(self):
        # missing device (path to devices mount point), and default doesn't
        # exist
        instance = {'ring': self.ring}
        with mock.patch('os.path.exists', return_value=False):
            self.swift_handoffs.check(instance)
        self.assertIn('devices must exist or be a directory',
                      self.swift_handoffs.log.get_loglines('error'))
        self.swift_handoffs.log = FakeLogger()

        # a device that isn't a dir
        instance = {'ring': self.ring,
                    'devices': '{}/random'.format(self.datadir)}
        with mock.patch('os.path.exists', return_value=True), \
                mock.patch('os.path.isdir', return_value=False):
            self.swift_handoffs.check(instance)
        self.assertIn('devices must exist or be a directory',
                      self.swift_handoffs.log.get_loglines('error'))
        self.swift_handoffs.log = FakeLogger()

        # missing ring
        instance = {'devices': self.datadir}
        self.swift_handoffs.check(instance)
        self.assertIn('ring must exist',
                      self.swift_handoffs.log.get_loglines('error'))
        self.swift_handoffs.log = FakeLogger()

        instance = {'devices': self.datadir, 'ring': self.ring}
        with mock.patch('os.path.isfile', return_value=False):
            self.swift_handoffs.check(instance)
        self.assertIn('ring must exist',
                      self.swift_handoffs.log.get_loglines('error'))
        self.swift_handoffs.log = FakeLogger()

        # granularity defaults to server. If specified it only allows either
        # server or drive. Anything else will be an error.
        instance = {'devices': self.datadir, 'ring': self.ring,
                    'granularity': 'something else'}
        self.swift_handoffs.check(instance)
        self.assertIn("granularity must be either 'server' or 'drive'",
                      self.swift_handoffs.log.get_loglines('error'))

    def setup_partitions(self, devices):
        for dev in devices:
            for part in devices[dev]:
                path = os.path.join(self.datadir, dev, 'objects', str(part))
                os.makedirs(path)

    @mock.patch('monasca_agent.collector.checks_d.swift_handoffs.Ring',
                MockRing)
    def test_all_paritions_in_correct_place(self):
        self.setup_partitions(self.expected_dev2part)
        instances = {'devices': self.datadir, 'ring': self.ring,
                     'granularity': 'device'}
        self.swift_handoffs.check(instances)

        self.assertTrue(self.swift_handoffs.gauge_called)
        for metric in ('swift.partitions.primary_count',
                       'swift.partitions.handoff_count'):
            # metric was called
            self.assertIn(metric, self.swift_handoffs.gauge_calls)

            # Each metric was called once per device, so 4 times.
            self.assertEqual(len(self.swift_handoffs.gauge_calls[metric]), 4)

        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.primary_count'],
            [12, 12, 12, 12])
        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.handoff_count'],
            [0, 0, 0, 0])

        # each device should be a device metric
        self.assertSetEqual(self.swift_handoffs.dimensions['device'],
                            {'sdb3', 'sdb2', 'sdb1', 'sdb4'})

    @mock.patch('monasca_agent.collector.checks_d.swift_handoffs.Ring',
                MockRing)
    def test_all_paritions_and_all_handoffs(self):

        for device in self.expected_dev2part:
            self.expected_dev2part[device].update(
                self.expected_handoffs[device])
        self.setup_partitions(self.expected_dev2part)
        instances = {'devices': self.datadir, 'ring': self.ring,
                     'granularity': 'device'}
        self.swift_handoffs.check(instances)

        self.assertTrue(self.swift_handoffs.gauge_called)
        for metric in ('swift.partitions.primary_count',
                       'swift.partitions.handoff_count'):
            # metric was called
            self.assertIn(metric, self.swift_handoffs.gauge_calls)

            # Each metric was called once per device, so 4 times.
            self.assertEqual(len(self.swift_handoffs.gauge_calls[metric]), 4)

        # all primaries were on each drive
        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.primary_count'],
            [12, 12, 12, 12])
        # so were 4 handoffs
        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.handoff_count'],
            [4, 4, 4, 4])

        # each device should be a device metric
        self.assertSetEqual(self.swift_handoffs.dimensions['device'],
                            {'sdb3', 'sdb2', 'sdb1', 'sdb4'})

    @mock.patch('monasca_agent.collector.checks_d.swift_handoffs.Ring',
                MockRing)
    def test_some_paritions_in_correct_no_handoffs(self):
        # Are parition will only be created on a drive if an object in that
        # partition has a been PUT into the cluster. So a partition missing
        # on a drive isn't bad (though in a realy cluster weird) but isn't
        # a failure.

        # let's remove a bunch of partitions from each cluster.
        for drive in self.expected_dev2part:
            self.expected_dev2part[drive].difference_update(
                list(self.expected_dev2part[drive])[:5])
        self.setup_partitions(self.expected_dev2part)
        instances = {'devices': self.datadir, 'ring': self.ring,
                     'granularity': 'device'}
        self.swift_handoffs.check(instances)

        self.assertTrue(self.swift_handoffs.gauge_called)
        for metric in ('swift.partitions.primary_count',
                       'swift.partitions.handoff_count'):
            # metric was called
            self.assertIn(metric, self.swift_handoffs.gauge_calls)

            # Each metric was called once per device, so 4 times.
            self.assertEqual(len(self.swift_handoffs.gauge_calls[metric]), 4)

        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.primary_count'],
            [7, 7, 7, 7])
        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.handoff_count'],
            [0, 0, 0, 0])

        # each device should be a device metric
        self.assertSetEqual(self.swift_handoffs.dimensions['device'],
                            {'sdb3', 'sdb2', 'sdb1', 'sdb4'})

    @mock.patch('monasca_agent.collector.checks_d.swift_handoffs.Ring',
                MockRing)
    def test_some_paritions_and_some_handoffs_less_devices(self):
        # Are parition will only be created on a drive if an object in that
        # partition has a been PUT into the cluster. So a partition missing
        # on a drive isn't bad (though in a realy cluster weird) but isn't
        # a failure.

        # let's remove a bunch of partitions from each cluster and 2 of the
        # devices
        for drive in 'sdb1', 'sdb4':
            self.expected_dev2part.pop(drive)

        for drive in self.expected_dev2part:
            self.expected_dev2part[drive].difference_update(
                list(self.expected_dev2part[drive])[:5])
            self.expected_dev2part[drive].update(
                list(self.expected_handoffs[drive])[:1])
        self.setup_partitions(self.expected_dev2part)
        instances = {'devices': self.datadir, 'ring': self.ring,
                     'granularity': 'device'}
        self.swift_handoffs.check(instances)

        self.assertTrue(self.swift_handoffs.gauge_called)
        for metric in ('swift.partitions.primary_count',
                       'swift.partitions.handoff_count'):
            # metric was called
            self.assertIn(metric, self.swift_handoffs.gauge_calls)

            # Each metric was called once per device, so 4 times.
            self.assertEqual(len(self.swift_handoffs.gauge_calls[metric]), 2)

        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.primary_count'],
            [7, 7])
        self.assertListEqual(
            self.swift_handoffs.gauge_calls['swift.partitions.handoff_count'],
            [1, 1])

        # each device should be a device metric
        self.assertSetEqual(self.swift_handoffs.dimensions['device'],
                            {'sdb3', 'sdb2'})
