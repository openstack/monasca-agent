import logging
import os

from datetime import datetime

import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)


class Crash(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Crash, self).__init__(name, init_config, agent_config)
        self.crash_dir = self.init_config.get('crash_dir', '/var/crash')
        log.debug('crash dir: %s', self.crash_dir)

    def check(self, instance):
        """Capture crash dump statistics
        """
        dimensions = self._set_dimensions(None, instance)
        dump_count = 0
        value_meta = {'latest': ''}

        # Parse the crash directory
        if os.path.isdir(self.crash_dir):
            for entry in sorted(os.listdir(self.crash_dir), reverse=True):
                if os.path.isdir(os.path.join(self.crash_dir, entry)):
                    try:
                        dt = datetime.strptime(entry, '%Y%m%d%H%M')
                    except ValueError:
                        continue

                    # Found a valid crash dump directory
                    log.debug('found crash dump dir: %s',
                              os.path.join(self.crash_dir, entry))
                    dump_count += 1

                    # Return the date-/timestamp of the most recent crash
                    if dump_count == 1:
                        value_meta = {'latest': unicode(dt)}

        log.debug('dump_count: %s', dump_count)
        self.gauge('crash.dump_count', dump_count, dimensions=dimensions,
                   value_meta=value_meta)
