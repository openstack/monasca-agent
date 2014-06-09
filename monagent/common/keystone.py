import json
import requests

token = None

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

    #: Create a singleton instance. Since the connection/auth process is expensive we
    #:  don't need to do it multiple times.
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

    def get_token_password_auth(self):
        global token
        self.password_auth['auth']['identity']['password']['user']['name'] = self.user_id
        self.password_auth['auth']['identity']['password']['user']['password'] = self.password
        self.password_auth['auth']['scope']['project']['name'] = self.project_name
        data = json.dumps(self.password_auth)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        token = response.headers['X-Subject-Token']
        return token
    