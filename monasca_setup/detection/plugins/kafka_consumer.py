# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
# Copyright 2016 FUJITSU LIMITED

import logging
import os
import re

from subprocess import CalledProcessError
from subprocess import STDOUT

from monasca_setup import agent_config

from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection import Plugin
from monasca_setup.detection import watch_process

from monasca_setup.detection.utils import check_output
from monasca_setup.detection.utils import find_addr_listening_on_port

log = logging.getLogger(__name__)

_VIA_KAFKA_TOPIC_INDEX = 1
_KAFKA_BIN_DIR = '/opt/kafka/bin'
_KAFKA_CONSUMER_GROUP_COMMAND = '%s/kafka-consumer-groups.sh' % _KAFKA_BIN_DIR
_KAFKA_ZOOKEEPER_SHELL_COMMAND = '%s/zookeeper-shell.sh' % _KAFKA_BIN_DIR

_CONSUMER_GROUP_COMMAND_LINE_VALUES_LEN = 7


class Kafka(Plugin):

    """Detect Kafka daemons and sets up configuration to monitor them.
        This plugin configures the kafka_consumer plugin and does not configure any jmx based checks against kafka.
        Note this plugin will pull the same information from kafka on each node in the cluster it runs on.

        To skip detection consumer groups and topics can be specified with plugin args, for example:
        `monasca-setup -d kafka -a "group1=topic1 group2=topic2/topic3"`
        All partitions are assumed for each topic and '/' is used to deliminate more than one topic per consumer group.

        For more information see:
            - https://cwiki.apache.org/confluence/display/KAFKA/A+Guide+To+The+Kafka+Protocol
    """

    def __init__(self, template_dir, overwrite=True, args=None, port=9092):
        Plugin.__init__(self, template_dir, overwrite, args)
        self.port = port
        self.zk_url = self._find_zookeeper_url()
        self.config = agent_config.Plugins()

    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        process_exists = find_process_cmdline('kafka') is not None
        has_dependencies = self.dependencies_installed()

        self._consumer_group_shell_exists = os.path.isfile(
            _KAFKA_CONSUMER_GROUP_COMMAND)
        self._zookeeper_shell_exists = os.path.isfile(
            _KAFKA_ZOOKEEPER_SHELL_COMMAND)

        kafka_has_scripts = (self._consumer_group_shell_exists or
                             self._zookeeper_shell_exists)

        self.available = (process_exists and has_dependencies and
                          kafka_has_scripts)

        if not self.available:
            if not process_exists:
                log.error('Kafka process does not exist.')
            elif not has_dependencies:
                log.error(('Kafka process exists but required '
                           'dependency kafka-python is '
                           'not installed.'))
            elif not kafka_has_scripts:
                log.error(('Kafka process exists, dependencies are installed '
                           'but neither %s nor %s '
                           'executable was found.'),
                          _KAFKA_CONSUMER_GROUP_COMMAND,
                          _KAFKA_CONSUMER_GROUP_COMMAND)

    def _detect_consumers(self):
        """Using zookeeper and a kafka connection find the consumers and associated topics. """
        try:
            log.info("\tInstalling kafka_consumer plugin.")

            kafka_connect_str = self._find_kafka_connection()

            consumers = None

            if self._consumer_group_shell_exists:
                consumers = self._detect_consumer_via_kafka()
            if not consumers and self._zookeeper_shell_exists:
                consumers = self._detect_consumer_via_zookeeper()

            instances = {
                'name': kafka_connect_str,
                'kafka_connect_str': kafka_connect_str,
                'per_partition': False,
                'consumer_groups': consumers or {}
            }
            self.config['kafka_consumer'] = {
                'init_config': None,
                'instances': [instances]
            }

        except Exception as ex:
            log.error('Error Detecting Kafka consumers/topics')
            log.exception(ex)

    def _detect_consumer_via_kafka(self):
        """Detect consumers groups using kafka-consumer-groups"""
        log.info("\tDetecting kafka consumers with {:s} command".format(
            _KAFKA_CONSUMER_GROUP_COMMAND))
        try:
            output = check_output([
                _KAFKA_CONSUMER_GROUP_COMMAND,
                '--zookeeper',
                self.zk_url,
                '--list'
            ], stderr=STDOUT)

            consumers = {}
            consumer_groups = output.splitlines()

            for consumer_group in consumer_groups:
                output = check_output([
                    _KAFKA_CONSUMER_GROUP_COMMAND,
                    '--zookeeper',
                    self.zk_url,
                    '--describe',
                    '--group',
                    consumer_group
                ], stderr=STDOUT)

                lines = output.splitlines()
                topics = {}
                for it, line in enumerate(reversed(lines)):
                    if it == len(lines) - 1 or not line:
                        break
                    values = line.split(',')
                    # There will be always 7 values in output
                    # after splitting the line by ,
                    if (values and len(values)
                            == _CONSUMER_GROUP_COMMAND_LINE_VALUES_LEN):
                        topics[values[_VIA_KAFKA_TOPIC_INDEX].strip()] = []
                if len(topics.keys()):
                    consumers[consumer_group] = topics

            return consumers
        except Exception as ex:
            log.warn(('Failed to retrieve consumers '
                      'with kafka-consumer-groups.sh. Error is %s'), ex)
        return None

    def _detect_consumer_via_zookeeper(self):
        """Try to get consumers via zookeeper.

        :return: map of consumers group to topics
        :rtype: dict
        """
        log.info("\tDetecting kafka consumers with {:s} command".format(
            _KAFKA_ZOOKEEPER_SHELL_COMMAND))
        try:
            consumers = {}
            for consumer in self._ls_zookeeper('/consumers'):
                topics = dict((topic, []) for topic in self._ls_zookeeper(
                    '/consumers/%s/offsets' % consumer))
                if len(topics) > 0:
                    consumers[consumer] = topics
            return consumers
        except Exception as ex:
            log.warn(('Failed to retrieve consumers '
                      'with zookeeper-shell.sh. Error is %s'), ex)

        return None

    def _find_kafka_connection(self):
        listen_ip = find_addr_listening_on_port(self.port)
        if listen_ip:
            log.info("\tKafka found listening on {:s}:{:d}".format(listen_ip, self.port))
        else:
            log.info("\tKafka not found listening on a specific IP (port {:d}), using 'localhost'".format(self.port))
            listen_ip = 'localhost'

        return "{:s}:{:d}".format(listen_ip, self.port)

    @staticmethod
    def _find_zookeeper_url():
        """Pull the zookeeper url the kafka config.
           :return: Zookeeper url
        """
        zk_connect = re.compile('zookeeper.connect=(.*)')
        try:
            with open('/etc/kafka/server.properties') as settings:
                match = zk_connect.search(settings.read())
        except IOError:
            return None

        if match is None:
            log.error('No zookeeper url found in the kafka server properties.')
            return None

        return match.group(1).split(',')[0]  # Only use the first zk url

    def _ls_zookeeper(self, path):
        """Do a ls on the given zookeeper path.
           I am using the local command line kafka rather than kazoo because it doesn't make sense to
           have kazoo as a dependency only for detection.
        """
        zk_shell = [_KAFKA_ZOOKEEPER_SHELL_COMMAND, self.zk_url, 'ls', path]
        try:
            output = check_output(zk_shell, stderr=STDOUT)
        except CalledProcessError:
            log.error('Error running the zookeeper shell to list path %s' % path)
            raise

        # The last line is like '[item1, item2, item3]', '[]' or an error message not starting with [
        last_line = output.splitlines()[-1]
        if len(last_line) == 2 or last_line[0] != '[':
            return []
        else:
            return [entry.strip() for entry in last_line.strip('[]').split(',')]

    def build_config(self):
        """Build the config as a Plugins object and return.
            Config includes: consumer_groups (include topics) and kafka_connection_str
        """
        # First watch the process
        self.config.merge(watch_process(['kafka.Kafka'], 'kafka', exact_match=False))
        log.info("\tWatching the kafka process.")

        if not self.dependencies_installed():
            log.warning("Dependencies not installed, skipping Kafka Consumer plugin configuration.")
        elif self.args is not None and len(self.args) > 0:
            kafka_connect_str = self._find_kafka_connection()
            consumers = {}
            service_name = kafka_connect_str
            # Check if the plugin passed in a service name
            # If it did, delete it after use so it doesn't become a consumer group
            if 'service_name' in self.args:
                service_name += '_' + str(self.args.pop('service_name'))
            for key, value in self.args.iteritems():
                value_dict = {topic: [] for topic in value.split('/')}
                consumers[key] = value_dict
            self.config['kafka_consumer'] = {'init_config': None,
                                             'instances': [{'name': service_name,
                                                            'kafka_connect_str': kafka_connect_str,
                                                            'per_partition': False,
                                                            'consumer_groups': consumers}]}
        elif self.zk_url is not None:
            self._detect_consumers()
        return self.config

    def dependencies_installed(self):
        try:
            import kafka
        except ImportError:
            return False

        return True
