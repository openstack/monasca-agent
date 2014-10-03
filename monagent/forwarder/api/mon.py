import logging
from collections import deque

from monascaclient import exc as exc, client
from monagent.common.keystone import Keystone
from monagent.common.util import get_hostname

import requests

log = logging.getLogger(__name__)

class MonAPI(object):

    """Sends measurements to MonAPI
        Any errors should raise an exception so the transaction calling
        this is not committed
    """

    LOG_INTERVAL = 10

    def __init__(self, config):
        """
        Initialize Mon api client connection.
        """
        self.config = config
        self.url = config['url']
        self.api_version = '2_0'
        self.default_dimensions = config['dimensions']
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
        self.max_buffer_size = config['max_buffer_size']
        self.backlog_send_rate = config['backlog_send_rate']
        self.message_queue = deque(maxlen=self.max_buffer_size)

    def _post(self, measurements, delegated_tenant=None):
        """Does the actual http post
            measurements is a list of Measurement
        """
        kwargs = {
            'jsonbody': measurements
        }

        if delegated_tenant is not None:
            kwargs['tenant_id'] = delegated_tenant
        if not self.mon_client:
            # construct the monasca client
            self.mon_client = self.get_client()

        if self._send_message(**kwargs):
            if len(self.message_queue) > 0:
                messages_sent = 0
                for index in range(0, len(self.message_queue)):
                    if index < self.backlog_send_rate:
                        msg = self.message_queue.pop()

                        if self._send_message(**msg):
                            messages_sent += 1
                        else:
                            self._queue_message(msg)
                            break
                    else:
                        break
                log.info("Sent {0} messages from the backlog.".format(messages_sent))
                log.info("{0} messages remaining in the queue.".format(len(self.message_queue)))
        else:
            self._queue_message(kwargs.copy())

    def post_metrics(self, measurements):
        """post_metrics
            given [Measurement, ...], format the request and post to
            the monitoring api
        """
        # Add default dimensions
        for measurement in measurements:
            if isinstance(measurement.dimensions, dict):
                for dimension in self.default_dimensions.keys():
                    if dimension not in measurement.dimensions.keys():
                        measurement.dimensions.update({dimension: self.default_dimensions[dimension]})
            else:
                measurement.dimensions = self.default_dimensions.copy()

        # Split out separate POSTs for each delegated tenant (includes 'None')
        tenant_group = {}
        for measurement in measurements:
            m_dict = measurement.__dict__
            delegated_tenant = m_dict.pop('delegated_tenant')
            if delegated_tenant not in tenant_group:
                tenant_group[delegated_tenant] = []
            tenant_group[delegated_tenant].extend([m_dict.copy()])
        for tenant in tenant_group:
            self._post(tenant_group[tenant], tenant)

    def get_client(self):
        """get_client
            get a new monasca-client object
        """
        token = self.keystone.refresh_token()
        # Re-create the client.  This is temporary until
        # the client is updated to be able to reset the
        # token.
        kwargs = {
            'token': token
        }
        return client.Client(self.api_version, self.url, **kwargs)

    def _send_message(self, **kwargs):
        try:
            self.mon_client.metrics.create(**kwargs)
            return True
        except exc.HTTPException as he:
            if 'unauthorized' in str(he):
                log.info("Invalid token detected. Getting a new token...")
                # Get a new token
                self.mon_client.replace_token(self.keystone.refresh_token())
            else:
                log.debug("Error sending message to monasca-api. Error is {0}."
                          .format(str(he.message)))
        except Exception as ex:
            log.debug("Error sending message to monasca-api. Error is {0}."
                      .format(str(ex.message)))

        return False

    def _queue_message(self, msg):
        self.message_queue.append(msg)
        queue_size = len(self.message_queue)
        if queue_size is 1 or queue_size % MonAPI.LOG_INTERVAL == 0:
            log.warn("API is down or unreachable.  Queuing the messages to send later...")
            log.info("Current agent queue size: {0} of {1}.".format(len(self.message_queue),
                                                                    self.max_buffer_size))
            log.info("A message will be logged for every {0} messages queued.".format(MonAPI.LOG_INTERVAL))
