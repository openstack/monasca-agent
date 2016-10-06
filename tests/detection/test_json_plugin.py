# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

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
