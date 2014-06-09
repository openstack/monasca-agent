"""Classes to aid in configuration of the agent."""

import collections


class Plugins(collections.defaultdict):
    """A container for the plugin configurations used by the mon-agent.
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
