import json
import logging
import threading
import monasca_agent.common.check_status as check_status
import monasca_agent.common.emitter as emitter
import monasca_agent.common.util as util

log = logging.getLogger(__name__)


WATCHDOG_TIMEOUT = 120
# Since we call flush more often than the metrics aggregation interval, we should
#  log a bunch of flushes in a row every so often.
FLUSH_LOGGING_PERIOD = 70
FLUSH_LOGGING_INITIAL = 10
FLUSH_LOGGING_COUNT = 5
EVENT_CHUNK_SIZE = 50


class Reporter(threading.Thread):
    """
    The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, aggregator, api_host, use_watchdog=False, event_chunk_size=None):
        threading.Thread.__init__(self)
        self.interval = int(interval)
        self.finished = threading.Event()
        self.aggregator = aggregator
        self.flush_count = 0
        self.log_count = 0

        self.watchdog = None
        if use_watchdog:
            from monasca_agent.common.util import Watchdog
            self.watchdog = Watchdog(WATCHDOG_TIMEOUT)

        self.api_host = api_host
        self.event_chunk_size = event_chunk_size or EVENT_CHUNK_SIZE

    @staticmethod
    def serialize_metrics(metrics):
        return json.dumps({"series": metrics})

    def stop(self):
        log.info("Stopping reporter")
        self.finished.set()

    def run(self):

        log.info("Reporting to %s every %ss" % (self.api_host, self.interval))
        log.debug("Watchdog enabled: %s" % bool(self.watchdog))

        # Persist a start-up message.
        check_status.MonascaStatsdStatus().persist()

        while not self.finished.isSet():  # Use camel case isSet for 2.4 support.
            self.finished.wait(self.interval)
            self.flush()
            if self.watchdog:
                self.watchdog.reset()

        # Clean up the status messages.
        log.debug("Stopped reporter")
        check_status.MonascaStatsdStatus.remove_latest_status()

    def flush(self):
        try:
            self.flush_count += 1
            self.log_count += 1

            metrics = self.aggregator.flush()
            count = len(metrics)
            if self.flush_count % FLUSH_LOGGING_PERIOD == 0:
                self.log_count = 0
            if count:
                try:
                    emitter.http_emitter(metrics, log, self.api_host)
                except Exception:
                    log.exception("Error running emitter.")

            events = self.aggregator.flush_events()
            event_count = len(events)
            if event_count:
                log.warn('Event received but events are not available in the monasca api')

            should_log = self.flush_count <= FLUSH_LOGGING_INITIAL or self.log_count <= FLUSH_LOGGING_COUNT
            log_func = log.info
            if not should_log:
                log_func = log.debug
            log_func(
                "Flush #%s: flushed %s metric%s and %s event%s" %
                (self.flush_count,
                 count,
                 util.plural(count),
                 event_count,
                 util.plural(event_count)))
            if self.flush_count == FLUSH_LOGGING_INITIAL:
                log.info(
                    "First flushes done, %s flushes will be logged every %s flushes." %
                    (FLUSH_LOGGING_COUNT, FLUSH_LOGGING_PERIOD))

            # Persist a status message.
            packet_count = self.aggregator.total_count
            packets_per_second = self.aggregator.packets_per_second(self.interval)
            check_status.MonascaStatsdStatus(flush_count=self.flush_count,
                                             packet_count=packet_count,
                                             packets_per_second=packets_per_second,
                                             metric_count=count,
                                             event_count=event_count).persist()

        except Exception:
            log.exception("Error flushing metrics")
