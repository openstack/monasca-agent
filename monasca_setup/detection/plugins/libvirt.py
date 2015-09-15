import ConfigParser
import grp
import logging
import os
import psutil
import subprocess

import monasca_setup.agent_config
from monasca_setup.detection import Plugin
from monasca_setup.detection.utils import find_process_name

from distutils.version import LooseVersion

log = logging.getLogger(__name__)

# Directory to use for instance and metric caches (preferred tmpfs "/dev/shm")
cache_dir = "/dev/shm"
# Maximum age of instance cache before automatic refresh (in seconds)
nova_refresh = 60 * 60 * 4  # Four hours
# Probation period before metrics are gathered for a VM (in seconds)
vm_probation = 60 * 5  # Five minutes
# List 'ping' commands (paths and parameters) in order of preference.
# The plugin will use the first fuctional command. 127.0.0.1 will be appended.
ping_options = [["/usr/bin/fping", "-n", "-c1", "-t250", "-q"],
                ["/sbin/fping", "-n", "-c1", "-t250", "-q"],
                ["/bin/ping", "-n", "-c1", "-w1", "-q"]]


class Libvirt(Plugin):
    """Configures VM monitoring through Nova"""

    def _detect(self):
        """Set self.available True if the process and config file are detected
        """
        # Detect Agent's OS username by getting the group owner of confg file
        try:
            gid = os.stat('/etc/monasca/agent/agent.yaml').st_gid
            self.agent_user = grp.getgrgid(gid)[0]
        except OSError:
            self.agent_user = None
        # Try to detect the location of the Nova configuration file.
        # Walk through the list of processes, searching for 'nova-compute'
        # process with 'nova.conf' inside one of the parameters
        nova_conf = None
        for proc in psutil.process_iter():
            try:
                cmd = proc.cmdline()
                if len(cmd) > 2 and 'python' in cmd[0] and 'nova-compute' in cmd[1]:
                    param = [cmd.index(y) for y in cmd if 'nova.conf' in y][0]
                    if '=' in cmd[param]:
                        nova_conf = cmd[param].split('=')[1]
                    else:
                        nova_conf = cmd[param]
            except IOError:
                # Process has already terminated, ignore
                continue
        if (nova_conf is not None and os.path.isfile(nova_conf)):
            self.available = True
            self.nova_conf = nova_conf

    def build_config(self):
        """Build the config as a Plugins object and return back.
        """
        config = monasca_setup.agent_config.Plugins()

        if self.dependencies_installed():
            nova_cfg = ConfigParser.SafeConfigParser()
            log.info("\tUsing nova configuration file {0}".format(self.nova_conf))
            nova_cfg.read(self.nova_conf)
            # Which configuration options are needed for the plugin YAML?
            # Use a dict so that they can be renamed later if necessary
            cfg_needed = {'admin_user': 'admin_user',
                          'admin_password': 'admin_password',
                          'admin_tenant_name': 'admin_tenant_name'}
            cfg_section = 'keystone_authtoken'

            # Handle Devstack's slightly different nova.conf names
            if (nova_cfg.has_option(cfg_section, 'username')
               and nova_cfg.has_option(cfg_section, 'password')
               and nova_cfg.has_option(cfg_section, 'project_name')):
                cfg_needed = {'admin_user': 'username',
                              'admin_password': 'password',
                              'admin_tenant_name': 'project_name'}

            # Start with plugin-specific configuration parameters
            init_config = {'cache_dir': cache_dir,
                           'nova_refresh': nova_refresh,
                           'vm_probation': vm_probation}

            for option in cfg_needed:
                init_config[option] = nova_cfg.get(cfg_section, cfg_needed[option])

            # Create an identity URI (again, slightly different for Devstack)
            if nova_cfg.has_option(cfg_section, 'auth_url'):
                init_config['identity_uri'] = "{0}/v2.0".format(nova_cfg.get(cfg_section, 'auth_url'))
            else:
                init_config['identity_uri'] = "{0}/v2.0".format(nova_cfg.get(cfg_section, 'identity_uri'))

            # Verify functionality of the ping command to enable ping checks
            if self.agent_user is None:
                log.warn("\tUnable to determine agent user.  Skipping ping checks.")
            else:
                for ping_cmd in ping_options:
                    if os.path.isfile(ping_cmd[0]):
                        with open(os.devnull, "w") as fnull:
                            # Build a test command that uses sudo and hits localhost
                            ping_local_cmd = ["sudo", "-u", self.agent_user]
                            ping_local_cmd.extend(ping_cmd)
                            ping_local_cmd.append("127.0.0.1")
                            try:
                                res = subprocess.call(ping_local_cmd,
                                                      stdout=fnull,
                                                      stderr=fnull)
                            except subprocess.CalledProcessError:
                                pass
                            if res == 0:
                                log.info("\tEnabling ping checks using {0}".format(ping_cmd[0]))
                                init_config['ping_check'] = " ".join(ping_cmd)
                                break
                if 'ping_check' not in init_config:
                    log.info("\tUnable to find suitable ping command, disabling ping checks.")
                    init_config['ping_check'] = self.literal_eval('False')

            # Handle monasca-setup detection arguments, which take precedence
            if self.args:
                for arg in self.args:
                    init_config[arg] = self.literal_eval(self.args[arg])

            config['libvirt'] = {'init_config': init_config,
                                 'instances': [{}]}

        return config

    def dependencies_installed(self):
        try:
            import novaclient
            import time
            import yaml
            # novaclient module versions were renamed in version 2.22
            if novaclient.__version__ < LooseVersion("2.22"):
                import novaclient.v1_1.client
            else:
                import novaclient.v2.client
            import monasca_agent.collector.virt.inspector
        except ImportError:
            log.warn("\tDependencies not satisfied; plugin not configured.")
            return False
        if os.path.isdir(cache_dir) is False:
            log.warn("\tCache directory {} not found;" +
                     " plugin not configured.".format(cache_dir))
            return False
        return True
