# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

"""Detection plugin for the existence of check_mk_agent, whose <<<local>>>
   check output may parsed for metrics."""

import logging
import monasca_setup.agent_config
import os

log = logging.getLogger(__name__)

# List common check_mk_agent locations
check_mk_agent_paths = ['/usr/bin/check_mk_agent',
                        '/usr/local/bin/check_mk_agent']


class CheckMKLocal(monasca_setup.detection.Plugin):
    """Identify existance of check_mk_agent by looking for the executable.
       The check_mk_agent process itself does not need to be running in order
       for this plugin to work, the agent program itself can return local data.
    """

    def _detect(self):
        self.agent_path = None
        for path in check_mk_agent_paths:
            if os.path.isfile(path):
                self.agent_path = path
                self.available = True

    def build_config(self):
        log.info("\tEnabling the check_mk_local plugin")
        config = monasca_setup.agent_config.Plugins()
        config['check_mk_local'] = {'init_config': {'mk_agent_path': self.agent_path},
                                    'instances': [{}]}
        return config
