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

import mock

from oslotest import base
import psutil

from monasca_setup.detection.plugins import ceph


MON_PROCESSES = [
    {'name': 'ceph-mon.mon0',
     'type': 'ceph-mon',
     'search_string': [
         '/usr/bin/ceph-mon --cluster ceph --id mon0 -f',
         '/usr/bin/ceph-mon --cluster ceph -f --id mon0',
         '/usr/bin/ceph-mon --id mon0 --cluster ceph -f',
         '/usr/bin/ceph-mon --id mon0 -f --cluster ceph',
         '/usr/bin/ceph-mon -f --cluster ceph --id mon0',
         '/usr/bin/ceph-mon -f --id mon0 --cluster ceph'
     ]},
    {'name': 'ceph1-mon.mon0',
     'type': 'ceph-mon',
     'search_string': [
         '/usr/bin/ceph-mon --cluster ceph1 --id mon0 -f',
         '/usr/bin/ceph-mon --cluster ceph1 -f --id mon0',
         '/usr/bin/ceph-mon --id mon0 --cluster ceph1 -f',
         '/usr/bin/ceph-mon --id mon0 -f --cluster ceph1',
         '/usr/bin/ceph-mon -f --cluster ceph1 --id mon0',
         '/usr/bin/ceph-mon -f --id mon0 --cluster ceph1'
     ]},
]

RGW_PROCESSES = [
    {'name': 'ceph-radosgw.rgw0',
     'type': 'ceph-radosgw',
     'search_string': [
         '/usr/bin/radosgw --cluster ceph --name client.rgw.rgw0 -f',
         '/usr/bin/radosgw --cluster ceph -f --name client.rgw.rgw0',
         '/usr/bin/radosgw --name client.rgw.rgw0 --cluster ceph -f',
         '/usr/bin/radosgw --name client.rgw.rgw0 -f --cluster ceph',
         '/usr/bin/radosgw -f --cluster ceph --name client.rgw.rgw0',
         '/usr/bin/radosgw -f --name client.rgw.rgw0 --cluster ceph'
     ]},
    {'name': 'ceph1-radosgw.rgw0',
     'type': 'ceph-radosgw',
     'search_string': [
         '/usr/bin/radosgw --cluster ceph1 --name client.rgw.rgw0 -f',
         '/usr/bin/radosgw --cluster ceph1 -f --name client.rgw.rgw0',
         '/usr/bin/radosgw --name client.rgw.rgw0 --cluster ceph1 -f',
         '/usr/bin/radosgw --name client.rgw.rgw0 -f --cluster ceph1',
         '/usr/bin/radosgw -f --cluster ceph1 --name client.rgw.rgw0',
         '/usr/bin/radosgw -f --name client.rgw.rgw0 --cluster ceph1'
     ]},
]


def mocked_service_config(*args, **kwargs):
    if args[1] == 'mon':
        return MON_PROCESSES
    elif args[1] == 'radosgw':
        return RGW_PROCESSES
    return []


class FakeProcess(object):
    cmdLine = None

    def as_dict(self, attrs=None):
        all_attrs = {'name': 'ceph',
                     'exe': FakeProcess.exe(),
                     'cmdline': FakeProcess.cmdline()}
        if attrs:
            for key in attrs:
                if key not in all_attrs:
                    all_attrs.pop(key, None)
        return all_attrs

    @staticmethod
    def exe():
        line = FakeProcess.cmdLine
        if not line:
            return None
        return line[0]

    @staticmethod
    def cmdline():
        return FakeProcess.cmdLine


class TestCephDetection(base.BaseTestCase):
    CLUSTERS = [
        {
            'cluster_name': 'ceph',
            'config_file': '/etc/ceph/ceph.conf'
        },
        {
            'cluster_name': 'ceph1',
            'config_file': '/etc/ceph/ceph1.conf'
        },
    ]

    def setUp(self):
        super(TestCephDetection, self).setUp()
        with mock.patch.object(ceph.Ceph, '_detect') as mock_detect:
            self._ceph = ceph.Ceph('ceph')
            self.assertTrue(mock_detect.called)

    def test_should_not_configure_if_no_process(self):
        FakeProcess.cmdLine = []
        self._detect(proc=True)
        self.assertFalse(self._ceph.available)

    def test_should_be_available_if_everything_matches(self):
        ceph_cmd = '/usr/bin/ceph-mon -f --cluster ceph --id mon0 --setuser' \
               ' ceph --setgroup ceph'
        FakeProcess.cmdLine = [ceph_cmd]
        self._detect()
        self.assertTrue(self._ceph.available)

    def test_build_search_string(self):
        executable = '/usr/bin/ceph-mon'
        args = ['--cluster ceph', '--id mon0', '-f']

        expected_strings = [
            '/usr/bin/ceph-mon --cluster ceph --id mon0 -f',
            '/usr/bin/ceph-mon --cluster ceph -f --id mon0',
            '/usr/bin/ceph-mon --id mon0 --cluster ceph -f',
            '/usr/bin/ceph-mon --id mon0 -f --cluster ceph',
            '/usr/bin/ceph-mon -f --cluster ceph --id mon0',
            '/usr/bin/ceph-mon -f --id mon0 --cluster ceph'
        ]

        search_strings = self._ceph._build_search_string(executable, args)
        self.assertEqual(expected_strings, search_strings)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.listdir', return_value=['ceph-mon0', 'ceph1-mon0'])
    def test_service_config(self, list_dir, path_exists):
        processes = self._ceph._service_config(self.CLUSTERS, 'mon')
        self.assertEqual(MON_PROCESSES, processes)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.listdir', return_value=['ceph-rgw.rgw0', 'ceph1-rgw.rgw0'])
    def test_radosgw_service_config(self, list_dir, path_exists):
        processes = self._ceph._service_config(self.CLUSTERS, 'radosgw')
        self.assertEqual(RGW_PROCESSES, processes)

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.listdir', return_value=[])
    def test_build_config_with_no_ceph_conf(self, list_dir, path_exists):
        config = self._ceph.build_config()
        self.assertEqual({}, dict(config))

    @mock.patch('os.path.exists', return_value=True)
    @mock.patch('os.listdir', return_value=['ceph.conf', 'ceph1.conf'])
    def test_build_config(self, list_dir, path_exists):
        self._ceph._service_config = mock.Mock(
            side_effect=mocked_service_config)

        processes = MON_PROCESSES + RGW_PROCESSES
        process_instances = list()

        for p in processes:
            instance = {
                'exact_match': False,
                'search_string': p['search_string'],
                'detailed': True,
                'name': p['name'],
                'dimensions':  {'component': p['type'], 'service': 'ceph'}
            }
            process_instances.append(instance)

        expected_config = {
            'process': {
                'init_config': None,
                'instances': process_instances,
            },
            'ceph': {
                'init_config': None,
                'instances': [{'cluster_name': 'ceph'},
                              {'cluster_name': 'ceph1'}]
            }
        }
        config = self._ceph.build_config()
        self.assertEqual(expected_config, dict(config))

    def _detect(self, proc=False):
        self._ceph.available = False
        processes = [FakeProcess()] if not proc else []
        process_iter = mock.patch.object(psutil, 'process_iter',
                                         return_value=processes)
        with process_iter as mock_process_iter:
            self._ceph._detect()
            self.assertTrue(mock_process_iter.called)
