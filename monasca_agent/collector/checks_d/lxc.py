#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import re

import monasca_agent.collector.checks as checks

_LXC_CGROUP_PWD = '/sys/fs/cgroup'
_LXC_CGROUP_CPU_PWD = '{0}/cpu/lxc'.format(_LXC_CGROUP_PWD)
_LXC_CGROUP_CPUSET_PWD = '{0}/cpuset/lxc'.format(_LXC_CGROUP_PWD)
_LXC_CGROUP_MEM_PWD = '{0}/memory/lxc'.format(_LXC_CGROUP_PWD)
_LXC_CGROUP_DISK_PWD = '{0}/blkio/lxc'.format(_LXC_CGROUP_PWD)

_LXC_NET_REGEX = re.compile(r'(\w+):(.+)')
_LXC_DISK_REGEX = re.compile(r'(\w+)\s(\d+)')


class LXC(checks.AgentCheck):
    """Agent to collect LXC cgroup information

    The information is mostly based on cgroup files of each container
    """

    def check(self, instance):
        self.instance = instance
        self.containers = self._containers_name()
        for container_name in self.containers:
            self._collect_cpu_metrics(container_name)
            self._collect_mem_metrics(container_name)
            self._collect_net_metrics(container_name)
            self._collect_disk_metrics(container_name)

    def _containers_name(self):
        container_name = self.instance.get('container')
        if container_name == 'all':
            return [name for name in os.listdir(_LXC_CGROUP_CPU_PWD)
                    if os.path.isdir(_LXC_CGROUP_CPU_PWD + name)]

        if os.path.isdir('{0}/{1}'.format(_LXC_CGROUP_CPU_PWD,
                                          container_name)):
            self.log.info('\tContainer name: ' + container_name)
            return [container_name]
        else:
            self.log.error('\tContainer {0} was not found'
                           .format(container_name))
            return

    def _collect_cpu_metrics(self, container_name):
        if not self.instance.get('cpu', True):
            return
        metrics = self._get_cpu_metrics(container_name)
        cpu_dimensions = self._get_dimensions(container_name)
        for metric, value in metrics.iteritems():
            self.gauge(metric, value, dimensions=cpu_dimensions)

    def _collect_mem_metrics(self, container_name):
        if not self.instance.get('mem', True):
            return
        metrics = self._get_mem_metrics(container_name)
        mem_dimensions = self._get_dimensions(container_name)
        for metric, value in metrics.iteritems():
            self.gauge(metric, value, dimensions=mem_dimensions)

    def _collect_net_metrics(self, container_name):
        if not self.instance.get('net', True):
            return
        metrics = self._get_net_metrics(container_name)
        for iface_name, iface_metrics in metrics.iteritems():
            net_dimensions = self._get_dimensions(container_name,
                                                  {'iface': iface_name})
            for metric, value in iface_metrics.iteritems():
                self.gauge(metric, value, dimensions=net_dimensions)

    def _collect_disk_metrics(self, container_name):
        if not self.instance.get('blkio', True):
            return
        metrics = self._get_disk_metrics(container_name)
        disk_dimensions = self._get_dimensions(container_name)
        for metric, value in metrics.iteritems():
            self.gauge(metric, value, dimensions=disk_dimensions)

    def _get_cpu_metrics(self, container_name):
        """Get metrics from cpuacct.usage cgroup file

            :return: a dictionary containing cpu metrics defined on container
            cgroup
        """
        metrics = {}
        cpu_cgroup = '{0}/{1}/'.format(_LXC_CGROUP_CPU_PWD, container_name)
        metrics['cpuacct.usage'] = int(open(cpu_cgroup + 'cpuacct.usage', 'r')
                                       .readline().rstrip('\n'))
        cpuacct_usage_percpu = open(cpu_cgroup + 'cpuacct.usage_percpu', 'r')\
            .readline().rstrip(' \n').split(' ')
        for cpu in range(len(cpuacct_usage_percpu)):
            metrics['cpuacct.usage_percpu.cpu{0}'.format(cpu)] = \
                int(cpuacct_usage_percpu[cpu])
        metrics_stat = self._get_metrics_by_file(cpu_cgroup + 'cpuacct.stat',
                                                 'cpuacct')
        metrics.update(metrics_stat)
        return metrics

    def _get_mem_metrics(self, container_name):
        """Get metrics from memory.stat cgroup file

           :returns: a dictionary containing memory metrics defined on
           container cgroup
        """
        mem_cgroup = '{0}/{1}/'.format(_LXC_CGROUP_MEM_PWD, container_name)
        metrics = self._get_metrics_by_file(mem_cgroup + 'memory.stat',
                                            'memory')
        return metrics

    def _get_net_metrics(self, container_name):
        """Get metrics for each net interface found

        :returns: a dictionary containing metrics regarding each
        net interface found, in the format:
        { 'lo': { 'net.rx.bytes': 1234 }, ...}
        """
        metrics = {}
        pid = self._get_pid_container(container_name)
        net_cgroup = '/proc/{0}/net/'.format(pid)
        with open(net_cgroup + 'dev', 'r') as dev_file:
            for line in dev_file:
                iface = re.search(_LXC_NET_REGEX, line)
                if iface:
                    iface_name = iface.group(1)
                    iface_info = iface.group(2).split()
                    metrics[iface_name] = {
                        'net.rx.bytes': int(iface_info[0]),
                        'net.rx.packets': int(iface_info[1]),
                        'net.rx.errs': int(iface_info[2]),
                        'net.rx.drop': int(iface_info[3]),
                        'net.rx.fifo': int(iface_info[4]),
                        'net.rx.frame': int(iface_info[5]),
                        'net.rx.compressed': int(iface_info[6]),
                        'net.rx.multicast': int(iface_info[7]),
                        'net.tx.bytes': int(iface_info[8]),
                        'net.tx.packets': int(iface_info[9]),
                        'net.tx.errs': int(iface_info[10]),
                        'net.tx.drop': int(iface_info[11]),
                        'net.tx.fifo': int(iface_info[12]),
                        'net.tx.frame': int(iface_info[13]),
                        'net.tx.compressed': int(iface_info[14]),
                        'net.tx.multicast': int(iface_info[15])
                    }
        return metrics

    def _get_disk_metrics(self, container_name):
        """Get metrics blkio.throttle.io_service_bytes from cgroup file

            :return: a dictionary containing blkio metrics used to verify disk
            cgroup usage
        """
        metrics = {}
        disk_cgroup = '{0}/{1}/blkio.throttle.io_service_bytes'.format(
                      _LXC_CGROUP_DISK_PWD, container_name)
        with open(disk_cgroup, 'r') as disk_file:
            for line in disk_file:
                disk = re.search(_LXC_DISK_REGEX, line)
                if disk:
                    disk_key = 'blkio.{0}'.format(disk.group(1)).lower()
                    disk_value = disk.group(2)
                    metrics[disk_key] = int(disk_value)
        return metrics

    def _get_metrics_by_file(self, filename, pre_key):
        """Some cgroup files have a pattern 'key value' that can be easily
        handled to a dictionary
        """
        metrics = {}
        with open(filename, 'r') as cgroup_file:
            for line in cgroup_file:
                resource_post_key, resource_value = line.split(' ')
                resource_key = '{0}.{1}'.format(pre_key, resource_post_key)
                metrics[resource_key] = int(resource_value)
        return metrics

    def _get_dimensions(self, container_name, options=None):
        dimensions = {'container_name': container_name,
                      'service': 'lxc'}
        dimensions.update(options)
        return self._set_dimensions(dimensions, self.instance)

    def _get_pid_container(self, container_name):
        cpu_tasks = '{0}/{1}/tasks'.format(_LXC_CGROUP_CPU_PWD,
                                           container_name)
        pid = open(cpu_tasks, 'r').readline().rstrip('\n')
        return pid
