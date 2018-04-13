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

# stdlib
import unittest
import logging
import gc
import sys

# 3p
# from nose.plugins.attrib import attr

# project
from monasca_agent.collector import checks as w32
from nose.plugins.skip import SkipTest

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)


AGENT_CONFIG = {}  # None of the windows checks use this.


class TestWin32(unittest.TestCase):

    def _checkMemoryLeak(self, func):
        # FIXME: This should use @attr('windows')instead of checking for the
        # platform, but just importing nose.plugins.attrib causes all the tests
        # to fail with uncollected garbage.
        if sys.platform != 'win32':
            return
        gc.set_debug(gc.DEBUG_LEAK)
        try:
            start = len(gc.garbage)
            func()
            end = len(gc.garbage)
            self.assertEqual(end - start, 0, gc.garbage)
        finally:
            gc.set_debug(0)

    def testDisk(self):
        raise SkipTest("Skipped windows support is temporarily broken.")
        dsk = w32.Disk(log)
        self._checkMemoryLeak(lambda: dsk.check(AGENT_CONFIG))

    def testIO(self):
        raise SkipTest("Skipped windows support is temporarily broken.")
        io = w32.IO(log)
        self._checkMemoryLeak(lambda: io.check(AGENT_CONFIG))

    def testProcesses(self):
        raise SkipTest("Skipped windows support is temporarily broken.")
        proc = w32.Processes(log)
        self._checkMemoryLeak(lambda: proc.check(AGENT_CONFIG))

    def testMemory(self):
        raise SkipTest("Skipped windows support is temporarily broken.")
        mem = w32.Memory(log)
        self._checkMemoryLeak(lambda: mem.check(AGENT_CONFIG))

    def testNetwork(self):
        raise SkipTest("Skipped windows support is temporarily broken.")
        net = w32.Network(log)
        self._checkMemoryLeak(lambda: net.check(AGENT_CONFIG))

    def testCPU(self):
        raise SkipTest("Skipped windows support is temporarily broken.")
        cpu = w32.Cpu(log)
        self._checkMemoryLeak(lambda: cpu.check(AGENT_CONFIG))


if __name__ == "__main__":
    unittest.main()
