#!/usr/bin/env python
# (C) Copyright 2015-2018 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
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

""" Detect running daemons then configure and start the agent.
"""

import argparse
from glob import glob
import json
import logging
import os
import pwd
import socket
import subprocess
import sys


from monasca_setup import agent_config
from monasca_setup.service.detection import detect_init
import monasca_setup.utils as utils
from monasca_setup.utils import write_template

LOG = logging.getLogger(__name__)

CUSTOM_PLUGIN_PATH = '/usr/lib/monasca/agent/custom_detect.d'
# dirname is called twice to get the dir 1 above the location of the script
PREFIX_DIR = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Configure and setup the agent. In a full run it will' +
        ' detect running daemons then configure and start the agent.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    args = parse_arguments(parser)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO,
                            format="%(levelname)s: %(message)s")

    if args.dry_run:
        LOG.info("Running in dry run mode, no changes will be made only"
                 " reported")

    # Skip agent service detection if only installing plugins
    if not args.install_plugins_only:
        # Detect and if possibly enable the agent service
        agent_service = detect_init(PREFIX_DIR, args.config_dir, args.log_dir,
                                    args.template_dir, username=args.user,
                                    name=args.agent_service_name)

    # Skip base setup if only installing plugins or running specific detection
    # plugins
    if not args.install_plugins_only and args.detection_plugins is None:
        if not args.skip_enable:
            agent_service.enable()

        # Verify required options
        if (args.username is None or
                args.password is None or
                args.keystone_url is None):
            LOG.error('Username, password and keystone_url are required when'
                      ' running full configuration.')
            parser.print_help()
            sys.exit(1)
        base_configuration(args)

    # Collect the set of detection plugins to run
    detected_plugins = utils.discover_plugins(CUSTOM_PLUGIN_PATH)
    if args.system_only:
        from monasca_setup.detection.plugins.system import System
        plugins = [System]
    elif args.detection_plugins is not None:
        plugins = utils.select_plugins(args.detection_plugins,
                                       detected_plugins)
    elif args.skip_detection_plugins is not None:
        plugins = utils.select_plugins(args.skip_detection_plugins,
                                       detected_plugins, skip=True)
    else:
        plugins = detected_plugins
    plugin_names = [p.__name__ for p in plugins]

    # Remove entries for each plugin from the various plugin config files.
    if args.remove_matching_args:
        LOG.debug("Calling remove configuration for matching arguments.")
        changes = remove_config_for_matching_args(args, plugin_names)
    elif args.remove:
        changes = remove_config(args, plugin_names)
    else:
        # Run detection for all the plugins, halting on any failures if plugins
        # were specified in the arguments
        detected_config = plugin_detection(plugins, args.template_dir,
                                           args.detection_args,
                                           args.detection_args_json,
                                           skip_failed=(args.detection_plugins
                                                        is None))
        if detected_config is None:
            # Indicates detection problem, skip remaining steps and give
            # non-zero exit code
            return 1

        changes = modify_config(args, detected_config)

    # Don't restart if only doing detection plugins and no changes found
    if args.detection_plugins is not None and not changes:
        LOG.info(
            'No changes found for plugins {0}, skipping restart of'
            'Monasca Agent'.format(plugin_names))
        return 0
    elif args.dry_run:
        LOG.info('Running in dry mode, skipping changes and restart of'
                 ' Monasca Agent')
        return 0

    # Now that the config is built, start the service
    if args.install_plugins_only:
        LOG.info('Command line option install_plugins_only set, skipping '
                 'service (re)start.')
    else:
        try:
            agent_service.start(restart=True)
        except subprocess.CalledProcessError:
            LOG.error('The service did not startup correctly see %s',
                      args.log_dir)


