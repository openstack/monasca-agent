"""System V style service.

"""
import glob
import logging
import os
import pwd
import subprocess

import service

log = logging.getLogger(__name__)


class SysV(service.Service):

    def __init__(self, prefix_dir, config_dir, log_dir, template_dir, name='monasca-agent', username='monasca-agent'):
        """Setup this service with the given init template.

        """
        super(SysV, self).__init__(prefix_dir, config_dir, log_dir, name)
        self.init_script = '/etc/init.d/%s' % self.name
        self.init_template = os.path.join(template_dir, 'monasca-agent.init.template')
        self.username = username

    def enable(self):
        """Sets monasca-agent to start on boot.

            Generally this requires running as super user
        """
        # Create monasca-agent user/group if needed
        try:
            user = pwd.getpwnam(self.username)
        except KeyError:
            subprocess.check_call(['useradd', '-r', self.username])
            user = pwd.getpwnam(self.username)

        # Create dirs
        # todo log dir is hardcoded
        for path in (self.log_dir, self.config_dir, '%s/conf.d' % self.config_dir):
            if not os.path.exists(path):
                os.makedirs(path, 0755)
                os.chown(path, 0, user.pw_gid)
        # the log dir needs to be writable by the user
        os.chown(self.log_dir, user.pw_uid, user.pw_gid)

        # Write the init script and enable.
        with open(self.init_template, 'r') as template:
            with open(self.init_script, 'w') as conf:
                conf.write(template.read().format(prefix=self.prefix_dir, config_dir=self.config_dir))
        os.chown(self.init_script, 0, 0)
        os.chmod(self.init_script, 0755)

        for runlevel in ['2', '3', '4', '5']:
            link_path = '/etc/rc%s.d/S10monasca-agent' % runlevel
            if not os.path.exists(link_path):
                os.symlink(self.init_script, link_path)

        log.info('Enabled {0} service via SysV init script'.format(self.name))

    def start(self, restart=True):
        """Starts monasca-agent.

            If the agent is running and restart is True, restart
        """
        if not self.is_enabled():
            log.error('The service is not enabled')
            return False

        log.info('Starting {0} service via SysV init script'.format(self.name))
        if restart:
            subprocess.check_call([self.init_script, 'restart'])  # Throws CalledProcessError on error
        else:
            subprocess.check_call([self.init_script, 'start'])  # Throws CalledProcessError on error
        return True

    def stop(self):
        """Stops monasca-agent.

        """
        if not self.is_enabled():
            log.error('The service is not enabled')
            return False

        log.info('Stopping {0} service via SysV init script'.format(self.name))
        subprocess.check_call([self.init_script, 'stop'])  # Throws CalledProcessError on error
        return True

    def is_enabled(self):
        """Returns True if monasca-agent is setup to start on boot, false otherwise.

        """
        if not os.path.exists(self.init_script):
            return False

        if len(glob.glob('/etc/rc?.d/S??monasca-agent')) > 0:
            return True
        else:
            return False
