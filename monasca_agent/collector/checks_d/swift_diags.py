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

import json
import logging
import os
import subprocess

import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)

DIAG_COMMAND = '/usr/local/bin/diagnostics'
CHECKER_COMMAND = '/usr/local/bin/swift-checker'

DIAG_ATTRS = ['check_mounts', 'disk_monitoring', 'file_ownership',
              'network_interface', 'ping_hosts', 'drive_audit']
CHECKER_ATTRS = ['diskusage', 'healthcheck', 'replication']


def run_command(command, input=None):
    log.info("Executing command - {0}".format(command))
    try:
        process = subprocess.Popen(command,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   stdin=subprocess.PIPE)
        stdout, stderr = process.communicate(input=input)
        errcode = process.returncode
        log.debug('errcode - {0}, stdout - {1}, stderr - {2}'.format(errcode,
                                                                     stdout,
                                                                     stderr))
        return errcode, stdout, stderr
    except Exception:
        log.error("Failure while executing command - {0}".format(command))


def process_command(command):
    """Runs the command and returns json output
    """
    try:
        errcode, stdout, stderr = run_command(command)
        json_output = json.loads(stdout)
        return json_output
    except Exception:
        log.error('Failure while processing output - {0}'.format(stdout))


class SwiftDiags(checks.AgentCheck):
    def __init__(self, name, init_config, agent_config):
        super(SwiftDiags, self).__init__(name, init_config, agent_config)

    def check(self, instance):
        """Get swift checks and propagate.
           The checks are part of HP swift-diags package and checks are
           are run only if the package exists.
        """
        if not (os.path.exists(DIAG_COMMAND) and
                os.path.exists(CHECKER_COMMAND)):
            return None

        dimensions = self._set_dimensions(None, instance)

        for attribute in DIAG_ATTRS:
            # have to give sudo privileges for these commands to execute
            cmd = '{0} {1} --{2}'.format('sudo', DIAG_COMMAND, attribute)
            try:
                output = process_command(cmd)
                self.gauge('swift.{0}'.format(attribute),
                           int(output['status']),
                           dimensions=dimensions,
                           value_meta={'message': output.get('message')})
            except Exception as e:
                log.error('Error in performing check - {0}, {1}'.
                          format(attribute, e.message))

        for attribute in CHECKER_ATTRS:
            # have to give sudo privileges for these commands to execute
            cmd = '{0} {1} --{2}'.format('sudo', CHECKER_COMMAND, attribute)
            try:
                output = process_command(cmd)
                self.gauge('swift.{0}'.format(attribute),
                           int(output['status']), dimensions=dimensions,
                           value_meta={'message': output.get('message')})
                if output.get('data') and 'name' in output.get('data', {}):
                    metric = 'swift.{0}.{1}'.format(attribute,
                                                    output['data']['name'])
                    value = output['data']['value']
                    self.gauge(metric, value=value, dimensions=dimensions)
            except Exception as e:
                log.error('Error in performing check - {0}, {1}'.
                          format(attribute, e.message))
