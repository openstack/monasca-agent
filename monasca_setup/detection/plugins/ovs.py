# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

import ConfigParser
import logging
import os
import psutil
import re

import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

# Maximum time to wait before updating neutron router cache(in seconds)
neutron_refresh = 60 * 60 * 4  # Four hours
# Directory to use for metric caches
cache_dir = "/dev/shm"
# ovs-vsctl command needs sudo privileges to connect to
# /var/run/openvswitch/db.sock which is created by ovsdb-server.
ovs_cmd = "sudo /usr/bin/ovs-vsctl"
# If set, will submit network metrics in bits
network_use_bits = False
# Regular expression for interface types
included_interface_re = 'qg.*|vhu.*|sg.*'
# If set, will submit raw counters from ovs-vsctl command output for the given
# network interface
use_absolute_metrics = True
# If set, will submit the rate metrics
use_rate_metrics = True
# If set, will submit the health metrics
use_health_metrics = True
# Acceptable arguments
acceptable_args = ['admin_user', 'admin_password', 'admin_tenant_name',
                   'identity_uri', 'cache_dir', 'neutron_refresh', 'ovs_cmd',
                   'network_use_bits', 'check_router_ha', 'region_name',
                   'included_interface_re', 'conf_file_path', 'use_absolute_metrics',
                   'use_rate_metrics', 'use_health_metrics']
# Arguments which must be ignored if provided
ignorable_args = ['admin_user', 'admin_password', 'admin_tenant_name',
                  'identity_uri', 'region_name', 'conf_file_path']
# Regular expression to match the URI version
uri_version_re = re.compile('.*v2.0|.*v3.0|.*v1|.*v2')


class Ovs(monasca_setup.detection.Plugin):
    """Detect OVS daemons and setup configuration to monitor

    """
    def _detect(self):
        neutron_conf = None
        if self.args:
            for arg in self.args:
                if arg == 'conf_file_path':
                    neutron_conf = self.args[arg]
        # Try to detect the location of the Neutron configuration file.
        # Walk through the list of processes, searching for 'neutron'
        # process with 'neutron.conf' inside one of the parameters.
        if not neutron_conf:
            for proc in psutil.process_iter():
                try:
                    proc_dict = proc.as_dict()
                    if proc_dict['name'] == 'neutron-openvsw':
                        cmd = proc_dict['cmdline']
                        neutron_config_params = [param for param in cmd if 'neutron.conf' in param]
                        if not neutron_config_params:
                            continue
                        if '=' in neutron_config_params[0]:
                            neutron_conf = neutron_config_params[0].split('=')[1]
                        else:
                            neutron_conf = neutron_config_params[0]
                except (IOError, psutil.NoSuchProcess):
                    # Process has already terminated, ignore
                    continue

        if (neutron_conf is not None and os.path.isfile(neutron_conf)):
            self.available = True
            self.neutron_conf = neutron_conf
        else:
            log.error("Neutron configuration file not found!!!")

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = monasca_setup.agent_config.Plugins()
        if self.dependencies_installed():
            neutron_cfg = ConfigParser.SafeConfigParser()
            log.info("\tUsing neutron configuration file {0}".format(self.neutron_conf))
            neutron_cfg.read(self.neutron_conf)
            cfg_needed = {'admin_user': 'admin_user',
                          'admin_password': 'admin_password',
                          'admin_tenant_name': 'admin_tenant_name'}
            cfg_section = 'keystone_authtoken'

            # Handle Devstack's slightly different neutron.conf names
            if (
               neutron_cfg.has_option(cfg_section, 'username') and
               neutron_cfg.has_option(cfg_section, 'password') and
               neutron_cfg.has_option(cfg_section, 'project_name')):
                cfg_needed = {'admin_user': 'username',
                              'admin_password': 'password',
                              'admin_tenant_name': 'project_name'}

            # Start with plugin-specific configuration parameters
            init_config = {'cache_dir': cache_dir,
                           'neutron_refresh': neutron_refresh,
                           'ovs_cmd': ovs_cmd,
                           'network_use_bits': network_use_bits,
                           'included_interface_re': included_interface_re,
                           'use_absolute_metrics': use_absolute_metrics,
                           'use_rate_metrics': use_rate_metrics,
                           'use_health_metrics': use_health_metrics}

            for option in cfg_needed:
                init_config[option] = neutron_cfg.get(cfg_section, cfg_needed[option])

            uri_version = 'v2.0'
            if neutron_cfg.has_option(cfg_section, 'auth_version'):
                uri_version = str(neutron_cfg.get(cfg_section, 'auth_version'))

            # Create an identity URI (again, slightly different for Devstack)
            if neutron_cfg.has_option(cfg_section, 'auth_url'):
                if re.match(uri_version_re, str(neutron_cfg.get(cfg_section, 'auth_url'))):
                    uri_version = ''
                init_config['identity_uri'] = "{0}/{1}".format(neutron_cfg.get(cfg_section, 'auth_url'), uri_version)
            else:
                init_config['identity_uri'] = "{0}/{1}".format(neutron_cfg.get(cfg_section, 'identity_uri'), uri_version)

            # Create an region_name (again, slightly different for Devstack)
            if neutron_cfg.has_option('service_auth', 'region'):
                init_config['region_name'] = str(neutron_cfg.get('service_auth', 'region'))
            else:
                init_config['region_name'] = str(neutron_cfg.get('nova', 'region_name'))
            # Handle monasca-setup detection arguments, which take precedence
            if self.args:
                for arg in self.args:
                    if arg in acceptable_args and arg not in ignorable_args:
                        if arg == 'included_interface_re':
                            try:
                                re.compile(self.args[arg])
                            except re.error as e:
                                exception_msg = (
                                    "Invalid regular expression given for "
                                    "'included_interface_re'. {0}.".format(e))
                                log.exception(exception_msg)
                                raise Exception(exception_msg)

                        init_config[arg] = self.literal_eval(self.args[arg])
                    elif arg in ignorable_args:
                        log.warn("Argument '{0}' is ignored; Fetching {0} from "
                                 "neutron configuration file.".format(arg))
                    else:
                        log.warn("Invalid argument '{0}' "
                                 "has been provided!!!".format(arg))

            config['ovs'] = {'init_config': init_config,
                             'instances': []}

        return config

    def dependencies_installed(self):
        try:
            import monasca_agent.collector.virt.inspector
            import neutronclient.v2_0.client

        except ImportError as e:
            exception_msg = (
                "Dependencies not satisfied; Plugin not "
                "configured. {0}.".format(e))
            log.exception(exception_msg)
            raise Exception(exception_msg)
        return True
