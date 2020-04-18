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
import os
import subprocess
from unittest import mock
import unittest

from monasca_agent.common import util
from monasca_agent.collector.checks_d import ceph


def mocked_check_output(args, shell=True, stderr='', version='jewel'):
    output = ''
    if '-f json df detail' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-df.json'.format(version))
    elif '-f json status' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-status.json'.format(version))
    elif 'status' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-status.plain'.format(version))
    elif '-f json osd df' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-osd-df.json'.format(version))
    elif '-f json osd perf' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-osd-perf.json'.format(version))
    elif '-f json osd dump' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-osd-dump.json'.format(version))
    elif '-f json osd pool stats' in args:
        output = open(os.path.dirname(os.path.abspath(__file__)) +
                      '/fixtures/ceph-{}/test_ceph-osd-pool-stats.json'.format(version))
    else:
        raise subprocess.CalledProcessError(1, cmd=args,
                                            output='Invalid command')
    return output.read()

def mocked_check_output_jewel(args, shell=True, stderr=''):
    return mocked_check_output(args, shell, stderr, 'jewel')

def mocked_check_output_luminous(args, shell=True, stderr=''):
    return mocked_check_output(args, shell, stderr, 'luminous')

class MockCephCheck(ceph.Ceph):

    CLUSTER = 'ceph'

    def __init__(self, ceph_version='jewel'):

        # Attach representative output from Ceph clusters of different versions
        if ceph_version == 'jewel':
            subprocess.check_output = mock.Mock(
                side_effect=mocked_check_output_jewel)
        elif ceph_version == 'luminous':
            subprocess.check_output = mock.Mock(
                side_effect=mocked_check_output_luminous)

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

    CEPH_VERSION='jewel'

    expected = {
        'pool_stats': {
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
        },
        'df_total': {
            'ceph.cluster.total_bytes': 150000,
            'ceph.cluster.total_used_bytes': 90000,
            'ceph.cluster.total_avail_bytes': 60000,
            'ceph.cluster.objects.total_count': 50,
            'ceph.cluster.utilization_perc': 0.6
        },
        'stats_metrics': {
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
        },
        'osd_metrics': {
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
        },
        'summary_metrics': {
            'ceph.osds.total_bytes': 150000.0,
            'ceph.osds.total_used_bytes': 75000.0,
            'ceph.osds.total_avail_bytes': 75000.0,
            'ceph.osds.avg_utilization_perc': 0.5
        },
        'pool_metrics': {
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
        },
        'mon_metrics': {
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
            },
        },
        'test_ceph_cmd_lens': {
            'df detail json': 2,
            'status json': 9,
            'status': 683,
            'osd df json': 3,
            'osd perf json': 1,
            'osd dump json': 15,
            'osd pool stats json': 2
        },
        'test_check_call_count': 144
    }

    def setUp(self):
        super(CephCheckTest, self).setUp()
        self.ceph_check = MockCephCheck(self.CEPH_VERSION)
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
        self.assertEqual(self.expected['test_ceph_cmd_lens']['df detail json'], len(df))
        self.assertIsInstance(st, dict)
        self.assertEqual(self.expected['test_ceph_cmd_lens']['status json'], len(st))
        self.assertIsInstance(st_plain, str)
        self.assertEqual(self.expected['test_ceph_cmd_lens']['status'], len(st_plain))
        self.assertIsInstance(osd_df, dict)
        self.assertEqual(self.expected['test_ceph_cmd_lens']['osd df json'], len(osd_df))
        self.assertIsInstance(osd_perf, dict)
        self.assertEqual(self.expected['test_ceph_cmd_lens']['osd perf json'], len(osd_perf))
        self.assertIsInstance(osd_dump, dict)
        self.assertEqual(self.expected['test_ceph_cmd_lens']['osd dump json'], len(osd_dump))
        self.assertIsInstance(osd_pool, list)
        self.assertEqual(self.expected['test_ceph_cmd_lens']['osd pool stats json'], len(osd_pool))

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
        metrics = self.ceph_check._get_usage_metrics(df)

        # NOTE: some metrics are floating point values and may not be
        # reliably compared with pre-computed float values
        self.assertEqual(
            { k: v for k, v in self.expected['df_total'].items()
                if k != 'ceph.cluster.utilization_perc'},
            { k: v for k, v in metrics.items()
                if k != 'ceph.cluster.utilization_perc'})
        self.assertAlmostEqual(
            self.expected['df_total']['ceph.cluster.utilization_perc'],
            metrics['ceph.cluster.utilization_perc'], places=3)

    def test_get_stats_metrics(self):
        status = self.ceph_check._ceph_cmd('status', 'json')
        status_plain = self.ceph_check._ceph_cmd('status')
        metrics = self.ceph_check._get_stats_metrics(status, status_plain)
        self.assertDictEqual(self.expected['stats_metrics'], metrics)

    def test_get_mon_metrics(self):
        status = self.ceph_check._ceph_cmd('status', 'json')

        metrics = self.ceph_check._get_mon_metrics(status)
        self.assertEqual(self.expected['mon_metrics'], metrics)

    def test_get_osd_metrics(self):
        df = self.ceph_check._ceph_cmd('osd df', 'json')
        perf = self.ceph_check._ceph_cmd('osd perf', 'json')
        dump = self.ceph_check._ceph_cmd('osd dump', 'json')

        metrics = self.ceph_check._get_osd_metrics(df, perf, dump)

        # NOTE: some metrics are floating point values and may not be
        # reliably compared with pre-computed float values
        for osd, osd_metrics in metrics.items():
            self.assertEqual(
                { k: v for k, v in self.expected['osd_metrics'][osd].items()
                    if not k in ['ceph.osd.utilization_perc', 'ceph.osd.variance']},
                { k: v for k, v in osd_metrics.items()
                    if not k in ['ceph.osd.utilization_perc', 'ceph.osd.variance']})

            self.assertAlmostEqual(
                self.expected['osd_metrics'][osd]['ceph.osd.utilization_perc'],
                osd_metrics['ceph.osd.utilization_perc'], places=2)
            self.assertAlmostEqual(
                self.expected['osd_metrics'][osd]['ceph.osd.variance'],
                osd_metrics['ceph.osd.variance'], places=2)

    def test_get_osd_summary_metrics(self):
        df = self.ceph_check._ceph_cmd('osd df', 'json')

        metrics = self.ceph_check._get_osd_summary_metrics(df)

        # NOTE: some metrics are floating point values and may not be
        # reliably compared with pre-computed float values
        self.assertEqual(
            { k: v for k, v in self.expected['summary_metrics'].items()
                if k != 'ceph.osds.avg_utilization_perc'},
            { k: v for k, v in metrics.items()
                if k != 'ceph.osds.avg_utilization_perc'})
        self.assertAlmostEqual(
            self.expected['summary_metrics']['ceph.osds.avg_utilization_perc'],
            metrics['ceph.osds.avg_utilization_perc'], places=3)


    def test_get_pool_metrics(self):
        df = self.ceph_check._ceph_cmd('df detail', 'json')

        # NOTE: some metrics are floating point values and may not be
        # reliably compared with pre-computed float values
        metrics = self.ceph_check._get_pool_metrics(df)
        for pool, pool_metrics in metrics.items():
            self.assertEqual(
                { k: v for k, v in self.expected['pool_metrics'][pool].items()
                    if k != 'ceph.pool.utilization_perc'},
                { k: v for k, v in metrics[pool].items()
                    if k != 'ceph.pool.utilization_perc'})

        self.assertAlmostEqual(
            self.expected['pool_metrics'][pool]['ceph.pool.utilization_perc'],
            pool_metrics['ceph.pool.utilization_perc'], places=3)

    def test_get_pool_stats_metrics(self):
        pool_stats = self.ceph_check._ceph_cmd('osd pool stats', 'json')
        metrics = self.ceph_check._get_pool_stats_metrics(pool_stats)

        self.assertEqual(self.expected['pool_stats'], metrics)

    def test_check(self):
        self.ceph_check.check({})
        self.assertEqual(self.expected['test_check_call_count'], self.ceph_check.gauge.call_count)

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


