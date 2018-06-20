# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

import glob
import imp
import inspect
import logging
import os
import sys
import yaml

from monasca_setup.detection import Plugin

log = logging.getLogger(__name__)


def discover_plugins(custom_path):
    """Find and import all detection plugins. It will look in detection/plugins dir of the code
    as well as custom_path

    :param custom_path: An additional path to search for detection plugins
    :return: A list of imported detection plugin classes.
    """

    # This was adapted from what monasca_agent.common.util.load_check_directory
    plugin_paths = glob.glob(
        os.path.join(
            os.path.dirname(
                os.path.realpath(__file__)),
            'detection/plugins',
            '*.py'))
    plugin_paths.extend(glob.glob(os.path.join(custom_path, '*.py')))

    plugins = []

    for plugin_path in plugin_paths:
        if os.path.basename(plugin_path) == '__init__.py':
            continue
        try:
            plugin = imp.load_source(
                os.path.splitext(
                    os.path.basename(plugin_path))[0],
                plugin_path)
        except Exception:
            log.exception('Unable to import detection plugin {0}'.format(plugin_path))
            continue

        # Verify this is a subclass of Plugin
        classes = inspect.getmembers(plugin, inspect.isclass)
        for _, clsmember in classes:
            if Plugin == clsmember:
                continue
            if issubclass(clsmember, Plugin):
                plugins.append(clsmember)

    return plugins


def select_plugins(plugin_names, plugin_list, skip=False):
    """:param plugin_names: A list of names
       :param plugin_list: A list of detection plugins classes
       :param skip: Inverts the behaviour by selecting only those plugins not in plugin_names
       :return: Returns a list of plugins from plugin_list that match plugin_names
    """
    lower_plugins = [p.lower() for p in plugin_names]
    plugins = []
    for plugin in plugin_list:
        selected = (plugin.__name__.lower() in lower_plugins)
        if selected != skip:
            plugins.append(plugin)

    if len(plugins) != len(plugin_names) and not skip:
        pnames = [p.__name__ for p in plugin_list]
        log.warn(
            "Not all plugins found, discovered plugins {0}\nAvailable plugins{1}".format(
                plugins,
                pnames))

    return plugins


def write_template(template_path,
                   out_path,
                   variables,
                   group,
                   user,
                   is_yaml=False):
    """Write a file using a simple python string template.
       Assumes 640 for the permissions and root:group for ownership.

    :param template_path: Location of the Template to use
    :param out_path: Location of the file to write
    :param variables: dictionary with key/value pairs to use in writing the template
    :param group: group to set as owner of config file
    :param user: user to set as owner of config file
    :param is_yaml: is configuration file in YAML format

    :return: None
    """
    if not os.path.exists(template_path):
        print("Error no template found at {0}".format(template_path))
        sys.exit(1)
    with open(template_path, 'r') as template:
        contents = template.read().format(**variables)
        with open(out_path, 'w') as conf:
            if is_yaml:
                conf.write((yaml.safe_dump(yaml.safe_load(contents),
                                           encoding='utf-8',
                                           allow_unicode=True,
                                           default_flow_style=False)).decode('utf-8'))
            else:
                conf.write(contents)

    os.chown(out_path, user, group)
    os.chmod(out_path, 0o640)
