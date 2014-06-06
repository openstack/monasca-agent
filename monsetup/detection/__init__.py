"""Classes for detection of running resources to be monitored.
    Detection classes should be platform independent
"""


class Plugin(object):
    """Abstract class implemented by the mon-agent plugin detection classes"""
    # todo these should include dependency detection

    def __init__(self, config_dir, overwrite=True):
        self.config_dir = config_dir
        self.dependencies = ()
        self.overwrite = overwrite
        self._detect()

    def _detect(self):
        """Run detection"""
        raise NotImplementedError

    def build_config(self):
        raise NotImplementedError

    def has_dependencies(self):
        raise NotImplementedError

    @property
    def name(self):
        """Return _name if set otherwise the class name"""
        if '_name' in self.__dict__:
            return self._name
        else:
            return self.__class__.__name__
