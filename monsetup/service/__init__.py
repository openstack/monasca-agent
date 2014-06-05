"""Classes implementing different methods for running mon-agent on startup as well as starting the process immediately
"""


class Service(object):
    """Abstract base class implementing the interface for various service types."""
    def __init__(self, name='mon-agent'):
        self.name = name

    def enable(self):
        """Sets mon-agent to start on boot.
            Generally this requires running as super user
        """
        raise NotImplementedError

    def start(self, restart=True):
        """Starts mon-agent
            If the agent is running and restart is True, restart
        """
        raise NotImplementedError

    def stop(self):
        """Stops mon-agent
        """
        raise NotImplementedError

    def is_enabled(self):
        """Returns True if mon-agent is setup to start on boot, false otherwise
        """
        raise NotImplementedError

    def is_running(self):
        """Returns True if mon-agent is running, false otherwise
        """
        raise NotImplementedError
