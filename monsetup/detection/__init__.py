"""Classes for detection of running resources to be monitored.
    Detection classes should be platform independent
"""


class Base(object):
    """Base detection class implementing the interface."""

    def __init__(self, config_dir, overwrite=True):
        self.config_dir = config_dir
        self.overwrite = overwrite

    def build_config(self):
        raise NotImplementedError


class Core(Base):
    """Detect details related to the core mon-agent configuration."""


class Plugin(Base):
    """Abstract class implemented by the mon-agent plugin detection classes"""
    # todo these should include dependency detection