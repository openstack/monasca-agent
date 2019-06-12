# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development LP
# Copyright 2016-2017 FUJITSU LIMITED
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
from os import path
import re
import subprocess as sp
from subprocess import CalledProcessError
from subprocess import STDOUT

from oslo_utils import importutils

from monasca_setup import agent_config
from monasca_setup.detection import find_process_cmdline
from monasca_setup.detection import Plugin
from monasca_setup.detection.utils import check_output
from monasca_setup.detection.utils import find_addr_listening_on_port_over_tcp
from monasca_setup.detection import watch_process

log = logging.getLogger(__name__)

_VIA_KAFKA_TOPIC_INDEX = 1
_KAFKA_BIN_LOCATIONS = (
    '',  # refers to kafka binaries being accessible
         # global (i.e. /usr/(local/)?bin)
    '/opt/kafka/bin'
)
_KAFKA_CONSUMER_GROUP_BIN = 'kafka-consumer-groups.sh'
_KAFKA_ZOOKEEPER_SHELL_BIN = 'zookeeper-shell.sh'

_CONSUMER_GROUP_COMMAND_LINE_VALUES_LEN = 7


class Kafka(Plugin):

    """Detect Kafka daemons and sets up configuration to monitor them.
       This plugin configures the kafka_consumer plugin and does not configure any jmx based
       checks against kafka.
       Note this plugin will pull the same information from kafka on each node in the cluster it
       runs on.

       To skip detection consumer groups and topics can be specified with plugin args,
       for example:
       `monasca-setup -d kafka -a "group1=topic1 group2=topic2/topic3"`
       All partitions are assumed for each topic and '/' is used to deliminate more than one
       topic per consumer group.

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

        (self._kafka_consumer_bin,
            self._zookeeper_consumer_bin) = self._find_topic_listing_binaries()

        kafka_has_scripts = (self._kafka_consumer_bin or
                             self._zookeeper_consumer_bin)

        self.available = (process_exists and has_dependencies and
                          kafka_has_scripts)

        if not self.available:
            if not process_exists:
                log.error('Kafka process does not exist.')
            elif not has_dependencies:
                log.error(('Kafka process exists but required '
                           'dependency monasca-common is '
                           'not installed.\n\t'
                           'Please install with: '
                           'pip install monasca-agent[kafka_plugin]'))
            elif not kafka_has_scripts:
                log.error(('Kafka process exists, dependencies are installed '
                           'but neither %s nor %s '
                           'executable was found.'),
                          _KAFKA_CONSUMER_GROUP_BIN,
                          _KAFKA_ZOOKEEPER_SHELL_BIN)

    def _detect_consumers(self):
        """Using zookeeper and a kafka connection find the consumers and associated topics. """
        try:
            log.info("\tInstalling kafka_consumer plugin.")

            kafka_connect_str = self._find_kafka_connection()

            consumers = None

            if self._kafka_consumer_bin:
                consumers = self._detect_consumer_via_kafka()
            if not consumers and self._zookeeper_consumer_bin:
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
            self._kafka_consumer_bin))
        try:
            output = check_output([
                self._kafka_consumer_bin,
                '--zookeeper',
                self.zk_url,
                '--list'
            ], stderr=STDOUT)

            consumers = {}
            consumer_groups = output.splitlines()

            for consumer_group in consumer_groups:
                output = check_output([
                    self._kafka_consumer_bin,
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
                    if (values and len(values) ==
                            _CONSUMER_GROUP_COMMAND_LINE_VALUES_LEN):
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
            self._zookeeper_consumer_bin))
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
        listen_ip = find_addr_listening_on_port_over_tcp(self.port)
        if listen_ip:
            log.info("\tKafka found listening on {:s}:{:d}".format(listen_ip, self.port))
        else:
            log.info(
                "\tKafka not found listening on a specific IP (port {:d}),"
                "using 'localhost'".format(
                    self.port))
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
           I am using the local command line kafka rather than kazoo because it doesn't make
           sense to have kazoo as a dependency only for detection.
        """
        zk_shell = [self._zookeeper_consumer_bin, self.zk_url, 'ls', path]
        try:
            output = check_output(zk_shell, stderr=STDOUT)
        except CalledProcessError:
            log.error('Error running the zookeeper shell to list path %s',
                      path)
            raise

        # The last line is like '[item1, item2, item3]', '[]' or an error message
        # not starting with [
        last_line = output.splitlines()[-1]
        if len(last_line) == 2 or last_line[0] != '[':
            return []
        else:
            return [entry.strip() for entry in last_line.strip('[]').split(',')]

    def _find_topic_listing_binaries(self):

        kafka_bin = zookeper_bin = None

        for location in _KAFKA_BIN_LOCATIONS:
            if not kafka_bin:
                kafka_bin = self._verify_callable_exists(
                    path.join(location, _KAFKA_CONSUMER_GROUP_BIN)
                )
            if not zookeper_bin:
                zookeper_bin = self._verify_callable_exists(
                    path.join(location, _KAFKA_ZOOKEEPER_SHELL_BIN)
                )

        # traversed all locations, this is what we've got
        if kafka_bin:
            log.debug('\tFound %s at %s', _KAFKA_CONSUMER_GROUP_BIN,
                      kafka_bin)
        if zookeper_bin:
            log.debug('\tFound %s at %s', _KAFKA_ZOOKEEPER_SHELL_BIN,
                      zookeper_bin)

        return kafka_bin, zookeper_bin

    @staticmethod
    def _verify_callable_exists(path):
        """Verify if callable exists.

        Method tries to execute binary located
        under path to see if that exists.

        If binary cannot be called, an :py:exc:`OSError` is thrown.
        Effectively that means that binary is not accessible.

        Note:
            If binary is not callable, method returns None

        :param path: path to binary
        :type path: str
        :return: path or None
        :rtype: (str, None)

        """
        try:
            sp.check_output(args=[path], stderr=sp.STDOUT)
        except sp.CalledProcessError:
            log.debug('\tExecutable %s exists', path)
        except OSError:
            log.debug('\tNo executable/file at %s', path)
            return None
        except Exception as ex:
            log.warning('Skipping exception %s', str(ex))
            # note(trebskit) we are not interested in other problems
            # from POV of this method only relevant information
            # is that OSError is not thrown which would be the case
            # if binary is not accessible
            pass
        return path  # return path if if it can be launched

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
            for key, value in self.args.items():
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
        return importutils.try_import('monasca_common', False)
