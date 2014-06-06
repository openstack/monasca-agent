#!/usr/bin/env python
""" Detect running daemons then configure and start the agent.
"""

import argparse
import logging
import os
import socket
import subprocess
import sys

from detection import network, nova
from service import sysv

# List of all detection plugins to run
DETECTION_PLUGINS = [network.Network, nova.Nova]
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
    parser.add_argument('--config_dir', help="Alternative configuration directory", default='/etc/mon-agent')
    parser.add_argument('--template_dir', help="Alternative template directory", default='/usr/local/share/mon/agent')
    parser.add_argument('--headless', help="Run in a non-interactive mode", action="store_true")
    parser.add_argument('--overwrite', help="Overwrite existing configuration", action="store_true")
    parser.add_argument('-v', '--verbose', help="Verbose Output", action="store_true")
    #todo provide an option to exclude certain detection plugins
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # todo implement a way to include some predefined configuration, useful for active checks
    # todo if overwrite is set I should either warn or just delete any config files not in the new config
    # todo add the ability to build the config in a temp dir then diff

    # Detect os
    detected_os = 'linux'  # todo add detection

    # Service enable, includes setup of config directories so must be done before configuration
    # todo is there a better place for basic directories to be made then the service enabling?
    agent_service = OS_SERVICE_MAP[detected_os](os.path.join(args.template_dir, 'mon-agent.init'), args.config_dir)
    # Todo add logic for situations where either enable or start is not needed or if not running as root isn't possible
    agent_service.enable()

    # Write the main agent.conf
    log.info('Configuring base Agent settings.')
    agent_template = open(os.path.join(args.template_dir, 'agent.conf.template'), 'r')
    agent_conf = open(os.path.join(args.config_dir, 'agent.conf'), 'w')
    agent_conf.write(agent_template.read().format(args=args, hostname=socket.gethostname()))
    agent_template.close()
    agent_conf.close()
    # Link the supervisor.conf
    supervisor_path = os.path.join(args.config_dir, 'supervisor.conf')
    if os.path.exists(supervisor_path):
        os.remove(supervisor_path)
    os.symlink(os.path.join(args.template_dir, 'supervisor.conf'), supervisor_path)

    # Run through detection and config building for the plugins
    for detect_class in DETECTION_PLUGINS:
        detect = detect_class(args.config_dir, args.template_dir, args.overwrite)
        if detect.available:
            log.info('Configuring {0}'.format(detect.name))
            detect.build_config()
        #todo add option to install dependencies

    # Now that the config is build start the service
    try:
        agent_service.start(restart=True)
    except subprocess.CalledProcessError:
        log.error('The service did not startup correctly see /var/log/mon-agent')


if __name__ == "__main__":
    sys.exit(main())