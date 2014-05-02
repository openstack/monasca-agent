#!/bin/env python
"""DataDog wrapper for Nagios checks"""

import hashlib
import json
import os
import pickle
import socket
import subprocess
import time

from monagent.collector.checks import AgentCheck


class WrapNagios(AgentCheck):
    """Inherit Agentcheck class to process Nagios checks"""

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)

    @staticmethod
    def _do_skip_check(instance, last_run_data):
        """ Determine whether or not to skip a check depending on
            the checks's check_interval, if specified, and the last
            time the check was run """
        if instance['service_name'] in last_run_data and 'check_interval' in instance:
            if time.time() < last_run_data[instance['service_name']] + instance['check_interval']:
                return True
        else:
            return False

    def check(self, instance):
        """Run the command specified by check_command and capture the result"""

        tags = [
            'observer_host:' + socket.getfqdn(),
        ]
        if 'host_name' in instance:
            tags.extend(['target_host:' + instance['host_name']])
        else:
            tags.extend(['target_host:' + socket.getfqdn()])

        extra_path = self.init_config.get('check_path')

        last_run_path = self.init_config.get('temp_file_path')
        # Use a default last_run_file if no temp_file is specified in the YAML
        if last_run_path is None:
            last_run_path = '/dev/shm/'

        if last_run_path.endswith('/') is False:
            last_run_path += '/'
        last_run_file = (last_run_path + 'nagios_wrapper_' + hashlib.md5(instance['service_name']).hexdigest() + '.pck')

        # Load last-run data from shared memory file
        last_run_data = {}
        if os.path.isfile(last_run_file):
            file_r = open(last_run_file, "r")
            last_run_data = pickle.load(file_r)
            file_r.close()

        # Exit here if it is not yet time to re-run this check
        if self._do_skip_check(instance, last_run_data) is True:
            return

        try:
            proc = subprocess.Popen(instance['check_command'].split(" "),
                                    env={"PATH": extra_path},
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            output = proc.communicate()
            # The check detail is all the text before the pipe
            detail = output[0].split('|')[0]
            if detail != '':
                # Serialize the output for JSON-friendliness and add to the tags
                tags.extend(['detail:' + json.dumps(detail)])
        except OSError:
            # Return an UNKNOWN code (3) if I have landed here
            self.gauge(instance['service_name'], 3, tags=tags)
            self.log.info(instance['check_command'].split(" ")[0] + " is missing or unreadable")
            return

        last_run_data[instance['service_name']] = time.time()
        self.gauge(instance['service_name'], proc.poll(), tags=tags)

        # Save last-run data
        file_w = open(last_run_file, "w")
        pickle.dump(last_run_data, file_w)
        file_w.close()
