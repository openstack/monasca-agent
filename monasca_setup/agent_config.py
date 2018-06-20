# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
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

"""Classes to aid in configuration of the agent."""

import collections
import logging
import os
import pwd
import yaml

log = logging.getLogger(__name__)


class Plugins(collections.defaultdict):

    """A container for the plugin configurations used by the monasca-agent.

        This is essentially a defaultdict(dict) but put into a class primarily to make the
        interface clear, also to add a couple of helper methods.
        Each plugin config is stored with the key being its config name (excluding .yaml).
        The value a dict which will convert to yaml.
    """

    def __init__(self):
        super(Plugins, self).__init__(dict)

    # todo Possibly enforce the key being a string without .yaml in it.

    def diff(self, other_plugins):
        raise NotImplementedError

    def merge(self, other):
        """Do a deep merge with precedence going to other (as is the case with update).

        """
        # Implemented as a function so it can be used for arbitrary dictionaries not just self,
        # this is needed for the recursive nature of the merge.
        deep_merge(self, other)


def deep_merge(adict, other):
    """A recursive merge of two dictionaries including combining of any lists within the data
    structure.

    """
    for key, value in other.items():
        if key in adict:
            if isinstance(adict[key], dict) and isinstance(value, dict):
                deep_merge(adict[key], value)
            elif isinstance(adict[key], list) and isinstance(value, list):
                adict[key] += value
        else:
            adict[key] = value


def merge_by_name(first, second):
    """Merge a list of dictionaries replacing any dictionaries with the same 'name' value rather
    than merging.

    The precedence goes to first.
    """
    first_names = [i['name'] for i in first if 'name' in i]
    for item in second:
        if 'name' not in item or item['name'] not in first_names:
            first.append(item)


def read_plugin_config_from_disk(config_dir, plugin_name):
    """Reads from the Agent on disk configuration the config for a specific plugin
    :param config_dir: Monasca Agent configuration directory
    :param plugin_name: The name of the check plugin
    :return: Dictionary of parsed yaml content
    """
    config_path = os.path.join(config_dir, 'conf.d', plugin_name + '.yaml')
    config = None
    if os.path.exists(config_path):
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file.read())
    return config


def save_plugin_config(config_dir, plugin_name, user, conf):
    """Writes configuration for plugin_name to disk in the config_dir
    :param config_dir: Monasca Agent configuration directory
    :param plugin_name: The name of the check plugin
    :param user: The username Monasca-agent will run as
    :param conf: The value of the configuration to write to disk
    :return: None
    """
    config_path = os.path.join(config_dir, 'conf.d', plugin_name + '.yaml')

    with open(config_path, 'w') as config_file:
        # The gid is created on service activation which we assume has happened
        config_file.write((yaml.safe_dump(conf,
                                          encoding='utf-8',
                                          allow_unicode=True,
                                          default_flow_style=False)).decode('utf-8'))
    stat = pwd.getpwnam(user)

    gid = stat.pw_gid
    uid = stat.pw_uid

    os.chmod(config_path, 0o640)
    os.chown(config_path, uid, gid)


def check_endpoint_changes(value, config):
    """Change urls in config with same path but different protocols into new
       endpoints.
    """
    new_url = value['instances'][0]['url']
    old_urls = [i['url'] for i in config['instances'] if 'url' in i]
    new_path = new_url.split("://")[1]
    old_paths = [url.split("://")[1] for url in old_urls]
    for i, old_path in enumerate(old_paths):
        if old_path == new_path:
            if config['instances'][i]['url'] == config['instances'][i]['name']:
                config['instances'][i]['name'] = new_url
            config['instances'][i]['url'] = new_url
    return config


def delete_from_config(args, config, file_path, plugin_name):
    if args.dry_run:
        info_msg = ("Changes would be made to the config file {0}".format(file_path))
    else:
        if len(config['instances']) == 0:
            info_msg = ("Removing configuration file {0} it is no longer needed.".format(file_path))
            os.remove(file_path)
        else:
            info_msg = ("Saving changes to configuration file {0}.".format(file_path))
            save_plugin_config(args.config_dir, plugin_name, args.user, config)
    log.info(info_msg)
