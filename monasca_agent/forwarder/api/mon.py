import collections
import copy
import logging

import monascaclient.client
import monasca_agent.common.keystone as keystone

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
        self.keystone = keystone.Keystone(config)
        self.mon_client = None
        self._failure_reason = None
        self.max_buffer_size = int(config['max_buffer_size'])
        self.backlog_send_rate = int(config['backlog_send_rate'])
        self.message_queue = collections.deque(maxlen=self.max_buffer_size)
        # 'amplifier' is completely optional and may not exist in the config
        try:
            self.amplifier = int(config['amplifier'])
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
            self.mon_client = self.get_monclient()
            if not self.mon_client:
                # Keystone is down, queue the message
                self._queue_message(kwargs.copy(), "Keystone API is down or unreachable")
                return

        if self._send_message(**kwargs):
            if len(self.message_queue) > 0:
                messages_sent = 0
                for index in range(0, len(self.message_queue)):
                    if index < self.backlog_send_rate:
                        msg = self.message_queue.pop()

                        if self._send_message(**msg):
                            messages_sent += 1
                        else:
                            self._queue_message(msg, self._failure_reason)
                            break
                    else:
                        break
                log.info("Sent {0} messages from the backlog.".format(messages_sent))
                log.info("{0} messages remaining in the queue.".format(len(self.message_queue)))
        else:
            self._queue_message(kwargs.copy(), self._failure_reason)

    def post_metrics(self, measurements):
        """post_metrics
            given [Measurement, ...], format the request and post to
            the monitoring api
        """
        # Add default dimensions
        for measurement in measurements:
            if isinstance(measurement.dimensions, list):
                measurement.dimensions = dict([(d[0], d[1]) for d in measurement.dimensions])

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
            m_dict['timestamp'] *= 1000
            if m_dict['value_meta'] is None:
                del m_dict['value_meta']
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
        token = self.keystone.get_token()
        if token:
            # Create the client.
            kwargs = {
                'token': token
            }

            if not self.url:
                self.url = self.keystone.get_monasca_url()

            return monascaclient.client.Client(self.api_version, self.url, **kwargs)

        return None

    def _send_message(self, **kwargs):
        try:
            self.mon_client.metrics.create(**kwargs)
            return True
        except monascaclient.exc.HTTPException as he:
            if he.code == 401:
                log.info("Invalid token detected. Getting a new token...")
                self._failure_reason = 'Invalid token detected. Getting a new token from Keystone'
                # Get a new keystone client and token
                self.mon_client.replace_token(self.keystone.refresh_token())
            else:
                log.debug("Error sending message to monasca-api. Error is {0}."
                          .format(str(he.message)))
                self._failure_reason = 'Error sending message to the Monasca API: {0}'.format(str(he.message))
        except Exception as ex:
            log.debug("Error sending message to Monasca API. Error is {0}."
                      .format(str(ex.message)))
            self._failure_reason = 'The Monasca API is DOWN or unreachable'

        return False

    def _queue_message(self, msg, reason):
        self.message_queue.append(msg)
        queue_size = len(self.message_queue)
        if queue_size is 1 or queue_size % MonAPI.LOG_INTERVAL == 0:
            log.warn("{0}. Queuing the messages to send later...".format(reason))
            log.info("Current agent queue size: {0} of {1}.".format(len(self.message_queue),
                                                                    self.max_buffer_size))
            log.info("A message will be logged for every {0} messages queued.".format(MonAPI.LOG_INTERVAL))
