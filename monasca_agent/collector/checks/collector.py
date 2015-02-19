# Core modules
import logging
import socket
import system.win32 as w32
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

        # add windows system checks
        if self.os == 'windows':
            self._checks = [w32.Disk(log),
                            w32.IO(log),
                            w32.Processes(log),
                            w32.Memory(log),
                            w32.Network(log),
                            w32.Cpu(log)]
        else:
            self._checks = []

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
            log.info("Finished run #%s. Collection time: %ss." %
                     (self.run_count, round(collect_duration, 2)))
            if self.run_count == FLUSH_LOGGING_INITIAL:
                log.info("First flushes done, next flushes will be logged every %s flushes." %
                         FLUSH_LOGGING_PERIOD)

        else:
            log.debug("Finished run #%s. Collection time: %ss." %
                      (self.run_count, round(collect_duration, 2),))

    def collector_stats(self, num_metrics, num_events, collection_time):
        metrics = {}
        thread_count = threading.active_count()
        metrics['monasca.thread_count'] = thread_count
        if thread_count > MAX_THREADS_COUNT:
            log.warn("Collector thread count is high: %d" % thread_count)

        metrics['monasca.collection_time_sec'] = collection_time
        if collection_time > MAX_COLLECTION_TIME:
            log.info("Collection time (s) is high: %.1f, metrics count: %d, events count: %d" %
                     (collection_time, num_metrics, num_events))

        return metrics

    def run(self):
        """Collect data from each check and submit their data.

        There are currently two types of checks the system checks and the configured ones from checks_d
        """
        timer = util.Timer()
        self.run_count += 1
        log.debug("Starting collection run #%s" % self.run_count)

        metrics_list = []

        timestamp = time.time()
        events = {}

        if self.os == 'windows':  # Windows uses old style checks.
            for check_type in self._checks:
                try:
                    for name, value in check_type.check().iteritems():
                        metrics_list.append(metrics.Measurement(name,
                                                                timestamp,
                                                                value,
                                                                self._set_dimensions(None),
                                                                None))
                except Exception:
                    log.exception('Error running check.')
        else:
            for check_type in self._checks:
                metrics_list.extend(check_type.check())

        # checks_d checks
        checks_d_metrics, checks_d_events, checks_statuses = self.run_checks_d()
        metrics_list.extend(checks_d_metrics)
        events.update(checks_d_events)

        # Store the metrics and events in the payload.
        collect_duration = timer.step()

        dimensions = {'component': 'monasca-agent'}
        # Add in metrics on the collector run
        for name, value in self.collector_stats(len(metrics_list), len(events),
                                                collect_duration).iteritems():
            metrics_list.append(metrics.Measurement(name,
                                                    timestamp,
                                                    value,
                                                    self._set_dimensions(dimensions),
                                                    None))
        emitter_statuses = self._emit(metrics_list)

        # Persist the status of the collection run.
        self._set_status(checks_statuses, emitter_statuses, collect_duration)

    def run_checks_d(self):
        """Run defined checks_d checks.

        returns a list of Measurements, a dictionary of events and a list of check statuses.
        """
        measurements = []
        events = {}
        check_statuses = []
        for check in self.initialized_checks_d:
            if not self.continue_running:
                return
            log.info("Running check %s" % check.name)
            instance_statuses = []
            metric_count = 0
            event_count = 0
            try:
                # Run the check.
                instance_statuses = check.run()

                # Collect the metrics and events.
                current_check_metrics = check.get_metrics()
                current_check_events = check.get_events()

                # Save them for the payload.
                measurements.extend(current_check_metrics)
                if current_check_events:
                    if check.name not in events:
                        events[check.name] = current_check_events
                    else:
                        events[check.name] += current_check_events

                # Save the status of the check.
                metric_count = len(current_check_metrics)
                event_count = len(current_check_events)
            except Exception:
                log.exception("Error running check %s" % check.name)

            status_check = check_status.CheckStatus(check.name, instance_statuses, metric_count, event_count,
                                                    library_versions=check.get_library_info())
            check_statuses.append(status_check)

        for check_name, info in self.init_failed_checks_d.iteritems():
            if not self.continue_running:
                return
            status_check = check_status.CheckStatus(check_name, None, None, None,
                                                    init_failed_error=info['error'],
                                                    init_failed_traceback=info['traceback'])
            check_statuses.append(status_check)

        return measurements, events, check_statuses

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
