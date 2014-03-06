import requests
from keystone import Keystone
from util import json, md5

class MonAPI(object):

    def __init__(self, mon_api_url, keystone_url, project_id, user_id, password):
        """
        Initialize Mon api connection.
        """
        self.keystone = Keystone(keystone_url)
        self.token = self.keystone.get_token_password_auth(user_id, password, project_id)
        print self.token
        self.endpoint = mon_api_url
        self.headers = {'content-type': 'application/json',
                        'X-Auth-Token': self.token}

    def create_or_update_metric(self, payload):
        url = self.endpoint
        data = json.dumps(payload)
        response = requests.post(url, data=data, headers=self.headers, verify=False)
        response.raise_for_status()
        return
