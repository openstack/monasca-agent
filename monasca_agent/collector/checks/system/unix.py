"""Unix system checks.
"""

# stdlib
import logging
import psutil
import re
import subprocess as sp
import sys
import time

# project

import monasca_agent.collector.checks.check as check
import monasca_agent.common.metrics as metrics
import monasca_agent.common.util as util


# locale-resilient float converter
to_float = lambda s: float(s.replace(",", "."))


class Disk(check.Check):
    """Collects metrics about the machine's disks.
    """

    def check(self):
        """Get disk space/inode stats.
        """
        # psutil can be used for disk usage stats but not for inode information, so df is used.

        fs_types_to_ignore = []
        # First get the configuration.
        if self.agent_config is not None:
            use_mount = self.agent_config.get("use_mount", False)
            blacklist_re = self.agent_config.get('device_blacklist_re', None)
            for fs_type in self.agent_config.get('ignore_filesystem_types', []):
                fs_types_to_ignore.extend(['-x', fs_type])
        else:
            use_mount = False
            blacklist_re = None
        platform_name = sys.platform

        try:
            dfk_out = _get_subprocess_output(['df', '-k'] + fs_types_to_ignore)
            stats = self.parse_df_output(
                dfk_out,
                platform_name,
                use_mount=use_mount,
                blacklist_re=blacklist_re
            )

            # Collect inode metrics.
            dfi_out = _get_subprocess_output(['df', '-i'] + fs_types_to_ignore)
            inodes = self.parse_df_output(
                dfi_out,
                platform_name,
                inodes=True,
                use_mount=use_mount,
                blacklist_re=blacklist_re
            )
            # parse into a list of Measurements
            stats.update(inodes)
            timestamp = time.time()
            measurements = [metrics.Measurement(key.split('.', 1)[1],
                                                timestamp,
                                                value,
                                                self._set_dimensions({'device': key.split('.', 1)[0]}),
                                                None)
                            for key, value in stats.iteritems()]

            return measurements

        except Exception:
            self.logger.exception('Error collecting disk stats')
            return []

    def parse_df_output(
            self, df_output, platform_name, inodes=False, use_mount=False, blacklist_re=None):
        """Parse the output of the df command.

        If use_volume is true the volume is used to anchor the metric, otherwise false the mount
        point is used. Returns a tuple of (disk, inode).
        """
        usage_data = {}

        # Transform the raw output into tuples of the df data.
        devices = self._transform_df_output(df_output, blacklist_re)

        # If we want to use the mount point, replace the volume name on each line.
        for parts in devices:
            try:
                if use_mount:
                    parts[0] = parts[-1]
                if inodes:
                    if util.Platform.is_darwin(platform_name):
                        # Filesystem 512-blocks Used Available Capacity iused ifree %iused  Mounted
                        # Inodes are in position 5, 6 and we need to compute the total
                        # Total
                        parts[1] = int(parts[5]) + int(parts[6])  # Total
                        parts[2] = int(parts[5])  # Used
                        parts[3] = int(parts[6])  # Available
                    elif util.Platform.is_freebsd(platform_name):
                        # Filesystem 1K-blocks Used Avail Capacity iused ifree %iused Mounted
                        # Inodes are in position 5, 6 and we need to compute the total
                        parts[1] = int(parts[5]) + int(parts[6])  # Total
                        parts[2] = int(parts[5])  # Used
                        parts[3] = int(parts[6])  # Available
                    else:
                        parts[1] = int(parts[1])  # Total
                        parts[2] = int(parts[2])  # Used
                        parts[3] = int(parts[3])  # Available
                else:
                    parts[1] = int(parts[1])  # Total
                    parts[2] = int(parts[2])  # Used
                    parts[3] = int(parts[3])  # Available
            except IndexError:
                self.logger.exception("Cannot parse %s" % (parts,))

            # Some partitions (EFI boot) may appear to have 0 available inodes
            if parts[1] == 0:
                continue

            #
            # Remote shared storage device names like '10.103.0.220:/instances'
            # cause invalid metrics on the api server side, so if we encounter
            # a colon, remove everything to the left of it (including the
            # offending colon).
            #
            device_name = parts[0]
            idx = device_name.find(":")
            if idx > 0:
                device_name = device_name[(idx+1):]
            if inodes:
                usage_data['%s.disk.inode_used_perc' % device_name] = float(parts[2]) / parts[1] * 100
            else:
                usage_data['%s.disk.space_used_perc' % device_name] = float(parts[2]) / parts[1] * 100

        return usage_data

    @staticmethod
    def _is_number(a_string):
        try:
            float(a_string)
        except ValueError:
            return False
        return True

    def _is_real_device(self, device):
        """Return true if we should track the given device name and false otherwise.
        """
        # First, skip empty lines.
        if not device or len(device) <= 1:
            return False

        # Filter out fake devices.
        device_name = device[0]
        if device_name == 'none':
            return False

        # Now filter our fake hosts like 'map -hosts'. For example:
        #       Filesystem    1024-blocks     Used Available Capacity  Mounted on
        #       /dev/disk0s2    244277768 88767396 155254372    37%    /
        #       map -hosts              0        0         0   100%    /net
        blocks = device[1]
        if not self._is_number(blocks):
            return False
        return True

    def _flatten_devices(self, devices):
        # Some volumes are stored on their own line. Rejoin them here.
        previous = None
        for parts in devices:
            if len(parts) == 1:
                previous = parts[0]
            elif previous and self._is_number(parts[0]):
                # collate with previous line
                parts.insert(0, previous)
                previous = None
            else:
                previous = None
        return devices

    def _transform_df_output(self, df_output, blacklist_re):
        """Given raw output for the df command, transform it into a normalized list devices.

        A 'device' is a list with fields corresponding to the output of df output on each platform.
        """
        all_devices = [l.strip().split() for l in df_output.split("\n")]

        # Skip the header row and empty lines.
        raw_devices = [l for l in all_devices[1:] if l]

        # Flatten the disks that appear in the mulitple lines.
        flattened_devices = self._flatten_devices(raw_devices)

        # Filter fake disks.
        def keep_device(device):
            if not self._is_real_device(device):
                return False
            if blacklist_re and blacklist_re.match(device[0]):
                return False
            return True

        devices = filter(keep_device, flattened_devices)

        return devices


