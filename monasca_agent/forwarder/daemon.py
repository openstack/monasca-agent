#!/usr/bin/env python
# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
    Licensed under Simplified BSD License (see LICENSE)
    (C) Boxed Ice 2010 all rights reserved
    (C) Datadog, Inc. 2010-2013 all rights reserved
"""

# Standard imports
import logging
import signal
import socket
import sys

from six import text_type

# set up logging before importing any other components
import monasca_agent.common.util as util
util.initialize_logging('forwarder')

import os
os.umask(0o22)

# Tornado
import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

# agent import
import monasca_agent.common.config as cfg
import monasca_agent.forwarder.api.monasca_api as mon


log = logging.getLogger('forwarder')

# Max amount of iterations to wait to meet min batch size before flushing
MAX_FLUSH_ATTEMPTS = 3

MIN_BATCH_SIZE = 200

message_batch = []

# In seconds
FLUSH_INTERVAL = 1


class AgentInputHandler(tornado.web.RequestHandler):
    def post(self):
        """Read the message and add it to the batch.
            Batch will be sent to Monasca API once the batch size or max wait time
            has been reached. Whichever one first.
        """
        global message_batch

        try:
            msg = tornado.escape.json_decode(self.request.body)
            message_batch.extend(msg)
        except Exception:
            log.exception('Error parsing body of Agent Input')
            raise tornado.web.HTTPError(500)


class Forwarder(tornado.web.Application):
    def __init__(self, port, agent_config, skip_ssl_validation=False,
                 use_simple_http_client=False):

        self._unflushed_iterations = 0
        self._endpoint = mon.MonascaAPI(agent_config)

        self._ioloop = tornado.ioloop.IOLoop.instance()

        self._port = int(port)
        self._flush_interval = FLUSH_INTERVAL * 1000
        self._non_local_traffic = agent_config.get("non_local_traffic", False)

        logging.getLogger().setLevel(agent_config.get('log_level', logging.INFO))

        self.skip_ssl_validation = skip_ssl_validation or agent_config.get(
            'skip_ssl_validation', False)
        self.use_simple_http_client = use_simple_http_client
        if self.skip_ssl_validation:
            log.info("Skipping SSL hostname validation, useful when using a transparent proxy")

    def log_request(self, handler):
        """Override the tornado logging method.
        If everything goes well, log level is DEBUG.
        Otherwise it's WARNING or ERROR depending on the response code.
        """
        if handler.get_status() < 400:
            log_method = log.debug
        elif handler.get_status() < 500:
            log_method = log.warning
        else:
            log_method = log.error
        request_time = 1000.0 * handler.request.request_time()
        log_method("%d %s %.2fms", handler.get_status(),
                   handler._request_summary(), request_time)

    def _add_tornado_handlers(self):
        handlers = [
            (r"/intake/?", AgentInputHandler)
        ]

        settings = dict(  # nosec B106
            cookie_secret="12oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
            xsrf_cookies=False,
            debug=False,
            log_function=self.log_request
        )

        tornado.web.Application.__init__(self, handlers, **settings)

    def _bind_http_server(self, http_server):
        try:
            # non_local_traffic must be == True to match, not just some non-false value
            if self._non_local_traffic is True:
                http_server.listen(self._port)
            else:
                # localhost in lieu of 127.0.0.1 to support IPv6
                try:
                    http_server.listen(self._port, address="localhost")
                except socket.gaierror:
                    log.warning(
                        "localhost seems undefined in your host file, using 127.0.0.1 instead")
                    http_server.listen(self._port, address="127.0.0.1")
                except socket.error as e:
                    if "Errno 99" in str(e):
                        log.warning("IPv6 doesn't seem to be fully supported. Falling back to IPv4")
                        http_server.listen(self._port, address="127.0.0.1")
                    else:
                        raise
        except socket.error as e:
            log.exception(
                "Socket error %s. Is another application listening on the same port ? Exiting", e)
            sys.exit(1)
        except Exception:
            log.exception("Uncaught exception. Forwarder is exiting.")
            sys.exit(1)

        log.info("Listening on port %d" % self._port)

    def _post_metrics(self):
        global message_batch
        self._endpoint.post_metrics(message_batch)
        log.info("wrote {}".format(len(message_batch)))
        message_batch = []
        self._unflushed_iterations = 0

    def flush(self):
        if not message_batch:
            return
        if len(message_batch) >= MIN_BATCH_SIZE or self._unflushed_iterations >= MAX_FLUSH_ATTEMPTS:
            self._post_metrics()
        else:
            self._unflushed_iterations += 1

    def run(self):
        log.info("Forwarder RUN")
        self._add_tornado_handlers()

        http_server = tornado.httpserver.HTTPServer(self)
        self._bind_http_server(http_server)

        callback = tornado.ioloop.PeriodicCallback(self.flush,
                                                   self._flush_interval)

        callback.start()

        self._ioloop.start()

    def stop(self):
        self._ioloop.stop()
        log.info("Stopped")


def init_forwarder(skip_ssl_validation=False, use_simple_http_client=False):
    config = cfg.Config()
    agent_config = config.get_config(['Main', 'Api', 'Logging'])

    port = agent_config['listen_port']
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
    tornado.options.define("sslcheck", default=1, help="Verify SSL hostname, on by default")
    tornado.options.define("use_simple_http_client", default=0,
                           help="Use Tornado SimpleHTTPClient instead of CurlAsyncHTTPClient")
    tornado.options.define("config_file", default=None,
                           help="Location for an alternate config rather than "
                                "using the default config location.")
    args = tornado.options.parse_command_line()
    skip_ssl_validation = False
    use_simple_http_client = False

    if text_type(tornado.options.options.sslcheck) == u"0":
        skip_ssl_validation = True

    if text_type(tornado.options.options.use_simple_http_client) == u"1":
        use_simple_http_client = True

    # If we don't have any arguments, run the server.
    if not args:
        app = init_forwarder(skip_ssl_validation, use_simple_http_client=use_simple_http_client)
        app.run()

    else:
        usage = "%s [help|info]. Run with no commands to start the server" % (sys.argv[0])
        command = args[0]
        if command == 'help':
            print(usage)
        else:
            print("Unknown command: %s" % command)
            print(usage)
            return -1
    return 0


if __name__ == "__main__":
    sys.exit(main())
