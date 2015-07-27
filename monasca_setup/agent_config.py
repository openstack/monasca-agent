"""Classes to aid in configuration of the agent."""

import collections
import os
import pwd
import yaml


class Plugins(collections.defaultdict):

    """A container for the plugin configurations used by the monasca-agent.

        This is essentially a defaultdict(dict) but put into a class primarily to make the interface clear, also
        to add a couple of helper methods.
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
        # Implemented as a function so it can be used for arbitrary dictionaries not just self, this is needed
        # for the recursive nature of the merge.
        deep_merge(self, other)


def deep_merge(adict, other):
    """A recursive merge of two dictionaries including combining of any lists within the data structure.

    """
    for key, value in other.iteritems():
        if key in adict:
            if isinstance(adict[key], dict) and isinstance(value, dict):
                deep_merge(adict[key], value)
            elif isinstance(adict[key], list) and isinstance(value, list):
                adict[key] += value
        else:
            adict[key] = value


def merge_by_name(first, second):
    """Merge a list of dictionaries replacing any dictionaries with the same 'name' value rather than merging.
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
            config = yaml.load(config_file.read())
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
        config_file.write(yaml.safe_dump(conf,
                                         encoding='utf-8',
                                         allow_unicode=True,
                                         default_flow_style=False))
    gid = pwd.getpwnam(user).pw_gid
    os.chmod(config_path, 0o640)
    os.chown(config_path, 0, gid)
