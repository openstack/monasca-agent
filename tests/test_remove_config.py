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

DEFAULT_HTTP_CHECK_2_CONFIG = {
    'init_config': None,
    'instances': [{'built_by': 'HttpCheck',
                   'match_pattern': '.*VERSION.*',
                   'url': 'http://127.0.0.1:9200',
                   'name': 'logging',
                   'timeout': '10',
                   'collect_response_time': True,
                   'use_keystone': False,
                   'dimensions': {'service': 'logging'}},
                  {'built_by': 'HttpCheck',
                   'match_pattern': '.*VERSION.*',
                   'url': 'http://127.0.0.2:9200',
                   'name': 'logging',
                   'timeout': '10',
                   'collect_response_time': True,
                   'use_keystone': False,
                   'dimensions': {'service': 'logging'}}
                  ]
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

DEFAULT_PROCESS_CHECK_CONFIG_2 = {
    'init_config': None,
    'instances': [{'built_by': 'MonNotification',
                   'detailed': True,
                   'dimensions': {'component': 'monasca-notification'},
                   'exact_match': False,
                   'name': 'monasca-notification',
                   'search_string': ['monasca-notification']
                   },
                  {'built_by': 'MonAPI',
                   'detailed': True,
                   'dimensions': {'component': 'monasca-api'},
                   'exact_match': False,
                   'name': 'monasca-api',
                   'search_string': ['monasca-api']
                   }
                  ]
}

DEFAULT_PING_CHECK_CONFIG_2COMP = {
    'init_config': None,
    'instances': [{'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'dimensions': {'service': 'compute'},
                   'host_name': 'test-test-1-host',
                   'name': 'test-test-1-host ping',
                   'target_hostname': 'test-test-1-mgmt'
                   },
                  {'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'dimensions': {'service': 'compute'},
                   'host_name': 'test-test-2-host',
                   'name': 'test-test-2-host ping',
                   'target_hostname': 'test-test-2-mgmt'
                   },
                  {'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'host_name': 'test-control-1-host',
                   'name': 'test-control-1-host ping',
                   'target_hostname': 'test-control-1-mgmt'
                   }
                  ]
}

DEFAULT_PING_CHECK_CONFIG_ALLCOMP = {
    'init_config': None,
    'instances': [{'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'dimensions': {'service': 'compute'},
                   'host_name': 'test-test-1-host',
                   'name': 'test-test-1-host ping',
                   'target_hostname': 'test-test-1-mgmt'
                   },
                  {'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'dimensions': {'service': 'compute'},
                   'host_name': 'test-test-2-host',
                   'name': 'test-test-2-host ping',
                   'target_hostname': 'test-test-2-mgmt'
                   },
                  {'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'dimensions': {'service': 'compute'},
                   'host_name': 'test-test-3-host',
                   'name': 'test-test-3-host ping',
                   'target_hostname': 'test-test-3-mgmt'
                   },
                  {'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'host_name': 'test-control-1-host',
                   'name': 'test-control-1-host ping',
                   'target_hostname': 'test-control-1-mgmt'
                   }
                  ]
}

DEFAULT_PING_CHECK_CONFIG_CONTONLY = {
    'init_config': None,
    'instances': [{'built_by': 'HostAlive',
                   'alive_test': 'ping',
                   'host_name': 'test-control-1-host',
                   'name': 'test-control-1-host ping',
                   'target_hostname': 'test-control-1-mgmt'
                   }
                  ]
}


INPUT_ARGS = collections.namedtuple(
    "InputArgs", ["overwrite", "user", "config_dir", "detection_args",
                  "detection_plugins", "dry_run", "detection_args_json",
                  "template_dir"])
INPUT_ARGS_WITH_DIMENSIONS = collections.namedtuple(
    "InputArgs", ["overwrite", "user", "config_dir", "detection_args",
                  "detection_plugins", "dry_run", "detection_args_json",
                  "template_dir", "dimensions"])


class TestRemoveConfig(unittest.TestCase):
    """ Unit tests for removing_config function in monasca_setup/main.py
        More details are documented in:
        monasca-agent/docs/DeveloperDocs/agent_internals.md
    """
    def setUp(self):
        self._config_data = {}

    def save_config(self, config_dir, plugin_name, user, data):
        self._config_data = data

    # to replace save_plugin_config(args.config_dir, plugin_name, args.user, config)
    #   in delete_config(args, config, file_path, plugin_name)
    def delete_config(self, args, config, file_path, plugin_name):
        self._config_data = config

    @mock.patch('monasca_setup.main.plugin_detection')
    @mock.patch('monasca_setup.main.agent_config.delete_from_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_no_remove_process_check_config(self, mock_read_config,
                                            mock_delete_config,
                                            mock_plugin_detection):
        mock_read_config.return_value = DEFAULT_PROCESS_CHECK_CONFIG
        mock_delete_config.side_effect = self.save_config

        # Add a new process check instance
        same_built_by = DEFAULT_PROCESS_CHECK_CONFIG['instances'][0][
            'built_by']
        same_name = DEFAULT_PROCESS_CHECK_CONFIG['instances'][0][
            'name']
        args, detected_config = self._get_mon_api_check_args_and_config(
            same_built_by, same_name)
        mock_plugin_detection.return_value = detected_config
        self._check_no_change_remove(args, ["HttpCheck"])

    @mock.patch('monasca_setup.main._get_config_yaml_files')
    @mock.patch('monasca_setup.main.plugin_detection')
    @mock.patch('monasca_setup.main.agent_config.delete_from_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_remove_process_check_config(self, mock_read_config,
                                         mock_delete_config,
                                         mock_plugin_detection,
                                         mock_glob):
        mock_read_config.return_value = DEFAULT_PROCESS_CHECK_CONFIG_2
        mock_delete_config.side_effect = self.delete_config
        mock_glob.return_value = ['conf.d--test/process_check-TESTONLY.yaml']

        # Trying to remove mon-api part
        built_by = 'MonAPI'
        name = 'monasca-api'
        args, detected_config = self._get_mon_api_check_args_and_config(
            built_by, name)

        mock_plugin_detection.return_value = detected_config
        print("det_conf {0}".format(detected_config))
        self._check_changes_remove(args, [built_by], DEFAULT_PROCESS_CHECK_CONFIG)

    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_no_modify_http_check_config(self, mock_read_config,
                                         mock_save_config):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_CONFIG
        mock_save_config.side_effect = self.save_config

        # keep url and match_pattern the same
        same_url = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['url']
        same_match_pattern = DEFAULT_HTTP_CHECK_CONFIG['instances'][0][
            'match_pattern']
        same_name = DEFAULT_HTTP_CHECK_CONFIG['instances'][0]['name']

        args, detected_config = self. _get_http_check_args_and_config(
            same_url, same_match_pattern, same_name)
        self._check_no_change_remove(args, detected_config)

    @mock.patch('monasca_setup.main._get_config_yaml_files')
    @mock.patch('monasca_setup.main.plugin_detection')
    @mock.patch('monasca_setup.main.agent_config.save_plugin_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_remove_http_check_config(self, mock_read_config,
                                      mock_save_config,
                                      mock_plugin_detection,
                                      mock_glob):
        mock_read_config.return_value = DEFAULT_HTTP_CHECK_2_CONFIG
        mock_save_config.side_effect = self.save_config
        mock_glob.return_value = ['conf.d--test/http_check.yaml']

        # don't change protocol or match_pattern
        url = 'http://127.0.0.2:9200'
        match_pattern = '.*VERSION.*'

        args, detected_config = self. _get_http_check_args_and_config(
            url, match_pattern, 'logging')
        mock_plugin_detection.return_value = detected_config
        expected_value = DEFAULT_HTTP_CHECK_CONFIG
        self._check_changes_remove(args, ['http_check'], expected_value)

    # TODO: test_remove_matching for http or process,
    # TODO: test if no match and test if multiple entries match

    # TODO: start from DEFAULT_PING_CHECK_CONFIG_ALLCOMP and remove the computes by dimension server:compute
    # TODO: do a ping check using JSON format detection arguments, (after that is implemented)

    # start from DEFAULT_PING_CHECK_CONFIG_ALLCOMP and remove just test3 compute
    @mock.patch('monasca_setup.main._get_config_yaml_files')
    @mock.patch('monasca_setup.main.plugin_detection')
    @mock.patch('monasca_setup.main.agent_config.delete_from_config')
    @mock.patch('monasca_setup.main.agent_config.read_plugin_config_from_disk')
    def test_remove_matching_ping_check_config(self, mock_read_config,
                                               mock_delete_config,
                                               mock_plugin_detection,
                                               mock_glob):
        mock_read_config.return_value = DEFAULT_PING_CHECK_CONFIG_ALLCOMP
        mock_delete_config.side_effect = self.delete_config
        mock_glob.return_value = ['conf.d--test/ping_check.yaml']

        same_built_by = DEFAULT_PING_CHECK_CONFIG_ALLCOMP['instances'][0][
            'built_by']
        # note: NOT testing the json args path
        test_args = INPUT_ARGS(False, 'mon-agent', '/etc/monasca/agent',
                               'hostname=deletehost-localcloud-mgmt '
                               'type=ping '
                               'dimensions=service:compute',
                               [same_built_by], False,
                               {},
                               '/etc/monasca/agent/conf.d--test')

        mock_plugin_detection.return_value = {'ping': {
            'instances': [{'built_by': same_built_by,
                           'alive_test': 'ping',
                           'dimensions': {'service': 'compute'},
                           'host_name': 'test-test-3-host',
                           'name': 'test-test-3-host ping',
                           'target_hostname': 'test-test-3-mgmt'}],
            'init_config': None}
        }

        changes = monasca_setup.main.remove_config_for_matching_args(test_args, [same_built_by])
        self.assertEqual(changes, True, "Should have removed config item but did not!")
        self.assertEqual(DEFAULT_PING_CHECK_CONFIG_2COMP, self._config_data,
                         "Expected value {0} did not match result of {1}"
                         .format(DEFAULT_PING_CHECK_CONFIG_2COMP, self._config_data))

    ####
    # helper functions
    def _check_no_change_remove(self, args, plugins):
        changes = monasca_setup.main.remove_config(args, plugins)
        self.assertEqual(changes, False)
        self.assertEqual(self._config_data, {})

    def _check_changes_remove(self, args, plugins, expected_value):
        changes = monasca_setup.main.remove_config(args, plugins)
        self.assertEqual(changes, True)
        self.assertEqual(expected_value, self._config_data,
                         "Expected value {0} did not match resulting config data {1}"
                         .format(expected_value, self._config_data))

    def _check_changes_remove_matching(self, args, plugins, expected_value):
        changes = monasca_setup.main.remove_config_for_matching_args(args, plugins)
        self.assertEqual(changes, True)
        self.assertEqual(expected_value, self._config_data,
                         "Expected value {0} did not match resulting config data {1}"
                         .format(expected_value, self._config_data))

    # Reminder of args: ["overwrite", "user", "config_dir", "detection_args",
    #                   "detection_plugins", "dry_run",
    #                   "detection_args_json", "template_dir"]
    def _get_mon_api_check_args_and_config(self, built_by, name):
        args = INPUT_ARGS(False, 'mon-agent', '/etc/monasca/agent', None,
                          ['MonAPI'], False,
                          '{}', '/etc/monasca/agent/conf.d--test')
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
                          ['HttpCheck'], False,
                          '{}', '/etc/monasca/agent/conf.d--test')
        detected_config = {
            'http_check':
                {'instances': [{'built_by': 'HttpCheck',
                                'match_pattern': match_pattern,
                                'url': url,
                                'name': name,
                                'timeout': '10',
                                'collect_response_time': True,
                                'use_keystone': False,
                                'dimensions': {'service': 'logging'}
                                }],
                 'init_config': None
                 }
        }
        return args, detected_config
