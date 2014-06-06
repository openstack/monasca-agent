from . import Plugin


class Nova(Plugin):
    """Detect Nova daemons and setup configuration to monitor them."""

    def _detect(self):
        """Run detection"""
        self.available = True

    def build_config(self):
        pass

    def dependencies_installed(self):
        pass