class IO(check.Check):

    def __init__(self, logger, agent_config=None):
        super(IO, self).__init__(logger, agent_config)
        self.header_re = re.compile(r'([%\\/\-_a-zA-Z0-9]+)[\s+]?')
        self.item_re = re.compile(r'^([a-zA-Z0-9\/]+)')
        self.value_re = re.compile(r'\d+\.\d+')
        self.stat_blacklist = ["await", "wrqm/s", "avgqu-sz", "r_await", "w_await", "rrqm/s",
                               "avgrq-sz", "%util", "svctm"]

    def _parse_linux2(self, output):
        recent_stats = output.split('Device:')[2].split('\n')
        header = recent_stats[0]
        header_names = re.findall(self.header_re, header)

        io_stats = {}

        for statsIndex in range(1, len(recent_stats)):
            row = recent_stats[statsIndex]

            if not row:
                # Ignore blank lines.
                continue

            device_match = self.item_re.match(row)

            if device_match is not None:
                # Sometimes device names span two lines.
                device = device_match.groups()[0]
            else:
                continue

            values = re.findall(self.value_re, row)

            if not values:
                # Sometimes values are on the next line so we encounter
                # instances of [].
                continue

            io_stats[device] = {}

            for header_index in range(len(header_names)):
                header_name = header_names[header_index]
                io_stats[device][self.xlate(header_name, "linux")] = values[header_index]

        return io_stats

    @staticmethod
    def _parse_darwin(output):
        lines = [l.split() for l in output.split("\n") if len(l) > 0]
        disks = lines[0]
        lastline = lines[-1]
        io = {}
        for idx, disk in enumerate(disks):
            kb_t, tps, mb_s = map(float, lastline[(3 * idx):(3 * idx) + 3])  # 3 cols at a time
            io[disk] = {
                'system.io.bytes_per_s': mb_s * 10 ** 6,
            }
        return io

    @staticmethod
    def xlate(metric_name, os_name):
        """Standardize on linux metric names.
        """
        if os_name == "sunos":
            names = {"wait": "await",
                     "svc_t": "svctm",
                     "%b": "%util",
                     "kr/s": "io.read_kbytes_sec",
                     "kw/s": "io.write_kbytes_sec",
                     "actv": "avgqu-sz"}
        elif os_name == "freebsd":
            names = {"svc_t": "await",
                     "%b": "%util",
                     "kr/s": "io.read_kbytes_sec",
                     "kw/s": "io.write_kbytes_sec",
                     "wait": "avgqu-sz"}
        elif os_name == "linux":
            names = {"rkB/s": "io.read_kbytes_sec",
                     "r/s": "io.read_req_sec",
                     "wkB/s": "io.write_kbytes_sec",
                     "w/s": "io.write_req_sec"}
        # translate if possible
        return names.get(metric_name, metric_name)

    def check(self):
        """Capture io stats.

        @rtype dict
        @return [metrics.Measurement, ]
        """

        # TODO psutil.disk_io_counters() will also return this infomration but it isn't per second and so must be
        # converted possibly by doing two runs a second apart or storing timestamp+data from the previous collection
        io = {}
        try:
            if util.Platform.is_linux():
                stdout = sp.Popen(['iostat', '-d', '1', '2', '-x', '-k'],
                                  stdout=sp.PIPE,
                                  close_fds=True).communicate()[0]

                #                 Linux 2.6.32-343-ec2 (ip-10-35-95-10)   12/11/2012      _x86_64_        (2 CPU)
                #
                # Device:     rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
                # sda1          0.00    17.61    0.26   32.63     4.23   201.04    12.48     0.16    4.81   0.53   1.73
                # sdb           0.00     2.68    0.19    3.84     5.79    26.07    15.82     0.02    4.93   0.22   0.09
                # sdg           0.00     0.13    2.29    3.84   100.53    30.61    42.78     0.05    8.41   0.88   0.54
                # sdf           0.00     0.13    2.30    3.84   100.54    30.61    42.78     0.06    9.12   0.90   0.55
                # md0           0.00     0.00    0.05    3.37     1.41    30.01    18.35     0.00    0.00   0.00   0.00
                #
                # Device:     rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
                # sda1          0.00     0.00    0.00   10.89     0.00    43.56     8.00     0.03    2.73   2.73   2.97
                # sdb           0.00     0.00    0.00    2.97     0.00    11.88     8.00     0.00    0.00   0.00   0.00
                # sdg           0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                # sdf           0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                # md0           0.00     0.00    0.00    0.00     0.00     0.00     0.00
                # 0.00    0.00   0.00   0.00
                io.update(self._parse_linux2(stdout))

            elif sys.platform == "sunos5":
                iostat = sp.Popen(["iostat", "-x", "-d", "1", "2"],
                                  stdout=sp.PIPE,
                                  close_fds=True).communicate()[0]

                #                   extended device statistics <-- since boot
                # device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
                # ramdisk1    0.0    0.0    0.1    0.1  0.0  0.0    0.0   0   0
                # sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd1        79.9  149.9 1237.6 6737.9  0.0  0.5    2.3   0  11
                #                   extended device statistics <-- past second
                # device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
                # ramdisk1    0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd1         0.0  139.0    0.0 1850.6  0.0  0.0    0.1   0   1

                # discard the first half of the display (stats since boot)
                lines = [l for l in iostat.split("\n") if len(l) > 0]
                lines = lines[len(lines) / 2:]

                assert "extended device statistics" in lines[0]
                headers = lines[1].split()
                assert "device" in headers
                for l in lines[2:]:
                    cols = l.split()
                    # cols[0] is the device
                    # cols[1:] are the values
                    io[cols[0]] = {}
                    for i in range(1, len(cols)):
                        io[cols[0]][self.xlate(headers[i], "sunos")] = cols[i]

            elif sys.platform.startswith("freebsd"):
                iostat = sp.Popen(["iostat", "-x", "-d", "1", "2"],
                                  stdout=sp.PIPE,
                                  close_fds=True).communicate()[0]

                # Be careful!
                # It looks like SunOS, but some columms (wait, svc_t) have different meaning
                #                        extended device statistics
                # device     r/s   w/s    kr/s    kw/s wait svc_t  %b
                # ad0        3.1   1.3    49.9    18.8    0   0.7   0
                #                         extended device statistics
                # device     r/s   w/s    kr/s    kw/s wait svc_t  %b
                # ad0        0.0   2.0     0.0    31.8    0   0.2   0

                # discard the first half of the display (stats since boot)
                lines = [l for l in iostat.split("\n") if len(l) > 0]
                lines = lines[len(lines) / 2:]

                assert "extended device statistics" in lines[0]
                headers = lines[1].split()
                assert "device" in headers
                for l in lines[2:]:
                    cols = l.split()
                    # cols[0] is the device
                    # cols[1:] are the values
                    io[cols[0]] = {}
                    for i in range(1, len(cols)):
                        io[cols[0]][self.xlate(headers[i], "freebsd")] = cols[i]
            elif sys.platform == 'darwin':
                iostat = sp.Popen(['iostat', '-d', '-c', '2', '-w', '1'],
                                  stdout=sp.PIPE,
                                  close_fds=True).communicate()[0]
                #          disk0           disk1          <-- number of disks
                #    KB/t tps  MB/s     KB/t tps  MB/s
                #   21.11  23  0.47    20.01   0  0.00
                #    6.67   3  0.02     0.00   0  0.00    <-- line of interest
                io = self._parse_darwin(iostat)
            else:
                return []

            # If we filter devices, do it know.
            if self.agent_config is not None:
                device_blacklist_re = self.agent_config.get('device_blacklist_re', None)
            else:
                device_blacklist_re = None
            if device_blacklist_re:
                filtered_io = {}
                for device, stats in io.iteritems():
                    if not device_blacklist_re.match(device):
                        filtered_io[device] = stats
            else:
                filtered_io = io

            measurements = []
            timestamp = time.time()
            for dev_name, stats in filtered_io.iteritems():
                filtered_stats = dict((stat, stats[stat])
                                  for stat in stats.iterkeys() if stat not in self.stat_blacklist)
                m_list = [metrics.Measurement(key,
                                              timestamp,
                                              value,
                                              self._set_dimensions({'device': dev_name}),
                                              None)
                          for key, value in filtered_stats.iteritems()]
                measurements.extend(m_list)

            return measurements

        except Exception:
            self.logger.exception("Cannot extract IO statistics")
            return []


