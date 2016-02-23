# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

""" Systemd based service
"""
import glob
import logging
import os
import pwd
import subprocess

import service


log = logging.getLogger(__name__)


class LinuxInit(service.Service):
    """Parent class for all Linux based init systems.
    """
    def enable(self):
        """Does user/group directory creation.
        """
        # Create user/group if needed
        try:
            user = pwd.getpwnam(self.username)
        except KeyError:
            subprocess.check_call(['useradd', '-r', self.username])
            user = pwd.getpwnam(self.username)

        # Create dirs
        # todo log dir is hardcoded
        for path in (self.log_dir, self.config_dir, '%s/conf.d' % self.config_dir):
            if not os.path.exists(path):
                os.makedirs(path, 0o755)
                os.chown(path, 0, user.pw_gid)
        # the log dir needs to be writable by the user
        os.chown(self.log_dir, user.pw_uid, user.pw_gid)

    def start(self, restart=True):
        if not self.is_enabled():
            log.error('The service is not enabled')
            return False

    def stop(self):
        if not self.is_enabled():
            log.error('The service is not enabled')
            return True

    def is_enabled(self):
        """Returns True if monasca-agent is setup to start on boot, false otherwise.

        """
        raise NotImplementedError


class Systemd(LinuxInit):
    def enable(self):
        """Sets monasca-agent to start on boot.

            Generally this requires running as super user
        """
        LinuxInit.enable(self)

        # Write the systemd script
        init_path = '/etc/systemd/system/{0}.service'.format(self.name)
        with open(os.path.join(self.template_dir, 'monasca-agent.service.template'), 'r') as template:
            with open(init_path, 'w') as service_script:
                service_script.write(template.read().format(prefix=self.prefix_dir, monasca_user=self.username,
                                                            config_dir=self.config_dir))
        os.chown(init_path, 0, 0)
        os.chmod(init_path, 0o644)

        # Enable the service
        subprocess.check_call(['systemctl', 'daemon-reload'])
        subprocess.check_call(['systemctl', 'enable', '{0}.service'.format(self.name)])
        log.info('Enabled {0} service via systemd'.format(self.name))

    def start(self, restart=True):
        """Starts monasca-agent.

            If the agent is running and restart is True, restart
        """
        LinuxInit.start(self)
        log.info('Starting {0} service via systemd'.format(self.name))
        if restart:
            subprocess.check_call(['systemctl', 'restart', '{0}.service'.format(self.name)])
        else:
            subprocess.check_call(['systemctl', 'start', '{0}.service'.format(self.name)])

        return True

    def stop(self):
        """Stops monasca-agent.
        """
        LinuxInit.stop(self)
        log.info('Stopping {0} service'.format(self.name))
        subprocess.check_call(['systemctl', 'stop', '{0}.service'.format(self.name)])
        return True

    def is_enabled(self):
        """Returns True if monasca-agent is setup to start on boot, false otherwise.
        """
        try:
            subprocess.check_output(['systemctl', 'is-enabled', '{0}.service'.format(self.name)])
        except subprocess.CalledProcessError:
            return False

        return True


class SysV(LinuxInit):

    def __init__(self, prefix_dir, config_dir, log_dir, template_dir, username, name='monasca-agent'):
        """Setup this service with the given init template.

        """
        service.Service.__init__(self, prefix_dir, config_dir, log_dir, template_dir, name, username)
        self.init_script = '/etc/init.d/%s' % self.name
        self.init_template = os.path.join(template_dir, 'monasca-agent.init.template')

    def enable(self):
        """Sets monasca-agent to start on boot.

            Generally this requires running as super user
        """
        LinuxInit.enable(self)
        # Write the init script and enable.
        with open(self.init_template, 'r') as template:
            with open(self.init_script, 'w') as conf:
                conf.write(template.read().format(prefix=self.prefix_dir, monasca_user=self.username,
                                                  config_dir=self.config_dir))
        os.chown(self.init_script, 0, 0)
        os.chmod(self.init_script, 0o755)

        for runlevel in ['2', '3', '4', '5']:
            link_path = '/etc/rc%s.d/S10monasca-agent' % runlevel
            if not os.path.exists(link_path):
                os.symlink(self.init_script, link_path)

        log.info('Enabled {0} service via SysV init script'.format(self.name))

    def start(self, restart=True):
        """Starts monasca-agent.

            If the agent is running and restart is True, restart
        """
        LinuxInit.start(self)

        log.info('Starting {0} service via SysV init script'.format(self.name))
        if restart:
            subprocess.check_call([self.init_script, 'restart'])  # Throws CalledProcessError on error
        else:
            subprocess.check_call([self.init_script, 'start'])  # Throws CalledProcessError on error
        return True

    def stop(self):
        """Stops monasca-agent.

        """
        LinuxInit.stop(self)

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
