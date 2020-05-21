from unittest import mock
import unittest

import monasca_agent.common.metrics as metrics_pkg
import monasca_agent.statsd.udp as udp


class TestStatsd(unittest.TestCase):
    def testSubmitPacket(self):
        mock_aggregator = mock.Mock()
        srv = udp.Server(mock_aggregator, 'localhost', 1234)
        test_packet = b"monasca.log.out_logs_truncated_bytes:0|g|#" \
            b"{'service': 'monitoring', 'component': 'monasca-log-api'}"
        srv.submit_packets(test_packet)
        mock_aggregator.submit_metric.assert_called_once_with(
            'monasca.log.out_logs_truncated_bytes',
            0,
            metrics_pkg.Gauge,
            dimensions={
                'service': 'monitoring',
                'component': 'monasca-log-api'},
            sample_rate=1)

    def testSubmitPackets(self):
        mock_aggregator = mock.Mock()
        srv = udp.Server(mock_aggregator, 'localhost', 1234)
        test_packet = b"monasca.log.out_logs_truncated_bytes:0|g|#" \
            b"{'service': 'monitoring', 'component': 'monasca-log-api'}\n" \
            b"application_metric:10|c|#{'service': 'workload'}"
        srv.submit_packets(test_packet)
        mock_aggregator.submit_metric.assert_has_calls([
            mock.call(
                'monasca.log.out_logs_truncated_bytes',
                0,
                metrics_pkg.Gauge,
                dimensions={
                    'service': 'monitoring',
                    'component': 'monasca-log-api'},
                sample_rate=1
            ),
            mock.call(
                'application_metric',
                10,
                metrics_pkg.Counter,
                dimensions={
                    'service': 'workload'},
                sample_rate=1
            )
        ])
