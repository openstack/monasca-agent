import copy
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

        self.keystone = Keystone(config)
        self.mon_client = None
        self.max_buffer_size = config['max_buffer_size']
        self.backlog_send_rate = config['backlog_send_rate']
        self.message_queue = deque(maxlen=self.max_buffer_size)
        # 'amplifier' is completely optional and may not exist in the config
        try:
            self.amplifier = config['amplifier']
        except KeyError:
            self.amplifier = None

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
            self.mon_client = self.get_monclient()

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
            if isinstance(measurement.dimensions, list):
                measurement.dimensions = dict([(d[0], d[1]) for d in measurement.dimensions])
            else:
                for dimension in self.default_dimensions.keys():
                    if dimension not in measurement.dimensions.keys():
                        measurement.dimensions.update({dimension: self.default_dimensions[dimension]})

        # "Amplify" these measurements to produce extra load, if so configured
        if self.amplifier is not None and self.amplifier > 0:
            extra_measurements = []
            for measurement in measurements:
                for multiple in range(1, self.amplifier + 1):
                    # Create a copy of the measurement, but with the addition
                    # of an 'amplifier' dimension
                    measurement_copy = copy.deepcopy(measurement)
                    measurement_copy.dimensions.update({'amplifier': multiple})
                    extra_measurements.append(measurement_copy)
            measurements.extend(extra_measurements)

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

    def get_monclient(self):
        """get_monclient
            get a new monasca-client object
        """
        # Create the client.
        kwargs = {
            'token': self.keystone.get_token()
        }
        return client.Client(self.api_version, self.url, **kwargs)

    def _send_message(self, **kwargs):
        try:
            self.mon_client.metrics.create(**kwargs)
            return True
        except exc.HTTPException as he:
            if 'unauthorized' in str(he):
                log.info("Invalid token detected. Getting a new token...")
                # Get a new keystone client and token
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
