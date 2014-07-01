import json
import requests


class Keystone(object):

    password_auth = {
        "auth": {
            "identity": {
                "methods": [
                    "password"
                ],
                "password": {
                    "user": {
                        "domain": {
                            "name": "Default"
                        },
                        "name": "",
                        "password": ""
                    }
                }
            },
            "scope": {
                "project": {
                    "domain": {
                        "name": "Default"
                    },
                    "name": ""
                }
            }
        }
    }

    # Make this a singleton class so we don't get the token every time
    # the class is created
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Keystone, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def __init__(self, endpoint, user_id, password, project_name):
        self.endpoint = endpoint
        self.user_id = user_id
        self.password = password
        self.project_name = project_name
        self.token = None

    def get_token(self):
        if not self.token:
            return self.refresh_token()
        return self.token

    def refresh_token(self):
        self.password_auth['auth']['identity']['password']['user']['name'] = self.user_id
        self.password_auth['auth']['identity']['password']['user']['password'] = self.password
        self.password_auth['auth']['scope']['project']['name'] = self.project_name
        data = json.dumps(self.password_auth)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            self.endpoint.rstrip('/') + '/auth/tokens', data=data, headers=headers)
        response.raise_for_status()
        self.token = response.headers['X-Subject-Token']
        return self.token
