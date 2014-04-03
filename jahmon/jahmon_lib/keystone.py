import requests

from util import json, md5

class Keystone(object):

    password_auth = {
        "auth": {
            "identity": {
                "methods": [
                    "password"
                ],
                "password": {
                    "user": {
                    }
                }
            },
            "scope": {
                "project": {
                }
            }
        }
    }

    access_token_auth = {
        "auth": {
            "identity": {
                "methods": [
                    "accessKey"
                ],
                "accessKey": {
                    "accessKey": {},
                    "secretKey": {},
                }
            }
        }
    }

    rescope_access_token = {
        "auth": {
            "identity": {
                "methods": [
                    "token"
                ],
                "token": {
                    "id": {}
                }
            },
            "scope": {
                "project": {
                    "id": {}
                }
            }
        }
    }

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def get_token_password_auth(self, user_id, password, project_id):
        self.password_auth['auth']['identity']['password']['user']['id'] = user_id
        self.password_auth['auth']['identity']['password']['user']['password'] = password
        self.password_auth['auth']['scope']['project']['id'] = project_id
        data = json.dumps(self.password_auth)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        return response.headers['X-Subject-Token']

    def get_token_access_key_auth(self, project_id, access_key, secret_key):
        self.access_token_auth['auth']['identity']['accessKey']['accessKey'] = access_key
        self.access_token_auth['auth']['identity']['accessKey']['secretKey'] = secret_key
        data = json.dumps(self.access_token_auth)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        first_token = response.headers['X-Subject-Token']
        self.rescope_access_token['auth']['scope']['project']['id'] = project_id
        self.rescope_access_token['auth']['identity']['token']['id'] = first_token
        data = json.dumps(self.rescope_access_token)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(self.endpoint, data=data, headers=headers)
        response.raise_for_status()
        return response.headers['X-Subject-Token']