def base_configuration(args):
    """Write out the primary Agent configuration and setup the service.

    :param args: Arguments from the command line
    :return: None
    """
    stat = pwd.getpwnam(args.user)

    uid = stat.pw_uid
    gid = stat.pw_gid

    # Write the main agent.yaml - Note this is always overwritten
    LOG.info('Configuring base Agent settings.')
    dimensions = {}
    # Join service in with the dimensions
    if args.service:
        dimensions.update({'service': args.service})
    if args.dimensions:
        dimensions.update(dict(item.strip().split(":")
                               for item in args.dimensions.split(",")))

    args.dimensions = dict((name, value)
                           for (name, value) in dimensions.items())
    write_template(os.path.join(args.template_dir, 'agent.yaml.template'),
                   os.path.join(args.config_dir, 'agent.yaml'),
                   {'args': args, 'hostname': socket.getfqdn()},
                   group=gid,
                   user=uid,
                   is_yaml=True)


def modify_config(args, detected_config):
    """Compare existing and detected config for each check plugin and write out
       the plugin config if there are changes
    """
    modified_config = False

    for detection_plugin_name, new_config in detected_config.items():
        if args.overwrite:
            modified_config = True
            if args.dry_run:
                continue
            else:
                agent_config.save_plugin_config(
                    args.config_dir, detection_plugin_name, args.user,
                    new_config)
        else:
            config = agent_config.read_plugin_config_from_disk(
                args.config_dir, detection_plugin_name)
            # merge old and new config, new has precedence
            if config is not None:
                # For HttpCheck, if the new input url has the same host and
                # port but a different protocol comparing with one of the
                # existing instances in http_check.yaml, we want to keep the
                # existing http check instance and replace the url with the
                # new protocol. If name in this instance is the same as the
                # url, we replace name with new url too.
                # For more details please see:
                # monasca-agent/docs/DeveloperDocs/agent_internals.md
                if detection_plugin_name == "http_check":
                    # Save old http_check urls from config for later comparison
                    config_urls = [i['url'] for i in config['instances'] if
                                   'url' in i]

                    # Check endpoint change, use new protocol instead
                    # Note: config is possibly changed after running
                    # check_endpoint_changes function.
                    config = agent_config.check_endpoint_changes(new_config,
                                                                 config)

                agent_config.merge_by_name(new_config['instances'],
                                           config['instances'])
                # Sort before compare, if instances have no name the sort will
                #  fail making order changes significant
                try:
                    new_config['instances'].sort(key=lambda k: k['name'])
                    config['instances'].sort(key=lambda k: k['name'])
                except Exception:
                    pass

                if detection_plugin_name == "http_check":
                    new_config_urls = [i['url'] for i in new_config['instances']
                                       if 'url' in i]
                    # Don't write config if no change
                    if new_config_urls == config_urls and new_config == config:
                        continue
                else:
                    if new_config == config:
                        continue
            modified_config = True
            if args.dry_run:
                LOG.info("Changes would be made to the config file for the {0}"
                         " check plugin".format(detection_plugin_name))
            else:
                agent_config.save_plugin_config(
                    args.config_dir, detection_plugin_name, args.user,
                    new_config)
    return modified_config


def validate_positive(value):
    int_value = int(value)
    if int_value <= 0:
        raise argparse.ArgumentTypeError("%s must be greater than zero" %
                                         value)
    return int_value


