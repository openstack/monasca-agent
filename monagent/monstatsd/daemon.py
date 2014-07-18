#!/usr/bin/env python
"""
A Python Statsd implementation with dimensions added
"""

# set up logging before importing any other components
from monagent.common.config import initialize_logging
from monagent.monstatsd.reporter import Reporter
from monagent.monstatsd.udp import Server

initialize_logging('monstatsd')

import os
os.umask(0o22)

# stdlib
import logging
import optparse
import signal
import sys

# project
from monagent.common.aggregator import MetricsBucketAggregator
from monagent.common.check_status import MonstatsdStatus
from monagent.common.config import get_config
from monagent.common.daemon import Daemon, AgentSupervisor
from monagent.common.util import PidFile, get_hostname

log = logging.getLogger('monstatsd')


class Monstatsd(Daemon):

    """ This class is the monstatsd daemon. """

    def __init__(self, pid_file, server, reporter, autorestart):
        Daemon.__init__(self, pid_file, autorestart=autorestart)
        self.server = server
        self.reporter = reporter

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm. Stopping run loop.")
        self.server.stop()

    def run(self):
        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # Start the reporting thread before accepting data
        self.reporter.start()

        try:
            try:
                self.server.start()
            except Exception as e:
                log.exception('Error starting server')
                raise e
        finally:
            # The server will block until it's done. Once we're here, shutdown
            # the reporting thread.
            self.reporter.stop()
            self.reporter.join()
            log.info("Monstatsd is stopped")
            # Restart if asked to restart
            if self.autorestart:
                sys.exit(AgentSupervisor.RESTART_EXIT_STATUS)

    def info(self):
        logging.getLogger().setLevel(logging.ERROR)
        return MonstatsdStatus.print_latest_status()


def init_monstatsd(config_path=None, use_watchdog=False):
    """Configure the server and the reporting thread.
    """
    c = get_config(parse_args=False, cfg_path=config_path)
    log.debug("Configuration monstatsd")

    port = c['monstatsd_port']
    interval = int(c['monstatsd_interval'])
    aggregator_interval = int(c['monstatsd_agregator_bucket_size'])
    non_local_traffic = c['non_local_traffic']
    forward_to_host = c.get('statsd_forward_host')
    forward_to_port = c.get('statsd_forward_port')
    event_chunk_size = c.get('event_chunk_size')

    target = c['forwarder_url']

    hostname = get_hostname(c)

    # Create the aggregator (which is the point of communication between the
    # server and reporting threads.
    assert 0 < interval

    aggregator = MetricsBucketAggregator(
        hostname,
        aggregator_interval,
        recent_point_threshold=c.get(
            'recent_point_threshold',
            None))

    # Start the reporting thread.
    reporter = Reporter(interval, aggregator, target, use_watchdog, event_chunk_size)

    # Start the server on an IPv4 stack
    # Default to loopback
    server_host = 'localhost'
    # If specified, bind to all addressses
    if non_local_traffic:
        server_host = ''

    server = Server(aggregator, server_host, port, forward_to_host=forward_to_host,
                    forward_to_port=forward_to_port)

    return reporter, server, c


def main(config_path=None):
    """ The main entry point for the unix version of monstatsd. """
    parser = optparse.OptionParser("%prog [start|stop|restart|status]")
    opts, args = parser.parse_args()

    reporter, server, cnf = init_monstatsd(config_path, use_watchdog=True)
    pid_file = PidFile('monstatsd')
    daemon = Monstatsd(pid_file.get_path(), server, reporter,
                       cnf.get('autorestart', False))

    # If no args were passed in, run the server in the foreground.
    # todo does this need to be a daemon even when it basically always runs in the foreground, if not
    # restructure and get rid of the silly init_function
    if not args:
        daemon.run()
        return 0

    # Otherwise, we're process the deamon command.
    else:
        command = args[0]

        if command == 'start':
            daemon.start()
        elif command == 'stop':
            daemon.stop()
        elif command == 'restart':
            daemon.restart()
        elif command == 'status':
            daemon.status()
        elif command == 'info':
            return daemon.info()
        else:
            sys.stderr.write("Unknown command: %s\n\n" % command)
            parser.print_help()
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())
