# (c) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

import os

from monasca_agent.collector.checks import AgentCheck


class PostfixCheck(AgentCheck):

    """This check provides metrics on the number of messages in a given postfix queue

    WARNING: the user that monasca-agent runs as must have sudo access for the 'find' command
             sudo access is not required when running monasca-agent as root (not recommended)

    example /etc/sudoers entry (assumes monasca-agent runs as user mon-agent):
             mon-agent ALL=(ALL) NOPASSWD:/usr/bin/find

    YAML config options:
        "directory" - the value of 'postconf -h queue_directory'
        "queues" - the postfix mail queues you would like to get message count totals for
    """

    def check(self, instance):
        config = self._get_config(instance)

        directory = config['directory']
        queues = config['queues']
        dimensions = self._set_dimensions(None, instance)

        self._get_queue_count(directory, queues, dimensions)

    @staticmethod
    def _get_config(instance):
        directory = instance.get('directory', None)
        queues = instance.get('queues', None)
        if not queues or not directory:
            raise Exception('missing required yaml config entry')

        instance_config = {
            'directory': directory,
            'queues': queues
        }

        return instance_config

    def _get_queue_count(self, directory, queues, dimensions):
        for queue in queues:
            queue_path = os.path.join(directory, queue)
            if not os.path.exists(queue_path):
                raise Exception('%s does not exist' % queue_path)

            count = 0
            if os.geteuid() == 0:
                # agent is running as root (not recommended)
                count = sum(len(files) for root, dirs, files in os.walk(queue_path))
            else:
                # can agent user run sudo?
                test_sudo = os.system('setsid sudo -l > /dev/null')
                if test_sudo == 0:
                    count = os.popen('sudo find %s -type f | wc -l' % queue_path)
                    count = count.readlines()[0].strip()
                else:
                    raise Exception('The monasca-agent user does not have sudo access')

            # emit an individually tagged metric
            dimensions.update({'queue': queue, 'instance': os.path.basename(directory)})
            self.gauge('postfix.queue_size', int(count), dimensions=dimensions)