def parse_arguments(parser):
    parser.add_argument(
        '-u',
        '--username',
        help="Username used for keystone authentication. " +
             "Required for basic configuration.")
    parser.add_argument(
        '-p',
        '--password',
        help="Password used for keystone authentication. " +
             "Required for basic configuration.")

    parser.add_argument(
        '--user_domain_id',
        help="User domain id for keystone authentication",
        default='')
    parser.add_argument(
        '--user_domain_name',
        help="User domain name for keystone authentication",
        default='')
    parser.add_argument(
        '--keystone_url',
        help="Keystone url. Required for basic configuration.")
    parser.add_argument(
        '--project_name',
        help="Project name for keystone authentication",
        default='')
    parser.add_argument(
        '--project_domain_id',
        help="Project domain id for keystone authentication",
        default='')
    parser.add_argument(
        '--project_domain_name',
        help="Project domain name for keystone authentication",
        default='')
    parser.add_argument(
        '--project_id',
        help="Keystone project id  for keystone authentication",
        default='')
    parser.add_argument(
        '--monasca_url',
        help="Monasca API url, if not defined the url is pulled from keystone",
        type=str,
        default='')
    parser.add_argument(
        '--service_type',
        help="Monasca API url service type in keystone catalog",
        default='')
    parser.add_argument(
        '--endpoint_type',
        help="Monasca API url endpoint type in keystone catalog",
        default='')
    parser.add_argument(
        '--region_name',
        help="Monasca API url region name in keystone catalog",
        default='')
    parser.add_argument(
        '--system_only',
        help="Setup the service but only configure the base config and system " +
        "metrics (cpu, disk, load, memory, network).",
        action="store_true",
        default=False)
    parser.add_argument(
        '-d',
        '--detection_plugins',
        nargs='*',
        help="Skip base config and service setup and only configure this " +
             "space separated list. " +
             "This assumes the base config has already run.")
    parser.add_argument(
        '--skip_detection_plugins', nargs='*',
        help="Skip detection for all plugins in this space separated list.")
    detection_args_group = parser.add_mutually_exclusive_group()
    detection_args_group.add_argument(
        '-a',
        '--detection_args',
        help="A string of arguments that will be passed to detection " +
        "plugins. Only certain detection plugins use arguments.")
    detection_args_group.add_argument(
        '-json',
        '--detection_args_json',
        help="A JSON string that will be passed to detection plugins that parse JSON.")
    parser.add_argument('--check_frequency', help="How often to run metric collection in seconds",
                        type=validate_positive, default=30)
    parser.add_argument(
        '--num_collector_threads',
        help="Number of Threads to use in Collector " +
        "for running checks",
        type=validate_positive,
        default=1)
    parser.add_argument(
        '--pool_full_max_retries',
        help="Maximum number of collection cycles where all of the threads " +
        "in the pool are still running plugins before the " +
        "collector will exit and be restart",
        type=validate_positive,
        default=4)
    parser.add_argument(
        '--plugin_collect_time_warn',
        help="Number of seconds a plugin collection time exceeds " +
        "that causes a warning to be logged for that plugin",
        type=validate_positive,
        default=6)
    parser.add_argument(
        '--dimensions',
        help="Additional dimensions to set for all metrics. A comma separated list " +
        "of name/value pairs, 'name:value,name2:value2'")
    parser.add_argument(
        '--ca_file',
        help="Sets the path to the ca certs file if using certificates. " +
        "Required only if insecure is set to False",
        default='')
    parser.add_argument(
        '--insecure',
        help="Set whether certificates are used for Keystone authentication",
        default=False)
    parser.add_argument(
        '--config_dir',
        help="Configuration directory",
        default='/etc/monasca/agent')
    parser.add_argument(
        '--log_dir',
        help="monasca-agent log directory",
        default='/var/log/monasca/agent')
    parser.add_argument(
        '--log_level',
        help="monasca-agent logging level (ERROR, WARNING, INFO, DEBUG)",
        required=False,
        default='WARN')
    parser.add_argument('--template_dir', help="Alternative template directory",
                        default=os.path.join(PREFIX_DIR, 'share/monasca/agent'))
    parser.add_argument('--overwrite',
                        help="Overwrite existing plugin configuration. " +
                             "The default is to merge. agent.yaml is always overwritten.",
                        action="store_true")
    parser.add_argument(
        '-r',
        '--remove',
        help="Rather than add the detected configuration remove it.",
        action="store_true",
        default=False)
    parser.add_argument(
        '--remove_matching_args',
        help="Remove any configuration that matches all of the supplied arguments."
             " Useful when removing a compute node but all the target_hostnames"
             " are not known.  Implies -r.",
        action="store_true",
        default=False)
    parser.add_argument(
        '--skip_enable',
        help="By default the service is enabled, " +
        "which requires the script run as root. Set this to skip that step.",
        action="store_true")
    parser.add_argument('--install_plugins_only', help="Only update plugin "
                        "configuration, do not configure services, users, etc."
                        " or restart services",
                        action="store_true")
    parser.add_argument('--user', help="User name to run monasca-agent as", default='mon-agent')
    parser.add_argument(
        '-s',
        '--service',
        help="Service this node is associated with, added as a dimension.")
    parser.add_argument(
        '--amplifier',
        help="Integer for the number of additional measurements to create. " +
        "Additional measurements contain the 'amplifier' dimension. " +
        "Useful for load testing; not for production use.",
        default=0)
    parser.add_argument('-v', '--verbose', help="Verbose Output", action="store_true")
    parser.add_argument(
        '--dry_run',
        help="Make no changes just report on changes",
        action="store_true")
    parser.add_argument('--max_buffer_size',
                        help="Maximum number of batches of measurements to"
                             " buffer while unable to communicate with monasca-api",
                        default=1000)
    parser.add_argument('--max_batch_size',
                        help="Maximum batch size of measurements to"
                             " write to monasca-api, 0 is no limit",
                        default=0)
    parser.add_argument('--max_measurement_buffer_size',
                        help="Maximum number of measurements to buffer when unable to communicate"
                             " with the monasca-api",
                        default=-1)
    parser.add_argument('--backlog_send_rate',
                        help="Maximum number of buffered batches of measurements to send at"
                             " one time when connection to the monasca-api is restored",
                        default=1000)
    parser.add_argument('--monasca_statsd_port',
                        help="Statsd daemon port number",
                        default=8125)
    parser.add_argument('--monasca_statsd_interval',
                        help="Statsd metric aggregation interval (seconds)",
                        default=20)
    parser.add_argument('--agent_service_name',
                        help="systemd/sysv service name of agent",
                        required=False,
                        default='monasca-agent')
    parser.add_argument('--enable_logrotate', help="Controls log file rotation", default=True)
    return parser.parse_args()


