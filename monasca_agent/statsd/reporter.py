# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
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
import threading

import monasca_agent.common.emitter as emitter
import monasca_agent.common.util as util

log = logging.getLogger(__name__)


# Since we call flush more often than the metrics aggregation interval, we should
#  log a bunch of flushes in a row every so often.
FLUSH_LOGGING_PERIOD = 70
FLUSH_LOGGING_INITIAL = 10
FLUSH_LOGGING_COUNT = 5
EVENT_CHUNK_SIZE = 50


class Reporter(threading.Thread):
    """The reporter periodically sends the aggregated metrics to the
    server.
    """

    def __init__(self, interval, aggregator, api_host, event_chunk_size=None):
        threading.Thread.__init__(self)
        self.interval = int(interval)
        self.finished = threading.Event()
        self.aggregator = aggregator
        self.flush_count = 0
        self.log_count = 0

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

        while not self.finished.isSet():  # Use camel case isSet for 2.4 support.
            self.finished.wait(self.interval)
            self.flush()

        # Clean up the status messages.
        log.debug("Stopped reporter")

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

            should_log = self.flush_count <= FLUSH_LOGGING_INITIAL \
                or self.log_count <= FLUSH_LOGGING_COUNT
            log_func = log.info
            if not should_log:
                log_func = log.debug
            log_func(
                "Flush #%s: flushed %s metric%s" %
                (self.flush_count,
                 count,
                 util.plural(count)))
            if self.flush_count == FLUSH_LOGGING_INITIAL:
                log.info(
                    "First flushes done, %s flushes will be logged every %s flushes." %
                    (FLUSH_LOGGING_COUNT, FLUSH_LOGGING_PERIOD))
        except Exception:
            log.exception("Error flushing metrics")
