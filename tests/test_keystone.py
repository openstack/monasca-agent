import os.path
import tempfile
import unittest

from monasca_agent.common.keystone import Keystone
from monasca_agent.common.util import is_valid_hostname
from monasca_agent.common.util import PidFile


class TestConfig(unittest.TestCase):
    def testKeyStoneIsSingleton(self):
        keystone_1 = Keystone({})
        keystone_2 = Keystone({})
        keystone_3 = Keystone({})

        self.assertTrue(keystone_1 is keystone_2)
        self.assertTrue(keystone_1 is keystone_3)
