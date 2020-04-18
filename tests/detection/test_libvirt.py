# (C) Copyright 2019 SUSE LLC

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

from collections import namedtuple
from unittest import mock
import unittest

from oslo_config import cfg

from monasca_setup.detection.plugins.libvirt import Libvirt
from monasca_setup.detection import utils


class TestLibvirt(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

    @mock.patch('monasca_setup.detection.utils.load_oslo_configuration')
    def test_load_oslo_configuration_params(self, patched_load_oslo_config):
        """Test oslo config options.

        Making sure libvirt detection plugin pass the correct
        params to utils.load_oslo_configuration().
        """
        plugin = Libvirt(mock.MagicMock())
        nova_conf = plugin._find_nova_conf(mock.MagicMock())
        self.assertTrue(patched_load_oslo_config.called)
        args, kwargs = patched_load_oslo_config.call_args_list[0]
        self.assertEqual('nova', kwargs['in_project'])
        expected_options = [
            'username',
            'user_domain_name',
            'password',
            'project_name',
            'project_domain_name',
            'auth_url']
        for opt in expected_options:
            self.assertTrue(
                any(d['opt'] == cfg.StrOpt(opt) for d in kwargs['for_opts']))

    def test_init_config(self):
        plugin = Libvirt(mock.MagicMock())
        keystone_authtoken_args = {
            'username': 'foo',
            'user_domain_name': 'Default',
            'password': 'secrete',
            'project_name': 'bar',
            'project_domain_name': 'Default',
            'auth_url': 'https://127.0.0.1:5000/v3'
        }
        plugin.nova_conf = {'keystone_authtoken': keystone_authtoken_args}
        init_config = plugin._get_init_config()
        for arg in keystone_authtoken_args:
            self.assertEqual(keystone_authtoken_args[arg], init_config[arg])
