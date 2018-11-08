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
from datetime import timedelta, datetime

from six.moves import range

from monasca_agent.forwarder.transaction import Transaction, TransactionManager
from monasca_agent.forwarder.daemon import MAX_QUEUE_SIZE, THROTTLING_DELAY


class memTransaction(Transaction):

    def __init__(self, size, manager):
        Transaction.__init__(self)
        self._trManager = manager
        self._size = size
        self._flush_count = 0

        self.is_flushable = False

    def flush(self):
        self._flush_count += 1
        if self.is_flushable:
            self._trManager.tr_success(self)
        else:
            self._trManager.tr_error(self)

        self._trManager.flush_next()


class TestTransaction(unittest.TestCase):

    def setUp(self):
        pass

    def testMemoryLimit(self):
        """Test memory limit as well as simple flush"""

        # No throttling, no delay for replay
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE, timedelta(seconds=0), {'dimensions': {}})

        step = 10
        oneTrSize = (MAX_QUEUE_SIZE / step) - 1
        for i in range(step):
            tr = memTransaction(oneTrSize, trManager)
            trManager.append(tr)

        trManager.flush()

        # There should be exactly step transaction in the list, with
        # a flush count of 1
        self.assertEqual(len(trManager._transactions), step)
        for tr in trManager._transactions:
            self.assertEqual(tr._flush_count, 1)

        # Try to add one more
        tr = memTransaction(oneTrSize + 10, trManager)
        trManager.append(tr)

        # At this point, transaction one (the oldest) should have been removed from the list
        self.assertEqual(len(trManager._transactions), step)
        for tr in trManager._transactions:
            self.assertNotEqual(tr._id, 1)

        trManager.flush()
        self.assertEqual(len(trManager._transactions), step)
        # Check and allow transactions to be flushed
        for tr in trManager._transactions:
            tr.is_flushable = True
            # Last transaction has been flushed only once
            if tr._id == step + 1:
                self.assertEqual(tr._flush_count, 1)
            else:
                self.assertEqual(tr._flush_count, 2)

        trManager.flush()
        self.assertEqual(len(trManager._transactions), 0)

    def testThrottling(self):
        """Test throttling while flushing"""

        # No throttling, no delay for replay
        trManager = TransactionManager(timedelta(seconds=0), MAX_QUEUE_SIZE, THROTTLING_DELAY, {'dimensions': {}})
        trManager._flush_without_ioloop = True  # Use blocking API to emulate tornado ioloop

        # Add 3 transactions, make sure no memory limit is in the way
        oneTrSize = MAX_QUEUE_SIZE / 10
        for i in range(3):
            tr = memTransaction(oneTrSize, trManager)
            trManager.append(tr)

        # Try to flush them, time it
        before = datetime.now()
        trManager.flush()
        after = datetime.now()
        self.assertTrue((after - before) > 3 * THROTTLING_DELAY - timedelta(microseconds=100000),
                        "before = %s after = %s" % (before, after))


if __name__ == '__main__':
    unittest.main()
