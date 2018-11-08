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

import json

from six.moves import urllib

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.common.util import headers


class CouchDb(AgentCheck):

    """Extracts stats from CouchDB via its REST API

    http://wiki.apache.org/couchdb/Runtime_Statistics
    """

    def _create_metric(self, data, dimensions=None):
        overall_stats = data.get('stats', {})
        for key, stats in overall_stats.items():
            for metric, val in stats.items():
                if val['current'] is not None:
                    metric_name = '.'.join(['couchdb', key, metric])
                    self.gauge(metric_name, val['current'], dimensions=dimensions)

        for db_name, db_stats in data.get('databases', {}).items():
            for name, val in db_stats.items():
                if name in ['doc_count', 'disk_size'] and val is not None:
                    metric_name = '.'.join(['couchdb', 'by_db', name])
                    metric_dimensions = dimensions.copy()
                    metric_dimensions['db'] = db_name
                    self.gauge(metric_name, val, dimensions=metric_dimensions, device_name=db_name)

    def _get_stats(self, url):
        """Hit a given URL and return the parsed json.

        """
        self.log.debug('Fetching Couchdb stats at url: %s' % url)
        req = urllib.request.Request(url, None, headers(self.agent_config))

        # Do the request, log any errors
        request = urllib.request.urlopen(req)
        response = request.read()
        return json.loads(response)

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("A server must be specified")
        # Get dimensions
        dimensions = self._set_dimensions({'instance': server}, instance)
        data = self.get_data(server)
        self._create_metric(data, dimensions=dimensions)

    def get_data(self, server):
        # The dictionary to be returned.
        couchdb = {'stats': None, 'databases': {}}

        # First, get overall statistics.
        endpoint = '/_stats/'

        url = '%s%s' % (server, endpoint)
        overall_stats = self._get_stats(url)

        # No overall stats? bail out now
        if overall_stats is None:
            raise Exception("No stats could be retrieved from %s" % url)

        couchdb['stats'] = overall_stats

        # Next, get all database names.
        endpoint = '/_all_dbs/'

        url = '%s%s' % (server, endpoint)
        databases = self._get_stats(url)

        if databases is not None:
            for dbName in databases:
                endpoint = '/%s/' % dbName

                url = '%s%s' % (server, endpoint)
                db_stats = self._get_stats(url)
                if db_stats is not None:
                    couchdb['databases'][dbName] = db_stats

        return couchdb
