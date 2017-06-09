# (C) Copyright 2015-2017 Hewlett Packard Enterprise Development LP

# Core modules
import logging
from multiprocessing.dummy import Pool
import os
import socket
import sys
import threading
import time

import monasca_agent.common.metrics as metrics
import monasca_agent.common.util as util


log = logging.getLogger(__name__)


MAX_THREADS_COUNT = 50
MAX_CPU_PCT = 10
FLUSH_LOGGING_PERIOD = 10
FLUSH_LOGGING_INITIAL = 5


class Collector(util.Dimensions):

    """The collector is responsible for collecting data from each check and

    passing it along to the emitters, who send it to their final destination.
    """

    def __init__(self, agent_config, emitter, checksd):
        super(Collector, self).__init__(agent_config)
        self.agent_config = agent_config
        self.os = util.get_os()
        self.plugins = None
        self.emitter = emitter
        socket.setdefaulttimeout(15)
        self.run_count = 0
        self.continue_running = True
        self.collection_metrics = {}

        # is of type {check_name: check}
        initialized_checks_d = checksd['initialized_checks']

        self.pool_size = int(self.agent_config.get('num_collector_threads', 1))
        log.info('Using %d Threads for Collector' % self.pool_size)
        self.pool = Pool(self.pool_size)
        self.pool_full_count = 0
        self.collection_times = {}
        self.collection_results = {}
        self.collect_runs = 0
        for check in initialized_checks_d:
            derived_collect_periods = 1
            if 'collect_period' in check.init_config:
                if check.init_config['collect_period'] < 0:
                    log.warn('Invalid negative time parameter. '
                             'collect_period for %s will be reset '
                             'to default' % check.name)
                else:
                    # This equation calculates on which nth run the plugin
                    # gets called. It converts the collect_period from seconds
                    # to an integer which holds the collection round the
                    # plugin should get called on.
                    derived_collect_periods = (
                        ((check.init_config['collect_period'] - 1)
                         / agent_config['check_freq']) + 1)
            self.collection_times[check.name] = {
                'check': check,
                'last_collect_time': 99999999,
                'derived_collect_periods': derived_collect_periods}
        self.pool_full_max_retries = int(self.agent_config.get('pool_full_max_retries',
                                                               4))

    def _emit(self, payload):
        """Send the payload via the emitter.
        """
        # Don't try to send to an emitter if we're stopping/
        if self.continue_running:
            try:
                self.emitter(payload, log, self.agent_config['forwarder_url'])
            except Exception:
                log.exception("Error running emitter: %s" % self.emitter.__name__)

    def _set_status(self, collect_duration):
        if self.run_count <= FLUSH_LOGGING_INITIAL or self.run_count % FLUSH_LOGGING_PERIOD == 0:
            log.info("Finished run #%s. Collection time: %.2fs." %
                     (self.run_count, round(collect_duration, 2)))
            if self.run_count == FLUSH_LOGGING_INITIAL:
                log.info("First flushes done, next flushes will be logged every %s flushes." %
                         FLUSH_LOGGING_PERIOD)

        else:
            log.debug("Finished run #%s. Collection time: %.2fs." %
                      (self.run_count, round(collect_duration, 2),))

    def add_collection_metric(self, name, value):
        self.collection_metrics[name] = value

    def collector_stats(self, num_metrics, collection_time):
        thread_count = threading.active_count()
        self.add_collection_metric('monasca.thread_count', thread_count)
        if thread_count > MAX_THREADS_COUNT:
            log.warn("Collector thread count is high: %d" % thread_count)

        self.add_collection_metric('monasca.collection_time_sec', collection_time)

    def run(self, check_frequency):
        """Collect data from each check and submit their data.

        Also, submit a metric which is how long the checks_d took
        """
        timer = util.Timer()
        self.run_count += 1
        log.debug("Starting collection run #%s" % self.run_count)

        # checks_d checks
        num_metrics = self.run_checks_d(check_frequency)

        collect_duration = timer.step()

        # Warn if collection time is approaching the collection period
        if collect_duration > (4 * check_frequency / 5):
            log.warn("Collection time (s) is high: %.1f, metrics count: %d" %
                     (collect_duration, num_metrics))

        self.collector_stats(num_metrics, collect_duration)
        collect_stats = []
        dimensions = {'component': 'monasca-agent', 'service': 'monitoring'}
        # Add in metrics on the collector run
        for name, value in self.collection_metrics.items():
            metric = metrics.Metric(name,
                                    self._set_dimensions(dimensions),
                                    tenant=None)
            collect_stats.append(metric.measurement(value, time.time()))
        self.collection_metrics.clear()
        self._emit(collect_stats)

        # Persist the status of the collection run.
        self._set_status(collect_duration)

    def run_single_check(self, check):
        """Run a single check

        returns number of measurement collected, collection time
        """

        sub_timer = util.Timer()
        count = 0
        log.debug("Running plugin %s" % check.name)
        try:

            # Run the check.
            check.run()

            current_check_metrics = check.get_metrics()

            # Emit the metrics after each check
            self._emit(current_check_metrics)

            # Save the status of the check.
            count += len(current_check_metrics)

        except Exception:
            log.exception("Error running plugin %s" % check.name)

        sub_collect_duration = sub_timer.step()
        sub_collect_duration_mills = sub_collect_duration * 1000
        log.debug("Finished plugin %s run. Collection time: %.2fms %d Metrics." % (
                  check.name, round(sub_collect_duration_mills, 2), count))
        if sub_collect_duration > util.get_sub_collection_warn():
            log.warn("Collection time for check %s is high: %.2fs." % (
                     check.name, round(sub_collect_duration, 2)))
        return count, sub_collect_duration_mills

    def wait_for_results(self, check_frequency, start_time):
        """Wait either for all running checks to finish or
        for check_frequency seconds, whichever comes first

        returns number of measurements collected
        """

        # Make sure we check for results at least once
        wait_time = check_frequency / 10
        measurements = 0
        time_left = check_frequency
        while time_left > 0 and self.collection_results:
            for check_name in list(self.collection_results.keys()):
                result = self.collection_results[check_name]['result']
                result.wait(wait_time)
                if result.ready():
                    log.debug('Plugin %s has completed' % check_name)
                    if not result.successful():
                        log.error('Plugin %s failed' % check_name)
                    else:
                        count, collect_time = result.get()
                        measurements += count
                        self.collection_times[check_name]['last_collect_time'] = collect_time
                    del self.collection_results[check_name]
                else:
                    log.debug('Plugin %s still running' % check_name)
            time_left = start_time + check_frequency - time.time()
        return measurements

    def start_checks_in_thread_pool(self, start_time):
        """Add the checks that are not already running to the Thread Pool
        """

        # Sort by the last collection time so the checks that take the
        # least amount of time are run first so they are more likely to
        # complete within the check_frequency
        sorted_checks = sorted(self.collection_times.itervalues(),
                               key=lambda x: x['last_collect_time'])
        for entry in sorted_checks:
            check = entry['check']
            last_collect_time = entry['last_collect_time']
            if not self.continue_running:
                break
            if check.name in self.collection_results:
                log.warning('Plugin %s is already running, skipping' % check.name)
                continue
            if self.collect_runs % entry['derived_collect_periods'] != 0:
                log.debug('%s has not skipped enough collection periods yet. '
                          'Skipping.' % check.name)
                continue
            log.debug('Starting plugin %s, old collect time %d' %
                      (check.name, last_collect_time))
            async_result = self.pool.apply_async(self.run_single_check, [check])
            self.collection_results[check.name] = {'result': async_result,
                                                   'start_time': start_time}
        self.collect_runs += 1

    def run_checks_d(self, check_frequency):
        """Run defined checks_d checks using the Thread Pool.

        returns number of Measurements.
        """

        start_time = time.time()
        self.start_checks_in_thread_pool(start_time)

        measurements = self.wait_for_results(check_frequency, start_time)

        # See if any checks are still running
        if self.collection_results:
            # Output a metric that can be used for Alarming. This metric is only
            # emitted when there are checks running too long so a deterministic
            # Alarm Definition should be created when monitoring it
            self.add_collection_metric('monasca.checks_running_too_long',
                                       len(self.collection_results))
            for check_name in self.collection_results:
                run_time = time.time() - self.collection_results[check_name]['start_time']
                log.warning('Plugin %s still running after %d seconds' % (
                            check_name, run_time))

        if len(self.collection_results) >= self.pool_size:
            self.pool_full_count += 1
            if (self.pool_full_count > self.pool_full_max_retries):
                log.error('Thread Pool full and %d plugins still running for ' +
                          '%d collection cycles, exiting' %
                          (len(self.collection_results), self.pool_full_count))
                os._exit(1)
        else:
            self.pool_full_count = 0

        return measurements

    def stop(self, timeout=0):
        """Tell the collector to stop at the next logical point.
        """
        # This is called when the process is being killed, so
        # try to stop the collector as soon as possible.
        # Most importantly, don't try to submit to the emitters
        # because the forwarder is quite possibly already killed
        # in which case we'll get a misleading error in the logs.
        # Best to not even try.

        log.info("stopping the collector with timeout %d seconds" % timeout)

        self.continue_running = False
        for check_name in self.collection_times:
            check = self.collection_times[check_name]['check']
            check.stop()

        for check_name in self.collection_results:
            run_time = time.time() - self.collection_results[check_name]['start_time']
            log.info('When exiting... Plugin %s still running after %d seconds' % (
                check_name, run_time))

        self.pool.close()

        # Won't call join() if timeout is zero. If we are in an event thread
        # a BlockingSwitchOutError occurs if wait

        if (timeout > 0):
            timer = util.Timer()
            for worker in self.pool._pool:
                t = timeout - timer.total()
                if t <= 0:
                    break
                if worker.is_alive():
                    try:
                        worker.join(t)
                    except Exception:
                        log.error("Unexpected error: ", sys.exc_info()[0])

        for worker in self.pool._pool:
            if worker.is_alive():
                # the worker didn't complete in the specified timeout.
                # collector must honor the stop request to avoid agent stop/restart hang.
                # os._exit() should be called after collector stops.
                log.info('worker %s is still alive when collector stop times out.' % worker.name)
