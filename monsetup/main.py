#!/usr/bin/env python
""" Detect running daemons then configure and start the agent.
"""

import argparse
import logging
import os
import pwd
import socket
import subprocess
import sys
import yaml

import agent_config
from detection import mysql, network, nova
from service import sysv

# List of all detection plugins to run
DETECTION_PLUGINS = [mysql.MySQL, network.Network, nova.Nova]
# Map OS to service type
OS_SERVICE_MAP = {'linux': sysv.SysV}

log = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Detect running daemons then configure and start the agent.')
    parser.add_argument('-u', '--username', help="Keystone username used to post metrics", required=True)
    parser.add_argument('-p', '--password', help="Keystone password used to post metrics", required=True)
    parser.add_argument('-s', '--service', help="Service this node is associated with.", required=True)
    parser.add_argument('--keystone_url', help="Keystone url", required=True)
    parser.add_argument('--mon_url', help="Mon API url", required=True)
    parser.add_argument('--config_dir', help="Configuration directory", default='/etc/mon-agent')
    parser.add_argument('--log_dir', help="mon-agent log directory", default='/var/log/mon-agent')
    parser.add_argument('--template_dir', help="Alternative template directory", default='/usr/local/share/mon/agent')
    parser.add_argument('--headless', help="Run in a non-interactive mode", action="store_true")
    parser.add_argument('--overwrite',
                        help="Overwrite existing plugin configuration." +
                             "The default is to merge. Agent.conf is always overwritten.",
                        action="store_true")
    parser.add_argument('--skip_enable', help="By default the service is enabled," +
                                              " which requires the script run as root. Set this to skip that step.",
                        action="store_true")
    parser.add_argument('--user', help="User name to run mon-agent as", default='mon-agent')
    parser.add_argument('-v', '--verbose', help="Verbose Output", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Detect os
    detected_os = 'linux'  # todo add detection

    # Service enable, includes setup of config directories so must be done before configuration
    agent_service = OS_SERVICE_MAP[detected_os](os.path.join(args.template_dir, 'mon-agent.init'), args.config_dir,
                                                args.log_dir, username=args.user)
    if args.skip_enable:
        agent_service.enable()

    # Write the main agent.conf - Note this is always overwritten
    log.info('Configuring base Agent settings.')
    with open(os.path.join(args.template_dir, 'agent.conf.template'), 'r') as agent_template:
        with open(os.path.join(args.config_dir, 'agent.conf'), 'w') as agent_conf:
            agent_conf.write(agent_template.read().format(args=args, hostname=socket.gethostname()))
    # Link the supervisor.conf
    supervisor_path = os.path.join(args.config_dir, 'supervisor.conf')
    if os.path.exists(supervisor_path):
        os.remove(supervisor_path)
    os.symlink(os.path.join(args.template_dir, 'supervisor.conf'), supervisor_path)

    # Run through detection and config building for the plugins
    plugin_config = agent_config.Plugins()
    for detect_class in DETECTION_PLUGINS:
        detect = detect_class(args.template_dir, args.overwrite)
        if detect.available:
            log.info('Configuring {0}'.format(detect.name))
            new_config = detect.build_config()
            plugin_config.update(new_config)

        #todo add option to install dependencies

    # Write out the plugin config
    for key, value in plugin_config.iteritems():
        # todo if overwrite is set I should either warn or just delete any config files not in the new config
        # todo add the ability to show a diff before overwriting or merging config
        config_path = os.path.join(args.config_dir, 'conf.d', key + '.yaml')
        if (not args.overwrite) and os.path.exists(config_path):  # merge old and new config, new has precedence
            with open(config_path, 'r') as config_file:
                old_config = yaml.load(config_file.read())
            if old_config is not None:
                value = old_config.update(value)
        with open(config_path, 'w') as config_file:
            os.chmod(config_path, 0640)
            os.chown(config_path, 0, pwd.getpwnam(args.user).pw_uid)
            config_file.write(yaml.dump(value))

    # Now that the config is build start the service
    try:
        agent_service.start(restart=True)
    except subprocess.CalledProcessError:
        log.error('The service did not startup correctly see %s' % args.log_dir)


if __name__ == "__main__":
    sys.exit(main())