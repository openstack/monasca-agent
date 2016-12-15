# Copyright 2016 FUJITSU LIMITED
#
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

import requests

from monasca_agent.collector import checks
from monasca_agent.common import util

from monasca_setup.detection.plugins import kibana as kibana_setup

LOG = logging.getLogger(__name__)

_ONE_MB = (1024 * 1024) * 1.0
_LOAD_TIME_SERIES = ['1m', '5m', '15m']


class Kibana(checks.AgentCheck):
    def get_library_versions(self):
        try:
            import yaml
            version = yaml.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"PyYAML": version}

    def check(self, instance):
        config_url = self.init_config.get('url', None)

        if config_url is None:
            raise Exception('An url to kibana must be specified')

        instance_metrics = instance.get('metrics', None)
        if not instance_metrics:
            LOG.warning('All metrics have been disabled in configuration '
                        'file, nothing to do.')
            return

        version = self._get_kibana_version(config_url)
        dimensions = self._set_dimensions({'version': version}, instance)

        LOG.debug('Kibana version %s', version)

        try:
            stats = self._get_data(config_url)
        except Exception as ex:
            LOG.error('Error while trying to get stats from Kibana[%s]' %
                      config_url)
            LOG.exception(ex)
            return

        if not stats:
            LOG.warning('No stats data was collected from kibana')
            return

        self._process_metrics(stats, dimensions, instance_metrics)

    def _get_data(self, url):
        return requests.get(
            url=url,
            headers=util.headers(self.agent_config)
        ).json()

    def _process_metrics(self, stats, dimensions, instance_metrics):
        # collect from instance which metrics should be checked
        actual_metrics = {kibana_setup.get_metric_name(k): v for k, v in
                          stats.get('metrics', {}).items()}
        instance_url = self.init_config.get('url')

        for metric in actual_metrics.keys():
            if metric not in instance_metrics:
                LOG.debug('%s has been disabled for %s check' % (
                    metric, instance_url))
                continue
            else:
                self._process_metric(metric,
                                     actual_metrics.get(metric),
                                     dimensions)

    def _process_metric(self, metric, stats, dimensions):
        LOG.debug('Processing metric %s' % metric)

        metric_name = self.normalize(metric, 'kibana')

        if metric in ['heap_size', 'heap_used']:
            metric_name = '%s_mb' % metric_name
        elif metric in ['resp_time_max', 'resp_time_avg']:
            metric_name = '%s_ms' % metric_name

        for item in stats:
            timestamp = int(item[0]) / 1000.0
            measurements = item[1]
            cleaned_metric_name = metric_name

            if not isinstance(measurements, list):
                # only load comes as list in measurements
                measurements = [measurements]

            for it, measurement in enumerate(measurements):
                if measurement is None:
                    LOG.debug('Measurement for metric %s at %d was not '
                              'returned from kibana server, skipping'
                              % (metric_name, timestamp))
                    continue

                if metric in ['heap_size', 'heap_used']:
                    measurement /= _ONE_MB
                elif metric == 'load':
                    load_sub_metric = _LOAD_TIME_SERIES[it]
                    cleaned_metric_name = '%s_avg_%s' % (metric_name,
                                                         load_sub_metric)

                LOG.debug('Reporting %s as gauge with value %f'
                          % (cleaned_metric_name, measurement))

                self.gauge(
                    metric=cleaned_metric_name,
                    value=measurement,
                    dimensions=dimensions,
                    timestamp=timestamp
                )

    def _get_kibana_version(self, url):
        return requests.head(url=url).headers['kbn-version']
