# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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
        self.service_name = 'ceph'
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

    def _service_config(self, clusters, service_type):
        display_name = self.service_constants[service_type]['display_name']
        service_dir = self.service_constants[service_type]['service_dir']
        executable = self.service_constants[service_type]['executable']
        expected_processes = list()

        for cluster in clusters:
            cluster_name = cluster['cluster_name']
            instance_list = list()

            # Get the list of daemon identifiers for given cluster
            if os.path.exists(service_dir):
                instance_list = [entry for entry in os.listdir(service_dir)
                                 if entry.split('-', 1)[0] == cluster_name]

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
                #
                # 'id' for radosgw is preceded by client.rgw. plus an
                # alphanumeric that is usually the hostname where the service
                # is running.
                # E.g., client.rgw.ceph-radosgw1.dom
                process = dict()
                if service_type == 'radosgw':
                    daemon_id = instance.split('.', 1)[-1]
                    process_args = ['--cluster %s' % cluster_name,
                                    '--name client.rgw.%s' % daemon_id, '-f']
                else:
                    daemon_id = instance.split(cluster_name + '-', 1)[1]
                    process_args = ['--cluster %s' % cluster_name,
                                    '--id %s' % daemon_id, '-f']
                process['search_string'] = self._build_search_string(
                    executable, process_args)
                process['name'] = '%s-%s.%s' \
                                  % (cluster_name, service_type, daemon_id)
                process['type'] = display_name
                expected_processes.append(process)

        return expected_processes

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()

        # There may be multiple clusters, and we construct a list of dicts
        # containing cluster_name and config_file for each cluster
        clusters = list()

        # Get the cluster_name from <cluster_name>.conf in /etc/ceph/ directory
        if os.path.exists(self.ceph_config_dir):
            config_files = [f for f in os.listdir(self.ceph_config_dir)
                            if f.endswith('.conf')]
            if not config_files:
                return config
            for config_file in config_files:
                cluster_dict = dict()
                cluster_dict['cluster_name'] = config_file[:-5]
                cluster_dict['config_file'] = \
                    os.path.join(self.ceph_config_dir, config_file)
                clusters.append(cluster_dict)

        expected_processes = list()

        expected_processes.extend(self._service_config(clusters, 'mon'))
        expected_processes.extend(self._service_config(clusters, 'osd'))
        expected_processes.extend(self._service_config(clusters, 'mds'))
        expected_processes.extend(self._service_config(clusters, 'radosgw'))

        for process in expected_processes:
            # Watch the service processes
            log.info("\tMonitoring the {0} {1} process.".format(
                process['name'], self.service_name))
            config.merge(watch_process(search_strings=process['search_string'],
                                       service=self.service_name,
                                       component=process['type'],
                                       process_name=process['name'],
                                       exact_match=False))

        # Configure ceph plugin
        instances = []
        for cluster in clusters:
            cluster_name = cluster['cluster_name']
            log.info("\tMonitoring ceph cluster: '{0}'.".format(cluster_name))
            instances.append({'cluster_name': cluster_name})
        config['ceph'] = {'init_config': None, 'instances': instances}
        return config
