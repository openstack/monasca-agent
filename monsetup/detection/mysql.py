from . import Plugin
from monsetup import agent_config


class MySQL(Plugin):
    """Detect MySQL daemons and setup configuration to monitor them."""

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        return agent_config.Plugins()

    def dependencies_installed(self):
        pass

