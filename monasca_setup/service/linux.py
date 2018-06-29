# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Systemd based service
"""
import logging
import os
import pwd
import subprocess

LOG = logging.getLogger(__name__)


class Systemd(object):
    """Manage service using systemd."""

    def __init__(self, prefix_dir, config_dir, log_dir, template_dir,
                 name='monasca-agent', username='mon-agent'):
        """Create a service."""
        self.prefix_dir = prefix_dir
        self.config_dir = config_dir
        self.log_dir = log_dir
        self.template_dir = template_dir
        self.name = name
        self.username = username

    def enable(self):
        """Set monasca-agent to start on boot.

        Generally this requires running as super user.
        """
        if os.geteuid() != 0:
            LOG.error('This service must be run as root')
            raise OSError

        # LinuxInit.enable(self)
        # Create user/group if needed
        try:
            user = pwd.getpwnam(self.username)
        except KeyError:
            subprocess.check_call(['useradd', '-r', self.username])
            user = pwd.getpwnam(self.username)

        # Create dirs
        for path in (self.log_dir, self.config_dir,
                     '%s/conf.d' % self.config_dir):
            if not os.path.exists(path):
                os.makedirs(path, 0o755)
                os.chown(path, 0, user.pw_gid)
        # log dir needs to be writable by the user
        os.chown(self.log_dir, user.pw_uid, user.pw_gid)

        # Get systemd services and target template
        templates = [f for f in os.listdir(self.template_dir)
                     if (f.endswith('service.template') or
                         f.endswith('target.template'))]
        systemd_path = '/etc/systemd/system/'

        # Write the systemd units configuration file: we have 3 services and
        # 1 target grouping all of them together
        for template_file_name in templates:
            service_file_name, e = os.path.splitext(template_file_name)
            service_file_path = os.path.join(systemd_path,
                                             service_file_name)
            with open(os.path.join(self.template_dir,
                      template_file_name), 'r') as template:
                with open(service_file_path, 'w') as service_file:
                    LOG.info('Creating service file %s', service_file_name)
                    service_file.write(template.read().
                                       format(prefix=self.prefix_dir,
                                              monasca_user=self.username))
            os.chown(service_file_path, 0, 0)
            os.chmod(service_file_path, 0o644)

        # Enable the service
        subprocess.check_call(['systemctl', 'daemon-reload'])
        subprocess.check_call(
            ['systemctl', 'enable', '{0}.target'.format(self.name)])
        LOG.info('Enabled %s target via systemd', self.name)

    def start(self, restart=True):
        """Start monasca-agent.

        If the agent is running and restart is True restart it.

        :return: True if monasca-agent is enabled on boot, False otherwise..
        """
        if not self.is_enabled():
            LOG.error('The service is not enabled')
            return False

        LOG.info('Starting %s services via systemd', self.name)
        if self.is_running() and restart:
            subprocess.check_call(
                ['systemctl', 'restart', '{0}.target'.format(self.name)])
        else:
            subprocess.check_call(
                ['systemctl', 'start', '{0}.target'.format(self.name)])
        return True

    def stop(self):
        """Stop monasca-agent.
        :return: True if monasca-agent was stopped successfully, False otherwise
        """
        LOG.info('Stopping %s services', self.name)
        try:
            subprocess.check_call(
                ['systemctl', 'stop', '{0}.target'.format(self.name)])
        except subprocess.CalledProcessError as call_error:
            LOG.error('Unable to stop monasca-agent.')
            LOG.error(call_error.output)
            return False
        else:
            return True

    def is_running(self):
        """Check if monasca-agent is running.

        :return: True if monasca-agent is running, false otherwise.
        """
        return(subprocess.call(['systemctl', 'is-active', '--quiet',
                               '{0}.target'.format(self.name)]) == 0)

    def is_enabled(self):
        """Check if monasca-agent is setup to start at boot time.

        :return: True if monasca-agent is enabled on boot, False otherwise.
        """
        return(subprocess.call(['systemctl', 'is-enabled', '--quiet',
                               '{0}.target'.format(self.name)]) == 0)
