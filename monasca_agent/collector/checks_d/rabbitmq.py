import json
import time
import urllib2
import urlparse

import monasca_agent.collector.checks as checks


EVENT_TYPE = SOURCE_TYPE_NAME = 'rabbitmq'
QUEUE_TYPE = 'queues'
EXCHANGE_TYPE = 'exchanges'
NODE_TYPE = 'nodes'
MAX_DETAILED_QUEUES = 150
MAX_DETAILED_EXCHANGES = 100
MAX_DETAILED_NODES = 50
# Post an event in the stream when the number of queues or nodes to
# collect is above 90% of the limit
ALERT_THRESHOLD = 0.9
QUEUE_ATTRIBUTES = [
    # Path, Name
    ('active_consumers', 'active_consumers'),
    ('consumers', 'consumers'),
    ('memory', 'memory'),

    ('messages', 'messages'),
    ('messages_details/rate', 'messages.rate'),

    ('messages_ready', 'messages.ready'),
    ('messages_ready_details/rate', 'messages.ready_rate'),

    ('messages_unacknowledged', 'messages.unacknowledged'),
    ('messages_unacknowledged_details/rate', 'messages.unacknowledged_rate'),

    ('message_stats/ack', 'messages.ack_count'),
    ('message_stats/ack_details/rate', 'messages.ack_rate'),

    ('message_stats/deliver', 'messages.deliver_count'),
    ('message_stats/deliver_details/rate', 'messages.deliver_rate'),

    ('message_stats/deliver_get', 'messages.deliver_get_count'),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get_rate'),

    ('message_stats/publish', 'messages.publish_count'),
    ('message_stats/publish_details/rate', 'messages.publish_rate'),

    ('message_stats/redeliver', 'messages.redeliver_count'),
    ('message_stats/redeliver_details/rate', 'messages.redeliver_rate')]

EXCHANGE_ATTRIBUTES = [('message_stats/publish_out', 'messages.published_count'),
                       ('message_stats/publish_out_details/rate', 'messages.published_rate'),

                       ('message_stats/publish_in', 'messages.received_count'),
                       ('message_stats/publish_in_details/rate', 'messages.received_rate')]

NODE_ATTRIBUTES = [
    ('fd_used', 'fd_used'),
    ('mem_used', 'mem_used'),
    ('run_queue', 'run_queue'),
    ('sockets_used', 'sockets_used')]

ATTRIBUTES = {QUEUE_TYPE: QUEUE_ATTRIBUTES,
              EXCHANGE_TYPE: EXCHANGE_ATTRIBUTES,
              NODE_TYPE: NODE_ATTRIBUTES}

DIMENSIONS_MAP = {
    'queues': {'name': 'queue',
               'vhost': 'vhost',
               'policy': 'policy'},
    'exchanges': {'name': 'exchange',
                  'vhost': 'vhost',
                  'type': 'type'},
    'nodes': {'name': 'node'}
}

METRIC_SUFFIX = {QUEUE_TYPE: "queue", EXCHANGE_TYPE: "exchange", NODE_TYPE: "node"}


