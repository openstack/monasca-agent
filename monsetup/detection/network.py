import os
import shutil

from . import Plugin


class Network(Plugin):
    """No configuration here, working networking is assumed so this is either on or off.
    """

    def _detect(self):
        """Run detection"""
        self.available = True

    def build_config(self):
        """No detection just copy the config"""
        shutil.copyfile(os.path.join(self.template_dir, 'conf.d/network.yaml'),
                        os.path.join(self.config_dir, 'conf.d/network.yaml'))

    def dependencies_installed(self):
        return True
