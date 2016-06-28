# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

import collections
import copy
import logging
import random
import time

import monasca_agent.common.keystone as keystone
import monascaclient.client

log = logging.getLogger(__name__)


class MonascaAPI(object):

    """Sends measurements to MonascaAPI
        Any errors should raise an exception so the transaction calling
        this is not committed
    """

    LOG_INTERVAL = 10  # messages
    MIN_BACKOFF = 10   # seconds
    MAX_BACKOFF = 60   # seconds

    def __init__(self, config):
        """Initialize Mon api client connection."""
        self.config = config
        self.url = config['url']
        self.api_version = '2_0'
        self.keystone = keystone.Keystone(config)
        self.mon_client = None
        self._failure_reason = None
        self._resume_time = None
        self.max_buffer_size = int(config['max_buffer_size'])
        self.backlog_send_rate = int(config['backlog_send_rate'])
        self.message_queue = collections.deque(maxlen=self.max_buffer_size)
        self.write_timeout = int(config['write_timeout'])
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
        for measurement_element in measurements:
            measurement = copy.deepcopy(measurement_element)
            m_dict = measurement.__dict__
            m_dict['timestamp'] *= 1000
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
            kwargs = self.keystone.get_credential_args()
            kwargs['token'] = token
            if not self.url:
                self.url = self.keystone.get_monasca_url()

            return monascaclient.client.Client(self.api_version, self.url, write_timeout=self.write_timeout, **kwargs)

        return None

    def _send_message(self, **kwargs):
        if self._resume_time:
            if time.time() > self._resume_time:
                self._resume_time = None
                log.debug("Getting new token...")
                # Get a new keystone client and token
                if self.keystone.refresh_token():
                    self.mon_client.replace_token(self.keystone.get_token())
            else:
                # Return without posting so the monasca client doesn't keep requesting new tokens
                return False
        try:
            self.mon_client.metrics.create(**kwargs)
            return True
        except monascaclient.exc.HTTPException as ex:
            if ex.code == 401:
                # monasca client should already have retried once with a new token before returning this exception
                self._failure_reason = 'Invalid token detected. Waiting to get new token from Keystone'
                wait_time = random.randint(MonascaAPI.MIN_BACKOFF, MonascaAPI.MAX_BACKOFF + 1)
                self._resume_time = time.time() + wait_time
                log.info("Invalid token detected. Waiting %d seconds before getting new token.", wait_time)
            else:
                log.exception("HTTPException: error sending message to monasca-api.")
                self._failure_reason = 'Error sending message to the Monasca API: {0}'.format(str(ex.message))
        except Exception:
            log.exception("Error sending message to Monasca API.")
            self._failure_reason = 'The Monasca API is DOWN or unreachable'

        return False

    def _queue_message(self, msg, reason):
        self.message_queue.append(msg)
        queue_size = len(self.message_queue)
        if queue_size is 1 or queue_size % MonascaAPI.LOG_INTERVAL == 0:
            log.warn("{0}. Queuing the messages to send later...".format(reason))
            log.info("Current agent queue size: {0} of {1}.".format(len(self.message_queue),
                                                                    self.max_buffer_size))
            log.info("A message will be logged for every {0} messages queued.".format(MonascaAPI.LOG_INTERVAL))
