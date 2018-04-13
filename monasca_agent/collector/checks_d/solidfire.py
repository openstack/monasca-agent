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
import logging
import time

import requests
from requests.packages.urllib3 import exceptions
import six
import warnings

import monasca_agent.collector.checks as checks


LOG = logging.getLogger(__name__)


class SolidFire(checks.AgentCheck):
    """SolidFire plugin for reporting cluster metrics. Reference the general
    plugin documentation for metric specifics.
    """

    def __init__(self, name, init_config, agent_config):
        super(SolidFire, self).__init__(name, init_config, agent_config)
        self.sf = None
        self.instance = None
        self.cluster = None

    def check(self, instance):
        """Pull down cluster stats."""
        self.cluster = instance.get('name')
        dimensions = {'service': 'solidfire',
                      'cluster': self.cluster}
        data = {}
        num_metrics = 0
        # Extract cluster auth information
        auth = self._pull_auth(instance)
        self.sf = SolidFireLib(auth)

        # Query cluster for stats
        data.update(self._get_cluster_stats())
        # Query for active cluster faults.
        data.update(self._list_cluster_faults())
        # Query for cluster capacity info
        data.update(self._get_cluster_capacity())

        # Dump data upstream.
        for key, value in data.items():
            if data[key] is None:
                continue
            self.gauge(key, value, dimensions)
            num_metrics += 1

        LOG.debug('Collected %s metrics' % (num_metrics))

    def _pull_auth(self, instance):
        """Extract auth data from instance data.

        Simple check to verify we have enough auth information to connect
        to the SolidFire cluster.
        """
        for k in ['mvip', 'username', 'password']:
            if k not in instance:
                msg = 'Missing config value: %s' % (k)
                LOG.error(msg)
                raise Exception(msg)
        auth = {'mvip': instance.get('mvip'),
                'port': instance.get('port', 443),
                'login': instance.get('username'),
                'passwd': instance.get('password')}
        auth['url'] = 'https://%s:%s' % (auth['mvip'],
                                         auth['port'])
        return auth

    def _get_cluster_stats(self):
        res = (self.sf.issue_api_request('GetClusterStats', {}, '8.0')
               ['result']['clusterStats'])
        # Cluster utilization is the overall load.
        data = {'solidfire.cluster_utilization': res['clusterUtilization']}
        return data

    def _get_cluster_capacity(self):
        res = (self.sf.issue_api_request('GetClusterCapacity', {}, '8.0')
               ['result']['clusterCapacity'])

        # Number of 4KiB blocks with data after the last garbage collection
        non_zero_blocks = res['nonZeroBlocks']
        # Number of 4KiB blocks without data after the last garbage collection
        zero_blocks = res['zeroBlocks']
        # Number of blocks(not always 4KiB) stored on block drives.
        unique_blocks = res['uniqueBlocks']
        # Amount of space the unique blocks take on the block drives.
        unique_blocks_space = res['uniqueBlocksUsedSpace']

        # Amount of space consumed by the block services, including cruft.
        active_block_space = res['activeBlockSpace']
        # Maximum amount of bytes allocated to the block services.
        max_block_space = res['maxUsedSpace']

        # Amount of space consumed by the metadata services.
        active_slice_space = res['usedMetadataSpace']
        # Amount of space consumed by the metadata services for snapshots.
        active_snap_space = res['usedMetadataSpaceInSnapshots']
        # Maximum amount of bytes allocated to the metadata services.
        max_slice_space = res['maxUsedMetadataSpace']

        # Volume provisioned space
        prov_space = res['provisionedSpace']
        # Max provisionable space if 100% metadata space used.
        max_prov_space = res['maxProvisionedSpace']
        # Overprovision limit.
        max_overprov_space = res['maxOverProvisionableSpace']

        # Number of active iSCSI sessions.
        iscsi_sessions = res['activeSessions']
        # Average IOPS since midnight UTC.
        avg_iops = res['averageIOPS']
        # Peak IOPS since midnight UTC.
        peak_iops = res['peakIOPS']
        # Current IOPs over the last 5 seconds.
        current_iops = res['currentIOPS']
        # Theoretical max IOPS
        max_iops = res['maxIOPS']

        # Single-node clusters can report zero values for some divisors.
        thin_factor, dedup_factor, comp_factor = 1, 1, 1
        # Same calculations used in the SolidFire UI.
        if non_zero_blocks:
            # Thin provisioning factor
            thin_factor = ((non_zero_blocks + zero_blocks) /
                           float(non_zero_blocks))
        if unique_blocks:
            # Data deduplication factor
            dedup_factor = non_zero_blocks / float(unique_blocks)
        if unique_blocks_space:
            # 4096 constant from our internal block size, pre-compression
            # Compression efficiency factor
            comp_factor = (unique_blocks * 4096) / float(unique_blocks_space)
        # Overall data reduction efficiency factor
        eff_factor = thin_factor * dedup_factor * comp_factor

        data = {'solidfire.num_iscsi_sessions': iscsi_sessions,
                'solidfire.iops.avg_utc': avg_iops,
                'solidfire.iops.peak_utc': peak_iops,
                'solidfire.iops.avg_5_sec': current_iops,
                'solidfire.iops.max_available': max_iops,
                'solidfire.provisioned_bytes': prov_space,
                'solidfire.max_provisioned_bytes': max_prov_space,
                'solidfire.max_overprovisioned_bytes': max_overprov_space,
                'solidfire.max_block_bytes': max_block_space,
                'solidfire.active_block_bytes': active_block_space,
                'solidfire.max_meta_bytes': max_slice_space,
                'solidfire.active_meta_bytes': active_slice_space,
                'solidfire.active_snapshot_bytes': active_snap_space,
                'solidfire.non_zero_blocks': non_zero_blocks,
                'solidfire.zero_blocks': zero_blocks,
                'solidfire.unique_blocks': unique_blocks,
                'solidfire.unique_blocks_used_bytes': unique_blocks_space,
                'solidfire.thin_provision_factor': thin_factor,
                'solidfire.deduplication_factor': dedup_factor,
                'solidfire.compression_factor': comp_factor,
                'solidfire.data_reduction_factor': eff_factor
                }
        return data

    def _list_cluster_faults(self):
        # Report the number of active faults. Might be useful for an alarm?
        res = (self.sf.issue_api_request('ListClusterFaults',
                                         {'faultTypes': 'current'},
                                         '8.0')
               ['result']['faults'])
        data = {'solidfire.active_cluster_faults': len(res)}
        return data


