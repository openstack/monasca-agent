# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

from collections import defaultdict
import re

from six.moves import urllib

from monasca_agent.collector.checks import AgentCheck


db_stats = re.compile(r'^db_(\d)+$')
whitespace = re.compile(r'\s')


class KyotoTycoonCheck(AgentCheck):

    """Report statistics about the Kyoto Tycoon DBM-style

    database server (http://fallabs.com/kyototycoon/)
    """

    GAUGES = {
        'repl_delay': 'replication.delay',
        'serv_thread_count': 'threads',
    }

    RATES = {
        'serv_conn_count': 'connections',
        'cnt_get': 'ops.get.hits',
        'cnt_get_misses': 'ops.get.misses',
        'cnt_set': 'ops.set.hits',
        'cnt_set_misses': 'ops.set.misses',
        'cnt_remove': 'ops.del.hits',
        'cnt_remove_misses': 'ops.del.misses',
    }

    DB_GAUGES = {
        'count': 'records',
        'size': 'size',
    }
    TOTALS = {
        'cnt_get': 'ops.get.total',
        'cnt_get_misses': 'ops.get.total',
        'cnt_set': 'ops.set.total',
        'cnt_set_misses': 'ops.set.total',
        'cnt_remove': 'ops.del.total',
        'cnt_remove_misses': 'ops.del.total',
    }

    def check(self, instance):
        url = instance.get('report_url')
        if not url:
            raise Exception('Invalid Kyoto Tycoon report url %r' % url)

        dimensions = self._set_dimensions(None, instance)
        name = instance.get('name')

        if name is not None:
            dimensions.update({'instance': name})

        response = urllib.request.urlopen(url)
        body = response.read()

        totals = defaultdict(lambda: 0)
        for line in body.split('\n'):
            if '\t' not in line:
                continue

            key, value = line.strip().split('\t', 1)
            if key in self.GAUGES:
                name = self.GAUGES[key]
                self.gauge('kyototycoon.%s' % name, float(value), dimensions=dimensions)

            elif key in self.RATES:
                name = self.RATES[key]
                self.rate('kyototycoon.%s_per_s' % name, float(value), dimensions=dimensions)

            elif db_stats.match(key):
                # Also produce a per-db metrics tagged with the db
                # number in addition to the default dimensions
                m = db_stats.match(key)
                dbnum = int(m.group(1))
                db_dimensions = dimensions.copy()
                db_dimensions.update({'db': dbnum})
                for part in whitespace.split(value):
                    k, v = part.split('=', 1)
                    if k in self.DB_GAUGES:
                        name = self.DB_GAUGES[k]
                        self.gauge('kyototycoon.%s' % name, float(v), dimensions=db_dimensions)

            if key in self.TOTALS:
                totals[self.TOTALS[key]] += float(value)

        for key, value in totals.items():
            self.rate('kyototycoon.%s_per_s' % key, value, dimensions=dimensions)
