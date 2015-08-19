# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging

from plugin import Plugin


log = logging.getLogger(__name__)


class ArgsPlugin(Plugin):
    """Base plugin for detection plugins that take arguments for configuration rather than do detection."""

    def _build_instance(self, arg_list):
        """If a value for each arg in the arg_list was specified build it into an instance dictionary. Also check for dimensions and add if they were specified.
        :param arg_list: Arguments to include
        :return: instance dictionary
        """
        instance = {}
        if 'dimensions' in self.args:
            instance['dimensions'] = dict(item.strip().split(":") for item in self.args['dimensions'].split(","))
        for arg in arg_list:
            if arg in self.args:
                instance[arg] = self.args[arg]
        return instance

    def _check_required_args(self, arg_list):
        """Check that the required args were specified
        :param arg_list: A list of arguments to verify were specified
        :return: True if the required args exist false otherwise
        """
        if self.args is None:
            return False
        for arg in arg_list:
            if arg not in self.args:
                return False
        return True

    def dependencies_installed(self):
        return True
