from keystoneclient.v3 import client as ksclient


class Keystone(object):

    # Make this a singleton class so we don't get the token every time
    # the class is created
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Keystone, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def __init__(self, config):
        self.config = config
        self._keystone_client = self._get_ksclient()

    def _get_ksclient(self):
        """Get an endpoint and auth token from Keystone.

        """
        auth_url = self.config.get('keystone_url', None)
        username = self.config.get('username', None)
        password = self.config.get('password', None)
        insecure = self.config.get('insecure', False)
        cacert = self.config.get('ca_file', None)
        project_id = self.config.get('project_id', None)
        project_name = self.config.get('project_name', None)
        project_domain_name = self.config.get('project_domain_name', None)
        project_domain_id = self.config.get('project_domain_id', None)

        kc_args = {'auth_url': auth_url,
                   'username': username,
                   'password': password}

        if insecure:
            kc_args.update({'insecure': insecure})
        else:
            if cacert:
                kc_args.update({'cacert': cacert})
        if project_id:
            kc_args.update({'project_id': project_id})
        elif project_name:
            kc_args.update({'project_name': project_name})
            if project_domain_name:
                kc_args.update({'project_domain_name': project_domain_name})
            if project_domain_id:
                kc_args.update({'project_domain_id': project_domain_id})

        return ksclient.Client(**kc_args)

    def get_token(self):
        """Validate token is project scoped and return it if it is

        project_id and auth_token were fetched when keystone client was created

        """
        if self._keystone_client.project_id:
            return self._keystone_client.auth_token
        raise exc.CommandError("User does not have a default project. "
                               "You must provide the following parameters "
                               "in the agent config file: "
                               "project_id OR (project_name AND "
                               "(project_domain OR project_domain_name)).")

    def refresh_token(self):
        """Gets a new keystone client object and token

        This method should be called if the token has expired

        """
        self._get_ksclient()
        return self.get_token()
