# (C) Copyright 2016 Hewlett Packard Enterprise Development LP

import mock
import unittest

import monasca_agent.common.util as util
from monasca_agent.collector.checks_d.host_alive import HostAlive

HOST_ALIVE_STATUS = 'host_alive_status'
SUCCESS = 0
FAILURE = 1


class TestHostAlive(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        init_config = {}
        agent_config = {}
        self._host_alive = HostAlive('TestHostAlive', init_config, agent_config)
        self._gauge = mock.Mock()
        self._host_alive.gauge = self._gauge
        self._host_name = 'monasca'
        self._instance = {'host_name': self._host_name,
                    'alive_test': 'ping'}
        self._base_dimensions = {
            'test_type': 'ping',
            'hostname': self._host_name,
            'observer_host': util.get_hostname()
        }

    def _run_check(self, host_name, instance, ping_result):
        mock_ping = mock.Mock(return_value=ping_result)
        self._host_alive._test_ping = mock_ping
        self._host_alive._check(instance)
        mock_ping.assert_called_with(host_name, None)

    def test_host_is_alive(self):
        ping_result = (True, None)
        self._run_check(self._host_name, self._instance, ping_result)
        self._gauge.assert_called_with(HOST_ALIVE_STATUS,
                       SUCCESS,
                       dimensions=self._base_dimensions)

    def test_host_is_dead(self):
        error_message = '''I'm not dead yet'''
        self._run_check(self._host_name, self._instance,
                       (False, error_message))

        self._gauge.assert_called_with('host_alive_status',
                       FAILURE,
                       dimensions=self._base_dimensions,
                       value_meta={'error': error_message})

    def test_host_is_alive_with_target_hostname(self):
        check_name = 'otherMonasca'
        self._instance['target_hostname'] = check_name
        self._run_check(check_name, self._instance, (True, None))
        self._base_dimensions['target_hostname'] = check_name
        self._gauge.assert_called_with(HOST_ALIVE_STATUS,
                       SUCCESS,
                       dimensions=self._base_dimensions)

    def test_host_is_alive_with_dup_target_hostname(self):
        host_name = 'monasca'
        self._instance['target_hostname'] = host_name
        self._run_check(host_name, self._instance, (True, None))
        self._gauge.assert_called_with(HOST_ALIVE_STATUS,
                       SUCCESS,
                       dimensions=self._base_dimensions)