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

import unittest

from six import StringIO

from tests.common import get_check


CONFIG = """
init_config:

instances:
    - host: 127.0.0.1
      port: 2181
      dimensions: {}
"""


class TestZookeeper(unittest.TestCase):

    def test_zk_stat_parsing_lt_v344(self):
        Zookeeper, instances = get_check('zk', CONFIG)
        stat_response = """Zookeeper version: 3.2.2--1, built on 03/16/2010 07:31 GMT
Clients:
 /10.42.114.160:32634[1](queued=0,recved=12,sent=0)
 /10.37.137.74:21873[1](queued=0,recved=53613,sent=0)
 /10.37.137.74:21876[1](queued=0,recved=57436,sent=0)
 /10.115.77.32:32990[1](queued=0,recved=16,sent=0)
 /10.37.137.74:21891[1](queued=0,recved=55011,sent=0)
 /10.37.137.74:21797[1](queued=0,recved=19431,sent=0)

Latency min/avg/max: -10/0/20007
Received: 101032173
Sent: 0
Outstanding: 0
Zxid: 0x1034799c7
Mode: leader
Node count: 487
"""
        expected = [
            ('zookeeper.latency.min', -10),
            ('zookeeper.latency.avg', 0),
            ('zookeeper.latency.max', 20007),
            ('zookeeper.bytes_received', 101032173),
            ('zookeeper.bytes_sent', 0),
            ('zookeeper.connections', 6),
            ('zookeeper.bytes_outstanding', 0),
            ('zookeeper.zxid.epoch', 1),
            ('zookeeper.zxid.count', 55024071),
            ('zookeeper.nodes', 487),
        ]

        buf = StringIO(stat_response)
        metrics, dimensions = Zookeeper.parse_stat(buf)

        self.assertEqual(dimensions, {'mode': 'leader'})
        self.assertEqual(metrics, expected)

    def test_zk_stat_parsing_gte_v344(self):
        Zookeeper, instances = get_check('zk', CONFIG)
        stat_response = """Zookeeper version: 3.4.5--1, built on 03/16/2010 07:31 GMT
Clients:
 /10.42.114.160:32634[1](queued=0,recved=12,sent=0)
 /10.37.137.74:21873[1](queued=0,recved=53613,sent=0)
 /10.37.137.74:21876[1](queued=0,recved=57436,sent=0)
 /10.115.77.32:32990[1](queued=0,recved=16,sent=0)
 /10.37.137.74:21891[1](queued=0,recved=55011,sent=0)
 /10.37.137.74:21797[1](queued=0,recved=19431,sent=0)

Latency min/avg/max: -10/0/20007
Received: 101032173
Sent: 0
Connections: 1
Outstanding: 0
Zxid: 0x1034799c7
Mode: leader
Node count: 487
"""
        expected = [
            ('zookeeper.latency.min', -10),
            ('zookeeper.latency.avg', 0),
            ('zookeeper.latency.max', 20007),
            ('zookeeper.bytes_received', 101032173),
            ('zookeeper.bytes_sent', 0),
            ('zookeeper.connections', 1),
            ('zookeeper.bytes_outstanding', 0),
            ('zookeeper.zxid.epoch', 1),
            ('zookeeper.zxid.count', 55024071),
            ('zookeeper.nodes', 487),
        ]

        buf = StringIO(stat_response)
        metrics, dimensions = Zookeeper.parse_stat(buf)

        self.assertEqual(dimensions, {'mode': 'leader'})
        self.assertEqual(metrics, expected)
