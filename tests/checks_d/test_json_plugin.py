# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP

import fcntl
import json
from shutil import rmtree
from socket import gethostname
import tempfile
import os
import unittest

from monasca_agent.collector.checks_d import json_plugin
import monasca_agent.common.config


HOSTNAME = gethostname()


def _create_agent_conf():
    # create a temp conf file
    tempdir = tempfile.mkdtemp()
    conf_file = os.path.join(tempdir, 'agent.yaml')
    with open(conf_file, 'wb') as fd:
        fd.write(
            """
            Logging:
              collector_log_file: /var/log/monasca/agent/collector.log
              forwarder_log_file: /var/log/monasca/agent/forwarder.log
              log_level: DEBUG
              statsd_log_file: /var/log/monasca/agent/statsd.log
            Main:
              check_freq: 60
              dimensions: {{}}
              hostname: {hostname}
            """.format(hostname=HOSTNAME)
        )

    config_obj = monasca_agent.common.config.Config(conf_file)
    config = config_obj.get_config(sections='Main')
    # clean up
    rmtree(tempdir, ignore_errors=True)
    return config


fake_now = 1


def FakeNow():
    global fake_now
    return fake_now


class MockJsonPlugin(json_plugin.JsonPlugin):
    def __init__(self):
        super(MockJsonPlugin, self).__init__(
            name='json_plugin',
            init_config={},
            instances=[],
            agent_config=_create_agent_conf()
        )
        self._metrics = []

    def check(self, instance):
        self._metrics = []
        return super(MockJsonPlugin, self).check(instance)

    def gauge(self, **kwargs):
        self._metrics.append(kwargs)


def metricsDiffer(expected, actual_orig, ignore_timestamps=True):
    expected = list(expected)
    actual = list(actual_orig)
    if ignore_timestamps:
        for metric in expected:
            metric['timestamp'] = 'ts'
        for metric in actual:
            metric['timestamp'] = 'ts'
    for metric in list(expected):
        if metric not in actual:
            return 'Expected...\n%s\n  ...is missing from actual:\n%s' %\
                   (metrics_sort(metric), metrics_sort(actual_orig))
        actual.remove(metric)
    if actual:
        return 'Unexpected (i.e., extra) metrics:\n%s' % metrics_sort(actual)
    return ''


def metrics_repr(metric):
    m = ''
    for key in ['timestamp', 'metric', 'value', 'dimensions', 'value_meta']:
        m += '%s ' % metric.get(key, '-')
    return m


def metrics_sort(metrics):
    """Makes it easier to debug failed asserts"""
    if isinstance(metrics, list):
        mlist = []
        for metric in metrics:
            mlist.append(metrics_repr(metric))
        mlist.sort()
    else:
        mlist = [metrics_repr(metrics)]
    return '\n'.join(mlist)


def write_metrics_file(file_name, metrics, replace_timestamps=False,
                       stale_age=None):
    file_data = {'replace_timestamps': replace_timestamps,
                 'measurements': []}
    if stale_age:
        file_data.update({'stale_age': stale_age})
    for metric in metrics:
        file_data['measurements'].append(metric)
    with open(file_name, mode='w') as fd:
        fd.write(json.dumps(file_data))


def make_expected(metrics, file_name, now, ts_override=None):
    expected = []
    for metric in list(metrics):
        if ts_override:
            metric['timestamp'] = ts_override
        metric['dimensions'].update({'hostname': HOSTNAME})
        expected.append(metric)
    json_plugin_status = {'metric': 'monasca.json_plugin.status', 'value': 0,
                          'dimensions': {'hostname': HOSTNAME},
                          'timestamp': now}
    expected.append(json_plugin_status)
    return expected


