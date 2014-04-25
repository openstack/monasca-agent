import requests
from keystone import Keystone
from util import json, md5

class MonAPI(object):

    def __init__(self, mon_api_config, logger):
        """
        Initialize Mon api connection.
        """
        self.logger = logger
        mon_api_url = mon_api_config['url']
        use_keystone = mon_api_config['use_keystone']
        keystone_url = mon_api_config['keystone_url']
        project_id = mon_api_config['project_id']
        user_id = mon_api_config['username']
        password = mon_api_config['password']
        self.endpoint = mon_api_url

        if use_keystone:
            self.keystone = Keystone(keystone_url)
            self.token = self.keystone.get_token_password_auth(user_id, password, project_id)
            self.headers = {'content-type': 'application/json',
                            'X-Auth-Token': self.token}
        else:
            self.headers = {'content-type': 'application/json',
                            'X-Tenant-Id': project_id}


    def post_metrics(self, payload):
        try:
            data = json.dumps(payload)
            self.logger.debug(data)
            response = requests.post(self.endpoint, data=data, headers=self.headers)
            if response:
                if response.status_code >= 200 and response.status_code <= 299:
                    # Good status from web service
                    self.logger.debug("Message sent successfully: {0}".format(str(data)))
                elif response.status_code >= 400 and response.status_code <= 499:
                    # Good status from web service but some type of issue with the data
                    self.logger.warn("Successful web service call but there were issues (Status: {0}, Status Message: {1}, Message Content: {1})".format(response.status_code, response.text, response.str(payload)))
                else:
                    # Not a good status
                    self.response.raise_for_status()
            else:
                self.logger.error("Unable to connect to mon-api at " + self.endpoint)

        except Exception as ex:
            self.logger.error("Error sending message to mon-api: " + str(ex))
        
        return
