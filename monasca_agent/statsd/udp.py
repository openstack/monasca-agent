# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
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

import ast
import logging
import select
import socket

import monasca_agent.common.metrics as metrics_pkg

log = logging.getLogger(__name__)


UDP_SOCKET_TIMEOUT = 5

metric_class = {
    'g': metrics_pkg.Gauge,
    'c': metrics_pkg.Counter,
    'r': metrics_pkg.Rate,
    'ms': metrics_pkg.Gauge,
    'h': metrics_pkg.Gauge
}


class Server(object):
    """A statsd udp server."""

    def __init__(self, aggregator, host, port, forward_to_host=None, forward_to_port=None):
        self.host = host
        self.port = int(port)
        self.address = (self.host, self.port)
        self.aggregator = aggregator
        self.buffer_size = 1024 * 8

        self.running = False

        self.should_forward = forward_to_host is not None

        self.forward_udp_sock = None
        # In case we want to forward every packet received to another statsd server
        if self.should_forward:
            if forward_to_port is None:
                forward_to_port = 8125

            log.info(
                "External statsd forwarding enabled. All packets received will"
                "be forwarded to %s:%s" %
                (forward_to_host, forward_to_port))
            try:
                self.forward_udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.forward_udp_sock.connect((forward_to_host, forward_to_port))
            except Exception:
                log.exception("Error while setting up connection to external statsd server")

    @staticmethod
    def _parse_service_check_packet(packet):
        parts = packet.split('|')
        name = parts[1]
        status = int(parts[2])
        dimensions = {}
        for metadata in parts[3:]:
            if metadata.startswith('#'):
                dimensions = Server._parse_dogstatsd_tags(metadata)

        return name, status, dimensions

    @staticmethod
    def _parse_metric_packet(packet):
        name_and_metadata = packet.split(':', 1)

        if len(name_and_metadata) != 2:
            raise Exception('Unparseable metric packet: %s' % packet)

        name = name_and_metadata[0]
        metadata = name_and_metadata[1].split('|')

        if len(metadata) < 2:
            raise Exception('Unparseable metric packet: %s' % packet)

        # Submit the metric
        raw_value = metadata[0]
        metric_type = metadata[1]

        if metric_type == 's':
            value = raw_value
        else:
            # Try to cast as an int first to avoid precision issues, then as a
            # float.
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError:
                    # Otherwise, raise an error saying it must be a number
                    raise Exception('Metric value must be a number: %s, %s' % (name, raw_value))

        # Parse the optional values - sample rate & dimensions.
        sample_rate = 1
        dimensions = {}
        for m in metadata[2:]:
            # Parse the sample rate
            if m[0] == '@':
                sample_rate = float(m[1:])
                assert 0 <= sample_rate <= 1
            # Parse dimensions, supporting both Monasca and DogStatsd extensions
            elif m[0] == '#' and len(m) > 2:
                if m[1] == '{':
                    dimensions = Server._parse_monasca_statsd_dims(m[1:])
                else:
                    dimensions = Server._parse_dogstatsd_tags(m[1:])

        return name, value, metric_type, dimensions, sample_rate

    @staticmethod
    def _parse_monasca_statsd_dims(dimensions):
        dimensions = ast.literal_eval(dimensions)
        return dimensions

    @staticmethod
    def _parse_dogstatsd_tags(statsd_msg):
        dimensions = {}
        s = ''
        key = ''
        for c in statsd_msg[1:]:
            if c == ':':
                key = s.strip()
                s = ''
            elif c == ',':
                s = s.strip()
                if len(key) > 0:
                    if len(s) > 0:
                        dimensions[key] = s
                    else:
                        dimensions[key] = '?'
                elif len(s) > 0:
                    # handle tags w/o value
                    dimensions[s] = "True"
                key = ''
                s = ''
            else:
                s += c
        s = s.strip()
        if len(s) > 0 and len(key) > 0:
            dimensions[key] = s

        return dimensions

    def submit_packets(self, packets):
        for packet in packets.split(b"\n"):

            packet = packet.decode("utf-8")
            if not packet.strip():
                continue

            if packet.startswith('_e'):
                # Monasca api doesnt support events
                log.warn("events not supported.")
                continue
            elif packet.startswith('_sc'):
                sample_rate = 1.0
                mtype = 'g'
                name, value, dimensions = self._parse_service_check_packet(packet)
            else:
                name, value, mtype, dimensions, sample_rate = self._parse_metric_packet(packet)

            if mtype not in metric_class:
                log.warn("metric type {} not supported.".format(mtype))
                continue

            self.aggregator.submit_metric(name,
                                          value,
                                          metric_class[mtype],
                                          dimensions=dimensions,
                                          sample_rate=sample_rate)

    def start(self):
        """Run the server."""
        # Bind to the UDP socket.
        # IPv4 only
        open_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        open_socket.setblocking(0)
        try:
            open_socket.bind(self.address)
        except socket.gaierror:
            if self.address[0] == 'localhost':
                log.warning(
                    "Warning localhost seems undefined in your host file, using 127.0.0.1 instead")
                self.address = ('127.0.0.1', self.address[1])
                open_socket.bind(self.address)

        log.info('Listening on host & port: %s' % str(self.address))

        # Inline variables for quick look-up.
        buffer_size = self.buffer_size
        sock = [open_socket]
        socket_recv = open_socket.recv
        select_select = select.select
        select_error = select.error
        timeout = UDP_SOCKET_TIMEOUT
        should_forward = self.should_forward
        forward_udp_sock = self.forward_udp_sock

        # Run our select loop.
        self.running = True
        while self.running:
            try:
                ready = select_select(sock, [], [], timeout)
                if ready[0]:
                    message = socket_recv(buffer_size)
                    self.submit_packets(message)

                    if should_forward:
                        forward_udp_sock.send(message)
            except select_error as se:
                # Ignore interrupted system calls from sigterm.
                errno = se[0]
                if errno != 4:
                    raise
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception:
                log.exception('Error receiving datagram')

    def stop(self):
        self.running = False
