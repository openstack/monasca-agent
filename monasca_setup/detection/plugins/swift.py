import os

import monasca_setup.detection


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

        # This is a bit of an abuse of the nagios_wrapper but the commands will return failed error code properly
        swift_health = "/bin/sh -c '" + \
                       "/usr/local/bin/diagnostics --check_mounts && " + \
                       "/usr/local/bin/diagnostics --disk_monitoring && " + \
                       "/usr/local/bin/diagnostics --file_ownership && " + \
                       "/usr/local/bin/diagnostics --network_interface && " + \
                       "/usr/local/bin/diagnostics --ping_hosts && " + \
                       "/usr/local/bin/diagnostics --swift_services && " + \
                       "/usr/local/bin/swift-checker --diskusage && " + \
                       "/usr/local/bin/swift-checker --healthcheck && " + \
                       "/usr/local/bin/swift-checker --replication'"

        if os.path.exists('/usr/local/bin/diagnostics') and os.path.exists('/usr/local/bin/swift-checker'):
            config['nagios_wrapper'] = {'init_config': None,
                                        'instances': [
                                            {'name': 'Swift.health',
                                             'check_command': swift_health,
                                             'check_interval': 60,
                                             'dimensions': {'service': 'swift'}}
                                        ]}

        return config
