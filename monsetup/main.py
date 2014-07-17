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
from detection.plugins import kafka, mon, mysql, network, zookeeper
from detection.plugins import nova, glance, cinder, neutron, swift
from detection.plugins import keystone, ceilometer
from service import sysv

# List of all detection plugins to run
DETECTION_PLUGINS = [kafka.Kafka, mon.MonAPI, mon.MonPersister, mon.MonThresh, mysql.MySQL,
                     network.Network, nova.Nova, cinder.Cinder, swift.Swift, glance.Glance,
                     ceilometer.Ceilometer, neutron.Neutron, keystone.Keystone, zookeeper.Zookeeper]
# Map OS to service type
OS_SERVICE_MAP = {'linux': sysv.SysV}

log = logging.getLogger(__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Detect running daemons then configure and start the agent.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-u', '--username', help="Keystone username used to post metrics", required=True)
    parser.add_argument(
        '-p', '--password', help="Keystone password used to post metrics", required=True)
    parser.add_argument('--project_name', help="Keystone project/tenant name", required=True)
    parser.add_argument(
        '-s', '--service', help="Service this node is associated with.", required=True)
    parser.add_argument('--keystone_url', help="Keystone url", required=True)
    parser.add_argument('--monasca_url', help="Monasca API url", required=True)
    parser.add_argument('--config_dir', help="Configuration directory", default='/etc/monasca/agent')
    parser.add_argument('--log_dir', help="monasca-agent log directory", default='/var/log/monasca/agent')
    parser.add_argument(
        '--template_dir', help="Alternative template directory", default='/usr/local/share/monasca/agent')
    parser.add_argument('--headless', help="Run in a non-interactive mode", action="store_true")
    parser.add_argument('--overwrite',
                        help="Overwrite existing plugin configuration." +
                             "The default is to merge. Agent.conf is always overwritten.",
                        action="store_true")
    parser.add_argument('--skip_enable', help="By default the service is enabled," +
                                              " which requires the script run as root. Set this to skip that step.",
                        action="store_true")
    parser.add_argument('--user', help="User name to run monasca-agent as", default='monasca-agent')
    parser.add_argument('-v', '--verbose', help="Verbose Output", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Detect os
    detected_os = 'linux'  # todo add detection

    # Service enable, includes setup of users/config directories so must be
    # done before configuration
    agent_service = OS_SERVICE_MAP[detected_os](os.path.join(args.template_dir, 'monasca-agent.init'),
                                                args.config_dir,
                                                args.log_dir, username=args.user)
    if not args.skip_enable:
        agent_service.enable()

    gid = pwd.getpwnam(args.user).pw_gid
    # Write the main agent.conf - Note this is always overwritten
    log.info('Configuring base Agent settings.')
    agent_conf_path = os.path.join(args.config_dir, 'agent.conf')
    with open(os.path.join(args.template_dir, 'agent.conf.template'), 'r') as agent_template:
        with open(agent_conf_path, 'w') as agent_conf:
            agent_conf.write(agent_template.read().format(args=args, hostname=socket.gethostname()))
    os.chown(agent_conf_path, 0, gid)
    os.chmod(agent_conf_path, 0o640)
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
            plugin_config.merge(new_config)

        # todo add option to install dependencies

    # Write out the plugin config
    for key, value in plugin_config.iteritems():
        # todo if overwrite is set I should either warn or just delete any config files not in the new config
        # todo add the ability to show a diff before overwriting or merging config
        config_path = os.path.join(args.config_dir, 'conf.d', key + '.yaml')
        # merge old and new config, new has precedence
        if (not args.overwrite) and os.path.exists(config_path):
            with open(config_path, 'r') as config_file:
                old_config = yaml.load(config_file.read())
            if old_config is not None:
                agent_config.deep_merge(old_config, value)
                value = old_config
        with open(config_path, 'w') as config_file:
            os.chmod(config_path, 0o640)
            os.chown(config_path, 0, gid)
            config_file.write(yaml.dump(value))

    # Now that the config is build start the service
    try:
        agent_service.start(restart=True)
    except subprocess.CalledProcessError:
        log.error('The service did not startup correctly see %s' % args.log_dir)


if __name__ == "__main__":
    sys.exit(main())