class Load(check.Check):

    def check(self):
        if util.Platform.is_linux():
            try:
                loadAvrgProc = open('/proc/loadavg', 'r')
                uptime = loadAvrgProc.readlines()
                loadAvrgProc.close()
            except Exception:
                self.logger.exception('Cannot extract load')
                return []

            uptime = uptime[0]  # readlines() provides a list but we want a string

        elif sys.platform in ('darwin', 'sunos5') or sys.platform.startswith("freebsd"):
            # Get output from uptime
            try:
                uptime = sp.Popen(['uptime'],
                                  stdout=sp.PIPE,
                                  close_fds=True).communicate()[0]
            except Exception:
                self.logger.exception('Cannot extract load')
                return {}

        # Split out the 3 load average values
        load = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
        timestamp = time.time()
        dimensions = self._set_dimensions(None)

        return [metrics.Measurement('load.avg_1_min', timestamp, float(load[0]), dimensions),
                metrics.Measurement('load.avg_5_min', timestamp, float(load[1]), dimensions),
                metrics.Measurement('load.avg_15_min', timestamp, float(load[2]), dimensions)]


class Memory(check.Check):

    def check(self):
        mem_info = psutil.virtual_memory()
        swap_info = psutil.swap_memory()
        mem_data = {
            'mem.total_mb': int(mem_info.total/1048576),
            'mem.free_mb': int(mem_info.free/1048576),
            'mem.usable_mb': int(mem_info.available/1048576),
            'mem.usable_perc': float(100 - mem_info.percent),
            'mem.swap_total_mb': int(swap_info.total/1048576),
            'mem.swap_used_mb': int(swap_info.used/1048576),
            'mem.swap_free_mb': int(swap_info.free/1048576),
            'mem.swap_free_perc': float(100 - swap_info.percent)
        }

        if 'buffers' in mem_info:
            mem_data['mem.used_buffers'] = int(mem_info.buffers/1048576)

        if 'cached' in mem_info:
            mem_data['mem.used_cache'] = int(mem_info.cached/1048576)

        if 'shared' in mem_info:
            mem_data['mem.used_shared'] = int(mem_info.shared/1048576)

        timestamp = time.time()
        dimensions = self._set_dimensions(None)
        return [metrics.Measurement(key, timestamp, value, dimensions) for key, value in mem_data.iteritems()]


