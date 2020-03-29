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
import re
import sys

from six.moves import urllib

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.collector.checks.utils import add_basic_auth
from monasca_agent.common.util import headers


# Constants
COUCHBASE_STATS_PATH = '/pools/nodes'
DEFAULT_TIMEOUT = 10


class Couchbase(AgentCheck):

    """Extracts stats from Couchbase via its REST API

    http://docs.couchbase.com/couchbase-manual-2.0/#using-the-rest-api
    """

    def _create_metrics(self, data, dimensions=None):
        storage_totals = data['stats']['storageTotals']
        for key, storage_type in storage_totals.items():
            for metric_name, val in storage_type.items():
                if val is not None:
                    metric_name = '.'.join(
                        ['couchbase', key, self.camel_case_to_joined_lower(metric_name)])
                    self.gauge(metric_name, val, dimensions=dimensions)

        for bucket_name, bucket_stats in data['buckets'].items():
            for metric_name, val in bucket_stats.items():
                if val is not None:
                    metric_name = '.'.join(
                        ['couchbase', 'by_bucket', self.camel_case_to_joined_lower(metric_name)])
                    metric_dimensions = dimensions.copy()
                    metric_dimensions['bucket'] = bucket_name
                    self.gauge(
                        metric_name, val[0], dimensions=metric_dimensions, device_name=bucket_name)

        for node_name, node_stats in data['nodes'].items():
            for metric_name, val in node_stats['interestingStats'].items():
                if val is not None:
                    metric_name = '.'.join(
                        ['couchbase', 'by_node', self.camel_case_to_joined_lower(metric_name)])
                    metric_dimensions = dimensions.copy()
                    metric_dimensions['node'] = node_name
                    self.gauge(
                        metric_name, val, dimensions=metric_dimensions, device_name=node_name)

    def _get_stats(self, url, instance):
        """Hit a given URL and return the parsed json.

        """
        self.log.debug('Fetching Couchbase stats at url: %s' % url)
        req = urllib.request.Request(url, None, headers(self.agent_config))
        if 'user' in instance and 'password' in instance:
            add_basic_auth(req, instance['user'], instance['password'])

        if instance['is_recent_python']:
            timeout = instance.get('timeout', DEFAULT_TIMEOUT)
            request = urllib.request.urlopen(req, timeout=timeout)
        else:
            request = urllib.request.urlopen(req)

        response = request.read()
        return json.loads(response)

    def check(self, instance):
        server = instance.get('server', None)
        if server is None:
            raise Exception("The server must be specified")
        instance['is_recent_python'] = sys.version_info >= (2, 6, 0)
        # Get dimensions
        dimensions = self._set_dimensions({'instance': server}, instance)
        data = self.get_data(server, instance)
        self._create_metrics(data, dimensions=dimensions)

    def get_data(self, server, instance):
        # The dictionary to be returned.
        couchbase = {'stats': None,
                     'buckets': {},
                     'nodes': {}
                     }

        # build couchbase stats entry point
        url = '%s%s' % (server, COUCHBASE_STATS_PATH)
        overall_stats = self._get_stats(url, instance)

        # No overall stats? bail out now
        if overall_stats is None:
            raise Exception("No data returned from couchbase endpoint: %s" % url)

        couchbase['stats'] = overall_stats

        nodes = overall_stats['nodes']

        # Next, get all the nodes
        if nodes is not None:
            for node in nodes:
                couchbase['nodes'][node['hostname']] = node

        # Next, get all buckets .
        endpoint = overall_stats['buckets']['uri']

        url = '%s%s' % (server, endpoint)
        buckets = self._get_stats(url, instance)

        if buckets is not None:
            for bucket in buckets:
                bucket_name = bucket['name']

                # We have to manually build the URI for the stats bucket, as this is not
                # auto discoverable
                url = '%s/pools/nodes/buckets/%s/stats' % (server, bucket_name)
                bucket_stats = self._get_stats(url, instance)
                bucket_samples = bucket_stats['op']['samples']
                if bucket_samples is not None:
                    couchbase['buckets'][bucket['name']] = bucket_samples

        return couchbase

    # Takes a camelCased variable and returns a joined_lower equivalent.
    # Returns input if non-camelCase variable is detected.
    def camel_case_to_joined_lower(self, variable):
        # replace non-word with _
        converted_variable = re.sub(r'\W+', '_', variable)

        # insert _ in front of capital letters and lowercase the string
        converted_variable = re.sub(r'([A-Z])', r'_\g<1>', converted_variable).lower()

        # remove duplicate _
        converted_variable = re.sub(r'_+', '_', converted_variable)

        # handle special case of starting/ending underscores
        converted_variable = re.sub(r'^_|_$', '', converted_variable)

        return converted_variable
