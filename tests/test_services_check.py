# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
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

from unittest import TestCase
from eventlet.green import time

from monasca_agent.collector.checks.services_checks import ServicesCheck

from monasca_agent.collector.checks.services_checks import Status

class DummyServiceCheck(ServicesCheck):
    def __init__(self, name, init_config, agent_config, instances=None):
        super(DummyServiceCheck, self).__init__(name, init_config, agent_config, instances)

    def _check(self, instance):
        w = instance.get('service_wait', 5)
        time.sleep(w)
        return Status.UP, "UP"

    def set_timeout(self, timeout):
        self.timeout = timeout

class TestServicesCheck(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        pass

    def test_service_check_timeout(self):

        init_config = {}
        agent_config = {'timeout': 4}
        instances = []
        for wait in [1,2, 6, 8]:
            instances.append({'service_wait': wait, 'name' : 'dummy %d' % wait})
        self.dummy_service = DummyServiceCheck("dummy service", init_config, agent_config, instances=instances)
        self.dummy_service.run()
        time.sleep(10)
        self.assertEqual(self.dummy_service.statuses['dummy 1'][0], Status.UP)
        self.assertEqual(self.dummy_service.statuses['dummy 2'][0], Status.UP)

        self.assertEqual(self.dummy_service.statuses['dummy 6'][0], "FAILURE")
        self.assertEqual(self.dummy_service.statuses['dummy 8'][0], "FAILURE")

