#!/usr/bin/env python
# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP

"""
A Python Statsd implementation with dimensions added
"""

# set up logging before importing any other components
import monasca_agent.common.util as util
util.initialize_logging('statsd')

import monasca_agent.common.config as cfg

import monasca_agent.statsd.reporter as reporter
import monasca_agent.statsd.udp as udp


# stdlib
import argparse
import logging
import signal
import sys

# project
import monasca_agent.common.aggregator as agg

log = logging.getLogger('statsd')


class MonascaStatsd(object):
    """This class is the monasca_statsd daemon. """

    def __init__(self, config_path):
        config = cfg.Config()
        statsd_config = config.get_config(['Main', 'Statsd'])

        # Create the aggregator (which is the point of communication between the server and reporting threads.
        aggregator = agg.MetricsAggregator(util.get_hostname(),
                                           recent_point_threshold=statsd_config['recent_point_threshold'],
                                           tenant_id=statsd_config.get('global_delegated_tenant', None))

        # Start the reporting thread.
        interval = int(statsd_config['monasca_statsd_interval'])
        assert 0 < interval

        self.reporter = reporter.Reporter(interval,
                                          aggregator,
                                          statsd_config['forwarder_url'],
                                          statsd_config.get('event_chunk_size'))

        # Start the server on an IPv4 stack
        if statsd_config['non_local_traffic']:
            server_host = ''
        else:
            server_host = 'localhost'

        self.server = udp.Server(aggregator, server_host, statsd_config['monasca_statsd_port'],
                                 forward_to_host=statsd_config.get('monasca_statsd_forward_host'),
                                 forward_to_port=int(statsd_config.get('monasca_statsd_forward_port')))

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
    """The main entry point for the unix version of monasca_statsd. """
    parser = argparse.ArgumentParser(description='Monasca statsd - statsd server supporting metric dimensions')
    parser.add_argument('--config', '--config-file', '-c',
                        help="Location for an alternate config rather than using the default config location.")
    args = parser.parse_args()

    monasca_statsd = MonascaStatsd(args.config)
    monasca_statsd.run()


if __name__ == '__main__':
    sys.exit(main())
