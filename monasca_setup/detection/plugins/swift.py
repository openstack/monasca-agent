import os

import monasca_setup.detection

DIAG_COMMAND = '/usr/local/bin/diagnostics'
CHECKER_COMMAND = '/usr/local/bin/swift-checker'

diag_attributes = ['check_mounts', 'disk_monitoring', 'file_ownership',
                   'network_interface', 'ping_hosts', 'drive_audit']

checker_attributes = ['diskusage', 'healthcheck', 'replication']


def get_instances(command, attributes):
    """
    Fetch instances per command type and attribute
    """
    instances = []
    for attribute in attributes:
        cmd = dict()
        cmd['name'] = '{0}.{1}'.format('swift', attribute)
        cmd['check_command'] = '{0} --{1}'.format(command, attribute)
        cmd['check_interval'] = 60
        cmd['dimensions'] = {'service': 'swift'}
        instances.append(cmd)
    return instances


def get_config_instances():
    """
    Fetch all instances per command type
    """
    config_instances = []
    config_instances.extend(get_instances(DIAG_COMMAND, diag_attributes))
    config_instances.extend(get_instances(CHECKER_COMMAND, checker_attributes))
    return config_instances


class Swift(monasca_setup.detection.ServicePlugin):

    """Detect Swift daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True):
        service_params = {
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'object-storage',
            'process_names': ['swift-container-updater', 'swift-account-auditor',
                              'swift-object-replicator', 'swift-container-replicator',
                              'swift-object-auditor', 'swift-container-auditor',
                              'swift-account-reaper', 'swift-container-sync',
                              'swift-account-replicator', 'swift-object-updater',
                              'swift-object-server', 'swift-account-server',
                              'swift-container-server', 'swift-proxy-server'],
            'service_api_url': 'http://localhost:8080/healthcheck',
            'search_pattern': '.*OK.*'
        }

        super(Swift, self).__init__(service_params)

    def build_config(self):
        config = super(Swift, self).build_config()

        if os.path.exists(DIAG_COMMAND) and \
                os.path.exists(CHECKER_COMMAND):
            config['nagios_wrapper'] = {'init_config': None,
                                        'instances': get_config_instances(),
                                        }

        return config
