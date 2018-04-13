# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
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

from httplib2 import Http
from httplib2 import HttpLib2Error
import json
import socket

from monasca_agent.collector.checks import AgentCheck


class Riak(AgentCheck):

    keys = ["vnode_gets",
            "vnode_puts",
            "vnode_index_reads",
            "vnode_index_writes",
            "vnode_index_deletes",
            "node_gets",
            "node_puts",
            "pbc_active",
            "pbc_connects",
            "memory_total",
            "memory_processes",
            "memory_processes_used",
            "memory_atom",
            "memory_atom_used",
            "memory_binary",
            "memory_code",
            "memory_ets",
            "read_repairs",
            "node_put_fsm_rejected_60s",
            "node_put_fsm_active_60s",
            "node_put_fsm_in_rate",
            "node_put_fsm_out_rate",
            "node_get_fsm_rejected_60s",
            "node_get_fsm_active_60s",
            "node_get_fsm_in_rate",
            "node_get_fsm_out_rate"]

    stat_keys = ["node_get_fsm_siblings",
                 "node_get_fsm_objsize",
                 "node_get_fsm_time",
                 "node_put_fsm_time"]

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config, agent_config, instances)
        for k in ["mean", "median", "95", "99", "100"]:
            [self.keys.append(m + "_" + k) for m in self.stat_keys]

        self.prev_coord_redirs_total = -1

    def check(self, instance):
        url = instance['url']
        default_timeout = self.init_config.get('default_timeout', 5)
        timeout = float(instance.get('timeout', default_timeout))

        dimensions = self._set_dimensions(None, instance)

        try:
            h = Http(timeout=timeout)
            resp, content = h.request(url, "GET")

        except socket.timeout:
            return

        except socket.error:
            return

        except HttpLib2Error:
            return

        stats = json.loads(content)

        [self.gauge("riak." + k, stats[k], dimensions=dimensions) for k in self.keys if k in stats]

        coord_redirs_total = stats["coord_redirs_total"]
        if self.prev_coord_redirs_total > -1:
            count = coord_redirs_total - self.prev_coord_redirs_total
            self.gauge('riak.coord_redirs', count, dimensions=dimensions)

        self.prev_coord_redirs_total = coord_redirs_total