def plugin_detection(
        plugins,
        template_dir,
        detection_args,
        detection_args_json,
        skip_failed=True,
        remove=False):
    """Runs the detection step for each plugin in the list and returns the complete detected
    agent config.
    :param plugins: A list of detection plugin classes
    :param template_dir: Location of plugin configuration templates
    :param detection_args: Arguments passed to each detection plugin
    :param detection_args_json: Alternate json format for detection arguments, use one or the other
    :param skip_failed: When False any detection failure causes the run to halt and return None
    :param remove: When True will not log a message indicating the detected name is configuring
    :return: An agent_config instance representing the total configuration from all detection
             plugins run.
    """
    plugin_config = agent_config.Plugins()
    if detection_args_json:
        json_data = json.loads(detection_args_json)
    for detect_class in plugins:
        # todo add option to install dependencies
        if detection_args_json:
            detect = detect_class(template_dir, False, **json_data)
        else:
            detect = detect_class(template_dir, False, detection_args)
        if detect.available:
            new_config = detect.build_config_with_name()
            if not remove:
                LOG.info('Configuring {0}'.format(detect.name))
            if new_config is not None:
                plugin_config.merge(new_config)
        elif not skip_failed:
            LOG.warning("Failed detection of plugin %s."
                        "\n\tPossible causes: Service not found or missing arguments. "
                        "\n\tFor services, the service is required to be running at "
                        "detection time. For other plugins, check the args (paths, "
                        "urls, etc)."
                        "\n\tDetection may also fail if monasca-agent services "
                        "(statsd, forwarder, collector) are not running.", detect.name)
            return None

    return plugin_config


def remove_config(args, plugin_names):
    """Parse all configuration removing any configuration built by plugins in plugin_names
       Note there is no concept of overwrite for removal.
    :param args: specified arguments
    :param plugin_names: A list of the plugin names to remove from the config
    :return: True if changes, False otherwise
    """
    changes = False
    existing_config_files = _get_config_yaml_files(args.config_dir)
    if existing_config_files == []:
        LOG.warning("Found no existing configuration files, no changes will be made!")
    detected_plugins = utils.discover_plugins(CUSTOM_PLUGIN_PATH)
    plugins = utils.select_plugins(args.detection_plugins, detected_plugins)
    LOG.debug("Plugins selected: %s", plugins)

    if args.detection_args or args.detection_args_json:
        detected_config = plugin_detection(
            plugins, args.template_dir, args.detection_args, args.detection_args_json,
            skip_failed=(args.detection_plugins is None), remove=True)
    LOG.debug("Detected configuration: %s", detected_config)

    for file_path in existing_config_files:
        deletes = False
        plugin_name = os.path.splitext(os.path.basename(file_path))[0]
        config = agent_config.read_plugin_config_from_disk(args.config_dir, plugin_name)
        # To avoid odd issues from iterating over a list you delete from, build a new instead
        new_instances = []
        if args.detection_args is None:
            # JSON version of detection_args
            for inst in config['instances']:
                if 'built_by' in inst and inst['built_by'] in plugin_names:
                    LOG.debug("Removing %s", inst)
                    changes = True
                    deletes = True
                    continue
                new_instances.append(inst)
            config['instances'] = new_instances
        else:
            for detected_key in detected_config.keys():
                for inst in detected_config[detected_key]['instances']:
                    if inst in config['instances']:
                        LOG.debug("Removing %s", inst)
                        changes = True
                        deletes = True
                        config['instances'].remove(inst)
        # TODO(joadavis) match dry-run functionality like in modify_config
        if deletes:
            agent_config.delete_from_config(args, config, file_path,
                                            plugin_name)
    return changes


