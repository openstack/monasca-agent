import sys

if sys.version_info < (2, 6):
    # Normally we'd write our checks to be compatible with >= python 2.4 but
    # the dependencies of this check are not compatible with 2.4 and would
    # be too much work to rewrite, so raise an exception here.
    raise Exception('kafka_consumer check requires at least Python 2.6')

import collections
import monasca_agent.collector.checks as checks

try:
    import kafka.client as client
    import kafka.common as common
    import kafka.consumer as consumer
except ImportError:
    raise Exception('Missing python dependency: kafka (https://github.com/mumrah/kafka-python)')


class KafkaCheck(checks.AgentCheck):
    """ Checks the configured kafka instance reporting the consumption lag
        for each partition per topic in each consumer group. If full_output
        is set also reports broker offsets and the current consumer offset.
        Works on Kafka version >= 0.8.1.1
    """
    def _validate_consumer_groups(self, val):
        """ Private config validation/marshalling functions
        """
        try:
            consumer_group, topic_partitions = val.items()[0]
            assert isinstance(consumer_group, (str, unicode))
            topic, partitions = topic_partitions.items()[0]
            assert isinstance(topic, (str, unicode))
            assert isinstance(partitions, (list, tuple))
            return val
        except Exception as e:
            self.log.exception(e)
            raise Exception('''The `consumer_groups` value must be a mapping of mappings, like this:
consumer_groups:
  myconsumer0: # consumer group name
    mytopic0: [0, 1] # topic: list of partitions
  myconsumer1:
    mytopic0: [0, 1, 2]
    mytopic1: [10, 12]
''')

    def check(self, instance):
        consumer_groups = self.read_config(instance, 'consumer_groups',
                                           cast=self._validate_consumer_groups)
        kafka_host_ports = self.read_config(instance, 'kafka_connect_str')
        full_output = self.read_config(instance, 'full_output', cast=bool)
        dimensions = {'component': 'kafka', 'service': 'kafka'}

        try:
            # Connect to Kafka
            kafka_conn = client.KafkaClient(kafka_host_ports)

            # Query Kafka for consumer offsets
            consumer_offsets = {}
            topics = collections.defaultdict(set)
            for consumer_group, topic_partitions in consumer_groups.iteritems():
                for topic, partitions in topic_partitions.iteritems():
                    kafka_consumer = consumer.SimpleConsumer(kafka_conn, consumer_group, topic)
                    # Remember the topic partitions that we've see so that we can
                    # look up their broker offsets later
                    topics[topic].update(set(partitions))
                    for partition in partitions:
                        try:
                            consumer_offsets[(consumer_group, topic, partition)] = kafka_consumer.offsets[partition]
                        except KeyError:
                            kafka_consumer.stop()
                            self.log.error('Error fetching consumer offset for {0} partition {1}'.format(topic, partition))
                    kafka_consumer.stop()

            # Query Kafka for the broker offsets, done in a separate loop so only one query is done
            # per topic even if multiple consumer groups watch the same topic
            broker_offsets = {}
            for topic, partitions in topics.items():
                offset_responses = []
                for p in partitions:
                    try:
                        response = kafka_conn.send_offset_request([common.OffsetRequest(topic, p, -1, 1)])
                        offset_responses.append(response[0])
                    except common.KafkaError as e:
                        self.log.error("Error fetching broker offset: {0}".format(e))

                for resp in offset_responses:
                    broker_offsets[(resp.topic, resp.partition)] = resp.offsets[0]
        finally:
            try:
                kafka_conn.close()
            except Exception:
                self.log.exception('Error cleaning up Kafka connection')

        # Report the broker data
        if full_output:
            broker_dimensions = dimensions.copy()
            for (topic, partition), broker_offset in broker_offsets.items():
                broker_dimensions.update({'topic': topic,
                                          'partition': partition})
                broker_offset = broker_offsets.get((topic, partition))
                self.gauge('kafka.broker_offset',
                           broker_offset,
                           dimensions=self._set_dimensions(broker_dimensions, instance))

        # Report the consumer data
        consumer_dimensions=dimensions.copy()
        for (consumer_group, topic, partition), consumer_offset in consumer_offsets.items():
            # Get the broker offset
            broker_offset = broker_offsets.get((topic, partition))
            # Report the consumer offset and lag
            consumer_dimensions.update({'topic': topic,
                                        'partition': partition,
                                        'consumer_group': consumer_group})
            if full_output:
                self.gauge('kafka.consumer_offset',
                           consumer_offset,
                           dimensions=self._set_dimensions(consumer_dimensions, instance))
            self.gauge('kafka.consumer_lag',
                       broker_offset - consumer_offset,
                       dimensions=self._set_dimensions(consumer_dimensions, instance))
