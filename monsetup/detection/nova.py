from . import Plugin
from monsetup import agent_config


class Nova(Plugin):
    """Detect Nova daemons and setup configuration to monitor them."""

    def _detect(self):
        """Run detection"""
        self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        return agent_config.Plugins()

    def dependencies_installed(self):
        pass

