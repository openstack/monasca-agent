# (C) Copyright 2016 Hewlett Packard Enterprise Development LP

import contextlib
import logging
import os
import psutil
import tempfile
import unittest

from mock import patch

from monasca_setup.detection.plugins.process import ProcessCheck

LOG = logging.getLogger('monasca_setup.detection.plugins.process')


class PSUtilGetProc(object):
    cmdLine = ['monasca-api']

    def as_dict(self, attrs=None):
        return {'name': 'monasca-api',
                'cmdline': PSUtilGetProc.cmdLine}

    def cmdline(self):
        return self.cmdLine


class TestProcessCheck(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        with patch.object(ProcessCheck, '_detect') as mock_detect:
            self.proc_plugin = ProcessCheck('temp_dir')
            self.assertTrue(mock_detect.called)

    def _detect(self,
                proc_plugin,
                config_is_file=False,
                by_process_name=True):
        proc_plugin.available = False
        psutil_mock = PSUtilGetProc()

        process_iter_patch = patch.object(psutil, 'process_iter',
                                          return_value=[psutil_mock])
        isfile_patch = patch.object(os.path, 'isfile',
                                    return_value=config_is_file)

        with contextlib.nested(process_iter_patch,
                               isfile_patch) as (
                mock_process_iter, mock_isfile):
            proc_plugin._detect()
            if by_process_name:
                self.assertTrue(mock_process_iter.called)
            self.assertFalse(mock_isfile.called)

    def test_detect_process_not_found(self):
        PSUtilGetProc.cmdLine = []
        self.proc_plugin.process_config = [{'process_names': ['monasca-api'], 'dimensions': {'service': 'monitoring'}}]
        self._detect(self.proc_plugin)
        self.assertFalse(self.proc_plugin.available)

    def test_detect_process_found(self):
        self.proc_plugin.process_config = [{'process_names': ['monasca-api'], 'dimensions': {'service': 'monitoring'}}]
        self._detect(self.proc_plugin)
        self.assertTrue(self.proc_plugin.available)

    def test_missing_arg(self):
        # monitor by process_username requires component
        self.proc_plugin.process_config = [{'process_username': 'dbadmin', 'dimensions': {'service': 'monitoring'}}]
        self._detect(self.proc_plugin, by_process_name=False)
        self.assertFalse(self.proc_plugin.available)

    def test_detect_build_config_process_name(self):
        self.proc_plugin.process_config = [{'process_names': ['monasca-api'], 'dimensions': {'service': 'monitoring'}}]
        self._detect(self.proc_plugin)
        result = self.proc_plugin.build_config()
        self.assertEqual(result['process']['instances'][0]['name'],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][0]['detailed'],
                         True)
        self.assertEqual(result['process']['instances'][0]['exact_match'],
                         False)
        self.assertEqual(result['process']['instances'][0]['dimensions']['service'],
                         'monitoring')
        self.assertEqual(result['process']['instances'][0]['dimensions']['component'],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][0]['search_string'][0],
                         'monasca-api')

    def test_detect_build_config_process_name_exact_match_true(self):
        self.proc_plugin.process_config = [
            {'process_names': ['monasca-api'], 'dimensions': {'service': 'monitoring'}, 'exact_match': True}]
        self._detect(self.proc_plugin)
        result = self.proc_plugin.build_config()
        self.assertEqual(result['process']['instances'][0]['name'],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][0]['detailed'],
                         True)
        self.assertEqual(result['process']['instances'][0]['exact_match'],
                         True)
        self.assertEqual(result['process']['instances'][0]['dimensions']['service'],
                         'monitoring')
        self.assertEqual(result['process']['instances'][0]['dimensions']['component'],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][0]['search_string'][0],
                         'monasca-api')

    def test_build_config_process_names(self):
        self.proc_plugin.valid_process_names = [
            {'process_names': ['monasca-api'],
             'dimensions': {'service': 'monitoring'},
             'found_process_names': ['monasca-api'],
             'exact_match': False},
            {'process_names': ['monasca-thresh'],
             'dimensions': {'service': 'monitoring'},
             'found_process_names': ['monasca-thresh'],
             'exact_match': False}]
        result = self.proc_plugin.build_config()
        self.assertEqual(result['process']['instances'][0]['name'],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][0]['detailed'],
                         True)
        self.assertEqual(result['process']['instances'][0]['exact_match'],
                         False)
        self.assertEqual(result['process']['instances'][0]['dimensions']['service'],
                         'monitoring')
        self.assertEqual(result['process']['instances'][0]['dimensions']['component'],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][0]['search_string'][0],
                         'monasca-api')
        self.assertEqual(result['process']['instances'][1]['name'],
                         'monasca-thresh')
        self.assertEqual(result['process']['instances'][1]['dimensions']['component'],
                         'monasca-thresh')

    def test_detect_build_config_process_username(self):
        self.proc_plugin.process_config = \
            [{'process_username': 'dbadmin', 'dimensions': {'service': 'monitoring', 'component': 'vertica'}}]
        self.proc_plugin._detect()
        result = self.proc_plugin.build_config()
        self.assertEqual(result['process']['instances'][0]['name'],
                         'vertica')
        self.assertEqual(result['process']['instances'][0]['detailed'],
                         True)
        self.assertEqual(result['process']['instances'][0]['dimensions']['service'],
                         'monitoring')
        self.assertEqual(result['process']['instances'][0]['dimensions']['component'],
                         'vertica')

    def test_input_yaml_file(self):
        # note: The previous tests will cover all yaml data variations, since the data is translated into a single dictionary.
        fd, temp_path = tempfile.mkstemp(suffix='.yaml')
        os.write(fd, '---\nprocess_config:\n- process_username: dbadmin\n  dimensions:\n    '
                 'service: monitoring\n    component: vertica\n')
        self.proc_plugin.args = {'conf_file_path': temp_path}
        self.proc_plugin._detect()
        result = self.proc_plugin.build_config()
        self.assertEqual(result['process']['instances'][0]['name'],
                         'vertica')
        self.assertEqual(result['process']['instances'][0]['detailed'],
                         True)
        self.assertEqual(result['process']['instances'][0]['dimensions']['service'],
                         'monitoring')
        self.assertEqual(result['process']['instances'][0]['dimensions']['component'],
                         'vertica')
        os.close(fd)
        os.remove(temp_path)
