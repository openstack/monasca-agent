# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP

import ConfigParser
import grp
import logging
import os
import psutil
import pwd
import subprocess
import sys

import monasca_setup.agent_config
from monasca_setup.detection import Plugin
from monasca_setup.detection.utils import find_process_name

from distutils.version import LooseVersion
from shutil import copy

log = logging.getLogger(__name__)

# Directory to use for instance and metric caches (preferred tmpfs "/dev/shm")
cache_dir = "/dev/shm"
# Maximum age of instance cache before automatic refresh (in seconds)
nova_refresh = 60 * 60 * 4  # Four hours
# Probation period before metrics are gathered for a VM (in seconds)
vm_probation = 60 * 5  # Five minutes
# List of instance metadata keys to be sent as dimensions
# By default 'scale_group' metadata is used here for supporting auto
# scaling in Heat.
metadata = ['scale_group']
# Include scale group dimension for customer metrics.
customer_metadata = ['scale_group']
# List 'ping' commands (paths and parameters) in order of preference.
# The plugin will use the first fuctional command. 127.0.0.1 will be appended.
ping_options = [["/usr/bin/fping", "-n", "-c1", "-t250", "-q"],
                ["/sbin/fping", "-n", "-c1", "-t250", "-q"],
                ["/bin/ping", "-n", "-c1", "-w1", "-q"]]
# Path to 'ip' command (needed to execute ping within network namespaces)
ip_cmd = "/sbin/ip"
# How many ping commands to run concurrently
default_max_ping_concurrency = 8
# Disk metrics can be collected at a larger interval than other vm metrics
default_disk_collection_period = 0
# VNIC metrics can be collected at a larger interval than other vm metrics
default_vnic_collection_period = 0

# Arguments which should be written as integers, not strings
INT_ARGS = ['disk_collection_period', 'vnic_collection_period',
            'max_ping_concurrency', 'nova_refresh', 'vm_probation']


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
                    conf_indexes = [cmd.index(y) for y in cmd if 'nova.conf' in y]
                    if not conf_indexes:
                        continue
                    param = conf_indexes[0]
                    if '=' in cmd[param]:
                        nova_conf = cmd[param].split('=')[1]
                    else:
                        nova_conf = cmd[param]
            except (IOError, psutil.NoSuchProcess):
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
                           'vm_probation': vm_probation,
                           'metadata': metadata,
                           'customer_metadata': customer_metadata,
                           'max_ping_concurrency': default_max_ping_concurrency,
                           'disk_collection_period': default_disk_collection_period,
                           'vnic_collection_period': default_vnic_collection_period}

            # Set default parameters for included checks
            init_config['vm_cpu_check_enable'] = self.literal_eval('True')
            init_config['vm_disks_check_enable'] = self.literal_eval('True')
            init_config['vm_network_check_enable'] = self.literal_eval('True')
            init_config['vm_ping_check_enable'] = self.literal_eval('True')
            init_config['vm_extended_disks_check_enable'] = self.literal_eval('False')

            for option in cfg_needed:
                init_config[option] = nova_cfg.get(cfg_section, cfg_needed[option])

            # Create an identity URI (again, slightly different for Devstack)
            if nova_cfg.has_option(cfg_section, 'auth_url'):
                init_config['identity_uri'] = "{0}/v2.0".format(nova_cfg.get(cfg_section, 'auth_url'))
            else:
                init_config['identity_uri'] = "{0}/v2.0".format(nova_cfg.get(cfg_section, 'identity_uri'))

            # Verify requirements to enable ping checks
            init_config['ping_check'] = self.literal_eval('False')
            if self.agent_user is None:
                log.warn("\tUnable to determine agent user.  Skipping ping checks.")
            else:
                try:
                    from neutronclient.v2_0 import client

                    # Copy system 'ip' command to local directory
                    copy(ip_cmd, sys.path[0])
                    # Restrict permissions on the local 'ip' command
                    os.chown("{0}/ip".format(sys.path[0]), pwd.getpwnam(self.agent_user).pw_uid, 0)
                    os.chmod("{0}/ip".format(sys.path[0]), 0o700)
                    # Set capabilities on 'ip' which will allow
                    # self.agent_user to exec commands in namespaces
                    setcap_cmd = ['/sbin/setcap', 'cap_sys_admin+ep',
                                  "{0}/ip".format(sys.path[0])]
                    subprocess.Popen(setcap_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    # Verify that the capabilities were set
                    setcap_cmd.extend(['-v', '-q'])
                    subprocess.check_call(setcap_cmd)
                    # Look for the best ping command
                    for ping_cmd in ping_options:
                        if os.path.isfile(ping_cmd[0]):
                            init_config['ping_check'] = "{0}/ip netns exec NAMESPACE {1}".format(sys.path[0],
                                                                                                 ' '.join(ping_cmd))
                            log.info("\tEnabling ping checks using {0}".format(ping_cmd[0]))
                            break
                    if init_config['ping_check'] is False:
                        log.warn("\tUnable to find suitable ping command, disabling ping checks.")
                except ImportError:
                    log.warn("\tneutronclient module missing, required for ping checks.")
                    pass
                except IOError:
                    log.warn("\tUnable to copy {0}, ping checks disabled.".format(ip_cmd))
                    pass
                except (subprocess.CalledProcessError, OSError):
                    log.warn("\tUnable to set up ping checks, setcap failed ({0})".format(' '.join(setcap_cmd)))
                    pass

            # Handle monasca-setup detection arguments, which take precedence
            if self.args:
                for arg in self.args:
                    if arg in INT_ARGS:
                        value = self.args[arg]
                        try:
                            init_config[arg] = int(value)
                        except ValueError:
                            log.warn("\tInvalid integer value '{0}' for parameter {1}, ignoring value"
                                     .format(value, arg))
                    else:
                        init_config[arg] = self.literal_eval(self.args[arg])

            config['libvirt'] = {'init_config': init_config,
                                 'instances': []}

        return config

    def dependencies_installed(self):
        try:
            import json
            import monasca_agent.collector.virt.inspector
            import time

            from netaddr import all_matching_cidrs
            from novaclient import client
        except ImportError:
            log.warn("\tDependencies not satisfied; plugin not configured.")
            return False
        if os.path.isdir(cache_dir) is False:
            log.warn("\tCache directory {} not found;" +
                     " plugin not configured.".format(cache_dir))
            return False
        return True
