import unittest

from monasca_agent.common.keystone import Keystone


class TestKeystone(unittest.TestCase):
    def testKeyStoneIsSingleton(self):
        keystone_1 = Keystone({})
        keystone_2 = Keystone({})
        keystone_3 = Keystone({})

        self.assertTrue(keystone_1 is keystone_2)
        self.assertTrue(keystone_1 is keystone_3)
