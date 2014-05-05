import json
import logging

import requests

from keystone import Keystone


log = logging.getLogger(__name__)


class MonAPI(object):
    """Sends measurements to MonAPI
        Any errors should raise and exception so the transaction calling this is not committed
    """
    def __init__(self, config):
        """
        Initialize Mon api connection.
        """
        self.url = config['url']
        self.default_dimensions = config['dimensions']

        #todo we should always use keystone, for development the keystone object should just return a dummy token
        if config['use_keystone']:
            self.keystone = Keystone(config['keystone_url'])
            token = self.keystone.get_token_password_auth(config['username'], config['password'], config['project_id'])
            self.headers = {'content-type': 'application/json',
                            'X-Auth-Token': token}
        else:
            self.headers = {'content-type': 'application/json',
                            'X-Tenant-Id': config['project_id']}

    def _post(self, measurements):
        """Does the actual http post
            measurements is a list of Measurement
        """
        data = [json.dumps(m.__dict__) for m in measurements]

        response = requests.post(self.url, data=data, headers=self.headers)
        if 200 <= response.status_code <= 299:
            # Good status from web service
            log.debug("Message sent successfully: {0}".format(str(data)))
        elif 400 <= response.status_code <= 499:
            # Good status from web service but some type of issue with the data
            error_msg = "Successful web service call but there were issues (Status: {0}," + \
                        "Status Message: {1}, Message Content: {1})"
            log.warn(error_msg.format(response.status_code, response.text, response.str(measurements)))
        else:  # Not a good status
            response.raise_for_status()

    def post_metrics(self, measurements):
        """post_metrics
            given [Measurement, ...], format the request and post to the monitoring api
        """
        # Add default dimensions
        for measurement in measurements:
            measurement.dimensions.update(self.default_dimensions)

        self._post(measurements)
