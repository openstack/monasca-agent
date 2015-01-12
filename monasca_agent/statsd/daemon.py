#!/usr/bin/env python
"""
A Python Statsd implementation with dimensions added
"""

# set up logging before importing any other components
from monasca_agent.common.config import initialize_logging
from monasca_agent.statsd.reporter import Reporter
from monasca_agent.statsd.udp import Server

initialize_logging('statsd')

# stdlib
import argparse
import logging
import signal
import sys

# project
from monasca_agent.common.aggregator import MetricsAggregator
from monasca_agent.common.check_status import MonascaStatsdStatus
from monasca_agent.common.config import get_config
from monasca_agent.common.util import get_hostname

log = logging.getLogger('statsd')


class MonascaStatsd(object):
    """ This class is the monasca_statsd daemon. """

    def __init__(self, config_path):
        config = get_config(parse_args=False, cfg_path=config_path)

        # Create the aggregator (which is the point of communication between the server and reporting threads.
        aggregator = MetricsAggregator(get_hostname(config),
                                             int(config['monasca_statsd_agregator_interval']),
                                             recent_point_threshold=config.get('recent_point_threshold', None))

        # Start the reporting thread.
        interval = int(config['monasca_statsd_interval'])
        assert 0 < interval
        self.reporter = Reporter(interval, aggregator, config['forwarder_url'], True, config.get('event_chunk_size'))

        # Start the server on an IPv4 stack
        if config['non_local_traffic']:
            server_host = ''
        else:
            server_host = 'localhost'

        self.server = Server(aggregator, server_host, config['monasca_statsd_port'],
                             forward_to_host=config.get('statsd_forward_host'),
                             forward_to_port=config.get('statsd_forward_port'))

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
            log.info("monasca_statsd is stopped")


def main():
    """ The main entry point for the unix version of monasca_statsd. """
    parser = argparse.ArgumentParser(description='Monasca statsd - statsd server supporting metric dimensions')
    parser.add_argument('--config', '-c',
                        help="Location for an alternate config rather than using the default config location.")
    parser.add_argument('--info', action='store_true', help="Output info about the running Monasca Statsd")
    args = parser.parse_args()

    if args.info:
        logging.getLogger().setLevel(logging.ERROR)
        return MonascaStatsdStatus.print_latest_status()

    monasca_statsd = MonascaStatsd(args.config)
    monasca_statsd.run()


if __name__ == '__main__':
    sys.exit(main())
