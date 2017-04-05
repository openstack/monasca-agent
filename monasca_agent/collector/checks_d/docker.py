# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP

from __future__ import absolute_import

import os
import re

import docker

from monasca_agent.collector import checks

CONTAINER_ID_RE = re.compile('[0-9a-f]{64}')
DEFAULT_BASE_URL = "unix://var/run/docker.sock"
DEFAULT_VERSION = "auto"
DEFAULT_TIMEOUT = 3
DEFAULT_ADD_KUBERNETES_DIMENSIONS = False
JIFFY_HZ = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
CGROUPS = ['cpuacct', 'memory', 'blkio']


class Docker(checks.AgentCheck):
    """Collect metrics and events from Docker API and cgroups"""

    def __init__(self, name, init_config, agent_config, instances=None):
        checks.AgentCheck.__init__(self, name, init_config, agent_config, instances)

        if instances is not None and len(instances) > 1:
            raise Exception('Docker check only supports one configured instance.')

        self.connection_timeout = int(init_config.get('connection_timeout', DEFAULT_TIMEOUT))
        self.docker_version = init_config.get('version', DEFAULT_VERSION)
        self.docker_root = init_config.get('docker_root', '/')
        # Locate cgroups directories
        self._mount_points = {}
        self._cgroup_filename_pattern = None
        for cgroup in CGROUPS:
            self._mount_points[cgroup] = self._find_cgroup(cgroup)
        self._prev_cpu = {}
        self._curr_cpu = {}
        self._cpu_count = None
        self._prev_system_cpu = None

    def check(self, instance):
        docker_url = instance.get('url', DEFAULT_BASE_URL)
        try:
            docker_client = docker.Client(base_url=docker_url, version=self.docker_version,
                                          timeout=self.connection_timeout)
            running_containers = {container['Id']: container for container in self._get_containers(docker_client)}
        except Exception as e:
            self.log.error("Could not get containers from Docker API skipping Docker check - {}".format(e))
            return
        add_kubernetes_dimensions = instance.get('add_kubernetes_dimensions', DEFAULT_ADD_KUBERNETES_DIMENSIONS)
        dimensions = self._set_dimensions(None, instance)
        self.gauge("container.running_count", len(running_containers), dimensions=dimensions)
        self._set_container_pids(running_containers)
        # Report container metrics from cgroups
        self._report_container_metrics(running_containers, add_kubernetes_dimensions, dimensions)

    def _report_rate_gauge_metric(self, metric_name, value, dimensions):
        self.rate(metric_name + "_sec", value, dimensions=dimensions)
        self.gauge(metric_name, value, dimensions=dimensions)

    def _report_container_metrics(self, container_dict, add_kubernetes_dimensions, dimensions):
        self._curr_system_cpu, self._cpu_count = self._get_system_cpu_ns()
        system_memory = self._get_total_memory()
        for container in container_dict.itervalues():
            try:
                container_dimensions = dimensions.copy()
                container_id = container['Id']
                container_dimensions['name'] = self._get_container_name(container['Names'], container_id)
                container_dimensions['image'] = container['Image']
                container_labels = container['Labels']
                if add_kubernetes_dimensions:
                    if 'io.kubernetes.pod.name' in container_labels:
                        container_dimensions['kubernetes_pod_name'] = container_labels['io.kubernetes.pod.name']
                    if 'io.kubernetes.pod.namespace' in container_labels:
                        container_dimensions['kubernetes_namespace'] = container_labels['io.kubernetes.pod.namespace']
                self._report_cgroup_cpuacct(container_id, container_dimensions)
                self._report_cgroup_memory(container_id, container_dimensions, system_memory)
                self._report_cgroup_blkio(container_id, container_dimensions)
                if "_proc_root" in container:
                    self._report_net_metrics(container, container_dimensions)

                self._report_cgroup_cpu_pct(container_id, container_dimensions)
            except IOError as err:
                # It is possible that the container got stopped between the
                # API call and now
                self.log.info("IO error while collecting cgroup metrics, "
                              "skipping container...", exc_info=err)
            except Exception as err:
                self.log.error("Error when collecting data about container {}".format(err))
        self._prev_system_cpu = self._curr_system_cpu

    def _get_container_name(self, container_names, container_id):
        container_name = None
        if container_names:
            for name in container_names:
                # if there is more than one / the name is actually an alias
                if name.count('/') <= 1:
                    container_name = str(name).lstrip('/')
                    break
        return container_name if container_name else container_id

    def _report_cgroup_cpuacct(self, container_id, container_dimensions):
        stat_file = self._get_cgroup_file('cpuacct', container_id, 'cpuacct.stat')
        stats = self._parse_cgroup_pairs(stat_file)
        self._report_rate_gauge_metric('container.cpu.user_time', stats['user'], container_dimensions)
        self._report_rate_gauge_metric('container.cpu.system_time', stats['system'], container_dimensions)

    def _report_cgroup_memory(self, container_id, container_dimensions, system_memory_limit):
        stat_file = self._get_cgroup_file('memory', container_id, 'memory.stat')
        stats = self._parse_cgroup_pairs(stat_file)

        cache_memory = stats['cache']
        rss_memory = stats['rss']
        self.gauge('container.mem.cache', cache_memory, dimensions=container_dimensions)
        self.gauge('container.mem.rss', rss_memory, dimensions=container_dimensions)

        swap_memory = 0
        if 'swap' in stats:
            swap_memory = stats['swap']
            self.gauge('container.mem.swap', swap_memory, dimensions=container_dimensions)

        # Get container max memory
        memory_limit_file = self._get_cgroup_file('memory', container_id, 'memory.limit_in_bytes')
        memory_limit = self._parse_cgroup_value(memory_limit_file, convert=float)
        if memory_limit > system_memory_limit:
            memory_limit = float(system_memory_limit)
        used_perc = round((((cache_memory + rss_memory + swap_memory) / memory_limit) * 100), 2)
        self.gauge('container.mem.used_perc', used_perc, dimensions=container_dimensions)

    def _report_cgroup_blkio(self, container_id, container_dimensions):
        stat_file = self._get_cgroup_file('blkio', container_id,
                                          'blkio.throttle.io_service_bytes')
        stats = self._parse_cgroup_blkio_metrics(stat_file)
        self._report_rate_gauge_metric('container.io.read_bytes', stats['io_read'], container_dimensions)
        self._report_rate_gauge_metric('container.io.write_bytes', stats['io_write'], container_dimensions)

    def _report_cgroup_cpu_pct(self, container_id, container_dimensions):
        usage_file = self._get_cgroup_file('cpuacct', container_id, 'cpuacct.usage')

        prev_cpu = self._prev_cpu.get(container_id, None)
        curr_cpu = self._parse_cgroup_value(usage_file)
        self._prev_cpu[container_id] = curr_cpu

        if prev_cpu is None:
            # probably first run, we need 2 data points
            return

        system_cpu_delta = float(self._curr_system_cpu - self._prev_system_cpu)
        container_cpu_delta = float(curr_cpu - prev_cpu)
        if system_cpu_delta > 0 and container_cpu_delta > 0:
            cpu_pct = (container_cpu_delta / system_cpu_delta) * self._cpu_count * 100
            self.gauge('container.cpu.utilization_perc', cpu_pct, dimensions=container_dimensions)

    def _report_net_metrics(self, container, container_dimensions):
        """Find container network metrics by looking at /proc/$PID/net/dev of the container process."""
        proc_net_file = os.path.join(container['_proc_root'], 'net/dev')
        try:
            with open(proc_net_file, 'r') as f:
                lines = f.readlines()
                """Two first lines are headers:
                Inter-|   Receive                                                |  Transmit
                 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
                """
                for line in lines[2:]:
                    cols = line.split(':', 1)
                    interface_name = str(cols[0]).strip()
                    if interface_name != 'lo':
                        container_network_dimensions = container_dimensions.copy()
                        container_network_dimensions['interface'] = interface_name
                        network_values = cols[1].split()
                        self._report_rate_gauge_metric("container.net.in_bytes", long(network_values[0]),
                                                       container_network_dimensions)
                        self._report_rate_gauge_metric("container.net.out_bytes", long(network_values[8]),
                                                       container_network_dimensions)
                        break
        except Exception as e:
            self.log.error("Failed to report network metrics from file {0}. Exception: {1}".format(proc_net_file, e))

    # Docker API
    def _get_containers(self, docker_client):
        """Gets the list of running containers in Docker."""
        return docker_client.containers()

    def _find_cgroup_filename_pattern(self, container_id):
        # We try with different cgroups so that it works even if only one is properly working
        for mountpoint in self._mount_points.itervalues():
            stat_file_path_lxc = os.path.join(mountpoint, "lxc")
            stat_file_path_docker = os.path.join(mountpoint, "docker")
            stat_file_path_coreos = os.path.join(mountpoint, "system.slice")
            stat_file_path_kubernetes = os.path.join(mountpoint, container_id)
            stat_file_path_kubernetes_docker = os.path.join(mountpoint, "system", "docker", container_id)
            stat_file_path_docker_daemon = os.path.join(mountpoint, "docker-daemon", "docker", container_id)

            if os.path.exists(stat_file_path_lxc):
                return '%(mountpoint)s/lxc/%(id)s/%(file)s'
            elif os.path.exists(stat_file_path_docker):
                return '%(mountpoint)s/docker/%(id)s/%(file)s'
            elif os.path.exists(stat_file_path_coreos):
                return '%(mountpoint)s/system.slice/docker-%(id)s.scope/%(file)s'
            elif os.path.exists(stat_file_path_kubernetes):
                return '%(mountpoint)s/%(id)s/%(file)s'
            elif os.path.exists(stat_file_path_kubernetes_docker):
                return '%(mountpoint)s/system/docker/%(id)s/%(file)s'
            elif os.path.exists(stat_file_path_docker_daemon):
                return '%(mountpoint)s/docker-daemon/docker/%(id)s/%(file)s'

        raise Exception("Cannot find Docker cgroup directory. Be sure your system is supported.")

    def _get_cgroup_file(self, cgroup, container_id, filename):
        # This can't be initialized at startup because cgroups may not be mounted yet
        if not self._cgroup_filename_pattern:
            self._cgroup_filename_pattern = self._find_cgroup_filename_pattern(container_id)

        return self._cgroup_filename_pattern % (dict(
            mountpoint=self._mount_points[cgroup],
            id=container_id,
            file=filename,
        ))

    def _get_total_memory(self):
        with open(os.path.join(self.docker_root, '/proc/meminfo')) as f:
            for line in f.readlines():
                tokens = line.split()
                if tokens[0] == 'MemTotal:':
                    return int(tokens[1]) * 1024

        raise Exception('Invalid formatting in /proc/meminfo: unable to '
                        'determine MemTotal')

    def _get_system_cpu_ns(self):
        # see also: getSystemCPUUsage of docker's stats_collector_unix.go
        total_jiffies = None
        cpu_count = 0

        with open(os.path.join(self.docker_root, '/proc/stat'), 'r') as f:
            for line in f.readlines():
                tokens = line.split()

                if tokens[0] == 'cpu':
                    if len(tokens) < 8:
                        raise Exception("Invalid formatting in /proc/stat")

                    total_jiffies = sum(map(lambda t: int(t), tokens[1:8]))
                elif tokens[0].startswith('cpu'):
                    # startswith but does not equal implies /cpu\d+/ or so
                    # we don't need full per-cpu usage to calculate %,
                    # so just count cores
                    cpu_count += 1

        if not total_jiffies:
            raise Exception("Unable to find CPU usage in /proc/stat")

        cpu_time_ns = (total_jiffies / JIFFY_HZ) * 1e9
        return cpu_time_ns, cpu_count

    def _find_cgroup(self, hierarchy):
        """Finds the mount point for a specified cgroup hierarchy. Works with
        old style and new style mounts.
        """
        with open(os.path.join(self.docker_root, "/proc/mounts"), 'r') as f:
            mounts = map(lambda x: x.split(), f.read().splitlines())

        cgroup_mounts = filter(lambda x: x[2] == "cgroup", mounts)
        if len(cgroup_mounts) == 0:
            raise Exception("Can't find mounted cgroups. If you run the Agent inside a container,"
                            " please refer to the documentation.")
        # Old cgroup style
        if len(cgroup_mounts) == 1:
            return os.path.join(self.docker_root, cgroup_mounts[0][1])

        candidate = None
        for _, mountpoint, _, opts, _, _ in cgroup_mounts:
            if hierarchy in opts:
                if mountpoint.startswith("/host/"):
                    return os.path.join(self.docker_root, mountpoint)
                candidate = mountpoint
        if candidate is not None:
            return os.path.join(self.docker_root, candidate)
        raise Exception("Can't find mounted %s cgroups." % hierarchy)

    def _parse_cgroup_value(self, stat_file, convert=int):
        """Parse a cgroup info file containing a single value."""
        with open(stat_file, 'r') as f:
            return convert(f.read().strip())

    def _parse_cgroup_pairs(self, stat_file, convert=int):
        """Parse a cgroup file for key/values."""
        with open(stat_file, 'r') as f:
            split_lines = map(lambda x: x.split(' ', 1), f.readlines())
            return {k: convert(v) for k, v in split_lines}

    def _parse_cgroup_blkio_metrics(self, stat_file):
        """Parse the blkio metrics."""
        with open(stat_file, 'r') as f:
            stats = f.read().splitlines()
            metrics = {
                'io_read': 0,
                'io_write': 0,
            }
            for line in stats:
                if 'Read' in line:
                    metrics['io_read'] += int(line.split()[2])
                if 'Write' in line:
                    metrics['io_write'] += int(line.split()[2])
            return metrics

    # checking if cgroup is a container cgroup
    def _is_container_cgroup(self, line, selinux_policy):
        if line[1] not in ('cpu,cpuacct', 'cpuacct,cpu', 'cpuacct') or line[2] == '/docker-daemon':
            return False
        if 'docker' in line[2]:
            return True
        if 'docker' in selinux_policy:
            return True
        if line[2].startswith('/') and re.match(CONTAINER_ID_RE, line[2][1:]):  # kubernetes
            return True
        return False

    def _set_container_pids(self, containers):
        """Find all proc paths for running containers."""
        proc_path = os.path.join(self.docker_root, 'proc')
        pid_dirs = [_dir for _dir in os.listdir(proc_path) if _dir.isdigit()]

        for pid_dir in pid_dirs:
            try:
                path = os.path.join(proc_path, pid_dir, 'cgroup')
                with open(path, 'r') as f:
                    content = [line.strip().split(':') for line in f.readlines()]

                selinux_policy = ''
                path = os.path.join(proc_path, pid_dir, 'attr', 'current')
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        selinux_policy = f.readlines()[0]
            except IOError as e:
                self.log.debug("Cannot read %s, "
                               "process likely raced to finish : %s" %
                               (path, str(e)))
                continue
            except Exception as e:
                self.log.warning("Cannot read %s : %s" % (path, str(e)))
                continue

            try:
                cpuacct = None
                for line in content:
                    if self._is_container_cgroup(line, selinux_policy):
                        cpuacct = line[2]
                        break
                matches = re.findall(CONTAINER_ID_RE, cpuacct) if cpuacct else None
                if matches:
                    container_id = matches[-1]
                    if container_id not in containers:
                        self.log.debug("Container %s not in container_dict, it's likely excluded", container_id)
                        continue
                    containers[container_id]['_pid'] = pid_dir
                    containers[container_id]['_proc_root'] = os.path.join(proc_path, pid_dir)
            except Exception as e:
                self.log.warning("Cannot parse %s content: %s" % (path, str(e)))
                continue
