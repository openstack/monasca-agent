# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# stdlib
from collections import defaultdict
import itertools
import re
import socket
import time
import xmlrpclib

# 3p
import supervisor.xmlrpc

# project
import monasca_agent.collector.checks as checks

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = '9001'
DEFAULT_SOCKET_IP = 'http://127.0.0.1'

STATUS = {
    'STOPPED': 'CRITICAL',
    'STARTING': 'UNKNOWN',
    'RUNNING': 'OK',
    'BACKOFF': 'CRITICAL',
    'STOPPING': 'CRITICAL',
    'EXITED': 'CRITICAL',
    'FATAL': 'CRITICAL',
    'UNKNOWN': 'UNKNOWN'
}

PROCESS_STATUS = {
    'CRITICAL': 'down',
    'OK': 'up',
    'UNKNOWN': 'unknown'
}

PROCESS_STATE = {
    'CRITICAL': 0,
    'OK': 1,
    'UNKNOWN': -1
}

SERVER_STATE = {
    'DOWN': 1,
    'UP': 0
}

SERVER_TAG = 'supervisord_server'

PROCESS_TAG = 'supervisord_process'


def _format_time(x):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(x))

SERVER_SERVICE_CHECK = 'supervisord.can_connect'
PROCESS_SERVICE_CHECK = 'supervisord.process.status'
PROCESS_UP_TIME_CHECK = 'supervisord.process.uptime'
PROCESS_COUNT_UP_CHECK = 'supervisord.process.count.status_up'
PROCESS_COUNT_DOWN_CHECK = 'supervisord.process.count.status_down'
PROCESS_COUNT_UNKNOWN_CHECK = 'supervisord.process.count.status_unknown'


class Supervisord(checks.AgentCheck):

    def check(self, instance):
        server_name = instance.get('name')
        proc_details_check = instance.get('proc_details_check', True)
        if proc_details_check in ['False', 'false']:
            proc_details_check = False
        proc_uptime_check = instance.get('proc_uptime_check', True)
        if proc_uptime_check in ['False', 'false']:
            proc_uptime_check = False

        if not server_name or not server_name.strip():
            raise Exception("Supervisor server name not specified in yaml configuration.")

        dimensions = self._set_dimensions({'server_name': server_name}, instance)
        supe = self._connect(instance)
        count_by_status = defaultdict(int)

        # Gather all process information
        try:
            processes = supe.getAllProcessInfo()
        except xmlrpclib.Fault as error:
            raise Exception(
                'An error occurred while reading process information: %s %s'
                % (error.faultCode, error.faultString)
            )
        except socket.error as error:
            host = instance.get('host', DEFAULT_HOST)
            port = instance.get('port', DEFAULT_PORT)
            sock = instance.get('socket')
            if sock is None:
                msg = 'Cannot connect to http://%s:%s. ' \
                      'Make sure supervisor is running and XML-RPC ' \
                      'inet interface is enabled.' % (host, port)
            else:
                msg = 'Cannot connect to %s. Make sure sure supervisor ' \
                      'is running and socket is enabled and socket file' \
                      ' has the right permissions.' % sock

            server_details = {'server_details': msg}
            self.gauge(SERVER_SERVICE_CHECK, SERVER_STATE['DOWN'],
                       dimensions=dimensions, value_meta=server_details)
            raise Exception(msg)

        except xmlrpclib.ProtocolError as error:
            if error.errcode == 401:  # authorization error
                msg = 'Username or password to %s are incorrect.' % server_name
            else:
                msg = "An error occurred while connecting to %s: "\
                    "%s %s " % (server_name, error.errcode, error.errmsg)

            server_details = {'server_details': msg}
            self.gauge(SERVER_SERVICE_CHECK, SERVER_STATE['DOWN'],
                       dimensions=dimensions, value_meta=server_details)
            raise Exception(msg)

        # If we're here, we were able to connect to the server
        self.gauge(SERVER_SERVICE_CHECK, SERVER_STATE['UP'], dimensions=dimensions)

        # Filter monitored processes on configuration directives
        proc_regex = instance.get('proc_regex', [])
        if not isinstance(proc_regex, list):
            raise Exception("Invalid proc_regex.")

        proc_names = instance.get('proc_names', [])
        if not isinstance(proc_names, list):
            raise Exception("Invalid proc_names.")

        # Collect information on each monitored process
        monitored_processes = []

        # monitor all processes if no filters were specified
        if len(proc_regex) == 0 and len(proc_names) == 0:
            monitored_processes = processes

        for pattern, process in itertools.product(proc_regex, processes):
            try:
                if re.match(pattern, process['name']) and process not in monitored_processes:
                    monitored_processes.append(process)
            except re.error:
                raise

        for process in processes:
            if process['name'] in proc_names and process not in monitored_processes:
                monitored_processes.append(process)

        # Report service checks and uptime for each process
        for proc in monitored_processes:
            proc_name = proc['name']
            dimensions[PROCESS_TAG] = proc_name

            # Retrieve status and update status count
            status = STATUS[proc['statename']]
            count_by_status[status] += 1

            # Report process details
            if proc_details_check:
                msg = self._build_message(proc)
                self.log.info('process details: %s' % msg)
                self.gauge(PROCESS_SERVICE_CHECK, PROCESS_STATE[status],
                           dimensions=dimensions)

            # Report Uptime
            if proc_uptime_check:
                uptime = self._extract_uptime(proc)
                self.gauge(PROCESS_UP_TIME_CHECK, uptime, dimensions=dimensions)

            dimensions.pop(PROCESS_TAG, None)

        # Report counts by status
        self.gauge(PROCESS_COUNT_UP_CHECK, count_by_status['OK'],
                   dimensions=dimensions)
        self.gauge(PROCESS_COUNT_DOWN_CHECK, count_by_status['CRITICAL'],
                   dimensions=dimensions)
        self.gauge(PROCESS_COUNT_UNKNOWN_CHECK, count_by_status['UNKNOWN'],
                   dimensions=dimensions)

    @staticmethod
    def _connect(instance):
        sock = instance.get('socket')
        if sock is not None:
            host = instance.get('host', DEFAULT_SOCKET_IP)
            transport = supervisor.xmlrpc.SupervisorTransport(None, None, sock)
            server = xmlrpclib.ServerProxy(host, transport=transport)
        else:
            host = instance.get('host', DEFAULT_HOST)
            port = instance.get('port', DEFAULT_PORT)
            user = instance.get('user')
            password = instance.get('pass')
            auth = '%s:%s@' % (user, password) if user and password else ''
            server = xmlrpclib.Server('http://%s%s:%s/RPC2' % (auth, host, port))
        return server.supervisor

    @staticmethod
    def _extract_uptime(proc):
        start, now = int(proc['start']), int(proc['now'])
        status = proc['statename']
        active_state = status in ['BACKOFF', 'RUNNING', 'STOPPING']
        return now - start if active_state else 0

    @staticmethod
    def _build_message(proc):
        start, stop, now = int(proc['start']), int(proc['stop']), int(proc['now'])
        proc['now_str'] = _format_time(now)
        proc['start_str'] = _format_time(start)
        proc['stop_str'] = '' if stop == 0 else _format_time(stop)

        return """Current time: %(now_str)s
Process name: %(name)s
Process group: %(group)s
Description: %(description)s
Error log file: %(stderr_logfile)s
Stdout log file: %(stdout_logfile)s
Log file: %(logfile)s
State: %(statename)s
Start time: %(start_str)s
Stop time: %(stop_str)s
Exit Status: %(exitstatus)s""" % proc
