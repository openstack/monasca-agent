import os
import logging

from monasca_setup import agent_config
from monasca_setup.detection import Plugin
from monasca_setup.detection.utils import find_process_cmdline
from monasca_setup.detection.utils import _get_dimensions

log = logging.getLogger(__name__)


def watch_process(search_strings, service=None, component=None,
                  process_name=None, exact_match=True, detailed=False):
    """This is a modification of watch_process utils method to accept an
    additional process_name argument. Takes a list of process search strings
    and returns a Plugins object with the config set.

    This is required because for Ceph, every instance of the service daemons is
    monitored. Hence the utils watch_process method which assumes
    search_strings[0] as process_name is not acceptable.

    """
    config = agent_config.Plugins()

    # Fallback to standard process_name strategy if not defined
    process_name = process_name if process_name else search_strings[0]
    parameters = {'name': process_name,
                  'detailed': detailed,
                  'exact_match': exact_match,
                  'search_string': search_strings}

    dimensions = _get_dimensions(service, component)
    if len(dimensions) > 0:
        parameters['dimensions'] = dimensions

    config['process'] = {'init_config': None,
                         'instances': [parameters]}
    return config


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

    Unlike OpenStack services monitoring a single instance of a service will
    be of no use for Ceph. Every daemon needs to be monitored. This can be
    achieved by scanning through the daemon identifiers.

    """

    def __init__(self,  template_dir, overwrite=True, args=None):
        self.service_name = 'ceph-storage'
        self.process_names = ['ceph-osd', 'ceph-mon', 'ceph-mds']
        self.ceph_osd_path = '/var/lib/ceph/osd/'
        self.ceph_mon_path = '/var/lib/ceph/mon/'
        self.ceph_mds_path = '/var/lib/ceph/mds/'
        self.ceph_osd_executable = '/usr/bin/ceph-osd'
        self.ceph_mon_executable = '/usr/bin/ceph-mon'
        self.ceph_mds_executable = '/usr/bin/ceph-mds'

        super(Ceph, self).__init__(template_dir, overwrite, args)

    def _detect(self):
        """Run detection.

        """
        self.found_processes = []

        for process in self.process_names:
            if find_process_cmdline(process) is not None:
                self.found_processes.append(process)
        if len(self.found_processes) > 0:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()

        # Get the list of daemon identifiers
        osd_list = os.listdir(self.ceph_osd_path) \
            if os.path.exists(self.ceph_osd_path) else []
        mon_list = os.listdir(self.ceph_mon_path) \
            if os.path.exists(self.ceph_mon_path) else []
        mds_list = os.listdir(self.ceph_mds_path) \
            if os.path.exists(self.ceph_mds_path) else []

        expected_processes = []

        for osd in osd_list:
            # OSD daemon identifier is of format <cluster_name>-<id>
            # Where 'id' is a unique numeric index for that OSD in the cluster
            # E.g., ceph-1, ceph-2 etc.
            cluster_name, daemon_id = osd.split('-', 1)
            process = dict()
            process['search_string'] = \
                '%s -f --cluster %s --id %s' \
                % (self.ceph_osd_executable, cluster_name, daemon_id)
            process['name'] = '%s-osd.%s' % (cluster_name, daemon_id)
            process['type'] = 'ceph-osd'
            expected_processes.append(process)

        for mon in mon_list:
            # MON daemon identifier is of format <cluster_name>-<id>
            # Where 'id' is alphanumeric and is usually the hostname
            # where the service is running.
            # E.g., ceph-monitor1.dom, ceph-monitor2.dom etc.
            cluster_name, daemon_id = mon.split('-', 1)
            process = dict()
            process['search_string'] = \
                '%s -f --cluster %s --id %s' \
                % (self.ceph_mon_executable, cluster_name, daemon_id)
            process['name'] = '%s-mon.%s' % (cluster_name, daemon_id)
            process['type'] = 'ceph-mon'
            expected_processes.append(process)

        for mds in mds_list:
            # MON daemon identifier is of format <cluster_name>-<id>
            # Where 'id' is alphanumeric and is usually the hostname
            # where the service is running.
            # E.g., ceph-mds1.dom, ceph-mds2.dom etc.
            cluster_name, daemon_id = mds.split('-', 1)
            process = dict()
            process['search_string'] = \
                '%s -f --cluster %s --id %s' \
                % (self.ceph_mds_executable, cluster_name, daemon_id)
            process['name'] = '%s-mds.%s' % (cluster_name, daemon_id)
            process['type'] = 'ceph-mds'
            expected_processes.append(process)

        for process in expected_processes:
            # Watch the service processes
            log.info("\tMonitoring the {0} {1} process.".format(
                process['name'], self.service_name))
            config.merge(watch_process([process['search_string']],
                                       self.service_name,
                                       process['type'],
                                       process['name'],
                                       exact_match=False))

        return config
