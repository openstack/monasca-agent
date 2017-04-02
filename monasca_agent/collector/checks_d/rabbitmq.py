# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP

import json
import re
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

ALERT_THRESHOLD = 0.9
QUEUE_ATTRIBUTES = [
    # Path, Name
    ('active_consumers', 'active_consumers', float),
    ('consumers', 'consumers', float),
    ('memory', 'memory', float),

    ('messages', 'messages', float),
    ('messages_details/rate', 'messages.rate', float),

    ('messages_ready', 'messages.ready', float),
    ('messages_ready_details/rate', 'messages.ready_rate', float),

    ('messages_unacknowledged', 'messages.unacknowledged', float),
    ('messages_unacknowledged_details/rate', 'messages.unacknowledged_rate', float),

    ('message_stats/ack', 'messages.ack_count', float),
    ('message_stats/ack_details/rate', 'messages.ack_rate', float),

    ('message_stats/deliver', 'messages.deliver_count', float),
    ('message_stats/deliver_details/rate', 'messages.deliver_rate', float),

    ('message_stats/deliver_get', 'messages.deliver_get_count', float),
    ('message_stats/deliver_get_details/rate', 'messages.deliver_get_rate', float),

    ('message_stats/publish', 'messages.publish_count', float),
    ('message_stats/publish_details/rate', 'messages.publish_rate', float),

    ('message_stats/redeliver', 'messages.redeliver_count', float),
    ('message_stats/redeliver_details/rate', 'messages.redeliver_rate', float)]

EXCHANGE_ATTRIBUTES = [('message_stats/publish_out', 'messages.published_count', float),
                       ('message_stats/publish_out_details/rate', 'messages.published_rate', float),

                       ('message_stats/publish_in', 'messages.received_count', float),
                       ('message_stats/publish_in_details/rate', 'messages.received_rate', float)]

NODE_ATTRIBUTES = [
    ('fd_used', 'fd_used', float),
    ('mem_used', 'mem_used', float),
    ('run_queue', 'run_queue', float),
    ('sockets_used', 'sockets_used', float),
    ('partitions', 'partitions', len)
]

ATTRIBUTES = {QUEUE_TYPE: QUEUE_ATTRIBUTES,
              EXCHANGE_TYPE: EXCHANGE_ATTRIBUTES,
              NODE_TYPE: NODE_ATTRIBUTES}

