"""Classes to aid in configuration of the agent."""

import collections


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