class Cpu(check.Check):

    def check(self):
        """Return an aggregate of CPU stats across all CPUs.
        """
        cpu_stats = psutil.cpu_times_percent(percpu=False)
        return self._format_results(cpu_stats.user + cpu_stats.nice,
                                    cpu_stats.system + cpu_stats.irq + cpu_stats.softirq,
                                    cpu_stats.iowait,
                                    cpu_stats.idle,
                                    cpu_stats.steal)

    def _format_results(self, us, sy, wa, idle, st):
        data = {'cpu.user_perc': us,
                'cpu.system_perc': sy,
                'cpu.wait_perc': wa,
                'cpu.idle_perc': idle,
                'cpu.stolen_perc': st}
        for key in data.keys():
            if data[key] is None:
                del data[key]

        timestamp = time.time()
        dimensions = self._set_dimensions(None)
        return [metrics.Measurement(key, timestamp, value, dimensions) for key, value in data.iteritems()]


def _get_subprocess_output(command):
    """Run the given subprocess command and return it's output.

    Raise an Exception if an error occurs.
    """
    proc = sp.Popen(command, stdout=sp.PIPE, close_fds=True)
    return proc.stdout.read()


if __name__ == '__main__':
    # 1s loop with results

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-15s %(message)s')
    log = logging.getLogger()
    config = {"device_blacklist_re": re.compile('.*disk0.*')}
    cpu = Cpu(log, config)
    disk = Disk(log, config)
    io = IO(log, config)
    load = Load(log, config)
    mem = Memory(log, config)

    while True:
        print("=" * 10)
        print("--- IO ---")
        print(io.check())
        print("--- Disk ---")
        print(disk.check())
        print("--- CPU ---")
        print(cpu.check())
        print("--- Load ---")
        print(load.check())
        print("--- Memory ---")
        print(mem.check())
        print("\n\n\n")
        time.sleep(1)
