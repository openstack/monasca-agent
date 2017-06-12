# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
# Copyright 2017 SUSE Linux GmbH

import logging
import os
import yaml

from monasca_setup import agent_config
from monasca_setup.detection import plugin
from monasca_setup.detection import utils

log = logging.getLogger(__name__)

_POSTFIX_PROC_NAME = 'postfix'
_POSTFIX_DIRECTORY = """/var/spool/postfix"""
_POSTFIX_CHECK_COMMAND = ('sudo -l -U {0} find %s/incoming '
                          '-type f > /dev/null' % _POSTFIX_DIRECTORY)
"""Command to verify if user running monasca-agent
 has sudo permission to access postfix directory"""


class Postfix(plugin.Plugin):
    """If postfix is running install the default config.
    """

    ERROR_MSG = 'postfix plugin will not be configured.'

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """

        try:
            has_process = (utils.find_process_cmdline(_POSTFIX_PROC_NAME)
                           is not None)
            agent_user = utils.get_agent_username() if has_process else None
            has_user = agent_user is not None
            has_sudoers = (self._has_sudoers(agent_user)
                           if agent_user else False)
        except Exception:
            self.available = False
            detailed_msg = ('Unexpected exception while '
                            'running postfix detection.')
            log.exception('%s\n%s' % (detailed_msg, self.ERROR_MSG))
        else:
            self.available = has_process and has_sudoers
            if not self.available:
                if not has_process:
                    detailed_msg = ('%s process was not found.'
                                    % _POSTFIX_PROC_NAME)
                    log.info('%s\n%s' % (detailed_msg, self.ERROR_MSG))
                elif not has_user:
                    detailed_msg = 'Did not locate agent\'s username.'
                    log.error('%s\n%s' % (detailed_msg, self.ERROR_MSG))
                elif not has_sudoers:
                    detailed_msg = ('%s cannot access %s directory. '
                                    '\n Refer to postfix plugin documentation '
                                    'for more details.'
                                    % (agent_user, _POSTFIX_DIRECTORY))
                    log.error('%s\n%s' % (detailed_msg, self.ERROR_MSG))

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        # A bit silly to parse the yaml only for it to be converted back but this
        # plugin is the exception not the rule
        with open(os.path.join(self.template_dir, 'conf.d/postfix.yaml.example'), 'r') as postfix_template:
            default_net_config = yaml.safe_load(postfix_template.read())
        config = agent_config.Plugins()
        config['postfix'] = default_net_config
        return config

    def dependencies_installed(self):
        return True

    @staticmethod
    def _has_sudoers(agent_user):
        test_sudo = os.system(_POSTFIX_CHECK_COMMAND.format(agent_user))
        return test_sudo == 0
