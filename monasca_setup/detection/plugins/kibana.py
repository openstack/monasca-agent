# Copyright 2016 FUJITSU LIMITED
# (C) Copyright 2016 Hewlett Packard Enterprise Development LP
# Copyright 2017 SUSE Linux GmbH
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
import os

import requests

from monasca_setup import agent_config
from monasca_setup import detection
from monasca_setup.detection import utils

LOG = logging.getLogger(__name__)

_KIBANA_CFG_FILE = '/opt/kibana/config/kibana.yml'
_API_STATUS = 'api/status'
_METRIC_ALIASES = {
    'heap_total': 'heap_size',
    'requests_per_second': 'req_sec',
    'response_time_avg': 'resp_time_avg',
    'response_time_max': 'resp_time_max'
}


def _to_snake_case(word):
    final = ''
    for item in word:
        if item.isupper():
            final += "_" + item.lower()
        else:
            final += item
    if final[0] == "_":
        final = final[1:]
    return final


def get_metric_name(metric):
    actual_name = _to_snake_case(metric)
    return _METRIC_ALIASES.get(actual_name, actual_name)


class Kibana(detection.Plugin):
    def _detect(self):
        # check process and port

        process_found = utils.find_process_cmdline('kibana') is not None
        has_deps = self.dependencies_installed()

        has_args = self.args is not None
        cfg_file = self._get_config_file() if has_args else _KIBANA_CFG_FILE
        has_config_file = os.path.isfile(cfg_file)

        available = process_found and has_deps and has_config_file

        self.available = available

        if not self.available:
            err_str = 'Plugin for Kibana will not be configured.'
            if not process_found:
                LOG.info('Kibana process has not been found. %s' % err_str)
            elif not has_deps:
                LOG.error('Kibana plugin dependencies are not satisfied. '
                          'Module "pyaml" not found. %s'
                          % err_str)
            elif not has_config_file:
                LOG.warning('Kibana plugin cannot find configuration file %s. %s'
                            % (cfg_file, err_str))

    def build_config(self):
        kibana_config = self._get_config_file()

        try:
            (kibana_host,
             kibana_port,
             kibana_protocol) = self._read_config(kibana_config)
        except Exception as ex:
            LOG.error('Failed to read configuration at %s' % kibana_config)
            LOG.exception(ex)
            return

        if kibana_protocol == 'https':
            LOG.error('"https" protocol is currently not supported')
            return None

        config = agent_config.Plugins()

        # retrieve user name and set in config
        # if passed in args (note args are optional)
        if (self.args and 'kibana-user' in self.args and
                self.args['kibana-user']):
            process = detection.watch_process_by_username(
                username=self.args['kibana-user'],
                process_name='kibana',
                service='monitoring',
                component='kibana'
            )
        else:
            process = detection.watch_process(['kibana'],
                                              service='monitoring',
                                              component='kibana',
                                              process_name='kibana')

        config.merge(process)

        kibana_url = '%s://%s:%d' % (
            kibana_protocol,
            kibana_host,
            kibana_port
        )

        if not self._has_metrics_support(kibana_url):
            LOG.warning('Running kibana does not support metrics, skipping...')
            return None
        else:
            metrics = self._get_all_metrics(kibana_url)
            config['kibana'] = {
                'init_config': {
                    'url': '%s/%s' % (kibana_url, _API_STATUS),
                },
                'instances': [
                    {
                        "name": kibana_url,
                        'metrics': metrics
                    }
                ]
            }

        LOG.info('\tWatching the kibana process.')

        return config

    def dependencies_installed(self):
        try:
            import yaml  # noqa
        except Exception:
            return False
        return True

    def _get_config_file(self):
        if self.args is not None:
            kibana_config = self.args.get('kibana-config', _KIBANA_CFG_FILE)
        else:
            kibana_config = _KIBANA_CFG_FILE
        return kibana_config

    @staticmethod
    def _read_config(kibana_cfg):
        import yaml
        with open(kibana_cfg, 'r') as stream:
            document = yaml.safe_load(stream=stream)

            has_ssl_support = ('server.ssl.cert' in document and
                               'server.ssl.key' in document)

            host = document.get('server.host')
            port = int(document.get('server.port'))
            protocol = 'https' if has_ssl_support else 'http'

            return host, port, protocol

    def _get_all_metrics(self, kibana_url):
        resp = self._get_metrics_request(kibana_url)
        data = resp.json()

        metrics = []
        # do not check plugins, check will go for overall status

        # get metrics
        for metric in data.get('metrics').keys():
            metrics.append(get_metric_name(metric))

        return metrics

    def _has_metrics_support(self, kibana_url):
        resp = self._get_metrics_request(kibana_url, method='HEAD')
        status_code = resp.status_code
        # Some Kibana versions may respond with 400:Bad Request
        # it means that URL is available but simply does
        # not support HEAD request
        return (status_code == 400) or (status_code == 200)

    def _get_metrics_request(self, url, method='GET'):
        request_url = '%s/%s' % (url, _API_STATUS)
        return requests.request(method=method, url=request_url)
