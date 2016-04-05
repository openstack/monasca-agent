# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
"""Gather metrics on specific processes.

"""
from collections import defaultdict
from collections import namedtuple
import monasca_agent.collector.checks as checks

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
        self._cached_processes = defaultdict(dict)
        self._current_process_list = None

    @staticmethod
    def is_psutil_version_later_than(v):
        try:
            import psutil
            vers = psutil.version_info
            return vers >= v
        except Exception:
            return False

    def find_pids(self, search_string, psutil, username, exact_match=True):
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

    def get_process_metrics(self, pids, psutil, name):
        processes_to_remove = set(self._cached_processes[name].keys()) - pids
        for pid in processes_to_remove:
            del self._cached_processes[name][pid]
        got_denied = False
        io_permission = True

        # initialize aggregation values
        total_thr = 0
        total_cpu = None
        total_rss = 0
        total_open_file_descriptors = 0
        total_read_count = 0
        total_write_count = 0
        total_read_kbytes = 0
        total_write_kbytes = 0

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
                total_rss += float(mem.rss / 1048576)
                total_thr += p.num_threads()

                try:
                    total_open_file_descriptors += float(p.num_fds())
                except psutil.AccessDenied:
                    got_denied = True

                if not added_process:
                    cpu = p.cpu_percent(interval=None)
                    if not total_cpu:
                        total_cpu = cpu
                    else:
                        total_cpu += cpu
                else:
                    p.cpu_percent(interval=None)

                # user might not have permission to call io_counters()
                if io_permission:
                    try:
                        io_counters = p.io_counters()
                        total_read_count += io_counters.read_count
                        total_write_count += io_counters.write_count
                        total_read_kbytes += float(io_counters.read_bytes / 1024)
                        total_write_kbytes += float(io_counters.write_bytes / 1024)
                    except psutil.AccessDenied:
                        self.log.debug('monasca-agent user does not have ' +
                                       'access to I/O counters for process' +
                                       ' %d: %s'
                                       % (pid, p.name))
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
                        (total_thr, total_cpu, total_rss, total_open_file_descriptors, total_read_count,
                         total_write_count, total_read_kbytes, total_write_kbytes)))

    def prepare_run(self):
        """Collect the list of processes once before each run"""
        try:
            import psutil
        except ImportError:
            raise Exception('You need the "psutil" package to run this check')

        self._current_process_list = []

        for process in psutil.process_iter():
            try:
                p = ProcessStruct(name=process.name(),
                                  pid=process.pid,
                                  username=process.username(),
                                  cmdline=' '.join(process.cmdline()))
                self._current_process_list.append(p)
            except psutil.NoSuchProcess:
                # No way to log useful information here so just move on
                pass
            except psutil.AccessDenied as e:
                self.log.info('Access denied to process {0}: {1}'.format(
                    process.name(), e))

    def check(self, instance):
        try:
            import psutil
        except ImportError:
            raise Exception('You need the "psutil" package to run this check')

        name = instance.get('name', None)
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', None)
        username = instance.get('username', None)

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if (search_string is None and username is None) or (search_string is not None and username is not None):
            raise KeyError('"You must provide either "search_string" or "user"')

        if username is None:
            dimensions = self._set_dimensions({'process_name': name}, instance)
        else:
            dimensions = self._set_dimensions({'process_user': username, 'process_name': name}, instance)

        pids = self.find_pids(search_string, psutil, username, exact_match=exact_match)

        self.log.debug('ProcessCheck: process %s analysed' % name)

        self.gauge('process.pid_count', len(pids), dimensions=dimensions)

        if instance.get('detailed', False):
            metrics = self.get_process_metrics(pids, psutil, name)
            for metric_name, metric_value in metrics.iteritems():
                if metric_value is not None and metric_value > 0:
                    self.gauge(metric_name, metric_value, dimensions=dimensions)
