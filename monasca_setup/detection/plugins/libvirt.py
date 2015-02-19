import logging
import os.path
import ConfigParser
import monasca_setup.detection
import monasca_setup.agent_config

log = logging.getLogger(__name__)

# Location of nova.conf from which to read credentials
nova_conf = "/etc/nova/nova.conf"
# Directory to use for instance and metric caches (preferred tmpfs "/dev/shm")
cache_dir = "/dev/shm"
# Maximum age of instance cache before automatic refresh (in seconds)
nova_refresh = 60 * 60 * 4  # Four hours
# Probation period before metrics are gathered for a VM (in seconds)
vm_probation = 60 * 5  # Five minutes


class Libvirt(monasca_setup.detection.Plugin):
    """Configures VM monitoring through Nova"""

    def _detect(self):
        """Run detection, set self.available True if the service is detected.
        """
        if (monasca_setup.detection.find_process_name('nova-api') is not None and
           os.path.isfile(nova_conf)):
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return back.
        """
        config = monasca_setup.agent_config.Plugins()

        if self.dependencies_installed():
            nova_cfg = ConfigParser.SafeConfigParser()
            nova_cfg.read(nova_conf)
            # Which configuration options are needed for the plugin YAML?
            cfg_needed = ['admin_user', 'admin_password',
                          'admin_tenant_name']
            cfg_section = 'keystone_authtoken'

            # Start with plugin-specific configuration parameters
            init_config = {'cache_dir': cache_dir,
                           'nova_refresh': nova_refresh,
                           'vm_probation': vm_probation}

            for option in cfg_needed:
                init_config[option] = nova_cfg.get(cfg_section, option)

            # Create an identity server URI
            init_config['identity_uri'] = "{0}://{1}:{2}/v2.0".format(nova_cfg.get(cfg_section, 'auth_protocol'),
                                                                      nova_cfg.get(cfg_section, 'auth_host'),
                                                                      nova_cfg.get(cfg_section, 'auth_port'))

            config['libvirt'] = {'init_config': init_config,
                                 'instances': [{}]}

        return config

    def dependencies_installed(self):
        try:
            import time
            import yaml
            import novaclient.v3.client
            import monasca_agent.collector.virt.inspector
        except ImportError:
            log.warn("\tDependencies not satisfied; plugin not configured.")
            return False
        if os.path.isdir(cache_dir) is False:
            log.warn("\tCache directory {} not found;" +
                     " plugin not configured.".format(cache_dir))
            return False
        return True
