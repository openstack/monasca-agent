# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
# Copyright 2017 SUSE Linux GmbH
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
import pwd

from oslo_config import cfg
from oslo_utils import importutils

from monasca_setup import agent_config
from monasca_setup.detection import plugin
from monasca_setup.detection import utils


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
# The plugin will use the first functional command. 127.0.0.1 will be appended.
ping_options = [["/usr/bin/fping", "-n", "-c1", "-t250", "-q"],
                ["/sbin/fping", "-n", "-c1", "-t250", "-q"],
                ["/bin/ping", "-n", "-c1", "-w1", "-q"],
                ["/usr/bin/ping", "-n", "-c1", "-w1", "-q"]]
# Path to 'ip' command (needed to execute ping within network namespaces)
ip_cmd = "sudo /bin/ip"
# How many ping commands to run concurrently
default_max_ping_concurrency = 8
# Disk metrics can be collected at a larger interval than other vm metrics
default_disk_collection_period = 0
# VNIC metrics can be collected at a larger interval than other vm metrics
default_vnic_collection_period = 0

# Arguments which should be written as integers, not strings
INT_ARGS = ['disk_collection_period', 'vnic_collection_period',
            'max_ping_concurrency', 'nova_refresh', 'vm_probation']

_REQUIRED_OPTS = [
    {'opt': cfg.StrOpt('username'), 'group': 'keystone_authtoken'},
    {'opt': cfg.StrOpt('user_domain_name'), 'group': 'keystone_authtoken'},
    {'opt': cfg.StrOpt('password'), 'group': 'keystone_authtoken'},
    {'opt': cfg.StrOpt('project_name'), 'group': 'keystone_authtoken'},
    {'opt': cfg.StrOpt('project_domain_name'), 'group': 'keystone_authtoken'},
    {'opt': cfg.StrOpt('auth_url'), 'group': 'keystone_authtoken'}
]
"""Nova configuration opts required by this plugin"""


class Libvirt(plugin.Plugin):
    """Configures VM monitoring through Nova"""

    FAILED_DETECTION_MSG = 'libvirt plugin will not not be configured.'

    def _detect(self):
        """Set self.available True if the process and config file are detected
        """

        # NOTE(trebskit) bind each check we execute to another one
        # that way if X-one fails following won't be executed
        # and detection phase will end faster
        nova_proc = utils.find_process_name('nova-compute')
        has_deps = self.dependencies_installed() if nova_proc else None
        nova_conf = self._find_nova_conf(nova_proc) if has_deps else None
        has_cache_dir = self._has_cache_dir() if nova_conf else None
        agent_user = utils.get_agent_username() if has_cache_dir else None

        self.available = nova_conf and has_cache_dir
        if not self.available:
            if not nova_proc:
                detailed_message = '\tnova-compute process not found.'
                log.info('%s\n%s' % (detailed_message,
                                     self.FAILED_DETECTION_MSG))
            elif not has_deps:
                detailed_message = ('\tRequired dependencies were not found.\n'
                                    'Run pip install monasca-agent[libvirt] '
                                    'to install all dependencies.')
                log.warning('%s\n%s' % (detailed_message,
                                        self.FAILED_DETECTION_MSG))
            elif not has_cache_dir:
                detailed_message = '\tCache directory %s not found' % cache_dir
                log.warning('%s\n%s' % (detailed_message,
                                        self.FAILED_DETECTION_MSG))
            elif not nova_conf:
                detailed_message = ('\tnova-compute process was found, '
                                    'but it was impossible to '
                                    'read it\'s configuration.')
                log.warning('%s\n%s' % (detailed_message,
                                        self.FAILED_DETECTION_MSG))
        else:
            self.nova_conf = nova_conf
            self._agent_user = agent_user

    def build_config(self):
        """Build the config as a Plugins object and return back.
        """
        config = agent_config.Plugins()
        init_config = self._get_init_config()

        self._configure_ping(init_config)

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

    def _configure_ping(self, init_config):
        if self._agent_user is None:
            log.warn("\tUnable to determine agent user. Skipping ping checks.")
            return

        client = importutils.try_import('neutronclient.v2_0.client',
                                        False)
        if not client:
            log.warning(
                '\tpython-neutronclient module missing, '
                'required for ping checks.')
            return

        # Look for the best ping command
        for ping_cmd in ping_options:
            if os.path.isfile(ping_cmd[0]):
                init_config[
                    'ping_check'] = "{0} netns exec NAMESPACE {1}".format(
                        ip_cmd,
                        ' '.join(ping_cmd))
                log.info(
                    "\tEnabling ping checks using {0}".format(ping_cmd[0]))
                break
        if init_config['ping_check'] is False:
            log.warn('\tUnable to find suitable ping command, '
                     'disabling ping checks.')

    def dependencies_installed(self):
        return importutils.try_import('novaclient.client', False)

    def _get_init_config(self):
        keystone_auth_section = self.nova_conf['keystone_authtoken']
        init_config = {
            'cache_dir': cache_dir,
            'nova_refresh': nova_refresh,
            'metadata': metadata,
            'vm_probation': vm_probation,
            'customer_metadata': customer_metadata,
            'max_ping_concurrency': default_max_ping_concurrency,
            'disk_collection_period': default_disk_collection_period,
            'vnic_collection_period': default_vnic_collection_period,
            'vm_cpu_check_enable': True,
            'vm_disks_check_enable': True,
            'vm_network_check_enable': True,
            'vm_ping_check_enable': True,
            'vm_extended_disks_check_enable': False,
            'ping_check': False,
            'username': keystone_auth_section['username'],
            'user_domain_name': keystone_auth_section['user_domain_name'],
            'password': keystone_auth_section['password'],
            'project_name': keystone_auth_section['project_name'],
            'project_domain_name': keystone_auth_section['project_domain_name'],
            'auth_url': keystone_auth_section['auth_url']
        }
        return init_config

    @staticmethod
    def _has_cache_dir():
        return os.path.isdir(cache_dir)

    @staticmethod
    def _find_nova_conf(nova_process):
        try:
            nova_cmd = nova_process.as_dict(['cmdline'])['cmdline']
            return utils.load_oslo_configuration(from_cmd=nova_cmd,
                                                 in_project='nova',
                                                 for_opts=_REQUIRED_OPTS)
        except cfg.Error:
            log.exception('Failed to load nova configuration')
        return None

    @staticmethod
    def _get_user_uid_gid(username):
        stat = pwd.getpwnam(username)
        uid = stat.pw_uid
        gid = stat.pw_gid
        return uid, gid
