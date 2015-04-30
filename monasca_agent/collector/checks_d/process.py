"""Gather metrics on specific processes.

"""
import monasca_agent.collector.checks as checks
import monasca_agent.common.util as util


class ProcessCheck(checks.AgentCheck):

    PROCESS_GAUGE = ('process.thread_count',
                     'process.cpu_perc',
                     'process.mem.rss_mbytes',
                     'process.mem.vsz_mbytes',
                     'process.mem.real_mbytes',
                     'process.open_file_descriptors',
                     'process.open_file_descriptors_perc',
                     'process.io.read_count',
                     'process.io.write_count',
                     'process.io.read_kbytes',
                     'process.io.write_kbytes',
                     'process.voluntary_ctx_switches',
                     'process.involuntary_ctx_switches')

    @staticmethod
    def is_psutil_version_later_than(v):
        try:
            import psutil
            vers = psutil.version_info
            return vers >= v
        except Exception:
            return False

    def find_pids(self, search_string, psutil, exact_match=True):
        """Create a set of pids of selected processes.

        Search for search_string
        """
        found_process_list = []
        for proc in psutil.process_iter():
            found = False
            for string in search_string:
                if exact_match:
                    try:
                        if proc.name() == string:
                            found = True
                    except psutil.NoSuchProcess:
                        self.log.warning('Process %s disappeared while scanning'
                                         % string)
                        pass
                    except psutil.AccessDenied as e:
                        self.log.error('Access denied to %s process' % string)
                        self.log.error('Error: %s' % e)
                        raise
                else:
                    try:
                        cmdline = proc.cmdline()

                        if string in ' '.join(cmdline):
                            found = True
                    except psutil.NoSuchProcess:
                        self.warning('Process %s disappeared while scanning'
                                     % string)
                        pass
                    except psutil.AccessDenied as e:
                        self.log.error('Access denied to %s process'
                                       % string)
                        self.log.error('Error: %s' % e)
                        raise

                if found or string == 'All':
                    found_process_list.append(proc.pid)

        return set(found_process_list)

    def get_process_metrics(self, pids, psutil, cpu_check_interval):

        # initialize process metrics
        # process metrics available for all versions of psutil
        rss = 0
        vms = 0
        cpu = 0
        thr = 0

        # process metrics available for psutil versions 0.6.0 and later
        extended_metrics_0_6_0 = (self.is_psutil_version_later_than((0, 6, 0))
                                  and not util.Platform.is_win32())
        # On Windows get_ext_memory_info returns different metrics
        if extended_metrics_0_6_0:
            real = 0
            voluntary_ctx_switches = 0
            involuntary_ctx_switches = 0
        else:
            real = None
            voluntary_ctx_switches = None
            involuntary_ctx_switches = None

        # process metrics available for psutil versions 0.5.0 and later on UNIX
        extended_metrics_0_5_0_unix = (self.is_psutil_version_later_than((0, 5, 0))
                                       and util.Platform.is_unix())
        if extended_metrics_0_5_0_unix:
            open_file_descriptors = 0
            open_file_descriptors_perc = 0
        else:
            open_file_descriptors = None
            open_file_descriptors_perc = None

        # process I/O counters (agent might not have permission to access)
        read_count = 0
        write_count = 0
        read_kbytes = 0
        write_kbytes = 0

        got_denied = False

        for pid in set(pids):
            try:
                p = psutil.Process(pid)
                if extended_metrics_0_6_0:
                    mem = p.get_ext_memory_info()
                    real += float((mem.rss - mem.shared) / 1048576)
                    try:
                        ctx_switches = p.get_num_ctx_switches()
                        voluntary_ctx_switches += ctx_switches.voluntary
                        involuntary_ctx_switches += ctx_switches.involuntary
                    except NotImplementedError:
                        # Handle old Kernels which don't provide this info.
                        voluntary_ctx_switches = None
                        involuntary_ctx_switches = None
                else:
                    mem = p.get_memory_info()

                if extended_metrics_0_5_0_unix:
                    try:
                        open_file_descriptors = float(p.get_num_fds())
                        max_open_file_descriptors = float(p.rlimit(psutil.RLIMIT_NOFILE)[1])
                        if max_open_file_descriptors > 0.0:
                            open_file_descriptors_perc = open_file_descriptors / max_open_file_descriptors * 100
                        else:
                            open_file_descriptors_perc = 0
                    except psutil.AccessDenied:
                        got_denied = True

                rss += float(mem.rss/1048576)
                vms += float(mem.vms/1048576)
                thr += p.get_num_threads()
                cpu += p.get_cpu_percent(cpu_check_interval)

                # user might not have permission to call get_io_counters()
                if read_count is not None:
                    try:
                        io_counters = p.get_io_counters()
                        read_count += io_counters.read_count
                        write_count += io_counters.write_count
                        read_kbytes += float(io_counters.read_bytes/1024)
                        write_kbytes += float(io_counters.write_bytes/1024)
                    except psutil.AccessDenied:
                        self.log.debug('monasca-agent user does not have ' +
                                       'access to I/O counters for process' +
                                       ' %d: %s'
                                       % (pid, p.name))
                        read_count = None
                        write_count = None
                        read_kbytes = None
                        write_kbytes = None

            # Skip processes dead in the meantime
            except psutil.NoSuchProcess:
                self.warning('Process %s disappeared while scanning' % pid)
                pass

        if got_denied:
            self.warning("The Monitoring Agent was denied access " +
                         "when trying to get the number of file descriptors")

        # Memory values are in Byte
        return (thr, cpu, rss, vms, real, open_file_descriptors,
                open_file_descriptors_perc, read_count, write_count,
                read_kbytes, write_kbytes, voluntary_ctx_switches,
                involuntary_ctx_switches)

    def check(self, instance):
        try:
            import psutil
        except ImportError:
            raise Exception('You need the "psutil" package to run this check')

        name = instance.get('name', None)
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', None)
        cpu_check_interval = instance.get('cpu_check_interval', 0.1)

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if search_string is None:
            raise KeyError('The "search_string" is mandatory')

        if not isinstance(cpu_check_interval, (int, long, float)):
            self.warning("cpu_check_interval not a number; defaulting to 0.1")
            cpu_check_interval = 0.1

        pids = self.find_pids(search_string, psutil, exact_match=exact_match)
        dimensions = self._set_dimensions({'process_name': name}, instance)

        self.log.debug('ProcessCheck: process %s analysed' % name)

        self.gauge('process.pid_count', len(pids), dimensions=dimensions)

        if instance.get('detailed', False):
            metrics = dict(zip(ProcessCheck.PROCESS_GAUGE,
                               self.get_process_metrics(pids,
                                                        psutil,
                                                        cpu_check_interval)))

            for metric, value in metrics.iteritems():
                if value is not None:
                    self.gauge(metric, value, dimensions=dimensions)
