"""Classes implementing different methods for running monasca-agent on startup as well as starting the process immediately.

"""
import psutil


class Service(object):

    """Abstract base class implementing the interface for various service types.

    """

    def __init__(self, prefix_dir, config_dir, log_dir, name='monasca-agent'):
        self.prefix_dir = prefix_dir
        self.config_dir = config_dir
        self.log_dir = log_dir
        self.name = name

    def enable(self):
        """Sets monasca-agent to start on boot.

            Generally this requires running as super user
        """
        raise NotImplementedError

    def start(self, restart=True):
        """Starts monasca-agent.

            If the agent is running and restart is True, restart
        """
        raise NotImplementedError

    def stop(self):
        """Stops monasca-agent.

        """
        raise NotImplementedError

    def is_enabled(self):
        """Returns True if monasca-agent is setup to start on boot, false otherwise.

        """
        raise NotImplementedError

    @staticmethod
    def is_running():
        """Returns True if monasca-agent is running, false otherwise.

        """
        # Looking for the supervisor process not the individual components
        for process in psutil.process_iter():
            if '/etc/monasca/agent/supervisor.conf' in process.cmdline():
                return True

        return False
