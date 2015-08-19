# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import six

from monascaclient import ksclient

import monasca_agent.common.singleton as singleton

log = logging.getLogger(__name__)


# Make this a singleton class so we don't get the token every time
# the class is created
@six.add_metaclass(singleton.Singleton)
class Keystone(object):

    def __init__(self, config):
        self.config = config
        self._keystone_client = None
        self._token = None

    def get_credential_args(self):
        auth_url = self.config.get('keystone_url', None)
        username = self.config.get('username', None)
        password = str(self.config.get('password', None))
        user_domain_id = self.config.get('user_domain_id', None)
        user_domain_name = self.config.get('user_domain_name', None)
        insecure = self.config.get('insecure', False)
        cacert = self.config.get('ca_file', None)
        project_id = self.config.get('project_id', None)
        project_name = self.config.get('project_name', None)
        project_domain_name = self.config.get('project_domain_name', None)
        project_domain_id = self.config.get('project_domain_id', None)
        keystone_timeout = self.config.get('keystone_timeout', None)

        kc_args = {'auth_url': auth_url,
                   'username': username,
                   'password': password,
                   'keystone_timeout': keystone_timeout}

        if user_domain_id:
            kc_args.update({'user_domain_id': user_domain_id})
        elif user_domain_name:
            kc_args.update({'user_domain_name': user_domain_name})

        if insecure:
            kc_args.update({'insecure': insecure})
        else:
            if cacert:
                kc_args.update({'os_cacert': cacert})
        if project_id:
            kc_args.update({'project_id': project_id})
        elif project_name:
            kc_args.update({'project_name': project_name})
            if project_domain_name:
                kc_args.update({'domain_name': project_domain_name})
            if project_domain_id:
                kc_args.update({'domain_id': project_domain_id})
        return kc_args

    def _get_ksclient(self):
        """Get an endpoint and auth token from Keystone.

        """
        kc_args = self.get_credential_args()
        return ksclient.KSClient(**kc_args)

    def get_monasca_url(self):
        if not self._keystone_client:
            self.get_token()

        if self._keystone_client:
            return self._keystone_client.monasca_url
        else:
            return None

    def get_token(self):
        """Validate token is project scoped and return it if it is

        project_id and auth_token were fetched when keystone client was created

        """
        if not self._token:
            if not self._keystone_client:
                try:
                    self._keystone_client = self._get_ksclient()
                except Exception as exc:
                    log.error("Unable to create the Keystone Client. " +
                              "Error was {0}".format(repr(exc)))
                    return None

            self._token = self._keystone_client.token

        return self._token

    def refresh_token(self):
        """Gets a new keystone client object and token

        This method should be called if the token has expired

        """
        self._token = None
        self._keystone_client = None
        return self.get_token()
