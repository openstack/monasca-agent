# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP

import ConfigParser
import logging

from monasca_agent.common.psutil_wrapper import psutil
import monasca_setup.agent_config
from monasca_setup.detection import Plugin
from monasca_setup.detection.utils import find_process_name


log = logging.getLogger(__name__)


class VCenter(Plugin):
    """Configures ESX Cluster monitoring through VCenter"""

    def _detect(self):
        """Method to detect the nova-compute service,
        if found set the nova.conf, the flags under vmware section will be used to
        configure the plugin, else the args are used to configure.
        """
        # Find the nova compute process and locate its conf
        process_exist = find_process_name('nova-compute') is not None
        # for cases where this plugin and nova-compute service runs separately
        # we will configure the plugin with given args.
        # so, we have to set these below variables
        self.nova_conf = self.get_nova_config_file() if process_exist else None
        has_config_file_or_args = (self.nova_conf is not None or
                                   self.args is not None)
        self.available = process_exist and has_config_file_or_args
        if not self.available:
            if not process_exist:
                log.error('Nova-compute process does not exist.')
            elif not has_config_file_or_args:
                log.error(('Nova-compute process exists but '
                           'the configuration file was not detected and no '
                           'arguments were given.'))

    def get_nova_config_file(self):
        nova_conf = None
        for proc in psutil.process_iter():
            try:
                cmd = proc.as_dict(['cmdline'])['cmdline']
                if len(cmd) > 2 and 'python' in cmd[0] and 'nova-compute' in cmd[1]:
                    params = [cmd.index(y) for y in cmd if 'hypervisor.conf' in y]
                    if not params:
                        # The configuration file is not found, skip
                        continue
                    else:
                        param = params[0]
                    if '=' in cmd[param]:
                        nova_conf = cmd[param].split('=')[1]
                    else:
                        nova_conf = cmd[param]
            except IOError:
                # Process has already terminated, ignore
                continue
        return nova_conf

    def build_config(self):
        """Build the config as a Plugins object and return back.
        """
        config = monasca_setup.agent_config.Plugins()

        if self.dependencies_installed():
            nova_cfg = ConfigParser.SafeConfigParser()
            instance = {}
            if self.nova_conf is None:
                log.warn("Nova compute configuration file was not found.")
                if self.args:
                    # read from arg list
                    instance = self._read_from_args(instance)
                else:
                    # get the default config format
                    instance = self._config_format()
            else:
                log.info("Using nova configuration file {0}".format(self.nova_conf))
                nova_cfg.read(self.nova_conf)
                cfg_section = 'vmware'

                # extract the vmware config from nova.conf and build instances
                if (nova_cfg.has_option(cfg_section, 'host_ip')
                        and nova_cfg.has_option(cfg_section, 'host_username')
                        and nova_cfg.has_option(cfg_section, 'host_password')
                        and nova_cfg.has_option(cfg_section, 'host_port')
                        and nova_cfg.has_option(cfg_section, 'cluster_name')):

                    instance = {
                        'vcenter_ip': nova_cfg.get(cfg_section, 'host_ip'),
                        'username': nova_cfg.get(cfg_section, 'host_username'),
                        'password': nova_cfg.get(cfg_section, 'host_password', raw=True),
                        'port': int(nova_cfg.get(cfg_section, 'host_port')),
                        'clusters': [nova_cfg.get(cfg_section, 'cluster_name')]
                    }
                else:
                    log.warn("One or more configuration parameters are missing"
                             " host_ip, host_username, host_password,"
                             " host_port, cluster_name")
                    # put default format
                    instance = self._config_format()
            config['vcenter'] = {'init_config': {},
                                 'instances': [instance]}
        return config

    def _config_format(self):
        """Default configuration format for vcenter plugin
        """
        instance = {'vcenter_ip': None,
                    'username': None,
                    'password': None,
                    'port': None,
                    'clusters': []}
        return instance

    def _read_from_args(self, instance):
        """Read the args and build the instance config
        """
        for arg in self.args:
            if arg == 'clusters':
                cls_lst = self.args[arg].split(',')
                instance[arg] = cls_lst
            else:
                instance[arg] = self.args[arg]
        return instance

    def dependencies_installed(self):
        """Import the dependencies.
        """
        return True
