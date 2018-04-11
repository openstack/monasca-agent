# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
VCenter plugin that returns only vm status. Takes no instances,
reads from a single configured VCenter
"""

from monasca_agent.collector.checks import AgentCheck
from oslo_vmware import api
from oslo_vmware import vim_util

STATUS_MAP = {
    "connected": 0
}


class VcenterSlim(AgentCheck):
    def __init__(self, name, init_config, agent_config):
        AgentCheck.__init__(self, name, init_config, agent_config, instances=[{}])
        self.max_objects = init_config.get("vcenter_max_objects", 100000)

    def check(self, instance):
        dim_base = self._set_dimensions(None, instance)
        allowed_keys = set(self.init_config.get("allowed_keys", []))
        key_map = self.init_config.get("key_map", {})

        session = self.get_api_session()

        result = session.invoke_api(
            vim_util,
            "get_objects",
            session.vim,
            "VirtualMachine",
            self.max_objects,
            ["runtime.connectionState",
             "config.annotation",
             "config.instanceUuid"])
        for vm in result[0]:
            vm_status = 1
            # vm_name = vm.obj.value
            vm_dimensions = dim_base.copy()
            for prop in vm.propSet:
                if prop.name == "runtime.connectionState":
                    if prop.val in STATUS_MAP:
                        vm_status = STATUS_MAP[prop.val]
                    else:
                        vm_status = 1
                if prop.name == "config.annotation":
                    for line in prop.val.split("\n"):
                        key_val = line.split(":")
                        if len(key_val) == 2 and key_val[0] in allowed_keys:
                            value = key_val[1]
                            key = key_val[0]
                            if key in key_map.keys():
                                key = key_map[key_val[0]]
                            vm_dimensions[key] = value
                if prop.name == "config.instanceUuid":
                    vm_dimensions["instance_id"] = prop.val

            self.gauge("vm.status", vm_status, vm_dimensions)

        session.logout()

    def get_api_session(self):
        api_session = api.VMwareAPISession(
            self.init_config.get("vcenter_ip", ""),
            self.init_config.get("vcenter_user", ""),
            self.init_config.get("vcenter_password", ""),
            self.init_config.get("retry_count", 3),  # retry count
            self.init_config.get("poll_interval", 0.5),  # task_poll_interval
            port=self.init_config.get("vcenter_port", 443),
            scheme="https")
        return api_session
