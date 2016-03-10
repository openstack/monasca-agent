# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
#
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

import itertools
import logging
import os

from monasca_setup import agent_config
from monasca_setup.detection import Plugin
from monasca_setup.detection.utils import find_process_cmdline
from monasca_setup.detection.utils import watch_process

log = logging.getLogger(__name__)


class Ceph(Plugin):

    """Detect Ceph daemons and setup configuration to monitor them.

    The Ceph services comprise of three main daemons:
      - Object Storage Daemon (OSD)
          There is a OSD service process per disk added in the cluster
          and has a corresponding daemon identifier at /var/lib/ceph/osd/
      - Monitor Servers (MON)
          There is a Monitor service process per monitoring host in the
          cluster and has a corresponding daemon identifier at
          /var/lib/ceph/mon/
      - Metadata Servers (MDS)
          There is a MDS service process per monitoring host in the
          cluster and has a corresponding daemon identifier at
          /var/lib/ceph/mds/

    The ceph object store is exposed via RADOS Gateway
      - RADOS Gateway (radosgw)
          'radosgw' is an HTTP REST gateway for the RADOS object store,
          a part of the Ceph distributed storage system.

    Unlike OpenStack services monitoring a single instance of a service will
    be of no use for Ceph. Every daemon needs to be monitored. This can be
    achieved by scanning through the daemon identifiers.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        self.service_name = 'ceph-storage'
        self.process_names = ['ceph-osd', 'ceph-mon', 'ceph-mds', 'radosgw']
        self.ceph_config_dir = '/etc/ceph/'
        self.service_constants = dict()
        for process in self.process_names:
            process_type = process.replace('ceph-', '')
            display_name = 'ceph-%s' % process \
                if not process.startswith('ceph-') else process
            self.service_constants[process_type] = {
                'service_dir': '/var/lib/ceph/%s/' % process_type,
                'executable': '/usr/bin/%s' % process,
                'display_name': display_name
            }

        super(Ceph, self).__init__(template_dir, overwrite, args)

    def _detect(self):
        """Run detection.

        """
        self.found_processes = list()

        for process in self.process_names:
            if find_process_cmdline(process) is not None:
                self.found_processes.append(process)
        if len(self.found_processes) > 0:
            self.available = True

    @staticmethod
    def _build_search_string(executable, options=None):
        search_strings = list()
        command = [executable]
        if options:
            command.extend(options)

        for permutation in itertools.permutations(command):
            if permutation[0] == executable:
                search_strings.append(" ".join(permutation))
        return search_strings

    def _service_config(self, cluster_name, service_type):
        display_name = self.service_constants[service_type]['display_name']
        service_dir = self.service_constants[service_type]['service_dir']
        executable = self.service_constants[service_type]['executable']
        expected_processes = list()
        # Get the list of daemon identifiers
        instance_list = os.listdir(service_dir) \
            if os.path.exists(service_dir) else list()

        for instance in instance_list:
            # Daemon identifier is of format <cluster_name>-<id>
            # 'id' for ceph-mon is alphanumeric and is usually the hostname
            # where the service is running for ceph-mon
            # E.g., ceph-monitor1.dom, ceph-monitor2.dom etc.
            #
            # 'id' for ceph-osd is a unique numeric index for
            # that OSD in the cluster
            # E.g., ceph-1, ceph-2 etc.
            #
            # 'id' for ceph-mds is alphanumeric and is usually the hostname
            # where the service is running.
            # E.g., ceph-mds1.dom, ceph-mds2.dom etc.
            daemon_id = instance.split(cluster_name + '-', 1)[1]
            process = dict()
            process_args = ['--cluster %s' % cluster_name,
                            '--id %s' % daemon_id, '-f']
            process['search_string'] = self._build_search_string(
                executable, process_args)
            process['name'] = '%s-%s.%s' \
                              % (cluster_name, service_type, daemon_id)
            process['type'] = display_name
            expected_processes.append(process)

        return expected_processes

    def _radosgw_config(self, cluster_name, config_file):
        service_dir = self.service_constants['radosgw']['service_dir']
        expected_processes = list()
        # Get the list of daemon identifiers
        instance_list = os.listdir(service_dir) \
            if os.path.exists(service_dir) else list()

        for instance in instance_list:
            # RADOS Gateway processes is of the format:
            # /usr/bin/radosgw -c <config_file> -n <rados_username>
            # E.g.,
            # /usr/bin/radosgw -c /etc/ceph/ceph.conf -n client.radosgw.gateway
            process = dict()

            # The rados user will have a designated data directory, of the
            # format ceph-radosw.<rados_username> in the service dir.
            # E.g., /var/lib/ceph/radosgw/ceph-radosgw.gateway
            rados_username = instance.replace('ceph-radosgw.', '')
            process['search_string'] = list()
            process['name'] = '%s-radosgw.%s' % (cluster_name, rados_username)
            process['type'] = self.service_constants['radosgw']['display_name']
            executable = self.service_constants['radosgw']['executable']

            process_options = ['-n client.radosgw.%s' % rados_username,
                               '--name=client.radosgw.%s' % rados_username]
            for opt in process_options:
                # Adding multiple combinations for all possible use cases,
                # since any of the following combination can be used to start
                # the process

                # Trivial case (This will be the most used scenario)
                # E.g.,
                # /usr/bin/radosgw -n client.radosgw.gateway
                process['search_string'].append('%s %s' % (executable, opt))

                # Service started with specific conf file (For rare cases)
                # E.g.,
                # /usr/bin/radosgw -c custom.conf -n client.radosgw.gateway
                process['search_string'].append(
                    '%s -c %s %s' % (executable, config_file, opt))
                process['search_string'].append(
                    '%s --conf=%s %s' % (executable, config_file, opt))

            expected_processes.append(process)
        return expected_processes

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()

        # Default cluster name
        cluster_name = 'ceph'
        config_file = '/etc/ceph/ceph.conf'

        # Get the cluster_name from <cluster_name>.conf in /etc/ceph/ directory
        if os.path.exists(self.ceph_config_dir):
            config_files = [f for f in os.listdir(self.ceph_config_dir)
                            if f.endswith('.conf')]
            if not config_files:
                return config
            config_file = os.path.join(self.ceph_config_dir, config_files[0])
            cluster_name = config_files[0][:-5]

        expected_processes = list()

        expected_processes.extend(self._service_config(cluster_name, 'mon'))
        expected_processes.extend(self._service_config(cluster_name, 'osd'))
        expected_processes.extend(self._service_config(cluster_name, 'mds'))
        # RADOS Gateway is little different from other ceph-daemons hence
        # the process definition is handled differently
        expected_processes.extend(self._radosgw_config(
            cluster_name, config_file))

        for process in expected_processes:
            # Watch the service processes
            log.info("\tMonitoring the {0} {1} process.".format(
                process['name'], self.service_name))
            config.merge(watch_process(search_strings=process['search_string'],
                                       service=self.service_name,
                                       component=process['type'],
                                       process_name=process['name'],
                                       exact_match=False))

        return config
