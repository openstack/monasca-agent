# Copyright 2017 OrangeLabs
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import os

from six.moves import configparser

from monasca_agent.common.psutil_wrapper import psutil
import monasca_setup.agent_config
import monasca_setup.detection

log = logging.getLogger(__name__)

# Directory to use for metric caches
cache_dir = "/dev/shm"
# Enable vm congestion check
enable_vm = True
# Ensure that ECN marking is enabled
enable_ecn = True
# Smoothing factor used to compute ecn congestion rate
s_factor = 0.1
# Period of time in second to collect metrics
collect_period = 30
# Acceptable arguments
acceptable_args = ['username', 'password', 'project_name',
                   'auth_url', 'cache_dir', 'enable_vm', 'enable_ecn',
                   'region_name', 's_factor', 'collect_period']


class Congestion(monasca_setup.detection.Plugin):

    """Configures congestion detection plugin."""

    def _detect(self):
        """Run detection, set self.available True if the service is
           detected.
        """
        self.available = False
        # Start with plugin-specific configuration parameters
        # Try to detect the location of the Nova configuration file.
        # Walk through the list of processes, searching for 'nova-compute'
        # process with 'nova.conf' inside one of the parameters
        nova_conf = None
        for proc in psutil.process_iter():
            try:
                cmd = proc.as_dict(['cmdline'])['cmdline']
                if (len(cmd) > 2 and 'python' in cmd[0] and
                        'nova-compute' in cmd[1]):
                    conf_indexes = [cmd.index(y)
                                    for y in cmd if 'nova.conf' in y]
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
        """Build the config as a Plugins object and return.  """
        config = monasca_setup.agent_config.Plugins()
        log.info("Configuring congestion plugin")
        nova_cfg = configparser.SafeConfigParser()
        log.info("\tUsing nova configuration file {0}".format(self.nova_conf))
        nova_cfg.read(self.nova_conf)
        # Which configuration options are needed for the plugin YAML?
        # Use a dict so that they can be renamed later if necessary
        cfg_needed = {
            'username': 'username', 'password': 'password',
            'project_name': 'project_name'}
        cfg_section = 'keystone_authtoken'
        region_name_sec = 'neutron'
        init_config = {
            'cache_dir': cache_dir,
            'enable_vm': enable_vm,
            'enable_ecn': enable_ecn,
            's_factor': s_factor,
            'collect_period': collect_period}
        for option in cfg_needed:
            init_config[option] = nova_cfg.get(
                cfg_section, cfg_needed[option])
        init_config['region_name'] = nova_cfg.get(
            region_name_sec, 'region_name')
        # Create an identity URI (again, slightly different for Devstack)
        if nova_cfg.has_option(cfg_section, 'auth_url'):
            init_config['auth_url'] = nova_cfg.get(cfg_section, 'auth_url')
        else:
            init_config['auth_url'] = nova_cfg.get(
                cfg_section, 'identity_uri')

        config = monasca_setup.agent_config.Plugins()
        config['congestion'] = {
            'init_config': init_config, 'instances': []}
        return config

    def dependencies_installed(self):
        return True
