# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP

import logging
import os
import re

from datetime import datetime

import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)


class Crash(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(Crash, self).__init__(name, init_config, agent_config)
        self.crash_dir = self.init_config.get('crash_dir', '/var/crash')
        log.debug('crash dir: %s', self.crash_dir)

    def _create_datetime_for_rhel71(self, dir_name):
        date_parts = dir_name.split('-')
        parts_len = len(date_parts)
        if parts_len > 2:
            try:
                # Use last two parts, because the front part(IP address part) is not checked.
                date_part = date_parts[parts_len - 2] + '-' + date_parts[parts_len - 1]
                return datetime.strptime(date_part, '%Y.%m.%d-%H:%M:%S')
            except ValueError:
                pass

    def _check_dir_name(self, dir_name):
        dt = None
        if dir_name is None:
            return None
        # Check for CentOS 7.1 and RHEL 7.1. <IP-address>-YYYY.MM.dd-HH:mm:ss (e.g. 127.0.0.1-2015.10.02-16:07:51)
        elif re.match(r".*-\d{4}[.]\d{2}[.]\d{2}-\d{2}:\d{2}:\d{2}$", dir_name):
            dt = self._create_datetime_for_rhel71(dir_name)
        else:
            try:
                dt = datetime.strptime(dir_name, '%Y%m%d%H%M')
            except ValueError:
                pass
        return dt

    def check(self, instance):
        """Capture crash dump statistics
        """
        dimensions = self._set_dimensions(None, instance)
        dump_count = 0
        value_meta = None

        # Parse the crash directory
        if os.path.isdir(self.crash_dir):
            for entry in sorted(os.listdir(self.crash_dir), reverse=True):
                if os.path.isdir(os.path.join(self.crash_dir, entry)):
                    dt = self._check_dir_name(entry)
                    if dt is None:
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
