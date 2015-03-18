import psutil
import logging

import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)


class Cpu(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Cpu, self).__init__(name, init_config, agent_config)

    def check(self, instance):
        """Capture cpu stats

        """
        dimensions = self._set_dimensions(None, instance)

        if instance is not None:
            send_rollup_stats =  instance.get("send_rollup_stats", False)
        else:
            send_rollup_stats =  False

        cpu_stats = psutil.cpu_times_percent(percpu=False)
        num_of_metrics = self._format_results(cpu_stats.user + cpu_stats.nice,
                                              cpu_stats.system + cpu_stats.irq + cpu_stats.softirq,
                                              cpu_stats.iowait,
                                              cpu_stats.idle,
                                              cpu_stats.steal,
                                              dimensions)
        if send_rollup_stats:
            self.gauge('cpu.total_logical_cores', psutil.cpu_count(logical=True), dimensions)
            num_of_metrics += 1
        log.debug('Collected {0} cpu metrics'.format(num_of_metrics))


    def _format_results(self, us, sy, wa, idle, st, dimensions):
        data = {'cpu.user_perc': us,
                'cpu.system_perc': sy,
                'cpu.wait_perc': wa,
                'cpu.idle_perc': idle,
                'cpu.stolen_perc': st}

        for key in data.keys():
            if data[key] is None:
                del data[key]

        [self.gauge(key, value, dimensions) for key, value in data.iteritems()]

        return len(data)
