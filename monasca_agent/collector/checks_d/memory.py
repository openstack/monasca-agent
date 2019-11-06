# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

import logging
import psutil

log = logging.getLogger(__name__)

import monasca_agent.collector.checks as checks


class Memory(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Memory, self).__init__(name, init_config, agent_config)
        process_fs_path_config = init_config.get('process_fs_path', None)
        if process_fs_path_config:
            psutil.PROCFS_PATH = process_fs_path_config
            self.log.debug('The path of the process filesystem set to %s', process_fs_path_config)
        else:
            self.log.debug('The process_fs_path not set. Use default path: /proc')

    def check(self, instance):
        """Capture memory stats

        """
        dimensions = self._set_dimensions(None, instance)

        mem_info = psutil.virtual_memory()
        swap_info = psutil.swap_memory()

        self.gauge('mem.total_mb',
                   int(mem_info.total / 1048576),
                   dimensions=dimensions)
        self.gauge('mem.free_mb',
                   int(mem_info.free / 1048576),
                   dimensions=dimensions)
        self.gauge('mem.usable_mb',
                   int(mem_info.available / 1048576),
                   dimensions=dimensions)
        self.gauge('mem.usable_perc',
                   float(100 - mem_info.percent),
                   dimensions=dimensions)
        self.gauge('mem.swap_total_mb',
                   int(swap_info.total / 1048576),
                   dimensions=dimensions)
        self.gauge('mem.swap_used_mb',
                   int(swap_info.used / 1048576),
                   dimensions=dimensions)
        self.gauge('mem.swap_free_mb',
                   int(swap_info.free / 1048576),
                   dimensions=dimensions)
        self.gauge('mem.swap_free_perc',
                   float(100 - swap_info.percent),
                   dimensions=dimensions)

        count = 9
        if hasattr(mem_info, 'buffers') and mem_info.buffers:
            self.gauge('mem.used_buffers',
                       int(mem_info.buffers / 1048576),
                       dimensions=dimensions)
            count += 1

        if hasattr(mem_info, 'cached') and mem_info.cached:
            self.gauge('mem.used_cache',
                       int(mem_info.cached / 1048576),
                       dimensions=dimensions)
            count += 1

        if (hasattr(mem_info, 'buffers') and mem_info.buffers and
                hasattr(mem_info, 'cached') and mem_info.cached):

            mem_used_real = mem_info.used
            if psutil.version_info < (4, 4, 0):
                #
                # pusutil versions prior to 4.4.0 didn't subtract buffers and
                # cache, but starting in 4.4.0 psutil does.
                #
                mem_used_real = mem_used_real - mem_info.buffers - mem_info.cached
            self.gauge('mem.used_real_mb', int(mem_used_real / 1048576),
                       dimensions=dimensions)
            count += 1

        if hasattr(mem_info, 'shared') and mem_info.shared:
            self.gauge('mem.used_shared',
                       int(mem_info.shared / 1048576),
                       dimensions=dimensions)
            count += 1

        # The slab metric was added in psutil 5.4.4
        if hasattr(mem_info, 'slab') and mem_info.slab:
            self.gauge('mem.used_slab_mb',
                       int(mem_info.slab / 1048576),
                       dimensions=dimensions)
            count += 1

        log.debug('Collected {0} memory metrics'.format(count))
