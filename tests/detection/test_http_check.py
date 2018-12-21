# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
# (C) Copyright 2018 SUSE LLC

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

import unittest

from monasca_setup.detection.plugins.http_check import HttpCheck


class TestHttpCheck(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

    def test_processs_keystone_global_args(self):
        args = ('keystone_url=https://my.keystone.host.com/identity '
                'keystone_user=foo keystone_password=testpasswd '
                'keystone_project=test_project keystone_project_domain=bar '
                'keystone_user_domain=bar use_keystone=True '
                'url=https://myurl.com')
        plugin = HttpCheck(None, args=args)
        conf = plugin.build_config()
        self.assertTrue('keystone_config' in conf['http_check']['init_config'])
        expected_keystone_config = {
            'keystone_url': 'https://my.keystone.host.com/identity',
            'username': 'foo',
            'password': 'testpasswd',
            'project_name': 'test_project',
            'project_domain_name': 'bar',
            'user_domain_name': 'bar'
        }
        self.assertDictEqual(
            expected_keystone_config,
            conf['http_check']['init_config']['keystone_config'])
