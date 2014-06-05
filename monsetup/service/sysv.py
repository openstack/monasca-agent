"""System V style service.
"""

from . import Service


class SysV(Service):
    def __init__(self, init_template):
        """Setup this service with the given init template"""
        super(SysV, self).__init__()
        self.init_template = init_template

    # todo largely unimplemented, all needed files end up in /usr/local/share/mon/agent
    # todo don't forget to setup the proper users for the agent to run as
    # todo will need to setup supervisor.con