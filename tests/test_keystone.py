# Copyright 2017 FUJITSU LIMITED
#
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

import mock
import random

from oslotest import base

from monasca_agent.common import keystone
from tests.common import base_config


class TestUtils(base.BaseTestCase):
    def test_should_sanitize_config(self):
        config_keys = [
            'keystone_url', 'username', 'password', 'project_name',
            'service_type', 'url', 'endpoint_type', 'region_name'
        ]
        config = {c: mock.NonCallableMock() for c in config_keys}
        random_key_for_no_value = random.choice(config_keys)
        config[random_key_for_no_value] = None

        clean = keystone.get_args(config)

        self.assertNotIn(random_key_for_no_value, clean)

    @mock.patch('monasca_agent.common.keystone.discover.Discover')
    @mock.patch('monasca_agent.common.keystone.get_session')
    def test_get_client_should_use_existing_session_if_present(self,
                                                               get_session,
                                                               _):
        sess = mock.Mock()
        sess.auth = mock.PropertyMock()
        sess.auth.get_auth_ref = mock.Mock()

        config = {
            'session': sess
        }
        keystone.get_client(**config)

        get_session.assert_not_called()

    @mock.patch('monasca_agent.common.keystone.discover.Discover')
    @mock.patch('monasca_agent.common.keystone.get_session')
    def test_get_client_should_create_session_if_missing(self,
                                                         get_session,
                                                         _):
        sess = mock.Mock()
        sess.auth = mock.PropertyMock()
        sess.auth.get_auth_ref = mock.Mock()

        config = {
            'username': __name__,
            'password': str(random.randint(10, 20))
        }
        keystone.get_client(**config)

        get_session.assert_called_once_with(**config)


class TestKeystone(base.BaseTestCase):
    default_endpoint_type = mock.NonCallableMock()
    default_service_type = mock.NonCallableMock()
    default_region_name = mock.NonCallableMock()

    def test_keystone_should_be_singleton(self):
        keystone_1 = keystone.Keystone({})
        keystone_2 = keystone.Keystone({})
        keystone_3 = keystone.Keystone({})

        self.assertTrue(keystone_1 is keystone_2)
        self.assertTrue(keystone_1 is keystone_3)

    def test_should_call_service_catalog_for_endpoint(self):
        keystone.Keystone.instance = None
        with mock.patch('keystoneauth1.identity.Password') as password, \
                mock.patch('keystoneauth1.session.Session') as session, \
                mock.patch('keystoneclient.discover.Discover') as discover:
            client = mock.Mock()
            discover.return_value = d = mock.Mock()
            d.create_client = mock.Mock(return_value=client)

            config = base_config.get_config('Api')
            config.update({
                'url': None,
                'service_type': self.default_service_type,
                'endpoint_type': self.default_endpoint_type,
                'region_name': self.default_region_name
            })

            k = keystone.Keystone(config)
            k.get_monasca_url()

            password.assert_called_once()
            session.assert_called_once()
            discover.assert_called_once()

            client.auth_ref.service_catalog.url_for.assert_called_once_with(**{
                'service_type': self.default_service_type,
                'interface': self.default_endpoint_type,
                'region_name': self.default_region_name
            })

    def test_should_use_url_from_config_catalog_config_present(self):
        keystone.Keystone.instance = None
        with mock.patch('keystoneauth1.identity.Password') as password, \
                mock.patch('keystoneauth1.session.Session') as session, \
                mock.patch('keystoneclient.discover.Discover') as discover:
            client = mock.Mock()
            discover.return_value = d = mock.Mock()
            d.create_client = mock.Mock(return_value=client)

            monasca_url = mock.NonCallableMock()

            config = base_config.get_config('Api')
            config.update({
                'url': monasca_url,
                'service_type': self.default_service_type,
                'endpoint_type': self.default_endpoint_type,
                'region_name': self.default_region_name
            })

            k = keystone.Keystone(config)
            k.get_monasca_url()

            password.assert_not_called()
            session.assert_not_called()
            discover.assert_not_called()
            client.auth_ref.service_catalog.url_for.assert_not_called()

    def test_should_use_url_from_config_if_catalog_config_missing(self):
        keystone.Keystone.instance = None
        with mock.patch('keystoneauth1.identity.Password') as password, \
                mock.patch('keystoneauth1.session.Session') as session, \
                mock.patch('keystoneclient.discover.Discover') as discover:
            client = mock.Mock()
            discover.return_value = d = mock.Mock()
            d.create_client = mock.Mock(return_value=client)

            monasca_url = mock.NonCallableMock()

            config = base_config.get_config('Api')
            config.update({
                'url': monasca_url,
                'service_type': None,
                'endpoint_type': None,
                'region_name': None
            })
            k = keystone.Keystone(config)
            k.get_monasca_url()

            password.assert_not_called()
            session.assert_not_called()
            discover.assert_not_called()
            client.auth_ref.service_catalog.url_for.assert_not_called()

    def test_should_init_client_just_once(self):
        keystone.Keystone.instance = None

        k = keystone.Keystone(config=base_config.get_config('Api'))
        client = mock.Mock()

        with mock.patch('monasca_agent.common.keystone.get_client') as gc:
            gc.return_value = client

            for _ in range(random.randint(5, 50)):
                k._init_client()

            self.assertIsNotNone(k._keystone_client)
            self.assertEqual(client, k._keystone_client)

            gc.assert_called_once()
