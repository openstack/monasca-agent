# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import collections
import Queue
import threading
import time

from gevent import monkey
from gevent import Timeout
from multiprocessing.dummy import Pool as ThreadPool

import monasca_agent.collector.checks


DEFAULT_TIMEOUT = 180
DEFAULT_SIZE_POOL = 6
MAX_LOOP_ITERATIONS = 1000
MAX_ALLOWED_THREADS = 200
FAILURE = "FAILURE"

up_down = collections.namedtuple('up_down', ['UP', 'DOWN'])
Status = up_down('UP', 'DOWN')
EventType = up_down("servicecheck.state_change.up", "servicecheck.state_change.down")
monkey.patch_all()


class ServicesCheck(monasca_agent.collector.checks.AgentCheck):
    SOURCE_TYPE_NAME = 'servicecheck'

    """Services checks inherits from this class.

    This class should never be directly instantiated.

    Work flow:
        The main agent loop will call the check function for each instance for
        each iteration of the loop.
        The check method will make an asynchronous call to the _process method in
        one of the thread initiated in the thread pool created in this class constructor.
        The _process method will call the _check method of the inherited class
        which will perform the actual check.

        The _check method must return a tuple which first element is either
            Status.UP or Status.DOWN.
            The second element is a short error message that will be displayed
            when the service turns down.
    """

    def __init__(self, name, init_config, agent_config, instances):
        monasca_agent.collector.checks.AgentCheck.__init__(self, name, init_config, agent_config, instances)

        # A dictionary to keep track of service statuses
        self.statuses = {}
        self.notified = {}
        self.resultsq = Queue.Queue()
        self.nb_failures = 0
        self.pool = None

        # The pool size should be the minimum between the number of instances
        # and the DEFAULT_SIZE_POOL. It can also be overridden by the 'threads_count'
        # parameter in the init_config of the check
        default_size = min(self.instance_count(), DEFAULT_SIZE_POOL)
        self.pool_size = int(self.init_config.get('threads_count', default_size))
        self.timeout = int(self.agent_config.get('timeout', DEFAULT_TIMEOUT))

    def start_pool(self):
        self.log.info("Starting Thread Pool")
        self.pool = ThreadPool(self.pool_size)
        if threading.activeCount() > MAX_ALLOWED_THREADS:
            self.log.error("Thread count ({0}) exceeds maximum ({1})".format(threading.activeCount(),
                                                                             MAX_ALLOWED_THREADS))
        self.running_jobs = set()

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool:
            self.pool.close()
            self.pool.join()
            self.pool = None

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def check(self, instance):
        if not self.pool:
            self.start_pool()
        self._process_results()
        name = instance.get('name', None)
        if name is None:
            self.log.error('Each service check must have a name')
            return

        if name not in self.running_jobs:
            # A given instance should be processed one at a time
            self.running_jobs.add(name)
            self.pool.apply_async(self._process, args=(instance,))
        else:
            self.log.info("Instance: %s skipped because it's already running." % name)

    def _process(self, instance):
        name = instance.get('name', None)
        try:
            with Timeout(self.timeout):
                return_value = self._check(instance)
            if not return_value:
                return
            status, msg = return_value
            result = (status, msg, name, instance)
            # We put the results in the result queue
            self.resultsq.put(result)
        except Timeout:
            self.log.error('ServiceCheck {0} timed out'.format(name))
        except Exception:
            self.log.exception('Failure in ServiceCheck {0}'.format(name))
            result = (FAILURE, FAILURE, FAILURE, FAILURE)
            self.resultsq.put(result)
        finally:
            self.running_jobs.remove(name)

    def _process_results(self):
        for i in range(MAX_LOOP_ITERATIONS):
            try:
                # We want to fetch the result in a non blocking way
                status, msg, name, queue_instance = self.resultsq.get_nowait()
            except Queue.Empty:
                break

            if status == FAILURE:
                self.nb_failures += 1
                if self.nb_failures >= self.pool_size - 1:
                    self.nb_failures = 0
                    self.restart_pool()
                continue

            event = None

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
                    event = self._create_status_event(status, msg, queue_instance)
                    self.notified[name] = Status.DOWN
            else:
                if self.notified.get(name, Status.UP) != Status.UP:
                    event = self._create_status_event(status, msg, queue_instance)
                    self.notified[name] = Status.UP

            if event is not None:
                self.events.append(event)

    def _check(self, instance):
        """This function should be implemented by inherited classes.

        """
        raise NotImplementedError