def remove_config_for_matching_args(args, plugin_names):
    """Parse all configuration removing any configuration built by plugins in plugin_names
       Will use the generated config fields to match against the stored configs
       Intended for use when removing all config for a deleted compute host.  May delete
       more than intended in other uses, so be cautious.
       Note there is no concept of overwrite for removal.
    :param args: specified arguments. detection_args or detection_args_json are Required.
    :param plugin_names: A list of the plugin names to remove from the config
    :return: True if changes, False otherwise
    """
    changes = False
    existing_config_files = _get_config_yaml_files(args.config_dir)
    if existing_config_files == []:
        LOG.warning("Found no existing configuration files, no changes will be made!")
    detected_plugins = utils.discover_plugins(CUSTOM_PLUGIN_PATH)
    plugins = utils.select_plugins(args.detection_plugins, detected_plugins)
    LOG.debug("Plugins selected: %s", plugins)

    if args.detection_args or args.detection_args_json:
        detected_config = plugin_detection(
            plugins, args.template_dir, args.detection_args, args.detection_args_json,
            skip_failed=(args.detection_plugins is None), remove=True)
    else:
        # this method requires detection_args
        LOG.warning("Removing a configuration for matching arguments requires"
                    " arguments. No changes to configuration will be made!")
        return changes
    LOG.debug("Detected configuration: %s", detected_config)

    for file_path in existing_config_files:
        deletes = False
        plugin_name = os.path.splitext(os.path.basename(file_path))[0]
        config = agent_config.read_plugin_config_from_disk(args.config_dir, plugin_name)
        # To avoid odd issues from iterating over a list you delete from, build a new instead
        new_instances = []
        if args.detection_args is None:
            # using detection_args_json
            LOG.error("Only key-value argument format is currently supported for removing "
                      "matching configuration. JSON format is not yet supported. "
                      "No changes to configuration will be made!")
            return False
        else:
            # here is where it will differ from remove_config()
            # detected_config = generated based on args, config = read from disk
            # for each field in the detected_config instance, check it matches the one on disk
            # note that the one on disk is allowed to have more fields
            for exist_inst in config['instances']:
                for detected_key in detected_config.keys():
                    for detected_inst in detected_config[detected_key]['instances']:
                        if len(detected_inst.keys()) < 1:
                            new_instances.append(exist_inst)
                            continue
                        needs_delete = True
                        for detect_inst_key in detected_inst.keys():
                            if detect_inst_key in exist_inst.keys():
                                if detected_inst[detect_inst_key] != exist_inst[detect_inst_key]:
                                    needs_delete = False
                            else:
                                # not a match
                                needs_delete = False
                                continue
                        if needs_delete:
                            LOG.debug("Removing configuration %s", exist_inst)
                            changes = True
                            deletes = True
                            continue
                        new_instances.append(exist_inst)
            config['instances'] = new_instances
        # TODO(joadavis) match dry-run functionality like in modify_config
        if deletes:
            agent_config.delete_from_config(args, config, file_path,
                                            plugin_name)
    return changes


# helper function to make mock testing easier
def _get_config_yaml_files(config_dir):
    return glob(os.path.join(config_dir, 'conf.d', '*.yaml'))


if __name__ == "__main__":
    sys.exit(main())
