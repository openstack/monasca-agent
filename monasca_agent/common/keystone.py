# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
# Copyright 2017 Fujitsu LIMITED
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

import logging

from keystoneauth1 import identity
from keystoneauth1 import session
from keystoneclient import discover
import six

from monasca_agent.common import singleton
from monasca_agent import version as ma_version

LOG = logging.getLogger(__name__)


_DEFAULT_SERVICE_TYPE = 'monitoring'
_DEFAULT_ENDPOINT_TYPE = 'public'


def _sanitize_args(data):
    """Removes keys for which value is None.

    :param data: dictionary with data
    :type data: dict
    :return: cleaned data
    :rtype: dict

    """
    return {k: v for k, v in data.items() if v is not None}


def get_session(**kwargs):
    """Creates new keystone session.

    Method uses :py:class:`keystoneauth1.identity.Password`
    abstracting from underlying Keystone version

    This method is capable of creating a session regardless of
    Keystone version (either v2 or v3). However if:

    - using **Keystone v2** following arguments [domain_id, domain_name,
      project_domain_id and project_domain_name] should not be set. Keystone V2
      does not support authentication with domain scope.
    - using **Keystone v2** following arguments are prohibited:
      [user_domain_id, user_domain_name]
    - using **Keystone v3** be careful with the scope of authentication.
      For more details about scopes refer to identity_tokens_ and v3_identity_

    .. _v3_api: https://docs.openstack.org/api-ref/identity/v3/index.html?expanded=token-authe
    ntication-with-scoped-authorization-detail
    .. _identity_tokens: https://docs.openstack.org/admin-guide/identity-tokens.html

    In overall:

    - for **Keystone V2** following arguments are allowed:
      [auth_url, user_id, username, password, trust_id, tenant_name,
      tenant_id, project_name, project_id].
    * for **Keystone V3** following argumenta are allowed:
      [auth_url, user_id, username, password, user_domain_id, user_domain_name,
      trust_id, project_id, project_name, project_domain_id,
      project_domain_name, domain_id, domain_name, tenant_id, tenant_name]

    However, note that project_id and project_name will override tenant_id
    and tenant_name, as in::

        >>> project_id = project_id or tenant_id
        >>> project_name = project_name or tenant_name

    Arguments tenant_id and tenant_name are kept for sake of
    backward compatibility between two versions of Keystone.

    Note:
        Keystone version is resolved on the runtime
        by keystoneauth1 library

    :param string auth_url: URL of keystone service.
    :param string username: Username for authentication.
    :param string password: Password for authentication.
    :param string user_id: User ID for authentication.
    :param string user_domain_id: User's domain ID for authentication
                            (replaced by default_domain_if if set)
    :param string user_domain_name: User's domain name for authentication
                            (replaced by default_domain_name if set)
    :param string project_id: Project ID for authentication
    :param string project_name: Project Name for authentication
    :param string project_domain_id: Project Domain ID for authentication
    :param string project_domain_name: Project Domain Name for authentication
    :param string tenant_id: Tenant ID for authentication
                            (replaced by project_id if set)
    :param string tenant_name: Tenant Name for authentication
                            (replaced by project_name if set)
    :param string domain_id: Domain ID for authentication.
    :param string domain_name: Domain name for authentication
    :param string trust_id: Trust ID for authentication.
    :param string default_domain_id: Default domain ID for authentication.
    :param string default_domain_name: Default domain name for authentication
    :param float keystone_timeout: A timeout to pass to requests. This should be a
                      numerical value indicating some amount (or fraction)
                      of seconds or 0 for no timeout. (optional, defaults
                      to 0)
    :param verify: The verification arguments to pass to requests. These are of
                   the same form as requests expects, so True or False to
                   verify (or not) against system certificates or a path to a
                   bundle or CA certs to check against or None for requests to
                   attempt to locate and use certificates. (optional, defaults
                   to True)
    :param bool reauthenticate: Should reauthenticate if token expires
                        (optional, defaults to True)
    :return: session instance
    :rtype: keystoneauth1.session.Session

    """

    LOG.debug('Initializing keystone session using generic password')

    auth = identity.Password(
        auth_url=kwargs.get('auth_url', None),
        username=kwargs.get('username', None),
        password=kwargs.get('password', None),
        user_id=kwargs.get('user_id', None),
        user_domain_id=kwargs.get('user_domain_id', None),
        user_domain_name=kwargs.get('user_domain_name', None),
        project_id=kwargs.get('project_id', None),
        project_name=kwargs.get('project_name', None),
        project_domain_id=kwargs.get('project_domain_id', None),
        project_domain_name=kwargs.get('project_domain_name', None),
        tenant_id=kwargs.get('tenant_id', None),
        tenant_name=kwargs.get('tenant_name', None),
        domain_id=kwargs.get('domain_id', None),
        domain_name=kwargs.get('domain_name', None),
        trust_id=kwargs.get('trust_id', None),
        default_domain_id=kwargs.get('default_domain_id', None),
        default_domain_name=kwargs.get('default_domain_name', None),
        reauthenticate=kwargs.get('reauthenticate', True)
    )
    sess = session.Session(auth=auth,
                           app_name='monasca-agent',
                           app_version=ma_version.version_string,
                           user_agent='monasca-agent',
                           timeout=kwargs.get('keystone_timeout', None),
                           verify=kwargs.get('verify', True))
    return sess


