#!/usr/bin/env python
"""
    Datadog
    www.datadoghq.com
    ----
    Make sense of your IT Data

    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010-2013 all rights reserved
"""

# set up logging before importing any other components
from monagent.common.config import initialize_logging
from monagent.forwarder.api.mon import MonAPI

initialize_logging('forwarder')
from monagent.common.config import get_logging_config

import os
os.umask(0o22)

# Standard imports
import logging
import sys
from datetime import timedelta
import signal
from socket import gaierror, error as socket_error

# Tornado
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.escape import json_decode
from tornado.options import define, parse_command_line, options

# agent import
from monagent.common.check_status import ForwarderStatus
from monagent.common.config import get_config
from monagent.common.metrics import Measurement
from monagent.common.util import Watchdog, get_tornado_ioloop
from transaction import Transaction, TransactionManager

log = logging.getLogger('forwarder')
log.setLevel(get_logging_config()['log_level'] or logging.INFO)

TRANSACTION_FLUSH_INTERVAL = 5000  # Every 5 seconds
WATCHDOG_INTERVAL_MULTIPLIER = 10  # 10x flush interval

# Maximum delay before replaying a transaction
MAX_WAIT_FOR_REPLAY = timedelta(seconds=90)

# Maximum queue size in bytes (when this is reached, old messages are dropped)
MAX_QUEUE_SIZE = 30 * 1024 * 1024  # 30MB

THROTTLING_DELAY = timedelta(microseconds=1000000 / 2)  # 2 msg/second


class MetricTransaction(Transaction):

    _application = None
    _trManager = None
    _endpoints = []

    @classmethod
    def set_application(cls, app):
        cls._application = app

    @classmethod
    def set_tr_manager(cls, manager):
        cls._trManager = manager

    @classmethod
    def get_tr_manager(cls):
        return cls._trManager

    @classmethod
    def set_endpoints(cls, endpoint):
        # todo we only have one endpoint option, generalize it better
        # the immediate use case for two endpoints could be our own monitoring boxes, they could send to
        # the main api and mini-mon api
        cls._endpoints.append(endpoint)

    def __init__(self, data, headers):
        self._data = data
        self._headers = headers

        # Call after data has been set (size is computed in Transaction's init)
        Transaction.__init__(self)

        # Insert the transaction in the Manager
        self._trManager.append(self)
        log.debug("Created transaction %d" % self.get_id())
        self._trManager.flush()

    def __sizeof__(self):
        return sys.getsizeof(self._data)

    def flush(self):
        try:
            for endpoint in self._endpoints:
                endpoint.post_metrics(self._data)
        except Exception:
            log.exception('Error flushing metrics to remote endpoints')
            self._trManager.tr_error(self)
        else:
            self._trManager.tr_success(self)
        self._trManager.flush_next()


class StatusHandler(tornado.web.RequestHandler):

    def get(self):
        threshold = int(self.get_argument('threshold', -1))

        m = MetricTransaction.get_tr_manager()

        self.write(
            "<table><tr><td>Id</td><td>Size</td><td>Error count</td><td>Next flush</td></tr>")
        transactions = m.get_transactions()
        for tr in transactions:
            self.write("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" %
                       (tr.get_id(), tr.get_size(), tr.get_error_count(), tr.get_next_flush()))
        self.write("</table>")

        if threshold >= 0:
            if len(transactions) > threshold:
                self.set_status(503)


class AgentInputHandler(tornado.web.RequestHandler):

    def post(self):
        """Read the message and forward it to the intake
            The message is expected to follow the format:

        """
        # read the message it should be a list of
        # monagent.common.metrics.Measurements expressed as a dict
        msg = tornado.escape.json_decode(self.request.body)
        try:
            measurements = [Measurement(**m) for m in msg]
        except Exception:
            log.exception('Error parsing body of Agent Input')
            raise tornado.web.HTTPError(500)

        headers = self.request.headers

        if len(measurements) > 0:
            # Setup a transaction for this message
            tr = MetricTransaction(measurements, headers)
        else:
            raise tornado.web.HTTPError(500)

        self.write("Transaction: %s" % tr.get_id())


