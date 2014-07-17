import logging

from monascaclient import exc as exc, client
from monagent.common.keystone import Keystone
from monagent.common.util import get_hostname

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
        if 'hostname' not in self.default_dimensions:
            self.default_dimensions['hostname'] = get_hostname()

        log.debug("Getting token from Keystone")
        self.keystone_url = config['keystone_url']
        self.username = config['username']
        self.password = config['password']
        self.project_name = config['project_name']

        self.keystone = Keystone(self.keystone_url,
                                 self.username,
                                 self.password,
                                 self.project_name)
        self.mon_client = None

    def _post(self, measurements):
        """Does the actual http post
            measurements is a list of Measurement
        """
        data = [m.__dict__ for m in measurements]
        kwargs = {
            'jsonbody': data
        }
        try:
            if not self.mon_client:
                # construct the mon client
                self.mon_client = self.get_client()

            done = False
            while not done:
                response = self.mon_client.metrics.create(**kwargs)
                if 200 <= response.status_code <= 299:
                    # Good status from web service
                    log.debug("Message sent successfully: {0}"
                              .format(str(data)))
                elif 400 <= response.status_code <= 499:
                    # Good status from web service but some type of issue
                    # with the data
                    if response.status_code == 401:
                        # Get a new token/client and retry
                        self.mon_client.replace_token(self.keystone.refresh_token())
                        continue
                    else:
                        error_msg = "Successful web service call but there" + \
                                    " were issues (Status: {0}, Status Message: " + \
                                    "{1}, Message Content: {1})"
                        log.error(error_msg.format(response.status_code,
                                                   response.reason, response.text))
                        response.raise_for_status()
                else:  # Not a good status
                    response.raise_for_status()
                done = True
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
            for dimension in self.default_dimensions.keys():
                if dimension not in measurement.dimensions.keys():
                    measurement.dimensions.update({dimension: self.default_dimensions[dimension]})

        self._post(measurements)

    def get_client(self):
        """get_client
            get a new mon-client object
        """
        token = self.keystone.refresh_token()
        # Re-create the client.  This is temporary until
        # the client is updated to be able to reset the
        # token.
        kwargs = {
            'token': token
        }
        return client.Client(self.api_version, self.url, **kwargs)
