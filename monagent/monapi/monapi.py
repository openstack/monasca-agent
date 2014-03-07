import requests
from keystone import Keystone
from util import json, md5

class MonAPI(object):

    def __init__(self, mon_api_url, use_keystone, keystone_url, project_id, user_id, password, logger):
        """
        Initialize Mon api connection.
        """
        self.logger = logger
        self.endpoint = mon_api_url
        if use_keystone:
            self.keystone = Keystone(keystone_url)
            self.token = self.keystone.get_token_password_auth(user_id, password, project_id)
            self.headers = {'content-type': 'application/json',
                            'X-Auth-Token': self.token}
        else:
            self.headers = {'content-type': 'application/json',
                            'X-Tenant-Id': project_id}


    def create_or_update_metric(self, payload):
        try:
            print self.endpoint
            data = json.dumps(payload)
            response = requests.post(self.endpoint, data=data, headers=self.headers, verify=False)
            if response:
                print response.status_code
                if response.status_code >= 200 and response.status_code <= 299:
                    print "Message sent successfully: {0}".format(str(data))
                    # Good status from web service
                    self.logger.debug("Message sent successfully: {0}".format(str(data)))
                elif response.status_code >= 400 and response.status_code <= 499:
                    print "Successful web service call but there were issues (Status: {0}, Message Content: {1})".format(response.status_code, str(payload))
                    # Good status from web service but some type of issue with the data
                    self.logger.warn("Successful web service call but there were issues (Status: {0}, Message Content: {1})".format(response.status_code, str(payload)))
                else:
                    print "Failed"
                    # Not a good status
                    self.response.raise_for_status()
            else:
                self.logger.error("Unable to connect to mon-api at " + self.endpoint)

        except Exception as ex:
            self.logger.error("Error sending message to mon-api: " + str(ex))
        
        return
