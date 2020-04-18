# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
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

from monasca_setup.detection.plugins.host_alive import HostAlive

class TestHostAliveDetect(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self._host_alive = HostAlive('AAAA')
        self._expected_config = {
            'host_alive':
                {
                 'init_config':
                    {
                     'ssh_timeout': self._host_alive.DEFAULT_SSH_TIMEOUT,
                     'ping_timeout': self._host_alive.DEFAULT_PING_TIMEOUT,
                     'ssh_port': self._host_alive.DEFAULT_SSH_PORT
                    }
                }
        }

    def _create_instances(self, host_names, target_hostnames=None):
        instances = []
        index = 0
        for name in host_names:
            instance = {
                'alive_test': 'ping',
                'name': name + ' ping',
                'host_name': name}
            if (target_hostnames and
                index < len(target_hostnames)):
                target_hostname = target_hostnames[index]
                # It is possible that a target_hostname is not
                # set for each hostname
                if target_hostname:
                    instance['target_hostname'] = target_hostname
            index += 1
            instances.append(instance)
        self._expected_config['host_alive']['instances'] = instances

    def _run_build_config(self, host_names, target_hostnames=None):
        hostname = ','.join(host_names)
        args = {
            'type': 'ping',
            'hostname': hostname,
        }
        if target_hostnames:
            args['target_hostname'] = ','.join(target_hostnames)
        self._host_alive.args = args
        config = self._host_alive.build_config()
        self._create_instances(host_names, target_hostnames)
        self.assertEqual(config, self._expected_config)

    def test_build_config_simple(self):
        hostname = 'aaaa'
        self._run_build_config([hostname])

    def test_build_config_multiple(self):
        host_names = ['aaaa', 'bbbb', 'cccc']
        self._run_build_config(host_names)

    def test_build_config_complex(self):
        host_names = ['aaaa', 'bbbb', 'cccc']
        target_hostnames = ['dddd', 'eeee', 'ffff']
        self._run_build_config(host_names, target_hostnames)

    def test_build_config_complex_sparse(self):
        host_names = ['aaaa', 'bbbb', 'cccc']
        target_hostnames = ['dddd', '', 'ffff']
        self._run_build_config(host_names, target_hostnames)

    def test_build_config_complex_not_matching(self):
        host_names = ['aaaa', 'bbbb', 'cccc']
        target_hostnames = ['dddd']
        self._run_build_config(host_names, target_hostnames)

    def test_build_config_complex_too_many(self):
        host_names = ['aaaa', 'bbbb', 'cccc']
        target_hostnames = ['dddd', 'eeee', 'ffff', 'gggg']
        with self.assertRaises(Exception):
            self._run_build_config(host_names, target_hostnames)
