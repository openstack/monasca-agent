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

from monasca_agent.collector.checks_d import swift_recon


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


class MockSwiftRecon(swift_recon.SwiftRecon):
    def __init__(self):
        super(MockSwiftRecon, self).__init__(
            name='swift_recon',
            init_config={},
            instances=[],
            agent_config={}
        )
        self.log = FakeLogger()
        self.scout_returns = []
        self.reset_gauge()

    def scout_host(self, base_url, recon_type, timeout=5):
        if not self.scout_returns:
            raise swift_recon.SwiftReconException("Mock error")
        if isinstance(self.scout_returns[0], swift_recon.SwiftReconException):
            raise self.scout_returns.pop(0)
        else:
            return self.scout_returns.pop(0)

    def gauge(self, key, value, dimensions, *args, **kwargs):
        self.gauge_called = True
        self.gauge_calls[key].append(value)
        for k, v in dimensions.items():
            self.dimensions[k].add(v)

    def reset_gauge(self):
        self.gauge_called = False
        self.gauge_calls = defaultdict(list)
        self.dimensions = defaultdict(set)


class SwiftReconTest(unittest.TestCase):
    def setUp(self):
        super(SwiftReconTest, self).setUp()
        self.swiftrecon = MockSwiftRecon()

    def test_to_grafana_date(self):
        for item in (0, 1, 5, 10, 10000, 9.999, "34984", '2303.230420'):
            self.assertEqual(float(item) * 1000,
                             swift_recon.to_grafana_date(item))

    def test_build_base_url(self):
        instance = {'hostname': 'a.great.url', 'port': 1234}
        expected = "http://a.great.url:1234/recon/"
        self.assertEqual(self.swiftrecon._build_base_url(instance), expected)

    def test_base_recon(self):
        instance = {'hostname': 'a.great.url', 'port': 1234}
        self.swiftrecon.scout_returns = [
            ("http://a.great.url:1234/recon/", {}, 200), ]

        # When scout is successful we just get the de-jsoned content and
        # a dimensions dict.
        content, dim = self.swiftrecon._base_recon(instance, 'blah')
        self.assertDictEqual(content, {})

        # An error will return None, None
        content, dim = self.swiftrecon._base_recon(instance, 'blah')
        self.assertIsNone(content)
        self.assertIsNone(dim)

    def _setup_speced_mock(self):
        mocked = MockSwiftRecon()
        mocked.log = FakeLogger()
        mocked.umount_check = mock.Mock()
        mocked.disk_usage = mock.Mock()
        mocked.quarantine_check = mock.Mock()
        mocked.driveaudit_check = mock.Mock()
        mocked.async_check = mock.Mock()
        mocked.object_auditor_check = mock.Mock()
        mocked.updater_check = mock.Mock()
        mocked.expirer_check = mock.Mock()
        mocked.auditor_check = mock.Mock()
        mocked.replication_check = mock.Mock()
        return mocked

    def test_check_missing_options(self):
        # missing hostname
        instance = {'server_type': 'object', 'port': 1234}
        self.swiftrecon.check(instance)
        self.assertIn('Missing hostname',
                      self.swiftrecon.log.get_loglines('error'))

        # missing port
        instance = {'server_type': 'object', 'hostname': 'a.great.url'}
        self.swiftrecon.log = FakeLogger()
        self.swiftrecon.check(instance)
        self.assertIn('Missing port',
                      self.swiftrecon.log.get_loglines('error'))

        # Missing server_type
        mocked_swift = self._setup_speced_mock()
        instance = {'hostname': 'a.great.url', 'port': 1234}
        called = ('umount_check', 'disk_usage', 'quarantine_check',
                  'driveaudit_check')
        not_called = ('async_check', 'object_auditor_check', 'updater_check',
                      'expirer_check', 'auditor_check', 'replication_check')
        mocked_swift.check(instance)
        self.assertIn('Missing server_type, so will only attempt '
                      'common checks',
                      mocked_swift.log.get_loglines('warning'))

        # only checks that aren't server_type related will be tested
        for method in called:
            self.assertTrue(getattr(mocked_swift, method).called)
        for method in not_called:
            self.assertFalse(getattr(mocked_swift, method).called)

    def test_checks_for_object_server_type(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}
        mocked_swift = self._setup_speced_mock()
        called = ('async_check', 'object_auditor_check', 'updater_check',
                  'expirer_check', 'replication_check', 'umount_check',
                  'disk_usage', 'quarantine_check', 'driveaudit_check')
        not_called = ('auditor_check', )
        mocked_swift.check(instance)

        for method in called:
            self.assertTrue(getattr(mocked_swift, method).called)
        for method in not_called:
            self.assertFalse(getattr(mocked_swift, method).called)

    def test_checks_for_container_server_type(self):
        instance = {'server_type': 'container', 'hostname': 'awesome.host',
                    'port': 1234}
        mocked_swift = self._setup_speced_mock()
        called = ('updater_check', 'auditor_check', 'replication_check',
                  'umount_check', 'disk_usage', 'quarantine_check',
                  'driveaudit_check')
        not_called = ('async_check', 'object_auditor_check', 'expirer_check')
        mocked_swift.check(instance)

        for method in called:
            self.assertTrue(getattr(mocked_swift, method).called)
        for method in not_called:
            self.assertFalse(getattr(mocked_swift, method).called)

    def test_checks_for_account_server_type(self):
        instance = {'server_type': 'account', 'hostname': 'awesome.host',
                    'port': 1234}
        mocked_swift = self._setup_speced_mock()
        called = ('auditor_check', 'replication_check',
                  'umount_check', 'disk_usage', 'quarantine_check',
                  'driveaudit_check')
        not_called = ('updater_check', 'async_check', 'object_auditor_check',
                      'expirer_check')
        mocked_swift.check(instance)

        for method in called:
            self.assertTrue(getattr(mocked_swift, method).called)
        for method in not_called:
            self.assertFalse(getattr(mocked_swift, method).called)

    def _test_scout_error_no_gauge(self, func, *args):
        # first time we run a check, a SwiftReconException will be thrown
        # so the gauge mock wont have been called.

        self.swiftrecon.reset_gauge()
        self.swiftrecon.scout_returns = [
            swift_recon.SwiftReconException('test')]
        func(*args)
        self.assertFalse(self.swiftrecon.gauge_called)

    def test_umount_check(self):
        instance = {'server_type': 'account', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        self._test_scout_error_no_gauge(self.swiftrecon.umount_check,
                                        instance)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content = [{"device": "sdb1", "mounted": False},
                         {"device": "sdb5", "mounted": False}]
        self.swiftrecon.scout_returns = [
            (expected_url, scout_content, 200)]

        self.swiftrecon.umount_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)
        self.assertIn('swift_recon.unmounted', self.swiftrecon.gauge_calls)
        self.assertEqual(
            self.swiftrecon.gauge_calls['swift_recon.unmounted'][0], 2)

    def test_disk_usage(self):
        instance = {'server_type': 'account', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        self._test_scout_error_no_gauge(self.swiftrecon.disk_usage,
                                        instance)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content = [
            {"device": "sdb1", "avail": "", "mounted": False,
             "used": "", "size": ""},
            {"device": "sdb5", "avail": "500", "mounted": True,
             "used": "200", "size": "700"}]
        self.swiftrecon.scout_returns = [
            (expected_url, scout_content, 200)]

        self.swiftrecon.disk_usage(instance)
        self.assertTrue(self.swiftrecon.gauge_called)

        for dim in ('sdb1', 'sdb5'):
            self.assertIn(dim, self.swiftrecon.dimensions['device'])

        for stat, count in (('mounted', 2), ('size', 1), ('used', 1),
                            ('avail', 1)):
            self.assertIn('swift_recon.disk_usage.{0}'.format(stat),
                          self.swiftrecon.gauge_calls)
            # We only send int values, so there should only be mounted sent
            # more then once.
            self.assertEqual(
                len(self.swiftrecon.gauge_calls[
                    'swift_recon.disk_usage.{0}'.format(stat)]), count)

    def test_quarantine_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        self._test_scout_error_no_gauge(self.swiftrecon.quarantine_check,
                                        instance)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content = {
            "objects": 0, "accounts": 1, "containers": 2,
            "policies": {
                0: {"objects": 5},
                1: {"objects": 4}
            }}
        self.swiftrecon.scout_returns = [
            (expected_url, scout_content, 200),
            (expected_url, {'objects': 1, 'containers': 2,
                            'accounts': 3}, 200)]

        # first we test the result from a Swift 2+ storage node (has
        # storage polices)
        self.swiftrecon.quarantine_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)

        self.assertIn('swift_recon.quarantined', self.swiftrecon.gauge_calls)
        values = self.swiftrecon.gauge_calls['swift_recon.quarantined']
        self.assertEqual(len(values), 4)
        self.assertListEqual(values, [1, 2, 5, 4])
        self.assertSetEqual(self.swiftrecon.dimensions['ring'],
                            {'account', 'container', 'object', 'object-1'})

        # now let's try a pre-storage policy result (swift <2.0)
        self.swiftrecon.reset_gauge()
        self.swiftrecon.quarantine_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)

        self.assertIn('swift_recon.quarantined', self.swiftrecon.gauge_calls)
        values = self.swiftrecon.gauge_calls['swift_recon.quarantined']
        self.assertEqual(len(values), 3)
        self.assertListEqual(values, [3, 2, 1])
        self.assertSetEqual(self.swiftrecon.dimensions['ring'],
                            {'account', 'container', 'object'})

    def test_driveaudit_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        self._test_scout_error_no_gauge(self.swiftrecon.driveaudit_check,
                                        instance)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)

        self.swiftrecon.scout_returns = [
            (expected_url, {"drive_audit_errors": 5}, 200),
            (expected_url, {"drive_audit_errors": None}, 200)]

        self.swiftrecon.driveaudit_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)
        self.assertIn('swift_recon.drive_audit_errors',
                      self.swiftrecon.gauge_calls)
        self.assertListEqual(
            self.swiftrecon.gauge_calls['swift_recon.drive_audit_errors'], [5])

        # If the result it None the gauge wont be called
        self.swiftrecon.reset_gauge()
        self.swiftrecon.driveaudit_check(instance)
        self.assertFalse(self.swiftrecon.gauge_called)

    def test_async_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        self._test_scout_error_no_gauge(self.swiftrecon.async_check,
                                        instance)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)

        self.swiftrecon.scout_returns = [
            (expected_url, {"async_pending": 12}, 200),
            (expected_url, {"async_pending": None}, 200)]

        self.swiftrecon.async_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)
        self.assertIn('swift_recon.object.async_pending',
                      self.swiftrecon.gauge_calls)
        self.assertListEqual(
            self.swiftrecon.gauge_calls['swift_recon.object.async_pending'],
            [12])

        # If the result it None the gauge wont be called
        self.swiftrecon.reset_gauge()
        self.swiftrecon.async_check(instance)
        self.assertFalse(self.swiftrecon.gauge_called)

    def test_object_auditor_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        self._test_scout_error_no_gauge(self.swiftrecon.object_auditor_check,
                                        instance)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content = {
            "object_auditor_stats_ALL": {
                "passes": 5,
                "errors": 1,
                "audit_time": 4,
                "start_time": 1531724606.053309,
                "quarantined": 2,
                "bytes_processed": 11885},
            "object_auditor_stats_ZBF": {
                "passes": 3,
                "errors": 0,
                "audit_time": 0,
                "start_time": 1531724665.303363,
                "quarantined": 0,
                "bytes_processed": 0}}

        self.swiftrecon.scout_returns = [
            (expected_url, scout_content, 200)]

        self.swiftrecon.object_auditor_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)

        prefix = 'swift_recon.object.auditor.{}'
        scout_key = 'object_auditor_stats_{}'
        for frag in ('ALL', 'ZBF'):
            scout_metric = scout_key.format(frag)
            metric = prefix.format(scout_metric)
            for key in scout_content[scout_metric]:
                self.assertIn('{}.{}'.format(metric, key),
                              self.swiftrecon.gauge_calls)
                if key == 'start_time':
                    # there is a hack to make epochs dates in grafana and that
                    # is to time it by 1000
                    scout_content[scout_metric][key] = \
                        scout_content[scout_metric][key] * 1000
                self.assertListEqual(
                    self.swiftrecon.gauge_calls['{}.{}'.format(metric, key)],
                    [scout_content[scout_metric][key]])

    def test_updater_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        for server_type in ('object', 'container'):
            self._test_scout_error_no_gauge(self.swiftrecon.updater_check,
                                            instance, server_type)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)

        self.swiftrecon.scout_returns = [
            (expected_url, {"object_updater_sweep":
                            0.10095596313476562}, 200),
            (expected_url, {"container_updater_sweep":
                            0.11764812469482422}, 200)]

        metric = 'swift_recon.{0}.{0}_updater_sweep'

        self.swiftrecon.updater_check(instance, 'object')
        self.assertTrue(self.swiftrecon.gauge_called)
        self.assertIn(metric.format('object'), self.swiftrecon.gauge_calls)
        self.assertListEqual(
            self.swiftrecon.gauge_calls[metric.format('object')],
            [0.10095596313476562])
        self.swiftrecon.reset_gauge()

        instance = {'server_type': 'container', 'hostname': 'awesome.host',
                    'port': 1234}
        self.swiftrecon.updater_check(instance, 'container')
        self.assertTrue(self.swiftrecon.gauge_called)
        self.assertIn(metric.format('container'), self.swiftrecon.gauge_calls)
        self.assertListEqual(
            self.swiftrecon.gauge_calls[metric.format('container')],
            [0.11764812469482422])

    def test_expirer_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        for server_type in ('object', 'container'):
            self._test_scout_error_no_gauge(self.swiftrecon.updater_check,
                                            instance, server_type)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content = {"object_expiration_pass": 0.021467924118041992,
                         "expired_last_pass": 5}

        self.swiftrecon.scout_returns = [
            (expected_url, scout_content, 200)]

        metric = 'swift_recon.object.expirer.{}'

        self.swiftrecon.expirer_check(instance)
        self.assertTrue(self.swiftrecon.gauge_called)

        for stat in ('object_expiration_pass', 'expired_last_pass'):
            self.assertIn(metric.format(stat), self.swiftrecon.gauge_calls)

        for key in scout_content:
            self.assertListEqual(
                self.swiftrecon.gauge_calls[metric.format(key)],
                [scout_content[key]])

    def test_auditor_check(self):
        instance = {'server_type': 'container', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        for server_type in ('container', 'account'):
            self._test_scout_error_no_gauge(self.swiftrecon.auditor_check,
                                            instance, server_type)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content_cont = {
            "container_audits_passed": 6,
            "container_auditor_pass_completed": 0.015977859497070312,
            "container_audits_since": 1531714368.710222,
            "container_audits_failed": 0}
        scout_content_acc = {
            "account_audits_passed": 2,
            "account_audits_failed": 1,
            "account_auditor_pass_completed": 7.200241088867188,
            "account_audits_since": 1531415933.143866}

        self.swiftrecon.scout_returns = [
            (expected_url, scout_content_cont, 200),
            (expected_url, scout_content_acc, 200)]

        for server_type, content in (('container', scout_content_cont),
                                     ('account', scout_content_acc)):
            instance['server_type'] = server_type
            self.swiftrecon.auditor_check(instance, server_type)
            self.assertTrue(self.swiftrecon.gauge_called)

            for key in content:
                metric = 'swift_recon.{0}.{1}'.format(server_type, key)
                self.assertIn(metric, self.swiftrecon.gauge_calls)
                if key.endswith('_audits_since'):
                    # there is a hack to make epochs dates in grafana and that
                    # is to time it by 1000
                    content[key] = content[key] * 1000
                self.assertListEqual(self.swiftrecon.gauge_calls[metric],
                                     [content[key]])
            self.swiftrecon.reset_gauge()

    def test_replication_check(self):
        instance = {'server_type': 'object', 'hostname': 'awesome.host',
                    'port': 1234}

        # test that the error case doesn't call gauge
        for server_type in ('object', 'container', 'account'):
            self._test_scout_error_no_gauge(self.swiftrecon.replication_check,
                                            instance, server_type)

        # now check the correct case
        expected_url = self.swiftrecon._build_base_url(instance)
        scout_content_obj = {
            "replication_last": 1531724665.483373,
            "replication_stats": {
                "rsync": 0, "success": 1194, "attempted": 647,
                "remove": 0, "suffix_count": 1460, "failure": 1,
                "hashmatch": 1194, "suffix_hash": 0, "suffix_sync": 0},
            "object_replication_last": 1531724665.483373,
            "replication_time": 0.11197113196055095,
            "object_replication_time": 0.11197113196055095}
        scout_content_cont = {
            "replication_last": 1531724675.549912,
            "replication_stats": {
                "no_change": 8, "rsync": 0, "success": 8,
                "deferred": 0, "attempted": 4, "ts_repl": 0,
                "remove": 0, "remote_merge": 0, "diff_capped": 0,
                "failure": 0, "hashmatch": 0, "diff": 0,
                "start": 1531724675.488349, "empty": 0},
            "replication_time": 0.06156301498413086}
        scout_content_acc = {
            "replication_last": 1531724672.644893,
            "replication_stats": {
                "no_change": 0, "rsync": 0, "success": 10, "deferred": 0,
                "attempted": 7, "ts_repl": 0, "remove": 0, "remote_merge": 0,
                "diff_capped": 0, "failure": 5, "hashmatch": 0, "diff": 0,
                "start": 1531724672.639242, "empty": 0},
            "replication_time": 0.005650997161865234}

        self.swiftrecon.scout_returns = [
            (expected_url, scout_content_obj, 200),
            (expected_url, scout_content_cont, 200),
            (expected_url, scout_content_acc, 200)]

        for server_type, content in (('object', scout_content_obj),
                                     ('container', scout_content_cont),
                                     ('account', scout_content_acc)):
            instance['server_type'] = server_type
            self.swiftrecon.replication_check(instance, server_type)
            self.assertTrue(self.swiftrecon.gauge_called)

            for key in ('replication_last', 'replication_time'):
                metric = 'swift_recon.{0}.{1}'.format(server_type, key)
                self.assertIn(metric, self.swiftrecon.gauge_calls)
                if key == 'replication_last':
                    # there is a hack to make epochs dates in grafana and that
                    # is to time it by 1000
                    content[key] = content[key] * 1000
                self.assertListEqual(self.swiftrecon.gauge_calls[metric],
                                     [content[key]])

            # Currently we are only grabbing the following 3 values. As you
            # can see there are much more. Adding more should be done at some
            # point.
            for key in ('attempted', 'failure', 'success'):
                metric = 'swift_recon.{0}.replication.{1}'.format(server_type,
                                                                  key)
                self.assertIn(metric, self.swiftrecon.gauge_calls)
                self.assertListEqual(self.swiftrecon.gauge_calls[metric],
                                     [content['replication_stats'][key]])
            self.swiftrecon.reset_gauge()