class Forwarder(tornado.web.Application):

    def __init__(self, port, agent_config, watchdog=True, skip_ssl_validation=False,
                 use_simple_http_client=False):
        self._port = int(port)
        self._agentConfig = agent_config
        self._metrics = {}
        MetricTransaction.set_application(self)
        MetricTransaction.set_endpoints(MonAPI(agent_config['Api']))
        self._tr_manager = TransactionManager(MAX_WAIT_FOR_REPLAY, MAX_QUEUE_SIZE, THROTTLING_DELAY)
        MetricTransaction.set_tr_manager(self._tr_manager)

        self._watchdog = None
        self.skip_ssl_validation = skip_ssl_validation or agent_config.get(
            'skip_ssl_validation', False)
        self.use_simple_http_client = use_simple_http_client
        if self.skip_ssl_validation:
            log.info("Skipping SSL hostname validation, useful when using a transparent proxy")

        if watchdog:
            watchdog_timeout = TRANSACTION_FLUSH_INTERVAL * WATCHDOG_INTERVAL_MULTIPLIER
            self._watchdog = Watchdog(
                watchdog_timeout, max_mem_mb=agent_config.get('limit_memory_consumption', None))

    def _post_metrics(self):

        if len(self._metrics) > 0:
            MetricTransaction(self._metrics, headers={'Content-Type': 'application/json'})
            self._metrics = {}

    # todo why is the tornado logging method overridden? Perhaps ditch this.
    def log_request(self, handler):
        """ Override the tornado logging method.
        If everything goes well, log level is DEBUG.
        Otherwise it's WARNING or ERROR depending on the response code. """
        if handler.get_status() < 400:
            log_method = log.debug
        elif handler.get_status() < 500:
            log_method = log.warning
        else:
            log_method = log.error
        request_time = 1000.0 * handler.request.request_time()
        log_method("%d %s %.2fms", handler.get_status(),
                   handler._request_summary(), request_time)

    def run(self):
        handlers = [
            (r"/intake/?", AgentInputHandler),
            (r"/api/v1/series/?", AgentInputHandler),
            (r"/status/?", StatusHandler),
        ]

        settings = dict(
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=False,
            log_function=self.log_request
        )

        non_local_traffic = self._agentConfig.get("non_local_traffic", False)

        tornado.web.Application.__init__(self, handlers, **settings)
        http_server = tornado.httpserver.HTTPServer(self)

        try:
            # non_local_traffic must be == True to match, not just some non-false value
            if non_local_traffic is True:
                http_server.listen(self._port)
            else:
                # localhost in lieu of 127.0.0.1 to support IPv6
                try:
                    http_server.listen(self._port, address="localhost")
                except gaierror:
                    log.warning(
                        "localhost seems undefined in your host file, using 127.0.0.1 instead")
                    http_server.listen(self._port, address="127.0.0.1")
                except socket_error as e:
                    if "Errno 99" in str(e):
                        log.warning("IPv6 doesn't seem to be fully supported. Falling back to IPv4")
                        http_server.listen(self._port, address="127.0.0.1")
                    else:
                        raise
        except socket_error as e:
            log.exception(
                "Socket error %s. Is another application listening on the same port ? Exiting", e)
            sys.exit(1)
        except Exception:
            log.exception("Uncaught exception. Forwarder is exiting.")
            sys.exit(1)

        log.info("Listening on port %d" % self._port)

        # Register callbacks
        self.mloop = get_tornado_ioloop()

        logging.getLogger().setLevel(get_logging_config()['log_level'] or logging.INFO)

        def flush_trs():
            if self._watchdog:
                self._watchdog.reset()
            self._post_metrics()
            self._tr_manager.flush()

        tr_sched = tornado.ioloop.PeriodicCallback(
            flush_trs, TRANSACTION_FLUSH_INTERVAL, io_loop=self.mloop)

        # Start everything
        if self._watchdog:
            self._watchdog.reset()
        tr_sched.start()

        self.mloop.start()
        log.info("Stopped")

    def stop(self):
        self.mloop.stop()


def init_forwarder(skip_ssl_validation=False, use_simple_http_client=False):
    agent_config = get_config(parse_args=False)

    port = agent_config.get('listen_port', 17123)
    if port is None:
        port = 17123
    else:
        port = int(port)

    app = Forwarder(port, agent_config, skip_ssl_validation=skip_ssl_validation,
                    use_simple_http_client=use_simple_http_client)

    def sigterm_handler(signum, frame):
        log.info("caught sigterm. stopping")
        app.stop()

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    return app


def main():
    define("sslcheck", default=1, help="Verify SSL hostname, on by default")
    define("use_simple_http_client", default=0,
           help="Use Tornado SimpleHTTPClient instead of CurlAsyncHTTPClient")
    args = parse_command_line()
    skip_ssl_validation = False
    use_simple_http_client = False

    if unicode(options.sslcheck) == u"0":
        skip_ssl_validation = True

    if unicode(options.use_simple_http_client) == u"1":
        use_simple_http_client = True

    # If we don't have any arguments, run the server.
    if not args:
        app = init_forwarder(skip_ssl_validation, use_simple_http_client=use_simple_http_client)
        try:
            app.run()
        finally:
            ForwarderStatus.remove_latest_status()

    else:
        usage = "%s [help|info]. Run with no commands to start the server" % (sys.argv[0])
        command = args[0]
        if command == 'info':
            logging.getLogger().setLevel(logging.ERROR)
            return ForwarderStatus.print_latest_status()
        elif command == 'help':
            print(usage)
        else:
            print("Unknown command: %s" % command)
            print(usage)
            return -1
    return 0

if __name__ == "__main__":
    sys.exit(main())