def retry(exc_tuple, tries=5, delay=1, backoff=2):
    # Retry decorator used for issuing API requests.
    def retry_dec(f):
        @six.wraps(f)
        def func_retry(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 1:
                try:
                    return f(*args, **kwargs)
                except exc_tuple:
                    time.sleep(_delay)
                    _tries -= 1
                    _delay *= backoff
                    LOG.debug('Retrying %(args)s, %(tries)s attempts '
                              'remaining...',
                              {'args': args, 'tries': _tries})
            msg = ('Retry count exceeded for command: %s' %
                   (args[1]))
            LOG.error(msg)
            raise Exception(msg)
        return func_retry
    return retry_dec


class SolidFireLib(object):
    """Gutted version of the Cinder driver.

    Just enough to communicate with a SolidFire cluster for POC.
    """

    retryable_errors = ['xDBVersionMismatch',
                        'xMaxSnapshotsPerVolumeExceeded',
                        'xMaxClonesPerVolumeExceeded',
                        'xMaxSnapshotsPerNodeExceeded',
                        'xMaxClonesPerNodeExceeded',
                        'xNotReadyForIO']

    retry_exc_tuple = (requests.exceptions.ConnectionError)

    def __init__(self, auth):
        self.endpoint = auth
        self.active_cluster_info = {}
        self._set_active_cluster_info(auth)

    @retry(retry_exc_tuple, tries=6)
    def issue_api_request(self, method, params, version='1.0', endpoint=None):
        if params is None:
            params = {}
        if endpoint is None:
            endpoint = self.active_cluster_info['endpoint']

        payload = {'method': method, 'params': params}
        url = '%s/json-rpc/%s/' % (endpoint['url'], version)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", exceptions.InsecureRequestWarning)
            req = requests.post(url,
                                data=json.dumps(payload),
                                auth=(endpoint['login'], endpoint['passwd']),
                                verify=False,
                                timeout=30)
        response = req.json()
        req.close()
        if (('error' in response) and
                (response['error']['name'] in self.retryable_errors)):
            msg = ('Retryable error (%s) encountered during '
                   'SolidFire API call.' % response['error']['name'])
            raise Exception(msg)

        if 'error' in response:
            msg = ('API response: %s') % response
            raise Exception(msg)

        return response

    def _set_active_cluster_info(self, endpoint):
        self.active_cluster_info['endpoint'] = endpoint

        for k, v in self.issue_api_request(
                'GetClusterInfo',
                {})['result']['clusterInfo'].items():
            self.active_cluster_info[k] = v

        # Add a couple extra things that are handy for us
        self.active_cluster_info['clusterAPIVersion'] = (
            self.issue_api_request('GetClusterVersionInfo',
                                   {})['result']['clusterAPIVersion'])
