import unittest
import mock

from monasca_agent.common.keystone import Keystone
from tests.common import base_config


class TestKeystone(unittest.TestCase):

    default_endpoint_type = 'publicURL'
    default_service_type = 'monitoring'

    def testKeyStoneIsSingleton(self):
        keystone_1 = Keystone({})
        keystone_2 = Keystone({})
        keystone_3 = Keystone({})

        self.assertTrue(keystone_1 is keystone_2)
        self.assertTrue(keystone_1 is keystone_3)

    def testServiceCatalogMonascaUrlUsingDefaults(self):
        Keystone.instance = None
        with mock.patch('keystoneclient.v3.client.Client') as client:
            config = base_config.get_config('Api')
            keystone = Keystone(config)
            keystone.get_monasca_url()
            self.assertTrue(client.called)
            self.assertIn('auth_url', client.call_args[client.call_count])
            self.assertNotIn('service_type', client.call_args[client.call_count])
            self.assertNotIn('endpoint_type', client.call_args[client.call_count])
            self.assertNotIn('region_name', client.call_args[client.call_count])
            client.return_value.service_catalog.url_for.assert_has_calls([
                mock.call(endpoint_type=self.default_endpoint_type, service_type=self.default_service_type)
            ])

    def testServiceCatalogMonascaUrlWithCustomServiceType(self):
        Keystone.instance = None
        service_type = 'my_service_type'
        with mock.patch('keystoneclient.v3.client.Client') as client:
            config = base_config.get_config('Api')
            config.update({'service_type': service_type})
            keystone = Keystone(config)
            keystone.get_monasca_url()
            self.assertTrue(client.called)
            self.assertIn('auth_url', client.call_args[client.call_count])
            self.assertNotIn('service_type', client.call_args[client.call_count])
            self.assertNotIn('endpoint_type', client.call_args[client.call_count])
            self.assertNotIn('region_name', client.call_args[client.call_count])
            client.return_value.service_catalog.url_for.assert_has_calls([
                mock.call(endpoint_type=self.default_endpoint_type, service_type=service_type)
            ])

    def testServiceCatalogMonascaUrlWithCustomEndpointType(self):
        Keystone.instance = None
        endpoint_type = 'internalURL'
        with mock.patch('keystoneclient.v3.client.Client') as client:
            config = base_config.get_config('Api')
            config.update({'endpoint_type': endpoint_type})
            keystone = Keystone(config)
            keystone.get_monasca_url()
            self.assertTrue(client.called)
            self.assertIn('auth_url', client.call_args[client.call_count])
            self.assertNotIn('service_type', client.call_args[client.call_count])
            self.assertNotIn('endpoint_type', client.call_args[client.call_count])
            self.assertNotIn('region_name', client.call_args[client.call_count])
            client.return_value.service_catalog.url_for.assert_has_calls([
                mock.call(endpoint_type=endpoint_type, service_type=self.default_service_type)
            ])

    def testServiceCatalogMonascaUrlWithCustomRegionName(self):
        Keystone.instance = None
        region_name = 'my_region'
        with mock.patch('keystoneclient.v3.client.Client') as client:
            config = base_config.get_config('Api')
            config.update({'region_name': region_name})
            keystone = Keystone(config)
            keystone.get_monasca_url()
            self.assertTrue(client.called)
            self.assertIn('auth_url', client.call_args[client.call_count])
            self.assertNotIn('service_type', client.call_args[client.call_count])
            self.assertNotIn('endpoint_type', client.call_args[client.call_count])
            self.assertNotIn('region_name', client.call_args[client.call_count])
            client.return_value.service_catalog.url_for.assert_has_calls([
                mock.call(endpoint_type=self.default_endpoint_type, service_type=self.default_service_type,
                          attr='region', filter_value=region_name)
            ])

    def testServiceCatalogMonascaUrlWithThreeCustomParameters(self):
        Keystone.instance = None
        endpoint_type = 'internalURL'
        service_type = 'my_service_type'
        region_name = 'my_region'
        with mock.patch('keystoneclient.v3.client.Client') as client:
            config = base_config.get_config('Api')
            config.update({'endpoint_type': endpoint_type})
            config.update({'service_type': service_type})
            config.update({'region_name': region_name})
            keystone = Keystone(config)
            keystone.get_monasca_url()
            self.assertTrue(client.called)
            self.assertIn('auth_url', client.call_args[client.call_count])
            self.assertNotIn('service_type', client.call_args[client.call_count])
            self.assertNotIn('endpoint_type', client.call_args[client.call_count])
            self.assertNotIn('region_name', client.call_args[client.call_count])
            client.return_value.service_catalog.url_for.assert_has_calls([
                mock.call(endpoint_type=endpoint_type, service_type=service_type,
                          attr='region', filter_value=region_name)
            ])