# whitelist of metrics to collect
DEFAULT_WHITELIST = {
    QUEUE_TYPE: ['messages',
                 'message_stats/deliver_details/rate',
                 'message_stats/publish_details/rate',
                 'message_stats/redeliver_details/rate'],
    EXCHANGE_TYPE: ['message_stats/publish_out',
                    'message_stats/publish_out_details/rate',
                    'message_stats/publish_in',
                    'message_stats/publish_in_details/rate'],
    NODE_TYPE: ['fd_used',
                'mem_used',
                'run_queue',
                'sockets_used']
}

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
            QUEUE_TYPE: {
                'explicit': instance.get('queues', []),
                'regexes': instance.get('queues_regexes', []),
            },
            EXCHANGE_TYPE: {
                'explicit': instance.get('exchanges', []),
                'regexes': instance.get('exchanges_regexes', []),
            },
            NODE_TYPE: {
                'explicit': instance.get('nodes', []),
                'regexes': instance.get('nodes_regexes', []),
            },
        }

        for object_type, filters in specified.items():
            for filter_type, filter_objects in filters.items():
                if type(filter_objects) != list:
                    raise TypeError(
                        "{0} / {0}_regexes parameter must be a list".format(object_type))

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
                       specified[QUEUE_TYPE])
        self.get_stats(instance,
                       base_url,
                       NODE_TYPE,
                       max_detailed[NODE_TYPE],
                       specified[NODE_TYPE])
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

    def get_stats(self, instance, base_url, object_type, max_detailed, filters):
        """instance: the check instance

        base_url: the url of the rabbitmq management api (e.g. http://localhost:15672/api)
        object_type: either QUEUE_TYPE, EXCHANGE_TYPE or NODE_TYPE
        max_detailed: the limit of objects to collect for this type
        filters: explicit or regexes filters of specified queues or nodes (specified in the yaml file)
        """
        data = self._get_data(urlparse.urljoin(base_url, object_type))
        # Make a copy of this list as we will remove items from it at each iteration
        explicit_filters = list(filters['explicit'])
        regex_filters = filters['regexes']

        """data is a list of nodes or queues:

        data = [
            {'status': 'running', 'node': 'rabbit@host', 'name': 'queue1', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False},
            {'status': 'running', 'node': 'rabbit@host, 'name': 'queue10', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False},
            {'status': 'running', 'node': 'rabbit@host', 'name': 'queue11', 'consumers': 0, 'vhost': '/', 'backing_queue_status': {'q1': 0, 'q3': 0, 'q2': 0, 'q4': 0, 'avg_ack_egress_rate': 0.0, 'ram_msg_count': 0, 'ram_ack_count': 0, 'len': 0, 'persistent_count': 0, 'target_ram_count': 'infinity', 'next_seq_id': 0, 'delta': ['delta', 'undefined', 0, 'undefined'], 'pending_acks': 0, 'avg_ack_ingress_rate': 0.0, 'avg_egress_rate': 0.0, 'avg_ingress_rate': 0.0}, 'durable': True, 'idle_since': '2013-10-03 13:38:18', 'exclusive_consumer_tag': '', 'arguments': {}, 'memory': 10956, 'policy': '', 'auto_delete': False},
            ...
        ]
        """
        if len(explicit_filters) > max_detailed:
            raise Exception("The maximum number of %s you can specify is %d." %
                            (object_type, max_detailed))

        # a list of queues/nodes is specified. We process only those
        if explicit_filters or regex_filters:
            matching_lines = []
            for data_line in data:
                name = data_line.get("name")
                if self._is_matching_stat(name, explicit_filters, regex_filters):
                    matching_lines.append(data_line)
                    continue

                # Absolute names work only for queues
                if object_type != QUEUE_TYPE:
                    continue
                absolute_name = '%s/%s' % (data_line.get("vhost"), name)
                if self._is_matching_stat(absolute_name, explicit_filters, regex_filters):
                    matching_lines.append(data_line)
                    continue

            data = matching_lines

        if len(data) > max_detailed:
            self.log.warning(
                "Too many %s to fetch.  Increase max_detailed_ in the config or results will be truncated." % object_type)

        for data_line in data[:max_detailed]:
            # We truncate the list of nodes/queues if it's above the limit
            self._get_metrics(data_line, object_type, instance)

    def _is_matching_stat(self, name, explicit_filters, regex_filters):
        if name in explicit_filters:
            return True
        for p in regex_filters:
            match = re.search(p, name)
            if match:
                return True
        return False

    def _get_metrics(self, data, object_type, instance):
        whitelist = instance.get('whitelist', {})
        object_whitelist = whitelist.get(object_type, DEFAULT_WHITELIST[object_type])

        dimensions_list = DIMENSIONS_MAP[object_type].copy()
        dimensions = self._set_dimensions({'component': 'rabbitmq', 'service': 'rabbitmq'},
                                          instance)
        for d in dimensions_list.iterkeys():
            dim = data.get(d, None)
            if dim not in [None, ""]:
                dimensions[dimensions_list[d]] = dim

        for attribute, metric_name, operation in ATTRIBUTES[object_type]:
            # Check if the metric should be collected
            if attribute not in object_whitelist:
                continue

            # Walk down through the data path, e.g. foo/bar => d['foo']['bar']
            root = data
            keys = attribute.split('/')
            for path in keys[:-1]:
                root = root.get(path, {})

            value = root.get(keys[-1], None)
            if value is None:
                value = 0.0
            try:
                self.log.debug("Collected data for %s: metric name: %s: value: %f dimensions: %s" % (object_type, metric_name, operation(value), str(dimensions)))
                self.gauge('rabbitmq.%s.%s' % (METRIC_SUFFIX[object_type], metric_name), operation(value), dimensions=dimensions)
            except ValueError:
                self.log.exception("Caught ValueError for %s %s = %s  with dimensions: %s" % (
                    METRIC_SUFFIX[object_type], attribute, value, dimensions))
