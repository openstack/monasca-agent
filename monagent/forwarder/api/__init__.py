import json
import logging

from threading import Timer
from monagent.common.keystone import Keystone
from monagent.common.util import get_hostname
from monclient import client
import monclient.exc as exc

log = logging.getLogger(__name__)


class MonAPI(object):
    """Sends measurements to MonAPI
        Any errors should raise an exception so the transaction calling
        this is not committed
    """
    def __init__(self, config):
        """
        Initialize Mon api client connection.
        """
        self.config = config
        self.url = config['url']
        self.api_version = '2_0'
        self.default_dimensions = config['dimensions']
        self.token_expiration = 1438
        # Verify the hostname is set as a dimension
        if not 'hostname' in self.default_dimensions:
            self.default_dimensions['hostname'] = get_hostname()

        try:
            log.debug("Getting token from Keystone")
            self.keystone = Keystone(config['keystone_url'],
                                     config['username'],
                                     config['password'],
                                     config['project_name'])
            
            self.token = keystone.get_token()
            
        except Exception as ex:
            log.error("Error getting token from Keystone: {0}".
                      format(str(ex.message)))
            raise ex

        # construct the mon client
        self.kwargs = {
            'token': self.token
        }
        self.mon_client = client.Client(self.api_version, self.url, **self.kwargs)

    def _post(self, measurements):
        """Does the actual http post
            measurements is a list of Measurement
        """
        data = [m.__dict__ for m in measurements]
        kwargs = {
            'jsonbody': data
        }
        try:
            successful = False
            retries = 0
            while not successful and retries <= 1:
                response = self.mon_client.metrics.create(**kwargs)
                if 200 <= response.status_code <= 299:
                    # Good status from web service
                    log.debug("Message sent successfully: {0}"
                              .format(str(data)))
                    successful = True
                elif 400 <= response.status_code <= 499:
                    # Good status from web service but some type of issue
                    # with the data
                    if response.status_code == 401:
                        # Get a new token and retry
                        self.token = self.keystone.get_token_password_auth()
                        # Recreate the client.  This is temporary until
                        # the client is updated to be able to reset the
                        # token.
                        self.mon_client = client.Client(self.api_version, self.url, **self.kwargs)
                        retries += 1
                    else:
                        error_msg = "Successful web service call but there" + \
                                    " were issues (Status: {0}, Status Message: " + \
                                    "{1}, Message Content: {1})"
                        log.error(error_msg.format(response.status_code,
                                                   response.reason, response.text))
                        response.raise_for_status()
                else:  # Not a good status
                    response.raise_for_status()
        except exc.HTTPException as he:
            log.error("Error sending message to mon-api: {0}"
                      .format(str(he.message)))

    def post_metrics(self, measurements):
        """post_metrics
            given [Measurement, ...], format the request and post to
            the monitoring api
        """
        # Add default dimensions
        for measurement in measurements:
            measurement.dimensions.update(self.default_dimensions)

        self._post(measurements)
