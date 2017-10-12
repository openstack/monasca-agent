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

import json
import mock
import os
import subprocess
import unittest

from monasca_agent.common import util
from monasca_agent.collector.checks_d import ceph


def mocked_check_output(args, shell=True, stderr=''):
    output = ''
    if '-f json df detail' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-df.json')
    elif '-f json status' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-status.json')
    elif 'status' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-status.plain')
    elif '-f json osd df' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-osd-df.json')
    elif '-f json osd perf' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-osd-perf.json')
    elif '-f json osd dump' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-osd-dump.json')
    elif '-f json osd pool stats' in args:
        output = file(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph/test_ceph-osd-pool-stats.json')
    else:
        raise subprocess.CalledProcessError(1, cmd=args,
                                            output='Invalid command')
    return output.read()


class MockCephCheck(ceph.Ceph):
    subprocess.check_output = mock.create_autospec(
        subprocess.check_output, side_effect=mocked_check_output)
    CLUSTER = 'ceph'

    def __init__(self):
        super(MockCephCheck, self).__init__(
            name='ceph',
            init_config={},
            instances=[],
            agent_config={}
        )

    def _ceph_cmd(self, *args):
        if hasattr(self, 'instance'):
            return super(MockCephCheck, self)._ceph_cmd(*args)
        else:
            self.instance = { 'use_sudo': False }
            ret = super(MockCephCheck, self)._ceph_cmd(*args)
            del self.instance
            return ret


class CephCheckTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        super(CephCheckTest, self).setUp()
        self.ceph_check = MockCephCheck()
        self.ceph_check.gauge = mock.Mock()

    def test_ceph_cmd(self):
        df = self.ceph_check._ceph_cmd('df detail', 'json')
        st = self.ceph_check._ceph_cmd('status', 'json')
        st_plain = self.ceph_check._ceph_cmd('status')
        osd_df = self.ceph_check._ceph_cmd('osd df', 'json')
        osd_perf = self.ceph_check._ceph_cmd('osd perf', 'json')
        osd_dump = self.ceph_check._ceph_cmd('osd dump', 'json')
        osd_pool = self.ceph_check._ceph_cmd('osd pool stats', 'json')

        self.assertIsInstance(df, dict)
        self.assertEqual(2, len(df))
        self.assertIsInstance(st, dict)
        self.assertEqual(9, len(st))
        self.assertIsInstance(st_plain, str)
        self.assertEqual(683, len(st_plain))
        self.assertIsInstance(osd_df, dict)
        self.assertEqual(3, len(osd_df))
        self.assertIsInstance(osd_perf, dict)
        self.assertEqual(1, len(osd_perf))
        self.assertIsInstance(osd_dump, dict)
        self.assertEqual(15, len(osd_dump))
        self.assertIsInstance(osd_pool, list)
        self.assertEqual(2, len(osd_pool))

        with self.assertRaises(subprocess.CalledProcessError) as e:
            self.ceph_check._ceph_cmd('foo', 'json')
            self.assertEqual("Unable to execute ceph command 'ceph --cluster"
                             "ceph -f json foo': Invalid command", e.output)

    def test_ceph_cmd_sudo(self):
        self.ceph_check.check({
            'use_sudo': True,
        })

        expect_cmd = 'sudo ceph --cluster ceph -f json df detail'

        with mock.patch('subprocess.check_output') as ceph_cmd_call:
            try:
                self.ceph_check._ceph_cmd('df detail', 'json')
            except Exception as e:
                pass
            ceph_cmd_call.assert_called_with(expect_cmd, shell=True,
                                             stderr=subprocess.STDOUT)

    def test_parse_ceph_status(self):
        self.assertEqual(0, self.ceph_check._parse_ceph_status('HEALTH_OK'))
        self.assertEqual(1, self.ceph_check._parse_ceph_status('HEALTH_WARN'))
        self.assertEqual(2, self.ceph_check._parse_ceph_status('HEALTH_ERR'))
        self.assertEqual(2, self.ceph_check._parse_ceph_status('foo'))

    def test_get_cache_io(self):
        cache_kb = 'cache io 1000000 kB/s flush, 1000000 kB/s evict,' \
                   ' 20 op/s promote'
        cache_mb = 'cache io 1000 MB/s flush, 1000 MB/s evict, 20 op/s promote'
        cache_gb = 'cache io 1 GB/s flush, 1 GB/s evict, 20 op/s promote'
        expected_metrics = {
            'ceph.cluster.cache.flush_bytes_per_sec': 1e9,
            'ceph.cluster.cache.evict_bytes_per_sec': 1e9,
            'ceph.cluster.cache.promote_ops': 20
        }

        metrics_kb = self.ceph_check._get_cache_io(cache_kb)
        metrics_mb = self.ceph_check._get_cache_io(cache_mb)
        metrics_gb = self.ceph_check._get_cache_io(cache_gb)
        self.assertEqual(expected_metrics, metrics_kb)
        self.assertEqual(expected_metrics, metrics_mb)
        self.assertEqual(expected_metrics, metrics_gb)

    def test_get_client_io(self):
        client_kb = 'client io 1000000 kB/s rd, 1000000 kb/s wr, 10 op/s rd,' \
                     ' 20 op/s wr'
        client_mb = 'client io 1000 MB/s rd, 1000 mb/s wr, 10 op/s rd,' \
                    ' 20 op/s wr'
        client_gb = 'client io 1 GB/s rd, 1 gb/s wr, 10 op/s rd, 20 op/s wr'
        expected_metrics = {
            'ceph.cluster.client.read_bytes_per_sec': 1e9,
            'ceph.cluster.client.write_bytes_per_sec': 1e9,
            'ceph.cluster.client.read_ops': 10,
            'ceph.cluster.client.write_ops': 20
        }

        metrics_kb = self.ceph_check._get_client_io(client_kb)
        metrics_mb = self.ceph_check._get_client_io(client_mb)
        metrics_gb = self.ceph_check._get_client_io(client_gb)
        self.assertEqual(expected_metrics, metrics_kb)
        self.assertEqual(expected_metrics, metrics_mb)
        self.assertEqual(expected_metrics, metrics_gb)

    def test_get_recovery_io(self):
        recovery_kb = 'recovery io 1000000 kB/s, 100 keys/s, 50 objects/s'
        recovery_mb = 'recovery io 1000 MB/s, 100 keys/s, 50 objects/s'
        recovery_gb = 'recovery io 1 GB/s, 100 keys/s, 50 objects/s'
        expected_metrics = {
            'ceph.cluster.recovery.bytes_per_sec': 1e9,
            'ceph.cluster.recovery.keys_per_sec': 100,
            'ceph.cluster.recovery.objects_per_sec': 50
        }

        metrics_kb = self.ceph_check._get_recovery_io(recovery_kb)
        metrics_mb = self.ceph_check._get_recovery_io(recovery_mb)
        metrics_gb = self.ceph_check._get_recovery_io(recovery_gb)
        self.assertEqual(expected_metrics, metrics_kb)
        self.assertEqual(expected_metrics, metrics_mb)
        self.assertEqual(expected_metrics, metrics_gb)

    def test_get_summary_metrics(self):
        summary_strs = [
            '1 pgs degraded', '2 pgs stuck degraded', '3 pgs unclean',
            '4 pgs stuck unclean', '5 pgs undersized',
            '6 pgs stuck undersized', '7 pgs stale', '8 pgs stuck stale',
            '9 requests are blocked', 'recovery 10/100 objects degraded',
            'recovery 11/100 objects misplaced'
        ]

        expected_metrics = {
            'ceph.cluster.pgs.degraded_count': 1,
            'ceph.cluster.pgs.stuck_degraded_count': 2,
            'ceph.cluster.pgs.unclean_count': 3,
            'ceph.cluster.pgs.stuck_unclean_count': 4,
            'ceph.cluster.pgs.undersized_count': 5,
            'ceph.cluster.pgs.stuck_undersized_count': 6,
            'ceph.cluster.pgs.stale_count': 7,
            'ceph.cluster.pgs.stuck_stale_count': 8,
            'ceph.cluster.slow_requests_count': 9,
            'ceph.cluster.objects.degraded_count': 10,
            'ceph.cluster.objects.misplaced_count': 11
        }

        metrics = {}
        self.assertEqual(self.ceph_check._get_summary_metrics(''), {})
        for s in summary_strs:
            metrics.update(self.ceph_check._get_summary_metrics(s))
        self.assertEqual(expected_metrics, metrics)

    def test_get_usage_metrics(self):
        df = self.ceph_check._ceph_cmd('df detail', 'json')
        expected_metrics = {
            'ceph.cluster.total_bytes': 150000,
            'ceph.cluster.total_used_bytes': 90000,
            'ceph.cluster.total_avail_bytes': 60000,
            'ceph.cluster.objects.total_count': 50,
            'ceph.cluster.utilization_perc': 0.6
        }

        metrics = self.ceph_check._get_usage_metrics(df)
        self.assertEqual(expected_metrics, metrics)

    def test_get_stats_metrics(self):
        status = self.ceph_check._ceph_cmd('status', 'json')
        status_plain = self.ceph_check._ceph_cmd('status')
        expected_metrics = {
            'ceph.cluster.health_status': 0,
            'ceph.cluster.osds.total_count': 3,
            'ceph.cluster.osds.up_count': 3,
            'ceph.cluster.osds.in_count': 3,
            'ceph.cluster.osds.down_count': 0,
            'ceph.cluster.osds.out_count': 0,
            'ceph.cluster.pgs.degraded_count': 1,
            'ceph.cluster.pgs.stuck_unclean_count': 4,
            'ceph.cluster.pgs.undersized_count': 5,
            'ceph.cluster.objects.degraded_count': 10,
            'ceph.cluster.pgs.active+clean': 192,
            'ceph.cluster.pgs.active+clean+scrubbing+deep': 1,
            'ceph.cluster.pgs.active+clean+scrubbing': 1,
            'ceph.cluster.pgs.scrubbing_count': 1,
            'ceph.cluster.pgs.deep_scrubbing_count': 1,
            'ceph.cluster.pgs.remapped_count': 0,
            'ceph.cluster.pgs.total_count': 192,
            'ceph.cluster.pgs.avg_per_osd': 64,
            'ceph.cluster.client.read_bytes_per_sec': 630000.0,
            'ceph.cluster.client.write_bytes_per_sec': 272000000.0,
            'ceph.cluster.client.read_ops': 263,
            'ceph.cluster.client.write_ops': 1964,
            'ceph.cluster.recovery.bytes_per_sec': 1e9,
            'ceph.cluster.recovery.keys_per_sec': 100,
            'ceph.cluster.recovery.objects_per_sec': 50,
            'ceph.cluster.cache.flush_bytes_per_sec': 1e8,
            'ceph.cluster.cache.evict_bytes_per_sec': 1e9,
            'ceph.cluster.cache.promote_ops': 20,
            'ceph.cluster.quorum_size': 3
        }

        metrics = self.ceph_check._get_stats_metrics(status, status_plain)
        self.assertEqual(expected_metrics, metrics)

    def test_get_mon_metrics(self):
        status = self.ceph_check._ceph_cmd('status', 'json')
        expected_metrics = {
            'mon0': {
                'ceph.monitor.total_bytes': 100000.0,
                'ceph.monitor.used_bytes': 50000.0,
                'ceph.monitor.avail_bytes': 50000.0,
                'ceph.monitor.avail_perc': 50,
                'ceph.monitor.store.total_bytes': 100,
                'ceph.monitor.store.sst_bytes': 0,
                'ceph.monitor.store.log_bytes': 10,
                'ceph.monitor.store.misc_bytes': 10,
                'ceph.monitor.skew': 0.000000,
                'ceph.monitor.latency': 0.000000
            },
            'mon1': {
                'ceph.monitor.total_bytes': 100000.0,
                'ceph.monitor.used_bytes': 50000.0,
                'ceph.monitor.avail_bytes': 50000.0,
                'ceph.monitor.avail_perc': 50,
                'ceph.monitor.store.total_bytes': 100,
                'ceph.monitor.store.sst_bytes': 0,
                'ceph.monitor.store.log_bytes': 10,
                'ceph.monitor.store.misc_bytes': 10,
                'ceph.monitor.skew': 0.000000,
                'ceph.monitor.latency': 0.002577
            },
            'mon2': {
                'ceph.monitor.total_bytes': 100000.0,
                'ceph.monitor.used_bytes': 50000.0,
                'ceph.monitor.avail_bytes': 50000.0,
                'ceph.monitor.avail_perc': 50,
                'ceph.monitor.store.total_bytes': 100,
                'ceph.monitor.store.sst_bytes': 0,
                'ceph.monitor.store.log_bytes': 10,
                'ceph.monitor.store.misc_bytes': 10,
                'ceph.monitor.skew': 0.000000,
                'ceph.monitor.latency': 0.003353
            }
        }

        metrics = self.ceph_check._get_mon_metrics(status)
        self.assertEqual(expected_metrics, metrics)

    def test_get_osd_metrics(self):
        df = self.ceph_check._ceph_cmd('osd df', 'json')
        perf = self.ceph_check._ceph_cmd('osd perf', 'json')
        dump = self.ceph_check._ceph_cmd('osd dump', 'json')
        expected_metrics = {
            'osd.0': {
                'ceph.osd.crush_weight': 0.999390,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.000000,
                'ceph.osd.total_bytes': 50000.0,
                'ceph.osd.used_bytes': 25000.0,
                'ceph.osd.avail_bytes': 25000.0,
                'ceph.osd.utilization_perc': 0.5,
                'ceph.osd.variance': 1.008811,
                'ceph.osd.pgs_count': 192,
                'ceph.osd.perf.commit_latency_seconds': 0.031,
                'ceph.osd.perf.apply_latency_seconds': 0.862,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.1': {
                'ceph.osd.crush_weight': 0.999390,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.000000,
                'ceph.osd.total_bytes': 50000.0,
                'ceph.osd.used_bytes': 25000.0,
                'ceph.osd.avail_bytes': 25000.0,
                'ceph.osd.utilization_perc': 0.5,
                'ceph.osd.variance': 0.998439,
                'ceph.osd.pgs_count': 192,
                'ceph.osd.perf.commit_latency_seconds': 0.025,
                'ceph.osd.perf.apply_latency_seconds': 1.390,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.2': {
                'ceph.osd.crush_weight': 0.999390,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.000000,
                'ceph.osd.total_bytes': 50000.0,
                'ceph.osd.used_bytes': 25000.0,
                'ceph.osd.avail_bytes': 25000.0,
                'ceph.osd.utilization_perc': 0.5,
                'ceph.osd.variance': 0.992750,
                'ceph.osd.pgs_count': 192,
                'ceph.osd.perf.commit_latency_seconds': 0.025,
                'ceph.osd.perf.apply_latency_seconds': 1.505,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            }
        }

        metrics = self.ceph_check._get_osd_metrics(df, perf, dump)
        self.assertEqual(expected_metrics, metrics)

    def test_get_osd_summary_metrics(self):
        df = self.ceph_check._ceph_cmd('osd df', 'json')
        expected_metrics = {
            'ceph.osds.total_bytes': 150000.0,
            'ceph.osds.total_used_bytes': 75000.0,
            'ceph.osds.total_avail_bytes': 75000.0,
            'ceph.osds.avg_utilization_perc': 0.5
        }

        metrics = self.ceph_check._get_osd_summary_metrics(df)
        self.assertEqual(expected_metrics, metrics)

    def test_get_pool_metrics(self):
        df = self.ceph_check._ceph_cmd('df detail', 'json')
        expected_metrics = {
            'images': {
                'ceph.pool.used_bytes': 10000,
                'ceph.pool.used_raw_bytes': 30000,
                'ceph.pool.max_avail_bytes': 20000,
                'ceph.pool.objects_count': 20,
                'ceph.pool.dirty_objects_count': 20,
                'ceph.pool.read_io': 6000,
                'ceph.pool.read_bytes': 20000,
                'ceph.pool.write_io': 2000,
                'ceph.pool.write_bytes': 20000,
                'ceph.pool.quota_max_bytes': 50000,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.total_bytes': 30000,
                'ceph.pool.utilization_perc': 0.3333333333333333
            },
            'vms': {
                'ceph.pool.used_bytes': 20000,
                'ceph.pool.used_raw_bytes': 60000,
                'ceph.pool.max_avail_bytes': 20000,
                'ceph.pool.objects_count': 30,
                'ceph.pool.dirty_objects_count': 30,
                'ceph.pool.read_io': 4000,
                'ceph.pool.read_bytes': 80000,
                'ceph.pool.write_io': 1000,
                'ceph.pool.write_bytes': 20000,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.total_bytes': 40000,
                'ceph.pool.utilization_perc': 0.5
            }
        }

        metrics = self.ceph_check._get_pool_metrics(df)
        self.assertEqual(expected_metrics, metrics)

    def test_get_pool_stats_metrics(self):
        pool_stats = self.ceph_check._ceph_cmd('osd pool stats', 'json')
        expected_metrics = {
            'images': {
                'ceph.pool.recovery.recovering_objects_per_sec': 3530,
                'ceph.pool.recovery.recovering_bytes_per_sec': 14462655,
                'ceph.pool.recovery.recovering_keys_per_sec': 0,
                'ceph.pool.recovery.num_objects_recovered': 7148,
                'ceph.pool.recovery.num_bytes_recovered': 29278208,
                'ceph.pool.recovery.num_keys_recovered': 0
            },
            'vms': {
                'ceph.pool.client.read_bytes_sec': 16869,
                'ceph.pool.client.write_bytes_sec': 9341127,
                'ceph.pool.client.read_op_per_sec': 369,
                'ceph.pool.client.write_op_per_sec': 1364
            }
        }

        metrics = self.ceph_check._get_pool_stats_metrics(pool_stats)
        self.assertEqual(expected_metrics, metrics)

    def test_check(self):
        self.ceph_check.check({})
        self.assertEqual(144, self.ceph_check.gauge.call_count)

    def test_check_disable_all_metrics(self):
        self.ceph_check._get_usage_metrics = mock.Mock(return_value={})
        self.ceph_check._get_stats_metrics = mock.Mock(return_value={})
        self.ceph_check._get_mon_metrics = mock.Mock(return_value={})
        self.ceph_check._get_osd_metrics = mock.Mock(return_value={})
        self.ceph_check._get_osd_summary_metrics = mock.Mock(return_value={})
        self.ceph_check._get_pool_metrics = mock.Mock(return_value={})
        self.ceph_check._get_pool_stats_metrics = mock.Mock(return_value={})

        self.ceph_check.check({
            'collect_usage_metrics': False,
            'collect_stats_metrics': False,
            'collect_mon_metrics': False,
            'collect_osd_metrics': False,
            'collect_pool_metrics': False,
        })

        self.assertFalse(self.ceph_check._get_usage_metrics.called)
        self.assertFalse(self.ceph_check._get_stats_metrics.called)
        self.assertFalse(self.ceph_check._get_mon_metrics.called)
        self.assertFalse(self.ceph_check._get_osd_metrics.called)
        self.assertFalse(self.ceph_check._get_osd_summary_metrics.called)
        self.assertFalse(self.ceph_check._get_pool_metrics.called)
        self.assertFalse(self.ceph_check._get_pool_stats_metrics.called)

    def test_check_disable_some_metrics(self):
        self.ceph_check._get_usage_metrics = mock.Mock(return_value={})
        self.ceph_check._get_stats_metrics = mock.Mock(return_value={})
        self.ceph_check._get_mon_metrics = mock.Mock(return_value={})
        self.ceph_check._get_osd_metrics = mock.Mock(return_value={})
        self.ceph_check._get_osd_summary_metrics = mock.Mock(return_value={})
        self.ceph_check._get_pool_metrics = mock.Mock(return_value={})
        self.ceph_check._get_pool_stats_metrics = mock.Mock(return_value={})

        self.ceph_check.check({
            'collect_usage_metrics': False,
            'collect_stats_metrics': False
        })

        self.assertFalse(self.ceph_check._get_usage_metrics.called)
        self.assertFalse(self.ceph_check._get_stats_metrics.called)
        self.assertTrue(self.ceph_check._get_mon_metrics.called)
        self.assertTrue(self.ceph_check._get_osd_metrics.called)
        self.assertTrue(self.ceph_check._get_osd_summary_metrics.called)
        self.assertTrue(self.ceph_check._get_pool_metrics.called)
        self.assertTrue(self.ceph_check._get_pool_stats_metrics.called)

    def test_check_enable_all_metrics(self):
        self.ceph_check._get_usage_metrics = mock.Mock(return_value={})
        self.ceph_check._get_stats_metrics = mock.Mock(return_value={})
        self.ceph_check._get_mon_metrics = mock.Mock(return_value={})
        self.ceph_check._get_osd_metrics = mock.Mock(return_value={})
        self.ceph_check._get_osd_summary_metrics = mock.Mock(return_value={})
        self.ceph_check._get_pool_metrics = mock.Mock(return_value={})
        self.ceph_check._get_pool_stats_metrics = mock.Mock(return_value={})

        self.ceph_check.check({
            'collect_usage_metrics': True,
            'collect_stats_metrics': True,
            'collect_mon_metrics': True,
            'collect_osd_metrics': True,
            'collect_pool_metrics': True,
        })

        self.assertTrue(self.ceph_check._get_usage_metrics.called)
        self.assertTrue(self.ceph_check._get_stats_metrics.called)
        self.assertTrue(self.ceph_check._get_mon_metrics.called)
        self.assertTrue(self.ceph_check._get_osd_metrics.called)
        self.assertTrue(self.ceph_check._get_osd_summary_metrics.called)
        self.assertTrue(self.ceph_check._get_pool_metrics.called)
        self.assertTrue(self.ceph_check._get_pool_stats_metrics.called)