class RabbitMQ(checks.AgentCheck):

    """This check is for gathering statistics from the RabbitMQ

    Management Plugin (http://www.rabbitmq.com/management.html)
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        checks.AgentCheck.__init__(self, name, init_config, agent_config, instances)
        self.already_alerted = []

    @staticmethod
    def _get_config(instance):
        # make sure 'rabbitmq_api_url; is present
        if 'rabbitmq_api_url' not in instance:
            raise Exception('Missing "rabbitmq_api_url" in RabbitMQ config.')

        # get parameters
        base_url = instance['rabbitmq_api_url']
        if not base_url.endswith('/'):
            base_url += '/'
        username = instance.get('rabbitmq_user', 'guest')
        password = instance.get('rabbitmq_pass', 'guest')

        # Limit of queues/nodes to collect metrics from
        max_detailed = {
            QUEUE_TYPE: int(instance.get('max_detailed_queues', MAX_DETAILED_QUEUES)),
            EXCHANGE_TYPE: int(instance.get('max_detailed_exchanges', MAX_DETAILED_EXCHANGES)),
            NODE_TYPE: int(instance.get('max_detailed_nodes', MAX_DETAILED_NODES)),
        }

        # List of queues/nodes to collect metrics from
        specified = {
            QUEUE_TYPE: instance.get('queues', []),
            EXCHANGE_TYPE: instance.get('exchanges', []),
            NODE_TYPE: instance.get('nodes', [])
        }

        for object_type, specified_objects in specified.iteritems():
            if not isinstance(specified_objects, list):
                raise TypeError("%s parameter must be a list" % object_type)

        # setup urllib2 for Basic Auth
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(
            realm='RabbitMQ Management', uri=base_url, user=username, passwd=password)
        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

        return base_url, max_detailed, specified

    def check(self, instance):
        base_url, max_detailed, specified = self._get_config(instance)

        self.get_stats(instance,
                       base_url,
                       QUEUE_TYPE,
                       max_detailed[QUEUE_TYPE],
                       list(specified[QUEUE_TYPE]))
        self.get_stats(instance,
                       base_url,
                       NODE_TYPE,
                       max_detailed[NODE_TYPE],
                       list(specified[NODE_TYPE]))
        self.get_stats(instance,
                       base_url,
                       EXCHANGE_TYPE,
                       max_detailed[EXCHANGE_TYPE],
                       specified[EXCHANGE_TYPE])

    @staticmethod
    def _get_data(url):
        try:
            data = json.loads(urllib2.urlopen(url).read())
        except urllib2.URLError as e:
            raise Exception('Cannot open RabbitMQ API url: %s %s' % (url, str(e)))
        except ValueError as e:
            raise Exception('Cannot parse JSON response from API url: %s %s' % (url, str(e)))
        return data

    def get_stats(self, instance, base_url, object_type, max_detailed, specified_list):
        """instance: the check instance

        base_url: the url of the rabbitmq management api (e.g. http://localhost:15672/api)
        object_type: either QUEUE_TYPE, EXCHANGE_TYPE or NODE_TYPE
        max_detailed: the limit of objects to collect for this type
        specified_list: a list of specified queues or nodes (specified in the yaml file)
        """
        data = self._get_data(urlparse.urljoin(base_url, object_type))
        # Make a copy of this list as we will remove items from it at each iteration
        specified_items = list(specified_list)

        """data is a list of nodes or queues:

        data = [
            {'status': 'running', 'node': 'rabbit@host', 'name': 'queue1', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False},
            {'status': 'running', 'node': 'rabbit@host, 'name': 'queue10', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False},
            {'status': 'running', 'node': 'rabbit@host', 'name': 'queue11', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False},
            ...
        ]
        """
        if len(specified_items) > max_detailed:
            raise Exception("The maximum number of %s you can specify is %d." %
                            (object_type, max_detailed))

        # If a list of exchanges/queues/nodes is specified,
        # we process only those.
        if specified_items is not None and len(specified_items) > 0:
            for data_line in data:
                name = data_line.get("name")
                if name not in specified_items:
                    if object_type == QUEUE_TYPE:
                        name = '%s/%s' % (data_line.get("vhost"), name)
                if name in specified_items:
                    self._get_metrics(data_line, object_type, instance)
                    specified_items.remove(name)

        # No queues/node are specified. We will process every queue/node if it's under the limit
        else:
# Monasca does not support events at this time.
#            if len(data) > ALERT_THRESHOLD * max_detailed:
#                # Post a message on the dogweb stream to warn
#                self.alert(base_url, max_detailed, len(data), object_type)

            if len(data) > max_detailed:
                # Display a warning in the info page
                self.warning(
                    "Too many queues to fetch. You must choose the %s you are interested in by editing the rabbitmq.yaml configuration file" %
                    object_type)

            for data_line in data[:max_detailed]:
                # We truncate the list of nodes/queues if it's above the limit
                self._get_metrics(data_line, object_type, instance)

    def _get_metrics(self, data, object_type, instance):
        dimensions_list = DIMENSIONS_MAP[object_type].copy()
        dimensions = self._set_dimensions({'component': 'rabbitmq', 'service': 'rabbitmq'},
                                          instance)
        for d in dimensions_list.iterkeys():
            dim = data.get(d, None)
            if dim not in [None, ""]:
                dimensions[dimensions_list[d]] = dim

        for attribute, metric_name in ATTRIBUTES[object_type]:
            # Walk down through the data path, e.g. foo/bar => d['foo']['bar']
            root = data
            keys = attribute.split('/')
            for path in keys[:-1]:
                root = root.get(path, {})

            value = root.get(keys[-1], None)
            if value == None:
                value = 0.0
            try:
                self.log.debug("Collected data for %s: metric name: %s: value: %f dimensions: %s" % (object_type, metric_name, float(value), str(dimensions)))
                self.gauge('rabbitmq.%s.%s' % (METRIC_SUFFIX[object_type], metric_name), float(value), dimensions=dimensions)
            except ValueError:
                self.log.debug("Caught ValueError for %s %s = %s  with dimensions: %s" % (
                    METRIC_SUFFIX[object_type], attribute, value, dimensions))

    def alert(self, base_url, max_detailed, size, object_type):
        key = "%s%s" % (base_url, object_type)
        if key in self.already_alerted:
            # We have already posted an event
            return

        self.already_alerted.append(key)

        title = "RabbitMQ integration is approaching the limit on the number of %s that can be collected from on %s" % (
            object_type, self.hostname)
        msg = """%s %s are present. The limit is %s.
        Please get in touch with Monasca development to increase the limit.""" % (size, object_type, max_detailed)

        event = {
            "timestamp": int(time.time()),
            "event_type": EVENT_TYPE,
            "msg_title": title,
            "msg_text": msg,
            "alert_type": 'warning',
            "source_type_name": SOURCE_TYPE_NAME,
            "host": self.hostname,
            "dimensions": {"base_url": base_url, "host": self.hostname},
            "event_object": "rabbitmq.limit.%s" % object_type,
        }

        self.event(event)
