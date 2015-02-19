import psutil
import logging

log = logging.getLogger(__name__)

import monasca_agent.collector.checks as checks


class Memory(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Memory, self).__init__(name, init_config, agent_config)

    def check(self, instance):
        """Capture memory stats

        """
        dimensions = self._set_dimensions(None, instance)

        mem_info = psutil.virtual_memory()
        swap_info = psutil.swap_memory()

        self.gauge('mem.total_mb',
                   int(mem_info.total/1048576),
                   dimensions=dimensions)
        self.gauge('mem.free_mb',
                   int(mem_info.free/1048576),
                   dimensions=dimensions)
        self.gauge('mem.usable_mb',
                   int(mem_info.available/1048576),
                   dimensions=dimensions)
        self.gauge('mem.usable_perc',
                   float(100 - mem_info.percent),
                   dimensions=dimensions)
        self.gauge('mem.swap_total_mb',
                   int(swap_info.total/1048576),
                   dimensions=dimensions)
        self.gauge('mem.swap_used_mb',
                   int(swap_info.used/1048576),
                   dimensions=dimensions)
        self.gauge('mem.swap_free_mb',
                   int(swap_info.free/1048576),
                   dimensions=dimensions)
        self.gauge('mem.swap_free_perc',
                   float(100 - swap_info.percent),
                   dimensions=dimensions)

        count = 8
        if 'buffers' in mem_info:
            self.gauge('mem.used_buffers',
                       int(mem_info.buffers/1048576),
                       dimensions=dimensions)
            count +=1

        if 'cached' in mem_info:
            self.gauge('mem.used_cache',
                       int(mem_info.cached/1048576),
                       dimensions=dimensions)
            count +=1

        if 'shared' in mem_info:
            self.gauge('mem.used_shared',
                       int(mem_info.shared/1048576),
                       dimensions=dimensions)
            count +=1

        log.debug('Collected {0} memory metrics'.format(count))
