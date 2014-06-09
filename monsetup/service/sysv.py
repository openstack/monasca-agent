"""System V style service.
"""
from glob import glob
import logging
import os
import pwd
import subprocess

from . import Service

log = logging.getLogger(__name__)


class SysV(Service):
    def __init__(self, init_template, config_dir, name='mon-agent', username='mon-agent'):
        """Setup this service with the given init template"""
        super(SysV, self).__init__(config_dir, name)
        self.init_script = '/etc/init.d/%s' % self.name
        self.init_template = init_template
        self.username = username

    def enable(self):
        """Sets mon-agent to start on boot.
            Generally this requires running as super user
        """
        # Create mon-agent user/group if needed
        try:
            user = pwd.getpwnam(self.username)
        except KeyError:
            subprocess.check_call(['useradd', '-r', self.username])
            user = pwd.getpwnam(self.username)

        # Create dirs
        # todo log dir is hardcoded
        for path in ('/var/log/mon-agent', self.config_dir, '%s/conf.d' % self.config_dir):
            if not os.path.exists(path):
                os.mkdir(path, 0755)
                os.chown(path, 'root', user.pw_gid)
        # the log dir needs to be writable by the user
        os.chown('/var/log/mon-agent', user.pw_uid, user.pw_gid)

        # link the init script, then enable
        if not os.path.exists(self.init_script):
            os.symlink(self.init_template, self.init_script)
            os.chmod(self.init_script, 0755)

        for runlevel in ['2', '3', '4', '5']:
            link_path = '/etc/rc%s.d/S10mon-agent' % runlevel
            if not os.path.exists(link_path):
                os.symlink(self.init_script, link_path)

        log.info('Enabled {0} service via SysV init script'.format(self.name))

    def start(self, restart=True):
        """Starts mon-agent
            If the agent is running and restart is True, restart
        """
        if not self.is_enabled():
            log.error('The service is not enabled')
            return False

        log.info('Starting {0} service via SysV init script'.format(self.name))
        subprocess.check_call([self.init_script, 'start'])  # Throws CalledProcessError on error
        return True

    def stop(self):
        """Stops mon-agent
        """
        if not self.is_enabled():
            log.error('The service is not enabled')
            return False

        log.info('Stopping {0} service via SysV init script'.format(self.name))
        subprocess.check_call([self.init_script, 'stop'])  # Throws CalledProcessError on error
        return True

    def is_enabled(self):
        """Returns True if mon-agent is setup to start on boot, false otherwise
        """
        if not os.path.exists(self.init_script):
            return False

        if len(glob('/etc/rc?.d/S??mon-agent')) > 0:
            return True
        else:
            return False

