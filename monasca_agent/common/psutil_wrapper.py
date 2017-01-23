#  Copyright 2017 Fujitsu LIMITED
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from collections import namedtuple

import psutil as psutil_orig


sconn = namedtuple('sconn', ['fd', 'family', 'type', 'laddr', 'raddr',
                             'status', 'pid'])

psutil = psutil_orig


def cpu_count(logical=True):
    if logical:
        return psutil.NUM_CPUS
    else:
        raise NotImplementedError


def net_connections(kind='inet'):
    ret = set()
    for p in psutil.process_iter():
        try:
            for c in p.connections(kind):
                conn = sconn(c.fd, c.family, c.type, c.laddr, c.raddr,
                             c.status, p.pid)
                ret.add(conn)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return list(ret)


def children(self, recursive=False):
    return psutil.Process.get_children(self, recursive=recursive)


def connections(self, kind='inet'):
    return psutil.Process.get_connections(self, kind=kind)


def cpu_affinity(self, cpus=None):
    return psutil.Process.get_cpu_affinity(self)


def cpu_percent(self, interval=None):
    return psutil.Process.get_cpu_percent(self, interval=interval)


def cpu_times(self):
    return psutil.Process.get_cpu_times(self)


def memory_info_ex(self):
    return psutil.Process.get_ext_memory_info(self)


def io_counters(self):
    return psutil.Process.get_io_counters(self)


def ionice(self, ioclass=None, value=None):
    return psutil.Process.get_ionice(self)


def memory_info(self):
    return psutil.Process.get_memory_info(self)


def memory_maps(self, grouped=True):
    return psutil.Process.get_memory_maps(self, grouped=grouped)


def memory_percent(self):
    return psutil.Process.get_memory_percent(self)


def nice(self, value=None):
    return psutil.Process.get_nice(self)


def num_ctx_switches(self):
    return psutil.Process.get_num_ctx_switches(self)


def num_fds(self):
    return psutil.Process.get_num_fds(self)


def num_threads(self):
    return psutil.Process.get_num_threads(self)


def open_files(self):
    return psutil.Process.get_open_files(self)


def threads(self):
    return psutil.Process.get_threads(self)


def cwd(self):
    return psutil.Process.getcwd(self)


if psutil.version_info < (2, 0):
    psutil.cpu_count = cpu_count
    psutil.Process.children = children
    psutil.Process.connections = connections
    psutil.Process.cpu_affinity = cpu_affinity
    psutil.Process.cpu_percent = cpu_percent
    psutil.Process.cpu_times = cpu_times
    psutil.Process.memory_info_ex = memory_info_ex
    psutil.Process.io_counters = io_counters
    psutil.Process.ionice = ionice
    psutil.Process.memory_info = memory_info
    psutil.Process.memory_maps = memory_maps
    psutil.Process.memory_percent = memory_percent
    psutil.Process.nice = nice
    psutil.Process.num_ctx_switches = num_ctx_switches
    psutil.Process.num_fds = num_fds
    psutil.Process.num_threads = num_threads
    psutil.Process.open_files = open_files
    psutil.Process.threads = threads
    psutil.Process.cwd = cwd

if psutil.version_info < (2, 1):
    psutil.net_connections = net_connections
