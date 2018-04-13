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

import nose.tools as nt

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.common.check_status import STATUS_OK, STATUS_ERROR, InstanceStatus, CheckStatus, CollectorStatus


class DummyAgentCheck(AgentCheck):

    @staticmethod
    def check(instance):
        if not instance['pass']:
            raise Exception("failure")


def test_check_status_fail():
    instances = [
        {'pass': True},
        {'pass': False},
        {'pass': True}
    ]

    check = DummyAgentCheck('dummy_agent_check', {}, {}, instances)
    instance_statuses = check.run()
    assert len(instance_statuses) == 3
    assert instance_statuses[0].status == STATUS_OK
    assert instance_statuses[1].status == STATUS_ERROR
    assert instance_statuses[2].status == STATUS_OK


def test_check_status_pass():
    instances = [
        {'pass': True},
        {'pass': True},
    ]

    check = DummyAgentCheck('dummy_agent_check', {}, {}, instances)
    instances_status = check.run()
    assert len(instances_status) == 2
    for i in instances_status:
        assert i.status == STATUS_OK


def test_persistence():
    i1 = InstanceStatus(1, STATUS_OK)
    chk1 = CheckStatus("dummy", [i1], 1, 2)
    c1 = CollectorStatus([chk1])
    c1.persist()

    c2 = CollectorStatus.load_latest_status()
    nt.assert_equal(1, len(c2.check_statuses))
    chk2 = c2.check_statuses[0]
    assert chk2.name == chk1.name
    assert chk2.status == chk2.status
    assert chk2.metric_count == 1
    assert chk2.event_count == 2


def test_persistence_fail():

    # Assert remove doesn't crap out if a file doesn't exist.
    CollectorStatus.remove_latest_status()
    CollectorStatus.remove_latest_status()

    status = CollectorStatus.load_latest_status()
    assert not status