def get_client(**kwargs):
    """Creates new keystone client.

    Initializes new keystone client.
    Method does not assume what version of keystone is used.
    That responsibility is delegated to
    :py:class:`keystoneauth1.discover.Discover`.
    Version of the keystone will be the newest one available.

    There are two ways to call this method:

    using existing session object (:py:class:`keystoneauth1.session.Session`::

        >>> s = session.Session(**args)
        >>> c = get_client(session=s)

    initializing new keystone client from credentials::

        >>> c = get_client({'username':'mini-mon', 'password':'test', ...})

    :param kwargs: list of arguments passed to method
    :type kwargs: dict
    :return: keystone client instance
    :rtype: Union[keystoneclient.v3.client.Client,
                  keystoneclient.v2_0.client.Client]
    """

    if 'session' not in kwargs:
        LOG.debug('Initializing fresh keystone client')
        sess = get_session(**kwargs)
    else:
        LOG.debug('Initializing keystone client from existing session')
        sess = kwargs.get('session')

    disc = discover.Discover(session=sess)
    LOG.debug('Available keystone versions are %s' % disc.version_data())

    ks = disc.create_client(**kwargs)
    ks.auth_ref = sess.auth.get_auth_ref(session=sess)
    LOG.info('Using keystone version %s', ks.version)

    return ks


def get_args(config):
    """Utility to extract keystone args from agent's config.

    Method retrieves all keystone related settings, from
    agent's configuration, that are actually set.

    :param config: agent's config
    :type config: dict
    :returns: cleaned args
    :rtype: dict

    """
    raw_args = {
        'auth_url': config.get('keystone_url', None),
        'username': config.get('username', None),
        'password': config.get('password', None),
        'user_id': config.get('user_id', None),
        'user_domain_id': config.get('user_domain_id', None),
        'user_domain_name': config.get('user_domain_name', None),
        'project_id': config.get('project_id', None),
        'project_name': config.get('project_name', None),
        'project_domain_name': config.get('project_domain_name', None),
        'project_domain_id': config.get('project_domain_id', None),
        'domain_id': config.get('domain_id', None),
        'domain_name': config.get('domain_name', None),
        'tenant_id': config.get('tenant_id', None),
        'tenant_name': config.get('tenant_name', None),
        'trust_id': config.get('trust_id', None),
        'default_domain_id': config.get('default_domain_id', None),
        'default_domain_name': config.get('default_domain_name', None),
        'url': config.get('url', None),  # hardcoded monasca-api url
        'service_type': config.get('service_type', _DEFAULT_SERVICE_TYPE),
        'endpoint_type': config.get('endpoint_type', _DEFAULT_ENDPOINT_TYPE),
        'region_name': config.get('region_name', None),
        'keystone_timeout': config.get('keystone_timeout', None),
        'verify': False if config.get('insecure') else config.get('ca_file', None),
        'reauthenticate': config.get('reauthenticate', True)
    }
    clean_args = _sanitize_args(raw_args)

    LOG.debug('Removed %d keys that did not present values in configuration',
              len(raw_args) - len(clean_args))

    return clean_args


@six.add_metaclass(singleton.Singleton)
class Keystone(object):

    def __init__(self, config):
        self._config = get_args(config)
        self._keystone_client = None

    def _init_client(self):
        """Get a new keystone client object.

        For more details see:

        - :py:func:`monasca_agent.common.keystone.get_session(**args)`
        - :py:func:`monasca_agent.common.keystone.get_client(**args)`

        Note:
            This method initializes client only once on
            behalf of its own

        :return: keystone client instance
        :rtype: Union[keystoneclient.v3.client.Client,
                      keystoneclient.v2_0.client.Client]

        """

        if self._keystone_client:
            LOG.debug('Keystone client is already initialized')
            return self._keystone_client

        ks = get_client(**self._config)
        self._keystone_client = ks

        return ks

    def get_monasca_url(self):
        """Retrieves monasca endpoint url.

        monasca endpoint url can be retrieved from two locations:

        * agent configuration (value must be present under api.url key)
        * keystone catalog (requires settings api.service_type,
          api.endpoint_type and api.region_name)

        First method tries low-cost approach: checking if url is available
        in configuration file. If not, it moves to querying the keystone
        catalog

        :return: monasca endpoint url
        :rtype: basestring

        """
        if self._config.get('url', None):
            endpoint = self._config.get('url')
            LOG.debug('Using monasca-api url %s from configuration' % endpoint)
        else:
            # NOTE(trebskit) no need to sanitize these values here
            # as we're using already local (clean) copy
            args = {
                'service_type': self._config.get('service_type'),
                'interface': self._config.get('endpoint_type'),
                'region_name': self._config.get('region_name', None)  # that one has no default
            }
            catalog = self._init_client().auth_ref.service_catalog
            endpoint = catalog.url_for(**args)
            LOG.debug('Using monasca-api url %s from catalog[%s]'
                      % (endpoint, args))

        return endpoint

    def get_token(self):
        """Validate token is project scoped and return it if it is

        project_id and auth_token were fetched when keystone client was created

        """
        return self._init_client().auth_token

    def refresh_token(self):
        """Gets a new keystone client object and token
        This method should be called if the token has expired

        """
        self._keystone_client = None
        return self.get_token()

    def get_session(self):
        """Returns session of this client.

        :return: session instance
        :rtype: keystoneauth1.session.Session

        """
        return self._init_client().session
