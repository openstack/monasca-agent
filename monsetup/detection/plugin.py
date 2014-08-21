"""Classes for detection of running resources to be monitored.

    Detection classes should be platform independent
"""


class Plugin(object):

    """Abstract class implemented by the monasca-agent plugin detection classes.

    """
    # todo these should include dependency detection

    def __init__(self, template_dir, overwrite=True, alarms=None):
        self.available = False
        self.template_dir = template_dir
        self.dependencies = ()
        self.overwrite = overwrite
        self.alarms = alarms
        self._detect()

    def _detect(self):
        """Run detection, set self.available True if the service is detected.

        """
        raise NotImplementedError

    def build_config(self):
        """Build the config as a Plugins object and return.

        """
        raise NotImplementedError

    def dependencies_installed(self):
        """Return True if dependencies are installed.

        """
        raise NotImplementedError

    @property
    def name(self):
        """Return _name if set otherwise the class name.

        """
        if '_name' in self.__dict__:
            return self._name
        else:
            return self.__class__.__name__