class CephCheckTestLuminous(CephCheckTest):

    CEPH_VERSION='luminous'

    expected = {
        'pool_stats': {
        },
        'df_total': {
            'ceph.cluster.total_bytes': 121070163910656,
            'ceph.cluster.total_used_bytes': 7961411256320,
            'ceph.cluster.total_avail_bytes': 113108752654336,
            'ceph.cluster.objects.total_count': 34566782,
            'ceph.cluster.utilization_perc': 0.0658
        },
        'stats_metrics': {
            'ceph.cluster.health_status': 1,
            'ceph.cluster.osds.total_count': 33,
            'ceph.cluster.osds.up_count': 22,
            'ceph.cluster.osds.in_count': 24,
            'ceph.cluster.osds.down_count': 11,
            'ceph.cluster.osds.out_count': 9,
            #'ceph.cluster.pgs.degraded_count': 2361,
            #'ceph.cluster.pgs.stuck_unclean_count': 2361,
            #'ceph.cluster.pgs.undersized_count': 2361,
            #'ceph.cluster.objects.degraded_count': 9196074,
            'ceph.cluster.pgs.active+clean': 873,
            'ceph.cluster.pgs.active+undersized+degraded': 2361,
            'ceph.cluster.pgs.active+clean+remapped': 14,
            'ceph.cluster.pgs.scrubbing_count': 0,
            'ceph.cluster.pgs.deep_scrubbing_count': 0,
            'ceph.cluster.pgs.remapped_count': 14,
            'ceph.cluster.pgs.total_count': 3248,
            'ceph.cluster.pgs.avg_per_osd': 98.42424242424242,
            #'ceph.cluster.client.read_bytes_per_sec': 4246.0,
            'ceph.cluster.client.write_bytes_per_sec': 374000.0,
            'ceph.cluster.client.read_ops': 2,
            'ceph.cluster.client.write_ops': 16,
            #'ceph.cluster.recovery.bytes_per_sec': 0,
            #'ceph.cluster.recovery.keys_per_sec': 0,
            #'ceph.cluster.recovery.objects_per_sec': 0,
            'ceph.cluster.quorum_size': 3,
        },
        'osd_metrics': {
            'osd.0': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 407044864000.0,
                'ceph.osd.avail_bytes': 5479588668000.0,
                'ceph.osd.utilization_perc': 6.91,
                'ceph.osd.variance': 1.051531,
                'ceph.osd.pgs_count': 228,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.1': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 411742144000.0,
                'ceph.osd.avail_bytes': 5474891388000.0,
                'ceph.osd.utilization_perc': 6.99,
                'ceph.osd.variance': 1.063665,
                'ceph.osd.pgs_count': 204,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.2': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 442908160000.0,
                'ceph.osd.avail_bytes': 5443725372000.0,
                'ceph.osd.utilization_perc': 7.52,
                'ceph.osd.variance': 1.144177,
                'ceph.osd.pgs_count': 227,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.3': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 348767744000.0,
                'ceph.osd.avail_bytes': 5537865788000.0,
                'ceph.osd.utilization_perc': 5.92,
                'ceph.osd.variance': 0.900982,
                'ceph.osd.pgs_count': 196,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.4': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 383320704000.0,
                'ceph.osd.avail_bytes': 5503312828000.0,
                'ceph.osd.utilization_perc': 6.51,
                'ceph.osd.variance': 0.990243,
                'ceph.osd.pgs_count': 204,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.5': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 356644416000.0,
                'ceph.osd.avail_bytes': 5529989116000.0,
                'ceph.osd.utilization_perc': 6.06,
                'ceph.osd.variance': 0.92133,
                'ceph.osd.pgs_count': 197,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.6': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 325735936000.0,
                'ceph.osd.avail_bytes': 5560897596000.0,
                'ceph.osd.utilization_perc': 5.53,
                'ceph.osd.variance': 0.841483,
                'ceph.osd.pgs_count': 185,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.7': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 367045952000.0,
                'ceph.osd.avail_bytes': 5519587580000.0,
                'ceph.osd.utilization_perc': 6.24,
                'ceph.osd.variance': 0.9482,
                'ceph.osd.pgs_count': 205,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.8': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 394521920000.0,
                'ceph.osd.avail_bytes': 5492111612000.0,
                'ceph.osd.utilization_perc': 6.7,
                'ceph.osd.variance': 1.01918,
                'ceph.osd.pgs_count': 214,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.9': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 369788800000.0,
                'ceph.osd.avail_bytes': 5516844732000.0,
                'ceph.osd.utilization_perc': 6.28,
                'ceph.osd.variance': 0.955286,
                'ceph.osd.pgs_count': 206,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.10': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 427759872000.0,
                'ceph.osd.avail_bytes': 5458873660000.0,
                'ceph.osd.utilization_perc': 7.27,
                'ceph.osd.variance': 1.105044,
                'ceph.osd.pgs_count': 218,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.11': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 404752640000.0,
                'ceph.osd.avail_bytes': 5481880892000.0,
                'ceph.osd.utilization_perc': 6.88,
                'ceph.osd.variance': 1.045609,
                'ceph.osd.pgs_count': 194,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.12': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 437294592000.0,
                'ceph.osd.avail_bytes': 5449338940000.0,
                'ceph.osd.utilization_perc': 7.43,
                'ceph.osd.variance': 1.129676,
                'ceph.osd.pgs_count': 230,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.13': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 388802944000.0,
                'ceph.osd.avail_bytes': 5497830588000.0,
                'ceph.osd.utilization_perc': 6.6,
                'ceph.osd.variance': 1.004406,
                'ceph.osd.pgs_count': 218,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.14': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 330687424000.0,
                'ceph.osd.avail_bytes': 5555946108000.0,
                'ceph.osd.utilization_perc': 5.62,
                'ceph.osd.variance': 0.854274,
                'ceph.osd.pgs_count': 190,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.15': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 405913792000.0,
                'ceph.osd.avail_bytes': 5480719740000.0,
                'ceph.osd.utilization_perc': 6.9,
                'ceph.osd.variance': 1.048609,
                'ceph.osd.pgs_count': 225,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.16': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 377519552000.0,
                'ceph.osd.avail_bytes': 5509113980000.0,
                'ceph.osd.utilization_perc': 6.41,
                'ceph.osd.variance': 0.975257,
                'ceph.osd.pgs_count': 192,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.17': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 362563072000.0,
                'ceph.osd.avail_bytes': 5524070460000.0,
                'ceph.osd.utilization_perc': 6.16,
                'ceph.osd.variance': 0.936619,
                'ceph.osd.pgs_count': 199,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.18': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 403252800000.0,
                'ceph.osd.avail_bytes': 5483380732000.0,
                'ceph.osd.utilization_perc': 6.85,
                'ceph.osd.variance': 1.041734,
                'ceph.osd.pgs_count': 229,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.19': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 5886633532000.0,
                'ceph.osd.used_bytes': 416788096000.0,
                'ceph.osd.avail_bytes': 5469845436000.0,
                'ceph.osd.utilization_perc': 7.08,
                'ceph.osd.variance': 1.076701,
                'ceph.osd.pgs_count': 210,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.20': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.21': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.22': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.23': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.24': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.25': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.26': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.27': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
            'osd.28': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 1
            },
            'osd.29': {
                'ceph.osd.crush_weight': 5.482391,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 1
            },
            'osd.30': {
                'ceph.osd.crush_weight': 0.232788,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 249955652000.0,
                'ceph.osd.used_bytes': 6512248000.0,
                'ceph.osd.avail_bytes': 243443404000.0,
                'ceph.osd.utilization_perc': 2.61,
                'ceph.osd.variance': 0.3962,
                'ceph.osd.pgs_count': 1030,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.31': {
                'ceph.osd.crush_weight': 0.232788,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 1.0,
                'ceph.osd.total_bytes': 249955652000.0,
                'ceph.osd.used_bytes': 5456072000.0,
                'ceph.osd.avail_bytes': 244499580000.0,
                'ceph.osd.utilization_perc': 2.18,
                'ceph.osd.variance': 0.331943,
                'ceph.osd.pgs_count': 1030,
                'ceph.osd.perf.commit_latency_seconds': 0.0,
                'ceph.osd.perf.apply_latency_seconds': 0.0,
                'ceph.osd.up': 1,
                'ceph.osd.in': 1
            },
            'osd.32': {
                'ceph.osd.crush_weight': 0.232788,
                'ceph.osd.depth': 2,
                'ceph.osd.reweight': 0.0,
                'ceph.osd.total_bytes': 0.0,
                'ceph.osd.used_bytes': 0.0,
                'ceph.osd.avail_bytes': 0.0,
                'ceph.osd.utilization_perc': 0.0,
                'ceph.osd.variance': 0.0,
                'ceph.osd.pgs_count': 0,
                'ceph.osd.up': 0,
                'ceph.osd.in': 0
            },
        },
        'summary_metrics': {
            'ceph.osds.total_bytes': 118232581944000.0,
            'ceph.osds.total_used_bytes': 7774823744000.0,
            'ceph.osds.total_avail_bytes': 110457758200000.0,
            'ceph.osds.avg_utilization_perc': 6.575872
        },
        'pool_metrics': {
            'cephfs_metadata': {
                'ceph.pool.dirty_objects_count': 66133,
                'ceph.pool.max_avail_bytes': 236492341248,
                'ceph.pool.objects_count': 66133,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.read_bytes': 1511467008,
                'ceph.pool.read_io': 545015,
                'ceph.pool.used_bytes': 47653204,
                'ceph.pool.used_raw_bytes': 91122080,
                'ceph.pool.utilization_perc': 0.000201459394257617,
                'ceph.pool.total_bytes': 236539994452,
                'ceph.pool.write_io': 1823016,
                'ceph.pool.write_bytes': 15099714560
            },
            'cephfs_data': {
                'ceph.pool.used_bytes': 1743163949040,
                'ceph.pool.dirty_objects_count': 1287159,
                'ceph.pool.max_avail_bytes': 52729787449344,
                'ceph.pool.objects_count': 1287159,
                'ceph.pool.utilization_perc': 0.0320005416319651,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 3419234369536,
                'ceph.pool.read_io': 624295721,
                'ceph.pool.read_bytes': 25137454158848,
                'ceph.pool.total_bytes': 54472951398384,
                'ceph.pool.write_io': 65020292,
                'ceph.pool.write_bytes': 18614600047616
            },
            '.rgw.root': {
                'ceph.pool.used_bytes': 1113,
                'ceph.pool.dirty_objects_count': 4,
                'ceph.pool.max_avail_bytes': 52953687785472,
                'ceph.pool.objects_count': 4,
                'ceph.pool.utilization_perc': 0.0000000000210183661709385,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 2226,
                'ceph.pool.read_io': 4806,
                'ceph.pool.read_bytes': 3280896,
                'ceph.pool.total_bytes': 52953687786585,
                'ceph.pool.write_io': 4,
                'ceph.pool.write_bytes': 4096
            },
            'default.rgw.control': {
                'ceph.pool.used_bytes': 0,
                'ceph.pool.dirty_objects_count': 8,
                'ceph.pool.max_avail_bytes': 52953687785472,
                'ceph.pool.objects_count': 8,
                'ceph.pool.utilization_perc': 0.0,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 0,
                'ceph.pool.read_io': 0,
                'ceph.pool.read_bytes': 0,
                'ceph.pool.total_bytes': 52953687785472,
                'ceph.pool.write_io': 0,
                'ceph.pool.write_bytes': 0
            },
            'default.rgw.meta': {
                'ceph.pool.used_bytes': 832,
                'ceph.pool.dirty_objects_count': 6,
                'ceph.pool.max_avail_bytes': 52953687785472,
                'ceph.pool.objects_count': 6,
                'ceph.pool.utilization_perc': 0.0000000000157118424567059,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 1664,
                'ceph.pool.read_io': 220,
                'ceph.pool.read_bytes': 204800,
                'ceph.pool.total_bytes': 52953687786304,
                'ceph.pool.write_io': 147,
                'ceph.pool.write_bytes': 19456
            },
            'default.rgw.log': {
                'ceph.pool.used_bytes': 0,
                'ceph.pool.dirty_objects_count': 207,
                'ceph.pool.max_avail_bytes': 52953687785472,
                'ceph.pool.objects_count': 207,
                'ceph.pool.utilization_perc': 0.0,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 0,
                'ceph.pool.read_io': 21378199,
                'ceph.pool.read_bytes': 21891063808,
                'ceph.pool.total_bytes': 52953687785472,
                'ceph.pool.write_io': 14245040,
                'ceph.pool.write_bytes': 0
            },
            'default.rgw.buckets.index': {
                'ceph.pool.used_bytes': 0,
                'ceph.pool.dirty_objects_count': 1,
                'ceph.pool.max_avail_bytes': 52953687785472,
                'ceph.pool.objects_count': 1,
                'ceph.pool.utilization_perc': 0.0,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 0,
                'ceph.pool.read_io': 562,
                'ceph.pool.read_bytes': 580608,
                'ceph.pool.total_bytes': 52953687785472,
                'ceph.pool.write_io': 237,
                'ceph.pool.write_bytes': 0
            },
            'default.rgw.buckets.data': {
                'ceph.pool.used_bytes': 95250,
                'ceph.pool.dirty_objects_count': 6,
                'ceph.pool.max_avail_bytes': 52953687785472,
                'ceph.pool.objects_count': 6,
                'ceph.pool.utilization_perc': 0.00000000179891153595516,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 190500,
                'ceph.pool.read_io': 162,
                'ceph.pool.read_bytes': 291840,
                'ceph.pool.total_bytes': 52953687880722,
                'ceph.pool.write_io': 427,
                'ceph.pool.write_bytes': 602112
            },
            'kubernetes': {
                'ceph.pool.used_bytes': 4859,
                'ceph.pool.dirty_objects_count': 8,
                'ceph.pool.max_avail_bytes': 79430529581056,
                'ceph.pool.objects_count': 8,
                'ceph.pool.utilization_perc': 0.0000000000611729523311855,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 8503,
                'ceph.pool.read_io': 164,
                'ceph.pool.read_bytes': 133120,
                'ceph.pool.total_bytes': 79430529585915,
                'ceph.pool.write_io': 90892,
                'ceph.pool.write_bytes': 126869424128
            },
            'volumes': {
                'ceph.pool.used_bytes': 0,
                'ceph.pool.dirty_objects_count': 0,
                'ceph.pool.max_avail_bytes': 79430529581056,
                'ceph.pool.objects_count': 0,
                'ceph.pool.utilization_perc': 0.0,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 0,
                'ceph.pool.read_io': 0,
                'ceph.pool.read_bytes': 0,
                'ceph.pool.total_bytes': 79430529581056,
                'ceph.pool.write_io': 0,
                'ceph.pool.write_bytes': 0
            },
            'benchmark': {
                'ceph.pool.used_bytes': 37906503270,
                'ceph.pool.dirty_objects_count': 33213250,
                'ceph.pool.max_avail_bytes': 79430529581056,
                'ceph.pool.objects_count': 33213250,
                'ceph.pool.utilization_perc': 0.000477000745676893,
                'ceph.pool.quota_max_bytes': 0,
                'ceph.pool.quota_max_objects': 0,
                'ceph.pool.used_raw_bytes': 66925428736,
                'ceph.pool.read_io': 2261777,
                'ceph.pool.read_bytes': 3829217280,
                'ceph.pool.total_bytes': 79468436084326,
                'ceph.pool.write_io': 33280403,
                'ceph.pool.write_bytes': 62774775808
            }
        },
        'mon_metrics': {
        },
        'test_ceph_cmd_lens': {
            'df detail json': 2,
            'status json': 11,
            'status': 842,
            'osd df json': 3,
            'osd perf json': 1,
            'osd dump json': 24,
            'osd pool stats json': 11
        },
        'test_check_call_count': 578
    }
