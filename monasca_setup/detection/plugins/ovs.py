# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

import ConfigParser
import logging
import os
import re

from oslo_config import cfg
from oslo_utils import importutils

from monasca_setup import agent_config
from monasca_setup import detection
from monasca_setup.detection import utils

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
# If set, router max capacity metrics will be published
publish_router_capacity = False
# Acceptable arguments
acceptable_args = ['username', 'password', 'project_name',
                   'auth_url', 'cache_dir', 'neutron_refresh', 'ovs_cmd',
                   'network_use_bits', 'check_router_ha', 'region_name',
                   'included_interface_re', 'conf_file_path', 'use_absolute_metrics',
                   'use_rate_metrics', 'use_health_metrics', 'publish_router_capacity']
# Arguments which must be ignored if provided
ignorable_args = ['username', 'password', 'project_name',
                  'auth_url', 'region_name', 'conf_file_path']


class Ovs(detection.Plugin):
    """Detect OVS daemons and setup configuration to monitor

    """

    PROC_NAME = 'neutron-openvsw'
    """Name of the ovs process to look for"""
    REQUIRED_CONF_SECTIONS = 'keystone_authtoken',
    """Tuple of sections that must be part of neutron configuration file"""

    def _detect(self):
        process_exist = utils.find_process_cmdline(Ovs.PROC_NAME)
        has_dependencies = self.dependencies_installed()
        neutron_conf = self._get_ovs_config_file() if process_exist else ''
        neutron_conf_exists = os.path.isfile(neutron_conf)
        neutron_conf_valid = (neutron_conf_exists
                              and self._is_neutron_conf_valid(neutron_conf))

        self.available = (process_exist is not None and
                          neutron_conf_valid and has_dependencies)
        self.cmd = ''
        if process_exist:
            self.cmd = process_exist.as_dict(attrs=['cmdline'])['cmdline']

        if not self.available:
            if not process_exist:
                log.error('OVS daemon process [%s] does not exist.',
                          Ovs.PROC_NAME)
            elif not neutron_conf_exists:
                log.error(('OVS daemon process exists but configuration '
                           'file was not found. Path to file does not exist '
                           'as a process parameter or was not '
                           'passed via args.'))
            elif not neutron_conf_valid:
                log.error(('OVS daemon process exists, configuration file was '
                           'found but it looks like it does not contain '
                           'one of following sections=%s. '
                           'Check if neutron was not configured to load '
                           'configuration from /etc/neutron/neutron.conf.d/.'),
                          Ovs.REQUIRED_CONF_SECTIONS)
                # NOTE(trebskit) the problem with that approach is that
                # each setting that Ovs plugin require might be scattered
                # through multiple files located inside
                # /etc/neutron/neutron.conf.d/
                # not to mention that it is still possible to have
                # yet another configuration file passed as neutron CLI
                # argument
            elif not has_dependencies:
                log.error(('OVS daemon process exists but required '
                           'dependencies were not found.\n'
                           'Run pip install monasca-agent[ovs] '
                           'to install all dependencies.'))
        else:
            for_opts = [{'opt': cfg.StrOpt('region', default='RegionOne'), 'group': 'service_auth'},
                        {'opt': cfg.StrOpt('region_name'), 'group': 'nova'},
                        {'opt': cfg.StrOpt('nova_region_name'), 'group': 'DEFAULT'},
                        {'opt': cfg.StrOpt('username'), 'group': 'keystone_authtoken'},
                        {'opt': cfg.StrOpt('password'), 'group': 'keystone_authtoken'},
                        {'opt': cfg.StrOpt('project_name'), 'group': 'keystone_authtoken'},
                        {'opt': cfg.StrOpt('auth_url'), 'group': 'keystone_authtoken'},
                        {'opt': cfg.StrOpt('identity_uri'), 'group': 'keystone_authtoken'}]
            self.conf = utils.load_oslo_configuration(from_cmd=self.cmd,
                                                      in_project='neutron',
                                                      for_opts=for_opts
                                                      )
            log.info("\tUsing neutron configuration file {0} for detection".format(neutron_conf))
            self.neutron_conf = neutron_conf

    def _is_neutron_conf_valid(self, conf_file):
        neutron_cfg = ConfigParser.SafeConfigParser()
        neutron_cfg.read(conf_file)

        for section in self.REQUIRED_CONF_SECTIONS:
            if not neutron_cfg.has_section(section=section):
                return False

        return True

    def _get_ovs_config_file(self):
        neutron_conf = None
        if self.args:
            for arg in self.args:
                if arg == 'conf_file_path':
                    neutron_conf = self.args[arg]
        # Try to detect the location of the Neutron configuration file.
        # Walk through the list of processes, searching for 'neutron'
        # process with 'neutron.conf' inside one of the parameters.
        if not neutron_conf:
            proc = utils.find_process_name(Ovs.PROC_NAME)
            proc_dict = proc.as_dict(attrs=['cmdline'])
            cmd = proc_dict['cmdline']
            neutron_config_params = [param for param in cmd if
                                     'neutron.conf' in param]
            if neutron_config_params:
                if '=' in neutron_config_params[0]:
                    neutron_conf = neutron_config_params[0].split('=')[1]
                else:
                    neutron_conf = neutron_config_params[0]
        return neutron_conf

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        config = agent_config.Plugins()
        log.info("\tUsing neutron configuration file {0} and configuration dir"
                 " {1}".format(self.conf.default_config_files, self.conf.default_config_dirs))
        cfg_section = 'keystone_authtoken'
        cfg_needed = {'username': 'username',
                      'password': 'password',
                      'project_name': 'project_name'}

        # Start with plugin-specific configuration parameters
        init_config = {'cache_dir': cache_dir,
                       'neutron_refresh': neutron_refresh,
                       'ovs_cmd': ovs_cmd,
                       'network_use_bits': network_use_bits,
                       'included_interface_re': included_interface_re,
                       'use_absolute_metrics': use_absolute_metrics,
                       'use_rate_metrics': use_rate_metrics,
                       'use_health_metrics': use_health_metrics,
                       'publish_router_capacity': publish_router_capacity}

        for option in cfg_needed:
            init_config[option] = self.get_option(cfg_section, cfg_needed[option])

        # Create an identity URI (again, slightly different for Devstack)
        if self.has_option(cfg_section, 'auth_url'):
            init_config['auth_url'] = self.get_option(cfg_section, 'auth_url')
        else:
            init_config['auth_url'] = self.get_option(cfg_section, 'identity_uri')

        # Create an region_name (again, slightly different for Devstack)
        if self.has_option('service_auth', 'region'):
            init_config['region_name'] = str(self.get_option('service_auth', 'region'))
        else:
            try:
                init_config['region_name'] = str(self.get_option('nova', 'region_name'))
            except ConfigParser.NoOptionError:
                log.debug(('Option region_name was not found in nova '
                           'section, nova_region_name option from '
                           'DEFAULT section will be used.'))
                init_config['region_name'] = str(self.get_option('DEFAULT',
                                                                 'nova_region_name'))

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
        return (importutils.try_import('neutronclient', False) and
                importutils.try_import('novaclient', False))

    def has_option(self, section, option):
        return option in self.conf.get(section)

    def get_option(self, section, option):
        return self.conf.get(section).get(option)
