import collections
import logging

from monsetup.detection import Plugin, find_process_cmdline, watch_process
from monsetup import agent_config

log = logging.getLogger(__name__)


class Kafka(Plugin):

    """Detect Kafka daemons and sets up configuration to monitor them.
        This plugin configures the kafka_consumer plugin and does not configure any jmx based checks against kafka.
        Note this plugin will pull the same information from kafka on each node in the cluster it runs on.
    """

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        if find_process_cmdline('kafka') is not None:
            self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.
        """
        config = agent_config.Plugins()
        # First watch the process
        config.merge(watch_process(['kafka']))
        log.info("\tWatching the kafka process.")

        if self.dependencies_installed():
            # todo this naively assumes zookeeper is also available on localhost

            import kazoo
            from kazoo.client import KazooClient

            # kazoo fills up the console without this
            logging.getLogger('kazoo').setLevel(logging.WARN)

            zk = KazooClient(hosts='127.0.0.1:2181', read_only=True)
            zk.start()
            topics = {}
            for topic in zk.get_children('/brokers/topics'):
                topics[topic] = zk.get_children('/brokers/topics/%s/partitions' % topic)

            # {'consumer_group_name': { 'topic1': [ 0, 1, 2] # partitions }}
            consumers = collections.defaultdict(dict)
            for consumer in zk.get_children('/consumers'):
                try:
                    for topic in zk.get_children('/consumers/%s/offsets' % consumer):
                        if topic in topics:
                            consumers[consumer][topic] = topics[topic]
                except kazoo.exceptions.NoNodeError:
                    continue

            log.info("\tInstalling kafka_consumer plugin.")
            config['kafka_consumer'] = {'init_config': None,
                                        'instances': [{'kafka_connect_str': 'localhost:9092',
                                                       'zk_connect_str': 'localhost:2181',
                                                       'consumer_groups': dict(consumers)}]}
        return config

    def dependencies_installed(self):
        try:
            import kafka
            import kazoo
        except ImportError:
            return False

        return True
