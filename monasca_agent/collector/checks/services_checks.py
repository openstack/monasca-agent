# (C) Copyright 2015-2017 Hewlett Packard Enterprise Development Company LP
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

import collections
from concurrent import futures
import threading

import eventlet
import multiprocessing
from six.moves.queue import Queue

import monasca_agent.collector.checks

DEFAULT_TIMEOUT = 180
DEFAULT_SIZE_POOL = 6
MAX_LOOP_ITERATIONS = 1000
MAX_ALLOWED_THREADS = 200
FAILURE = "FAILURE"

up_down = collections.namedtuple('up_down', ['UP', 'DOWN'])
Status = up_down('UP', 'DOWN')
EventType = up_down("servicecheck.state_change.up", "servicecheck.state_change.down")


class ServicesCheck(monasca_agent.collector.checks.AgentCheck):
    SOURCE_TYPE_NAME = 'servicecheck'

    """Services checks inherits from this class.

    This class should never be directly instantiated.

    Work flow:
        The main agent loop will call the check function for each instance for
        each iteration of the loop.
        The check method will make an asynchronous call to the _process method in
        one of the thread pool executors created in this class constructor.
        The _process method will call the _check method of the inherited class
        which will perform the actual check.

        The _check method must return a tuple which first element is either
            Status.UP or Status.DOWN.
            The second element is a short error message that will be displayed
            when the service turns down.
    """

    def __init__(self, name, init_config, agent_config, instances):
        monasca_agent.collector.checks.AgentCheck.__init__(
            self, name, init_config, agent_config, instances)

        # A dictionary to keep track of service statuses
        self.statuses = {}
        self.notified = {}
        self.resultsq = Queue()
        self.nb_failures = 0
        self.pool = None

        # The pool size should be the minimum between the number of instances
        # and the DEFAULT_SIZE_POOL. It can also be overridden by the 'threads_count'
        # parameter in the init_config of the check
        try:
            default_size = min(self.instance_count(), multiprocessing.cpu_count() + 1)
        except NotImplementedError:
            default_size = min(self.instance_count(), DEFAULT_SIZE_POOL)
        self.pool_size = int(self.init_config.get('threads_count', default_size))
        self.timeout = int(self.agent_config.get('timeout', DEFAULT_TIMEOUT))

    def start_pool(self):
        if self.pool is None:
            self.log.info("Starting Thread Pool Exceutor")
            self.pool = futures.ThreadPoolExecutor(max_workers=self.pool_size)
            if threading.activeCount() > MAX_ALLOWED_THREADS:
                self.log.error('Thread count (%d) exceeds maximum (%d)' % (threading.activeCount(),
                                                                           MAX_ALLOWED_THREADS))
            self.running_jobs = {}

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool:
            self.pool.shutdown(wait=True)
            self.pool = None

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def check(self, instance):
        self.start_pool()
        name = instance.get('name', None)
        if name is None:
            self.log.error('Each service check must have a name')
            return

        if (name not in self.running_jobs) or self.running_jobs[name].done():
            # A given instance should be processed one at a time
            self.running_jobs[name] = self.pool.submit(self._process, instance)
        else:
            self.log.info("Instance: %s skipped because it's already running." % name)

    def _process(self, instance):
        name = instance.get('name', None)
        try:
            with eventlet.timeout.Timeout(self.timeout):
                return_value = self._check(instance)
            if not return_value:
                return
            status, msg = return_value
            self._process_result(status, msg, name, instance)
        except eventlet.Timeout:
            msg = 'ServiceCheck {0} timed out'.format(name)
            self.log.error(msg)
            self._process_result(FAILURE, msg, name, instance)
        except Exception:
            msg = 'Failure in ServiceCheck {0}'.format(name)
            self.log.exception(msg)
            self._process_result(FAILURE, msg, name, instance)
        finally:
            del self.running_jobs[name]

    def _process_result(self, status, msg, name, queue_instance):
        if name not in self.statuses:
            self.statuses[name] = []

        self.statuses[name].append(status)

        window = int(queue_instance.get('window', 1))

        if window > 256:
            self.log.warning("Maximum window size (256) exceeded, defaulting it to 256")
            window = 256

        threshold = queue_instance.get('threshold', 1)

        if len(self.statuses[name]) > window:
            self.statuses[name].pop(0)

        nb_failures = self.statuses[name].count(Status.DOWN)

        if nb_failures >= threshold:
            if self.notified.get(name, Status.UP) != Status.DOWN:
                self.notified[name] = Status.DOWN
        else:
            if self.notified.get(name, Status.UP) != Status.UP:
                self.notified[name] = Status.UP

    def _check(self, instance):
        """This function should be implemented by inherited classes.

        """
        raise NotImplementedError
