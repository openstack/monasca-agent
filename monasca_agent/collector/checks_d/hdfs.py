# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP
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

from monasca_agent.collector.checks import AgentCheck


class HDFSCheck(AgentCheck):

    """Report on free space and space used in HDFS.

    """

    def check(self, instance):
        try:
            import snakebite.client
        except ImportError:
            raise ImportError('HDFSCheck requires the snakebite module')

        if 'namenode' not in instance:
            raise ValueError('Missing key \'namenode\' in HDFSCheck config')

        host, port = instance['namenode'], instance.get('port', 8020)
        if not isinstance(port, int):
            # PyYAML converts the number to an int for us
            raise ValueError('Port %r is not an integer' % port)

        dimensions = self._set_dimensions(None, instance)

        hdfs = snakebite.client.Client(host, port)
        stats = hdfs.df()
        # {'used': 2190859321781L,
        #  'capacity': 76890897326080L,
        #  'under_replicated': 0L,
        #  'missing_blocks': 0L,
        #  'filesystem': 'hdfs://hostname:port',
        #  'remaining': 71186818453504L,
        #  'corrupt_blocks': 0L}

        self.gauge('hdfs.used', stats['used'], dimensions=dimensions)
        self.gauge('hdfs.free', stats['remaining'], dimensions=dimensions)
        self.gauge('hdfs.capacity', stats['capacity'], dimensions=dimensions)
        self.gauge('hdfs.in_use', float(stats['used']) /
                   float(stats['capacity']), dimensions=dimensions)
        self.gauge('hdfs.under_replicated', stats['under_replicated'], dimensions=dimensions)
        self.gauge('hdfs.missing_blocks', stats['missing_blocks'], dimensions=dimensions)
        self.gauge('hdfs.corrupt_blocks', stats['corrupt_blocks'], dimensions=dimensions)


if __name__ == '__main__':
    check, instances = HDFSCheck.from_yaml('./hdfs.yaml')
    for instance in instances:
        check.check(instance)
        print("Metrics: %r" % check.get_metrics())
