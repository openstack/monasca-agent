# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
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

import os
import shutil
import tempfile
import unittest

from monasca_setup.detection.plugins import json_plugin


class TestJsonPlugin(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.plugin_obj = json_plugin.JsonPlugin('temp_dir')
        self.varcachedir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.varcachedir)

    def test_var_cache_exists(self):
        json_plugin.VAR_CACHE_DIR = self.varcachedir
        self.plugin_obj._detect()
        result = self.plugin_obj.build_config()
        self.assertTrue(self.plugin_obj.available)
        self.assertEqual(result['json_plugin']['instances'],
                         [{'name': self.varcachedir,
                            'metrics_dir': self.varcachedir}])

    def test_var_cache_not_exists(self):
        json_plugin.VAR_CACHE_DIR = os.path.join(self.varcachedir, 'dummy')
        self.plugin_obj._detect()
        self.assertFalse(self.plugin_obj.available)

    def test_dependencies_installed(self):
        self.assertTrue(self.plugin_obj.dependencies_installed())
