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

"""
Redis check tests.
"""
import logging
import os
import unittest
import subprocess
import time
import pprint
import redis

from tests.common import load_check
from nose.plugins.skip import SkipTest
logger = logging.getLogger()

MAX_WAIT = 20
NOAUTH_PORT = 16379
AUTH_PORT = 26379
DEFAULT_PORT = 6379
MISSING_KEY_TOLERANCE = 0.5


class TestRedis(unittest.TestCase):

    def is_travis(self):
        global logger
        logger.info("Running on travis-ci")
        return "TRAVIS" in os.environ

    def wait4(self, p, pattern):
        """Waits until a specific pattern shows up in the stdout
        """
        out = p.stdout
        loop = 0
        while True:
            l = out.readline()
            if l.find(pattern) > -1:
                break
            else:
                time.sleep(0.1)
                loop += 1
                if loop >= MAX_WAIT:
                    break

    def setUp(self):
        raise SkipTest("Requires Redis installed")
        if not self.is_travis():
            self.redis_noauth = subprocess.Popen(
                ["redis-server", "tests/redisnoauth.cfg"], stdout=subprocess.PIPE)
            self.wait4(self.redis_noauth, "The server is now ready to accept connections")
            self.redis_auth = subprocess.Popen(
                ["redis-server", "tests/redisauth.cfg"], stdout=subprocess.PIPE)
            self.wait4(self.redis_auth, "The server is now ready to accept connections")

    def tearDown(self):
        if not self.is_travis():
            self.redis_noauth.terminate()
            self.redis_auth.terminate()

    def test_redis_auth(self):
        # Test connection with password
        if not self.is_travis():
            # correct password
            r = load_check('redisdb', {}, {})
            instance = {
                'host': 'localhost',
                'port': AUTH_PORT,
                'password': 'datadog-is-devops-best-friend'
            }
            r.check(instance)
            metrics = self._sort_metrics(r.get_metrics())
            assert len(metrics) > 0, "No metrics returned"

            # wrong passwords
            instances = [
                {
                    'host': 'localhost',
                    'port': AUTH_PORT,
                    'password': ''
                },
                {
                    'host': 'localhost',
                    'port': AUTH_PORT,
                    'password': 'badpassword'
                }
            ]
            for instance in instances:
                r = load_check('redisdb', {}, {})
                r.check(instance)
                metrics = self._sort_metrics(r.get_metrics())
                assert len(
                    metrics) == 0, "Should have failed with bad password; got %s instead" % metrics

    def test_redis_default(self):
        # Base test, uses the noauth instance
        if self.is_travis():
            port = DEFAULT_PORT
        else:
            port = NOAUTH_PORT

        instance = {
            'host': 'localhost',
            'port': port
        }

        db = redis.Redis(port=port, db=14)  # Datadog's test db
        db.flushdb()
        db.set("key1", "value")
        db.set("key2", "value")
        db.setex("expirekey", "expirevalue", 1000)

        r = load_check('redisdb', {}, {})
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        assert metrics, "No metrics returned"

        # Assert we have values, timestamps and dimensions for each metric.
        for m in metrics:
            assert isinstance(m[1], int)    # timestamp
            assert isinstance(m[2], (int, float, long))  # value
            dimensions = m[3]["dimensions"]
            expected_dimensions = {"redis_host": "localhost", "redis_port": port}
            for e in expected_dimensions:
                assert e in dimensions

        def assert_key_present(expected, present, tolerance):
            "Assert we have the rest of the keys (with some tolerance for missing keys)"
            e = set(expected)
            p = set(present)
            assert len(e - p) < tolerance * len(e), pprint.pformat((p, e - p))

        # gauges collected?
        remaining_keys = [m[0] for m in metrics]
        expected = r.GAUGE_KEYS.values()
        assert_key_present(expected, remaining_keys, MISSING_KEY_TOLERANCE)

        # Assert that the keys metrics are tagged by db. just check db0, since
        # it's the only one we can guarantee is there.
        db_metrics = self._sort_metrics(
            [m for m in metrics if m[0] in ['redis.keys', 'redis.expires'] and "redis_db:db14" in m[3]["dimensions"]])
        self.assertEqual(2, len(db_metrics))

        self.assertEqual('redis.expires', db_metrics[0][0])
        self.assertEqual(1, db_metrics[0][2])

        self.assertEqual('redis.keys', db_metrics[1][0])
        self.assertEqual(3, db_metrics[1][2])

        # Run one more check and ensure we get total command count
        # and other rates
        time.sleep(5)
        r.check(instance)
        metrics = self._sort_metrics(r.get_metrics())
        keys = [m[0] for m in metrics]
        assert 'redis.net.commands' in keys

    def _sort_metrics(self, metrics):
        def sort_by(m):
            return m[0], m[1], m[3]
        return sorted(metrics, key=sort_by)

if __name__ == "__main__":
    unittest.main()
