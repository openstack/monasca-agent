# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP

# Core modules
import logging
import socket
import threading
import time

import monasca_agent.common.check_status as check_status
import monasca_agent.common.metrics as metrics
import monasca_agent.common.util as util


log = logging.getLogger(__name__)


MAX_THREADS_COUNT = 50
MAX_COLLECTION_TIME = 30
MAX_CPU_PCT = 10
FLUSH_LOGGING_PERIOD = 10
FLUSH_LOGGING_INITIAL = 5


class Collector(util.Dimensions):

    """The collector is responsible for collecting data from each check and

    passing it along to the emitters, who send it to their final destination.
    """

    def __init__(self, agent_config, emitter, checksd=None):
        super(Collector, self).__init__(agent_config)
        self.agent_config = agent_config
        self.os = util.get_os()
        self.plugins = None
        self.emitter = emitter
        socket.setdefaulttimeout(15)
        self.run_count = 0
        self.continue_running = True
        self.initialized_checks_d = []
        self.init_failed_checks_d = []

        if checksd:
            # is of type {check_name: check}
            self.initialized_checks_d = checksd['initialized_checks']
            # is of type {check_name: {error, traceback}}
            self.init_failed_checks_d = checksd['init_failed_checks']

    def _emit(self, payload):
        """Send the payload via the emitter.
        """
        statuses = []
        # Don't try to send to an emitter if we're stopping/
        if self.continue_running:
            name = self.emitter.__name__
            emitter_status = check_status.EmitterStatus(name)
            try:
                self.emitter(payload, log, self.agent_config['forwarder_url'])
            except Exception as e:
                log.exception("Error running emitter: %s" % self.emitter.__name__)
                emitter_status = check_status.EmitterStatus(name, e)
            statuses.append(emitter_status)
        return statuses

    def _set_status(self, check_statuses, emitter_statuses, collect_duration):
        try:
            check_status.CollectorStatus(check_statuses, emitter_statuses).persist()
        except Exception:
            log.exception("Error persisting collector status")

        if self.run_count <= FLUSH_LOGGING_INITIAL or self.run_count % FLUSH_LOGGING_PERIOD == 0:
            log.info("Finished run #%s. Collection time: %.2fs." %
                     (self.run_count, round(collect_duration, 2)))
            if self.run_count == FLUSH_LOGGING_INITIAL:
                log.info("First flushes done, next flushes will be logged every %s flushes." %
                         FLUSH_LOGGING_PERIOD)

        else:
            log.debug("Finished run #%s. Collection time: %.2fs." %
                      (self.run_count, round(collect_duration, 2),))

    def collector_stats(self, num_metrics, collection_time):
        metrics = {}
        thread_count = threading.active_count()
        metrics['monasca.thread_count'] = thread_count
        if thread_count > MAX_THREADS_COUNT:
            log.warn("Collector thread count is high: %d" % thread_count)

        metrics['monasca.collection_time_sec'] = collection_time
        if collection_time > MAX_COLLECTION_TIME:
            log.info("Collection time (s) is high: %.1f, metrics count: %d" %
                     (collection_time, num_metrics))

        return metrics

    def run(self):
        """Collect data from each check and submit their data.

        There are currently two types of checks the system checks and the configured ones from checks_d
        """
        timer = util.Timer()
        self.run_count += 1
        log.debug("Starting collection run #%s" % self.run_count)

        # checks_d checks
        num_metrics, emitter_statuses, checks_statuses = self.run_checks_d()

        collect_duration = timer.step()

        collect_stats = []
        dimensions = {'component': 'monasca-agent', 'service': 'monitoring'}
        # Add in metrics on the collector run
        for name, value in self.collector_stats(num_metrics, collect_duration).iteritems():
            collect_stats.append(metrics.Measurement(name,
                                                     time.time(),
                                                     value,
                                                     self._set_dimensions(dimensions),
                                                     None))
        emitter_statuses.append(self._emit(collect_stats))

        # Persist the status of the collection run.
        self._set_status(checks_statuses, emitter_statuses, collect_duration)

    def run_checks_d(self):
        """Run defined checks_d checks.

        returns a list of Measurements and a list of check statuses.
        """
        sub_timer = util.Timer()
        measurements = 0
        check_statuses = []
        emitter_statuses = []
        for check in self.initialized_checks_d:
            if not self.continue_running:
                return
            log.debug("Running check %s" % check.name)
            instance_statuses = []
            metric_count = 0
            try:
                # Run the check.
                instance_statuses = check.run()

                current_check_metrics = check.get_metrics()

                # Emit the metrics after each check
                emitter_statuses.append(self._emit(current_check_metrics))

                # Save the status of the check.
                metric_count = len(current_check_metrics)
                measurements += metric_count
            except Exception:
                log.exception("Error running check %s" % check.name)

            status_check = check_status.CheckStatus(check.name, instance_statuses, metric_count,
                                                    library_versions=check.get_library_info())
            check_statuses.append(status_check)
            sub_collect_duration = sub_timer.step()
            sub_collect_duration_mills = sub_collect_duration * 1000
            log.debug("Finished run check %s. Collection time: %.2fms." % (
                check.name, round(sub_collect_duration_mills, 2)))
            if sub_collect_duration > util.get_sub_collection_warn():
                log.warn("Collection time for check %s is high: %.2fs." % (
                    check.name, round(sub_collect_duration, 2)))

        for check_name, info in self.init_failed_checks_d.iteritems():
            if not self.continue_running:
                return
            status_check = check_status.CheckStatus(check_name, None, None,
                                                    init_failed_error=info['error'],
                                                    init_failed_traceback=info['traceback'])
            check_statuses.append(status_check)

        return measurements, emitter_statuses, check_statuses

    def stop(self):
        """Tell the collector to stop at the next logical point.
        """
        # This is called when the process is being killed, so
        # try to stop the collector as soon as possible.
        # Most importantly, don't try to submit to the emitters
        # because the forwarder is quite possibly already killed
        # in which case we'll get a misleading error in the logs.
        # Best to not even try.
        self.continue_running = False
        for check in self.initialized_checks_d:
            check.stop()
