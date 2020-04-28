# (C) Copyright 2015-2016,2018 Hewlett Packard Enterprise Development LP
# Copyright 2017 Fujitsu LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import collections
import copy
import json
import logging

from keystoneauth1.exceptions import base as keystoneauth_exception
from monascaclient import client
from osc_lib import exceptions

from monasca_agent.common import keystone

log = logging.getLogger(__name__)


class MonascaAPI(object):

    """Sends measurements to MonascaAPI
        Any errors should raise an exception so the transaction calling
        this is not committed
    """

    LOG_INTERVAL = 10  # messages

    def __init__(self, config):
        """Initialize Mon api client connection."""
        self._config = config
        self._mon_client = None
        self._api_version = '2_0'

        self._failure_reason = None
        self._log_interval_remaining = 1
        self._current_number_measurements = 0
        self._max_buffer_size = int(config['max_buffer_size'])
        self._max_batch_size = int(config['max_batch_size'])
        self._max_measurement_buffer_size = int(
            config['max_measurement_buffer_size'])

        if self._max_buffer_size > -1:
            log.debug("'max_buffer_size' is deprecated. Please use"
                      " 'max_measurement_buffer_size' instead")
            if self._max_measurement_buffer_size > -1:
                log.debug("Overriding 'max_buffer_size' option with new"
                          " 'max_measurment_buffer_size' option")
                self._max_buffer_size = -1

        self.backlog_send_rate = int(config['backlog_send_rate'])
        if self._max_buffer_size > -1:
            self.message_queue = collections.deque(maxlen=self._max_buffer_size)
        else:
            self.message_queue = collections.deque()
        self.write_timeout = int(config['write_timeout'])
        # 'amplifier' is completely optional and may not exist in the config
        try:
            self.amplifier = int(config['amplifier'])
        except KeyError:
            self.amplifier = None

    def _post(self, measurements, tenant=None):
        """Does the actual http post
            measurements is a list of Measurement
        """
        kwargs = {
            'jsonbody': measurements
        }

        if tenant:
            kwargs['tenant_id'] = tenant

        if not self._mon_client:
            self._mon_client = self._get_mon_client()
            if not self._mon_client:
                # Keystone is down, queue the message
                self._queue_message(kwargs.copy(), "Keystone API is down or unreachable")
                return

        if self._send_message(**kwargs):
            if len(self.message_queue) > 0:
                messages_sent = 0
                for index in range(0, len(self.message_queue)):
                    if index < self.backlog_send_rate:

                        msg = json.loads(self.message_queue.pop())

                        if self._send_message(**msg):
                            messages_sent += 1
                            for value in msg.values():
                                self._current_number_measurements -= len(value)
                        else:
                            self._queue_message(msg, self._failure_reason)
                            break
                    else:
                        break
                log.info("Sent {0} messages from the backlog.".format(messages_sent))
                log.info("{0} messages remaining in the queue.".format(len(self.message_queue)))
                self._log_interval_remaining = 0
        else:
            self._queue_message(kwargs.copy(), self._failure_reason)

    def post_metrics(self, measurements):
        """post_metrics
            given [Measurement, ...], format the request and post to
            the monitoring api
        """
        # Add default dimensions
        for envelope in measurements:
            measurement = envelope['measurement']
            if isinstance(measurement['dimensions'], list):
                measurement['dimensions'] = dict([(d[0], d[1]) for d in measurement['dimensions']])

        # Split out separate POSTs for each delegated tenant (includes 'None')
        tenant_group = {}
        for envelope in measurements:
            measurement = envelope['measurement']
            tenant = envelope['tenant_id']
            tenant_group.setdefault(tenant, []).append(copy.deepcopy(measurement))
            if self._max_batch_size and len(tenant_group[tenant]) >= self._max_batch_size:
                self._post(tenant_group[tenant], tenant)
                del tenant_group[tenant]

        for tenant in tenant_group:
            self._post(tenant_group[tenant], tenant)

    def _get_mon_client(self):
        try:
            k = keystone.Keystone(self._config)
            endpoint = k.get_monasca_url()
            session = k.get_session()
            c = client.Client(
                api_version=self._api_version,
                endpoint=endpoint,
                session=session,
                timeout=self.write_timeout,
                **keystone.get_args(self._config)
            )
            return c
        except keystoneauth_exception.ClientException as ex:
            log.error('Failed to initialize Monasca client. {}'.format(ex))

    def _send_message(self, **kwargs):
        try:
            self._mon_client.metrics.create(**kwargs)
            return True
        except exceptions.ClientException as ex:
            log.exception("ClientException: error sending "
                          "message to monasca-api.")
            self._failure_reason = ('Error sending message to '
                                    'the Monasca API: {0}').format(str(ex))
        except Exception:
            log.exception("Error sending message to Monasca API.")
            self._failure_reason = 'The Monasca API is DOWN or unreachable'

        return False

    def _queue_message(self, msg, reason):
        if self._max_buffer_size == 0 or self._max_measurement_buffer_size == 0:
            return

        self.message_queue.append(json.dumps(msg))

        for value in msg.values():
            self._current_number_measurements += len(value)

        if self._max_measurement_buffer_size > -1:
            while self._current_number_measurements > self._max_measurement_buffer_size:
                self._remove_oldest_from_queue()

        if self._log_interval_remaining <= 1:
            log.warn("{0}. Queuing the messages to send later...".format(reason))
            log.info("Current agent queue size: {0} of {1}.".format(len(self.message_queue),
                                                                    self._max_buffer_size))
            log.info("Current measurements in queue: {0} of {1}".format(
                self._current_number_measurements, self._max_measurement_buffer_size))

            log.info(
                "A message will be logged for every {0} messages queued.".format(
                    MonascaAPI.LOG_INTERVAL))
            self._log_interval_remaining = MonascaAPI.LOG_INTERVAL
        else:
            self._log_interval_remaining -= 1

    def _remove_oldest_from_queue(self):
        removed_batch = json.loads(self.message_queue.popleft())
        num_discarded = 0
        for value in removed_batch.values():
            num_discarded += len(value)
        self._current_number_measurements -= num_discarded
        log.warn("Queue too large, discarding oldest batch: {0} measurements discarded".format(
            num_discarded))
