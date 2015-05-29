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
from detection.utils import find_plugins
from service.detection import detect_init


log = logging.getLogger(__name__)

CUSTOM_PLUGIN_PATH = '/usr/lib/monasca/agent/custom_detect.d'
# dirname is called twice to get the dir 1 above the location of the script
PREFIX_DIR = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))


def write_template(template_path, out_path, variables, group, is_yaml=False):
    """ Write a file using a simple python string template.
        Assumes 640 for the permissions and root:group for ownership.
    :param template_path: Location of the Template to use
    :param out_path: Location of the file to write
    :param variables: dictionary with key/value pairs to use in writing the template
    :return: None
    """
    if not os.path.exists(template_path):
        print("Error no template found at {0}".format(template_path))
        sys.exit(1)
    with open(template_path, 'r') as template:
        contents = template.read().format(**variables)
        with open(out_path, 'w') as conf:
            if is_yaml:
                conf.write(yaml.safe_dump(yaml.safe_load(contents),
                                          encoding='utf-8',
                                          allow_unicode=True,
                                          default_flow_style=False))
            else:
                conf.write(contents)
    os.chown(out_path, 0, group)
    os.chmod(out_path, 0640)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Configure and setup the agent. In a full run it will detect running' +
                                                 ' daemons then configure and start the agent.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-u', '--username', help="Username used for keystone authentication. Required for basic configuration.")
    parser.add_argument(
        '-p', '--password', help="Password used for keystone authentication. Required for basic configuration.")
    parser.add_argument('--keystone_url', help="Keystone url. Required for basic configuration.")
    parser.add_argument('--project_name', help="Project name for keystone authentication", default='')
    parser.add_argument('--project_domain_id', help="Project domain id for keystone authentication", default='')
    parser.add_argument('--project_domain_name', help="Project domain name for keystone authentication", default='')
    parser.add_argument('--project_id', help="Keystone project id  for keystone authentication", default='')
    parser.add_argument('--monasca_url', help="Monasca API url, if not defined the url is pulled from keystone",
                        default='')
    parser.add_argument('--system_only', help="Setup the service but only configure the base config and system " +
                                              "metrics (cpu, disk, load, memory, network).",
                        action="store_true", default=False)
    parser.add_argument('-d', '--detection_plugins', nargs='*',
                        help="Skip base config and service setup and only configure this space separated list. " +
                             "This assumes the base config has already run.")
    parser.add_argument('-a', '--detection_args', help="A string of arguments that will be passed to detection " +
                                                       "plugins. Only certain detection plugins use arguments.")
    parser.add_argument('--check_frequency', help="How often to run metric collection in seconds", type=int, default=60)
    parser.add_argument('--dimensions', help="Additional dimensions to set for all metrics. A comma seperated list " +
                                             "of name/value pairs, 'name:value,name2:value2'")
    parser.add_argument('--ca_file', help="Sets the path to the ca certs file if using certificates. " +
                                          "Required only if insecure is set to False", default='')
    parser.add_argument('--insecure', help="Set whether certificates are used for Keystone authentication",
                        default=False)
    parser.add_argument('--config_dir', help="Configuration directory", default='/etc/monasca/agent')
    parser.add_argument('--log_dir', help="monasca-agent log directory", default='/var/log/monasca/agent')
    parser.add_argument('--log_level', help="monasca-agent logging level (ERROR, WARNING, INFO, DEBUG)", required=False,
                        default='WARN')
    parser.add_argument( '--template_dir', help="Alternative template directory",
                         default=os.path.join(PREFIX_DIR, 'share/monasca/agent'))
    parser.add_argument('--overwrite',
                        help="Overwrite existing plugin configuration. " +
                             "The default is to merge. agent.yaml is always overwritten.",
                        action="store_true")
    parser.add_argument('--skip_enable', help="By default the service is enabled, " +
                                              "which requires the script run as root. Set this to skip that step.",
                        action="store_true")
    parser.add_argument('--user', help="User name to run monasca-agent as", default='mon-agent')
    parser.add_argument('-s', '--service', help="Service this node is associated with, added as a dimension.")
    parser.add_argument('--amplifier', help="Integer for the number of additional measurements to create. " +
                                            "Additional measurements contain the 'amplifier' dimension. " +
                                            "Useful for load testing; not for production use.", default=0)
    parser.add_argument('-v', '--verbose', help="Verbose Output", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Detect and if possibly enable the agent service
    agent_service = detect_init(PREFIX_DIR, args.config_dir, args.log_dir, args.template_dir, username=args.user)

    if args.detection_plugins is None:  # Skip base setup if running specific detection plugins
        # Verify required options
        if args.username is None or args.password is None or args.keystone_url is None:
            log.error('Username, password and keystone_url are required when running full configuration.')
            parser.print_help()
            sys.exit(1)
        if not args.skip_enable:
            agent_service.enable()

        gid = pwd.getpwnam(args.user).pw_gid
        # Write the main agent.yaml - Note this is always overwritten
        log.info('Configuring base Agent settings.')
        dimensions = {}
        # Join service in with the dimensions
        if args.service:
            dimensions.update({'service': args.service})
        if args.dimensions:
            dimensions.update(dict(item.strip().split(":") for item in args.dimensions.split(",")))

        args.dimensions = dict((name, value) for (name, value) in dimensions.iteritems())
        write_template(os.path.join(args.template_dir, 'agent.yaml.template'),
                       os.path.join(args.config_dir, 'agent.yaml'),
                       {'args': args, 'hostname': socket.getfqdn()},
                       gid,
                       is_yaml=True)

        # Write the supervisor.conf
        write_template(os.path.join(args.template_dir, 'supervisor.conf.template'),
                       os.path.join(args.config_dir, 'supervisor.conf'),
                       {'prefix': PREFIX_DIR, 'log_dir': args.log_dir, 'monasca_user': args.user},
                       gid)

    # Run through detection and config building for the plugins
    plugin_config = agent_config.Plugins()
    detected_plugins = find_plugins(CUSTOM_PLUGIN_PATH)
    if args.system_only:
        from detection.plugins.system import System
        plugins = [System]
    elif args.detection_plugins is not None:
        lower_plugins = [p.lower() for p in args.detection_plugins]
        plugins = []
        for plugin in detected_plugins:
            if plugin.__name__.lower() in lower_plugins:
                plugins.append(plugin)

        if len(plugins) != len(args.detection_plugins):
            plugin_names = [p.__name__ for p in detected_plugins]
            log.warn("Not all plugins found, discovered plugins {0}\nAvailable plugins{1}".format(plugins,
                                                                                                  plugin_names))
    else:
        plugins = detected_plugins

    for detect_class in plugins:
        detect = detect_class(args.template_dir, args.overwrite, args.detection_args)
        if detect.available:
            log.info('Configuring {0}'.format(detect.name))
            new_config = detect.build_config()
            plugin_config.merge(new_config)
        elif args.detection_plugins is not None:  # Give a warning on failed detection when a plugin is called out
            log.warn('Failed detection of plugin {0}.'.format(detect.name) +
                     "\n\tPossible causes: Service not found or missing arguments.")

    # todo add option to install dependencies

    # Write out the plugin config
    changes = False
    # The gid is created on service activation which we assume has happened before this step or before running with -d
    gid = pwd.getpwnam(args.user).pw_gid
    for key, value in plugin_config.iteritems():
        # todo if overwrite is set I should either warn or just delete any config files not in the new config
        config_path = os.path.join(args.config_dir, 'conf.d', key + '.yaml')
        # merge old and new config, new has precedence
        if (not args.overwrite) and os.path.exists(config_path):
            with open(config_path, 'r') as config_file:
                old_config = yaml.load(config_file.read())
            if old_config is not None:
                agent_config.merge_by_name(value['instances'], old_config['instances'])
                # Sort before compare, if instances have no name the sort will fail making order changes significant
                try:
                    value['instances'].sort(key=lambda k: k['name'])
                    old_config['instances'].sort(key=lambda k: k['name'])
                except Exception:
                    pass
                if value == old_config:  # Don't write config if no change
                    continue
        with open(config_path, 'w') as config_file:
            changes = True
            os.chmod(config_path, 0640)
            os.chown(config_path, 0, gid)
            config_file.write(yaml.safe_dump(value,
                                             encoding='utf-8',
                                             allow_unicode=True,
                                             default_flow_style=False))

    # Don't restart if only doing detection plugins and no changes found
    if args.detection_plugins is not None and not changes:
        plugin_names = [p.__name__ for p in plugins]
        log.info('No changes found for plugins {0}, skipping restart of Monasca Agent'.format(plugin_names))
        return 0

    # Now that the config is built, start the service
    try:
        agent_service.start(restart=True)
    except subprocess.CalledProcessError:
        log.error('The service did not startup correctly see %s' % args.log_dir)


if __name__ == "__main__":
    sys.exit(main())
