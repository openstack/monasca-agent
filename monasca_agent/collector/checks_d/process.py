# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
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

"""Gather metrics on specific processes.

"""
from collections import defaultdict
from collections import namedtuple

import monasca_agent.collector.checks as checks
from monasca_agent.common.psutil_wrapper import psutil

ProcessStruct = namedtuple("Process", "name pid username cmdline")


class ProcessCheck(checks.AgentCheck):
    PROCESS_GAUGE = ('process.thread_count',
                     'process.cpu_perc',
                     'process.mem.rss_mbytes',
                     'process.open_file_descriptors',
                     'process.io.read_count',
                     'process.io.write_count',
                     'process.io.read_kbytes',
                     'process.io.write_kbytes')

    def __init__(self, name, init_config, agent_config, instances=None):
        super(ProcessCheck, self).__init__(name, init_config, agent_config,
                                           instances)
        process_fs_path_config = init_config.get('process_fs_path', None)
        if process_fs_path_config:
            psutil.PROCFS_PATH = process_fs_path_config
            self.log.debug('The path of the process filesystem set to %s', process_fs_path_config)
        else:
            self.log.debug('The process_fs_path not set. Use default path: /proc')

        self._cached_processes = defaultdict(dict)
        self._current_process_list = None

    def find_pids(self, search_string, username, exact_match=True):
        """Create a set of pids of selected processes.

        Search for search_string
        """
        found_process_list = []
        if username:
            found_process_list = \
                [proc.pid for proc in self._current_process_list if
                 proc.username == username]
        else:
            for string in search_string:
                if string == 'All':
                    found_process_list.extend(
                        [proc.pid for proc in self._current_process_list])
                elif exact_match:
                    found_process_list.extend(
                        [proc.pid for proc in self._current_process_list
                         if proc.name == string])
                else:
                    found_process_list.extend(
                        [proc.pid for proc in self._current_process_list
                         if string in proc.cmdline])

        return set(found_process_list)

    @staticmethod
    def _safely_increment_var(var, value):
        if var:
            return var + value
        else:
            return value

    def get_process_metrics(self, pids, name):
        processes_to_remove = set(self._cached_processes[name].keys()) - pids
        for pid in processes_to_remove:
            del self._cached_processes[name][pid]
        got_denied = False
        io_permission = True

        # initialize aggregation values
        total_thr = None
        total_cpu = None
        total_rss = None
        total_open_file_descriptors = None
        total_read_count = None
        total_write_count = None
        total_read_kbytes = None
        total_write_kbytes = None

        for pid in set(pids):
            try:
                added_process = False
                if pid not in self._cached_processes[name]:
                    p = psutil.Process(pid)
                    self._cached_processes[name][pid] = p
                    added_process = True
                else:
                    p = self._cached_processes[name][pid]

                mem = p.memory_info_ex()
                total_rss = self._safely_increment_var(total_rss, float(mem.rss / 1048576))
                total_thr = self._safely_increment_var(total_thr, p.num_threads())

                try:
                    total_open_file_descriptors = self._safely_increment_var(
                        total_open_file_descriptors, float(p.num_fds()))
                except psutil.AccessDenied:
                    got_denied = True

                if not added_process:
                    total_cpu = self._safely_increment_var(total_cpu, p.cpu_percent(interval=None))
                else:
                    p.cpu_percent(interval=None)

                # user might not have permission to call io_counters()
                if io_permission:
                    try:
                        io_counters = p.io_counters()
                        total_read_count = self._safely_increment_var(
                            total_read_count, io_counters.read_count)
                        total_write_count = self._safely_increment_var(
                            total_write_count, io_counters.write_count)
                        total_read_kbytes = self._safely_increment_var(
                            total_read_kbytes, float(io_counters.read_bytes / 1024))
                        total_write_kbytes = self._safely_increment_var(
                            total_write_kbytes, float(io_counters.write_bytes / 1024))
                    except psutil.AccessDenied:
                        self.log.debug('monasca-agent user does not have ' +
                                       'access to I/O counters for process' +
                                       ' %d: %s'
                                       % (pid, p.as_dict(['name'])['name']))
                        io_permission = False
                        total_read_count = None
                        total_write_count = None
                        total_read_kbytes = None
                        total_write_kbytes = None

            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.log.warn('Process %s disappeared while metrics were being collected' % pid)
                pass

        if got_denied:
            self.log.debug("The Monitoring Agent was denied access " +
                           "when trying to get the number of file descriptors")

        return dict(zip(ProcessCheck.PROCESS_GAUGE,
                        (total_thr,
                         total_cpu,
                         total_rss,
                         total_open_file_descriptors,
                         total_read_count,
                         total_write_count,
                         total_read_kbytes,
                         total_write_kbytes)))

    def prepare_run(self):
        """Collect the list of processes once before each run"""

        self._current_process_list = []

        for process in psutil.process_iter():
            try:
                process_dict = process.as_dict(
                    attrs=['name', 'pid', 'username', 'cmdline'])
                p = ProcessStruct(name=process_dict['name'],
                                  pid=process_dict['pid'],
                                  username=process_dict['username'],
                                  cmdline=' '.join(process_dict['cmdline']))
                self._current_process_list.append(p)
            except psutil.NoSuchProcess:
                # No way to log useful information here so just move on
                pass
            except psutil.AccessDenied as e:
                process_dict = process.as_dict(attrs=['name'])
                self.log.info('Access denied to process {0}: {1}'.format(
                    process_dict['name'], e))

    def check(self, instance):
        name = instance.get('name', None)
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', None)
        username = instance.get('username', None)

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if (search_string is None and username is None) or (
                search_string is not None and username is not None):
            raise KeyError('"You must provide either "search_string" or "user"')

        if username is None:
            dimensions = self._set_dimensions({'process_name': name}, instance)
        else:
            dimensions = self._set_dimensions(
                {'process_user': username, 'process_name': name}, instance)

        pids = self.find_pids(search_string, username, exact_match=exact_match)

        self.log.debug('ProcessCheck: process %s analysed' % name)

        self.gauge('process.pid_count', len(pids), dimensions=dimensions)

        if instance.get('detailed', False):
            metrics = self.get_process_metrics(pids, name)
            for metric_name, metric_value in metrics.items():
                if metric_value is not None:
                    self.gauge(metric_name, metric_value, dimensions=dimensions)
