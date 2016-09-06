# (C) Copyright 2016 Hewlett Packard Enterprise Development LP

import collections
import mock
import unittest

import monasca_setup
import monasca_setup.agent_config

DEFAULT_HTTP_CHECK_CONFIG = {
    'init_config': None,
    'instances': [{'built_by': 'HttpCheck',
                   'match_pattern': '.*VERSION.*',
                   'url': 'http://127.0.0.1:9200',
                   'name': 'logging',
                   'timeout': '10',
                   'collect_response_time': True,
                   'use_keystone': False,
                   'dimensions': {'service': 'logging'}}]
}

DEFAULT_PROCESS_CHECK_CONFIG = {
    'init_config': None,
    'instances': [{'built_by': 'MonNotification',
                   'detailed': True,
                   'dimensions': {'component': 'monasca-notification'},
                   'exact_match': False,
                   'name': 'monasca-notification',
                   'search_string': ['monasca-notification']
                   }]
}

INPUT_ARGS = collections.namedtuple(
    "InputArgs", ["overwrite", "user", "config_dir", "detection_args",
                  "detection_plugins", "dry_run"])


class TestModifyConfig(unittest.TestCase):
    """ Unit tests for modify_config function in monasca_setup/main.py
        More details are documented in:
        monasca-agent/docs/DeveloperDocs/agent_internals.md
    """
    def setUp(self):
        self._config_data = {}

    def save_config(self, config_dir, plugin_name, user, data):
        self._config_data = data

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_no_modify_process_check_config(self, mock_read_config,
                                            mock_save_config):
        mock_read_config.return_value = DEFAULT_PROCESS_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # Add a new process check instance
        same_built_by = DEFAULT_PROCESS_CHECK_CONFIG['instances'][0][
            'built_by']
        same_name = DEFAULT_PROCESS_CHECK_CONFIG['instances'][0][
            'name']
        args, detected_config = self._get_mon_api_check_args_and_config(
            same_built_by, same_name)
        self._check_no_change(args, detected_config)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_modify_process_check_config(self, mock_read_config,
                                         mock_save_config):
        mock_read_config.return_value = DEFAULT_PROCESS_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # Add a new process check instance
        built_by = 'MonAPI'
        name = 'monasca-api'
        args, detected_config = self._get_mon_api_check_args_and_config(
            built_by, name)
        expected_value = \
            {'init_config': None,
             'instances': [{'built_by': built_by,
                            'detailed': True,
                            'dimensions': {'component': 'monasca-api'},
                            'exact_match': False,
                            'name': name,
                            'search_string': ['monasca-api']
                            },
                           DEFAULT_PROCESS_CHECK_CONFIG['instances'][0]]
             }
        self._check_changes(args, detected_config, expected_value)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_no_modify_http_check_config(self, mock_read_config,
                                         mock_save_config):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # keep url and match_pattern are the same
        same_url = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['url']
        same_match_pattern = DEFAULT_HTTP_CHECK_CONFIG['instances'][0][
            'match_pattern']
        same_name = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['name']

        args, detected_config = self. _get_http_check_args_and_config(
            same_url, same_match_pattern, same_name)
        self._check_no_change(args, detected_config)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_modify_http_check_config(self, mock_read_config,
                                      mock_save_config):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # Change protocol and match_pattern
        url = 'https://127.0.0.1:9200'
        match_pattern = '.*OK.*'

        args, detected_config = self. _get_http_check_args_and_config(
            url, match_pattern, 'logging')
        expected_value = {'init_config': None,
                          'instances':
                          [{'built_by': 'HttpCheck',
                            'collect_response_time': True,
                            'url': url,
                            'match_pattern': match_pattern,
                            'name': 'logging',
                            'timeout': '10',
                            'use_keystone': False,
                            'dimensions': {'service': 'logging'}}]
                          }
        self._check_changes(args, detected_config, expected_value)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_http_check_endpoint_change(self, mock_read_config,
                                        mock_save_config):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # Change only protocol
        new_url = 'https://127.0.0.1:9200'
        same_match_pattern = DEFAULT_HTTP_CHECK_CONFIG['instances'][0][
            'match_pattern']
        same_name = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['name']
        args, detected_config = self. _get_http_check_args_and_config(
            new_url, same_match_pattern, same_name)
        expected_value = {'init_config': None,
                          'instances':
                          [{'built_by': 'HttpCheck',
                            'collect_response_time': True,
                            'url': new_url,
                            'match_pattern': same_match_pattern,
                            'name': same_name,
                            'timeout': '10',
                            'use_keystone': False,
                            'dimensions': {'service': 'logging'}}]
                          }
        self._check_changes(args, detected_config, expected_value)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_http_check_only_match_pattern(self, mock_read_config,
                                           mock_save_config):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # Change only match_pattern
        same_url = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['url']
        new_match_pattern = '.*TEST.*'
        same_name = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['name']
        args, detected_config = self. _get_http_check_args_and_config(
            same_url, new_match_pattern, same_name)
        expected_value = {'init_config': None,
                          'instances':
                          [{'built_by': 'HttpCheck',
                            'collect_response_time': True,
                            'url': same_url,
                            'match_pattern': new_match_pattern,
                            'name': same_name,
                            'timeout': '10',
                            'use_keystone': False,
                            'dimensions': {'service': 'logging'}}]
                          }
        self._check_changes(args, detected_config, expected_value)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_http_check_new_url(self, mock_read_config, mock_save_config):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # Pass in a new url
        new_url = 'http://192.168.10.6:8070'
        new_match_pattern = '.*TEST.*'
        new_name = new_url
        args, detected_config = self. _get_http_check_args_and_config(
            new_url, new_match_pattern, new_name)
        expected_value = {'init_config': None,
                          'instances':
                          [{'built_by': 'HttpCheck',
                            'collect_response_time': True,
                            'url': new_url,
                            'match_pattern': new_match_pattern,
                            'name': new_name,
                            'timeout': '10',
                            'use_keystone': False,
                            'dimensions': {'service': 'logging'}},
                           DEFAULT_HTTP_CHECK_CONFIG['instances'][0]
                           ]
                          }
        self._check_changes(args, detected_config, expected_value)

    def _check_no_change(self, args, detected_config):
        changes = monasca_setup.main.modify_config(args, detected_config)
        self.assertEqual(changes, False)
        self.assertEqual(self._config_data, {})

    def _check_changes(self, args, detected_config, expected_value):
        changes = monasca_setup.main.modify_config(args, detected_config)
        self.assertEqual(changes, True)
        self.assertEqual(expected_value, self._config_data)

    def _get_mon_api_check_args_and_config(self, built_by, name):
        args = INPUT_ARGS(False, 'mon-agent', '/etc/monasca/agent', None,
                          ['MonAPI'], False)
        detected_config = {
            'process':
                {'instances': [{'built_by': built_by,
                                'detailed': True,
                                'dimensions':  {
                                    'component': name},
                                'exact_match': False,
                                'name': name,
                                'search_string': [name]
                                }],
                 'init_config': None
                 }
        }
        return args, detected_config

    def _get_http_check_args_and_config(self, url, match_pattern, name):
        args = INPUT_ARGS(False, 'mon-agent', '/etc/monasca/agent',
                          'url={0} match_pattern={1} name={2} timeout=10 '
                          'use_keystone=False'.format(
                              url, match_pattern, name),
                          ['HttpCheck'], False)
        detected_config = {
            'http_check':
                {'instances': [{'name': name,
                                'url': url,
                                'built_by': 'HttpCheck',
                                'use_keystone': False,
                                'match_pattern': match_pattern,
                                'collect_response_time': True,
                                'timeout': '10',
                                'dimensions': {'service': 'logging'}
                                }],
                 'init_config': None
                 }
        }
        return args, detected_config