class JsonPluginCheckTest(unittest.TestCase):
    def setUp(self):
        super(JsonPluginCheckTest, self).setUp()
        self.json_plugin = MockJsonPlugin()

    def test_no_config(self):
        self.json_plugin.check({})

    def test_metric_dir(self):
        tempdir = tempfile.mkdtemp()
        # Empty metrics_dir:
        self.json_plugin.check({'dimensions': {},
                                'metrics_dir': tempdir})
        self.assertEqual([], self.json_plugin.metrics_files)
        expected = [
            {'metric': 'monasca.json_plugin.status', 'value': 0,
             'dimensions': {'hostname': HOSTNAME}}]
        differs = metricsDiffer(expected, self.json_plugin._metrics)
        self.assertEqual('', differs, msg=differs)

        # Create json files:
        file1 = os.path.join(tempdir, 'file1.json')
        file2 = os.path.join(tempdir, 'file2.json')
        for metric_file in [file1, file2]:
            with open(metric_file, mode='w') as fd:
                fd.write('[]')
        self.json_plugin.check({'dimensions': {},
                                'metrics_dir': tempdir})
        self.assertIn(file1, self.json_plugin.metrics_files)
        self.assertIn(file2, self.json_plugin.metrics_files)
        rmtree(tempdir, ignore_errors=True)

        expected = [
            {'metric': 'monasca.json_plugin.status', 'value': 0,
             'dimensions': {'hostname': HOSTNAME}}
        ]
        differs = metricsDiffer(expected, self.json_plugin._metrics)
        self.assertEqual('', differs, msg=differs)

    def test_bad_json_reporting(self):
        global fake_now
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        with open(file1, mode='w') as fd:
            fd.write('{')
        self.json_plugin.check({'dimensions': {},
                                'metrics_file': file1})
        rmtree(tempdir, ignore_errors=True)
        for now in [1000, 2000]:
            fake_now = now
            expected = [{'metric': 'monasca.json_plugin.status', 'value': 1,
                         'dimensions': {'hostname': HOSTNAME},
                         'value_meta': {
                             'msg': '%s: failed parsing json: Expecting'
                                    ' object: line 1'
                                    ' column 1 (char 0)' % file1}}]
            differs = metricsDiffer(expected, self.json_plugin._metrics)
            self.assertEqual('', differs, msg=differs)

    def test_replaced_timestamps(self):
        global fake_now
        json_plugin._now = FakeNow
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        metrics = [
            {'metric': 'name1', 'value': 1,
             'dimensions': {'dim1': 'dim1val'}},
            {'metric': 'name2', 'value': 2,
             'dimensions': {'dim2': 'dim2val'}}
        ]

        write_metrics_file(file1, metrics, replace_timestamps=True)
        for now in [1000, 2000]:
            fake_now = now
            expected = make_expected(metrics, file1, now, ts_override=now)
            self.json_plugin.check({'dimensions': {},
                                   'metrics_file': file1})
            differs = metricsDiffer(expected, self.json_plugin._metrics,
                                    ignore_timestamps=False)
            self.assertEqual('', differs, msg=differs)
        rmtree(tempdir, ignore_errors=True)

    def test_with_timestamps(self):
        global fake_now
        json_plugin._now = FakeNow
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        metrics = [
            {'metric': 'name1', 'value': 1,
             'dimensions': {'dim1': 'dim1val'}},
            {'metric': 'name2', 'value': 2,
             'dimensions': {'dim2': 'dim2val'}}
        ]
        for now in [1000, 2000]:
            fake_now = now
            for metric in metrics:
                metric['timestamp'] = now
            write_metrics_file(file1, metrics, replace_timestamps=False,
                               stale_age=3000)
            expected = make_expected(metrics, file1, now)
            self.json_plugin.check({'dimensions': {},
                                   'metrics_file': file1})
            differs = metricsDiffer(expected, self.json_plugin._metrics,
                                    ignore_timestamps=False)
            self.assertEqual('', differs, msg=differs)
        rmtree(tempdir, ignore_errors=True)

    def test_with_stale_age(self):
        global fake_now
        json_plugin._now = FakeNow
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        metrics = [
            {'metric': 'name1', 'value': 1,
             'dimensions': {'dim1': 'dim1val'}},
            {'metric': 'name2', 'value': 2,
             'dimensions': {'dim2': 'dim2val'}}
        ]
        now = 1000
        fake_now = now
        for metric in metrics:
            metric['timestamp'] = now
        write_metrics_file(file1, metrics, replace_timestamps=False,
                           stale_age=500)
        expected = make_expected(metrics, file1, now, ts_override=now)
        self.json_plugin.check({'dimensions': {},
                               'metrics_file': file1})
        differs = metricsDiffer(expected, self.json_plugin._metrics,
                                ignore_timestamps=False)
        self.assertEqual('', differs, msg=differs)

        # Time moves on, but don't re-write the metrics file
        now = 2000
        fake_now = now
        expected = [{'metric': 'monasca.json_plugin.status', 'value': 1,
                     'dimensions': {'hostname': HOSTNAME},
                     'value_meta': {
                         'msg': '%s: Metrics are older than 500 seconds;'
                                ' file not updating?' % file1}}]
        self.json_plugin.check({'dimensions': {},
                               'metrics_file': file1})
        differs = metricsDiffer(expected, self.json_plugin._metrics,
                                ignore_timestamps=True)
        self.assertEqual('', differs, msg=differs)
        rmtree(tempdir, ignore_errors=True)

    def test_no_duplicates(self):
        global fake_now
        json_plugin._now = FakeNow
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        metrics = [
            {'metric': 'name1', 'value': 1,
             'dimensions': {'dim1': 'dim1val'}},
            {'metric': 'name2', 'value': 2,
             'dimensions': {'dim2': 'dim2val'}}
        ]
        now = 1000
        fake_now = now
        for metric in metrics:
            metric['timestamp'] = now
        write_metrics_file(file1, metrics, replace_timestamps=False,
                           stale_age=5000)
        expected = make_expected(metrics, file1, now, ts_override=now)
        self.json_plugin.check({'dimensions': {},
                               'metrics_file': file1})
        differs = metricsDiffer(expected, self.json_plugin._metrics,
                                ignore_timestamps=False)
        self.assertEqual('', differs, msg=differs)

        # Time moves on, but don't re-write the metrics file
        now = 2000
        fake_now = now
        # We don't get the metrics from the file again -- just the plugin
        # status metric
        expected = [{'metric': 'monasca.json_plugin.status', 'value': 0,
                     'dimensions': {'hostname': HOSTNAME},
                     'timestamp': now}]
        self.json_plugin.check({'dimensions': {},
                               'metrics_file': file1})
        differs = metricsDiffer(expected, self.json_plugin._metrics,
                                ignore_timestamps=False)
        self.assertEqual('', differs, msg=differs)
        rmtree(tempdir, ignore_errors=True)

    def test_validate_metrics(self):
        metrics = [
            {'metric': 'ok1', 'value': 1},
            {'name': 'ok2', 'value': 2},
            {'metric': 'ok3', 'value': 3, 'dimensions': {}, 'value_meta': {},
             'timestamp': 123},
            {'metric': 'bad1'},
            {'metric': 'bad2', 'junk_key': 'extra'},
            {'value': 1, 'value_meta': {'msg': 'no name or metric key'}},
            {'metric': 'ok4', 'value': 1},
        ]
        valid = self.json_plugin._filter_metrics(metrics, 'dummy.json')
        self.assertTrue('dummy.json' in self.json_plugin.plugin_failures)
        self.assertEqual(4, len(valid))

    def test_posted_metrics_are_purged(self):
        global fake_now
        json_plugin._now = FakeNow
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        metrics = [
            {'metric': 'name1', 'value': 1,
             'dimensions': {'dim1': 'dim1val'}},
            {'metric': 'name2', 'value': 2,
             'dimensions': {'dim2': 'dim2val'}}
        ]
        for now in [1000, 2000, 3000, 4000, 5000, 6000]:
            fake_now = now
            for metric in metrics:
                metric['timestamp'] = now
            write_metrics_file(file1, metrics, replace_timestamps=False,
                               stale_age=2000)
            self.json_plugin.check({'dimensions': {},
                                   'metrics_file': file1})
        for metric in self.json_plugin.posted_metrics[file1]:
            self.assertTrue(metric.get('timestamp', 0) >= 2001, 'not purged')
        self.assertTrue(len(self.json_plugin.posted_metrics[file1]) > 0,
                        'posted metrics not being cached')
        rmtree(tempdir, ignore_errors=True)

    def test_take_lock(self):
        tempdir = tempfile.mkdtemp()
        file1 = os.path.join(tempdir, 'file1.json')
        with open(file1, 'w') as fd_writer:
            with open(file1, 'r') as fd_reader:
                fcntl.flock(fd_writer, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(IOError):
                    json_plugin.JsonPlugin._take_shared_lock(fd_reader)
