# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import re
import subprocess

from monasca_agent.collector import checks

_CACHE_FLUSH_RATE_REGEX = re.compile(r'(\d+) ([kKmMgG][bB])/s flush')
_CACHE_EVICT_RATE_REGEX = re.compile(r'(\d+) ([kKmMgG][bB])/s evict')
_CACHE_PROMOTE_OPS_REGEX = re.compile(r'(\d+) op/s promote')

_CLIENT_IO_READ_REGEX = re.compile(r'(\d+) ([kKmMgG][bB])/s rd')
_CLIENT_IO_WRITE_REGEX = re.compile(r'(\d+) ([kKmMgG][bB])/s wr')
_CLIENT_IO_READ_OPS_REGEX = re.compile(r'(\d+) op/s rd')
_CLIENT_IO_WRITE_OPS_REGEX = re.compile(r'(\d+) op/s wr')

_RECOVERY_IO_RATE_REGEX = re.compile(r'(\d+) ([kKmMgG][bB])/s')
_RECOVERY_IO_KEY_REGEX = re.compile(r'(\d+) keys/s')
_RECOVERY_IO_OBJECT_REGEX = re.compile(r'(\d+) objects/s')

_DEGRADED_REGEX = re.compile(r'([\d]+) pgs degraded')
_STUCK_DEGRADED_REGEX = re.compile(r'([\d]+) pgs stuck degraded')
_UNCLEAN_REGEX = re.compile(r'([\d]+) pgs unclean')
_STUCK_UNCLEAN_REGEX = re.compile(r'([\d]+) pgs stuck unclean')
_UNDERSIZED_REGEX = re.compile(r'([\d]+) pgs undersized')
_STUCK_UNDERSIZED_REGEX = re.compile(r'([\d]+) pgs stuck undersized')
_STALE_REGEX = re.compile(r'([\d]+) pgs stale')
_STUCK_STALE_REGEX = re.compile(r'([\d]+) pgs stuck stale')
_SLOW_REQUEST_REGEX = re.compile(r'([\d]+) requests are blocked')
_DEGRADED_OBJECTS_REGEX = re.compile(
    r'recovery ([\d]+)/([\d]+) objects degraded')
_MISPLACED_OBJECTS_REGEX = re.compile(
    r'recovery ([\d]+)/([\d]+) objects misplaced')


class Ceph(checks.AgentCheck):

    def check(self, instance):
        self.instance = instance
        self.CLUSTER = instance.get('cluster_name', 'ceph')
        self.dimensions = self._set_dimensions({'ceph_cluster': self.CLUSTER,
                                                'service': 'ceph'}, instance)

        self._collect_usage_metrics()
        self._collect_stats_metrics()
        self._collect_mon_metrics()
        self._collect_osd_metrics()
        self._collect_pool_metrics()

    def _collect_usage_metrics(self):
        if not self.instance.get('collect_usage_metrics', True):
            return
        ceph_df = self._ceph_cmd('df detail', 'json')
        metrics = self._get_usage_metrics(ceph_df)
        for metric, value in metrics.iteritems():
            self.gauge(metric, value, dimensions=self.dimensions)

    def _collect_stats_metrics(self):
        if not self.instance.get('collect_stats_metrics', True):
            return
        ceph_status = self._ceph_cmd('status', 'json')
        ceph_status_plain = self._ceph_cmd('status')
        metrics = self._get_stats_metrics(ceph_status, ceph_status_plain)
        for metric, value in metrics.iteritems():
            self.gauge(metric, value, dimensions=self.dimensions)

    def _collect_mon_metrics(self):
        if not self.instance.get('collect_mon_metrics', True):
            return
        ceph_status = self._ceph_cmd('status', 'json')
        mon_metrics_dict = self._get_mon_metrics(ceph_status)
        for monitor, metrics in mon_metrics_dict.iteritems():
            mon_dimensions = self.dimensions.copy()
            mon_dimensions['monitor'] = monitor
            for metric, value in metrics.iteritems():
                self.gauge(metric, value, dimensions=mon_dimensions)

    def _collect_osd_metrics(self):
        if not self.instance.get('collect_osd_metrics', True):
            return
        ceph_osd_df = self._ceph_cmd('osd df', 'json')
        ceph_osd_perf = self._ceph_cmd('osd perf', 'json')
        ceph_osd_dump = self._ceph_cmd('osd dump', 'json')
        osd_metrics_dict = self._get_osd_metrics(ceph_osd_df,
                                                 ceph_osd_perf,
                                                 ceph_osd_dump)
        for osd, metrics in osd_metrics_dict.iteritems():
            osd_dimensions = self.dimensions.copy()
            osd_dimensions['osd'] = osd
            for metric, value in metrics.iteritems():
                self.gauge(metric, value, dimensions=osd_dimensions)

        osd_summary_metrics = self._get_osd_summary_metrics(ceph_osd_df)
        for metric, value in osd_summary_metrics.iteritems():
            self.gauge(metric, value, dimensions=self.dimensions)

    def _collect_pool_metrics(self):
        if not self.instance.get('collect_pool_metrics', True):
            return
        ceph_df = self._ceph_cmd('df detail', 'json')
        pool_metrics_dict = self._get_pool_metrics(ceph_df)
        for pool, metrics in pool_metrics_dict.iteritems():
            pool_dimensions = self.dimensions.copy()
            pool_dimensions['pool'] = pool
            for metric, value in metrics.iteritems():
                self.gauge(metric, value, dimensions=pool_dimensions)
        self.gauge('ceph.pools.count', len(pool_metrics_dict.keys()),
                   dimensions=self.dimensions)

        ceph_osd_pool_stats = self._ceph_cmd('osd pool stats', 'json')
        pool_stats_dict = self._get_pool_stats_metrics(ceph_osd_pool_stats)
        for pool, metrics in pool_stats_dict.iteritems():
            pool_dimensions = self.dimensions.copy()
            pool_dimensions['pool'] = pool
            for metric, value in metrics.iteritems():
                self.gauge(metric, value, dimensions=pool_dimensions)

    def _ceph_cmd(self, args, format='plain'):
        cmd = 'ceph --cluster {0} -f {1} {2}'.format(self.CLUSTER, format,
                                                     args)
        if self.instance.get('use_sudo', False):
            cmd = "sudo " + cmd

        try:
            output = subprocess.check_output(cmd, shell=True,
                                             stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Unable to execute ceph command '{}': {}".format(cmd,
                                                                 e.output))
            raise

        if format == 'json':
            return json.loads(output)
        return output

    def _parse_ceph_status(self, status_str):
        return {
            'HEALTH_OK': 0,
            'HEALTH_WARN': 1,
            'HEALTH_ERR': 2,
        }.get(status_str, 2)

    def _get_cache_io(self, cache_str):
        """Parse a cache string and returns a dictionary with metrics
        in the format {'metric1': value1, ...}
        """
        metrics = {}

        match_flush = re.search(_CACHE_FLUSH_RATE_REGEX, cache_str)
        if match_flush:
            rate = int(match_flush.group(1))
            unit = match_flush.group(2).lower()
            if unit == 'gb':
                rate = rate * 1e9
            elif unit == 'mb':
                rate = rate * 1e6
            elif unit == 'kb':
                rate = rate * 1e3
            metrics['ceph.cluster.cache.flush_bytes_per_sec'] = rate

        match_evict = re.search(_CACHE_EVICT_RATE_REGEX, cache_str)
        if match_evict:
            rate = int(match_evict.group(1))
            unit = match_evict.group(2).lower()
            if unit == 'gb':
                rate = rate * 1e9
            elif unit == 'mb':
                rate = rate * 1e6
            elif unit == 'kb':
                rate = rate * 1e3
            metrics['ceph.cluster.cache.evict_bytes_per_sec'] = rate

        match_promote = re.search(_CACHE_PROMOTE_OPS_REGEX, cache_str)
        if match_promote:
            metrics['ceph.cluster.cache.promote_ops'] = int(
                match_promote.group(1))

        return metrics

    def _get_client_io(self, client_str):
        """Parse a client string and returns a dictionary with metrics
        in the format {'metric1': value1, ...}
        """
        metrics = {}

        match_read = re.search(_CLIENT_IO_READ_REGEX, client_str)
        if match_read:
            rate = int(match_read.group(1))
            unit = match_read.group(2).lower()
            if unit == 'gb':
                rate = rate * 1e9
            elif unit == 'mb':
                rate = rate * 1e6
            elif unit == 'kb':
                rate = rate * 1e3
            metrics['ceph.cluster.client.read_bytes_per_sec'] = rate

        match_write = re.search(_CLIENT_IO_WRITE_REGEX, client_str)
        if match_write:
            rate = int(match_write.group(1))
            unit = match_write.group(2).lower()
            if unit == 'gb':
                rate = rate * 1e9
            elif unit == 'mb':
                rate = rate * 1e6
            elif unit == 'kb':
                rate = rate * 1e3
            metrics['ceph.cluster.client.write_bytes_per_sec'] = rate

        match_read_ops = re.search(_CLIENT_IO_READ_OPS_REGEX, client_str)
        if match_read_ops:
            metrics['ceph.cluster.client.read_ops'] = int(
                match_read_ops.group(1))

        match_write_ops = re.search(_CLIENT_IO_WRITE_OPS_REGEX, client_str)
        if match_write_ops:
            metrics['ceph.cluster.client.write_ops'] = int(
                match_write_ops.group(1))
        return metrics

    def _get_recovery_io(self, recovery_str):
        """Parse a recovery string and returns a dictionary with metrics
        in the format {'metric1': value1, ...}
        """
        metrics = {}

        match_rate = re.search(_RECOVERY_IO_RATE_REGEX, recovery_str)
        if match_rate:
            rate = int(match_rate.group(1))
            unit = match_rate.group(2).lower()
            if unit == 'gb':
                rate = rate * 1e9
            elif unit == 'mb':
                rate = rate * 1e6
            elif unit == 'kb':
                rate = rate * 1e3
            metrics['ceph.cluster.recovery.bytes_per_sec'] = rate

        match_key = re.search(_RECOVERY_IO_KEY_REGEX, recovery_str)
        if match_key:
            metrics['ceph.cluster.recovery.keys_per_sec'] = int(
                match_key.group(1))

        match_object = re.search(_RECOVERY_IO_OBJECT_REGEX, recovery_str)
        if match_object:
            metrics['ceph.cluster.recovery.objects_per_sec'] = int(
                match_object.group(1))

        return metrics

    def _get_summary_metrics(self, summary_str):
        """Parse a summary string and returns a dictionary with metrics
        in the format {'metric1': value1, ...}
        """
        metrics = {}

        match_degraded = re.search(_DEGRADED_REGEX, summary_str)
        if match_degraded:
            metrics['ceph.cluster.pgs.degraded_count'] = int(
                match_degraded.group(1))
            return metrics

        match_stuck_degraded = re.search(_STUCK_DEGRADED_REGEX, summary_str)
        if match_stuck_degraded:
            metrics['ceph.cluster.pgs.stuck_degraded_count'] = int(
                match_stuck_degraded.group(1))
            return metrics

        match_unclean = re.search(_UNCLEAN_REGEX, summary_str)
        if match_unclean:
            metrics['ceph.cluster.pgs.unclean_count'] = int(
                match_unclean.group(1))
            return metrics

        match_stuck_unclean = re.search(_STUCK_UNCLEAN_REGEX, summary_str)
        if match_stuck_unclean:
            metrics['ceph.cluster.pgs.stuck_unclean_count'] = int(
                match_stuck_unclean.group(1))
            return metrics

        match_undersized = re.search(_UNDERSIZED_REGEX, summary_str)
        if match_undersized:
            metrics['ceph.cluster.pgs.undersized_count'] = int(
                match_undersized.group(1))
            return metrics

        match_stuck_undersized = re.search(_STUCK_UNDERSIZED_REGEX,
                                           summary_str)
        if match_stuck_undersized:
            metrics['ceph.cluster.pgs.stuck_undersized_count'] = int(
                match_stuck_undersized.group(1))
            return metrics

        match_stale = re.search(_STALE_REGEX, summary_str)
        if match_stale:
            metrics['ceph.cluster.pgs.stale_count'] = int(match_stale.group(1))
            return metrics

        match_stuck_stale = re.search(_STUCK_STALE_REGEX, summary_str)
        if match_stuck_stale:
            metrics['ceph.cluster.pgs.stuck_stale_count'] = int(
                match_stuck_stale.group(1))
            return metrics

        match_slow_request = re.search(_SLOW_REQUEST_REGEX, summary_str)
        if match_slow_request:
            metrics['ceph.cluster.slow_requests_count'] = int(
                match_slow_request.group(1))
            return metrics

        match_degraded_objects = re.search(_DEGRADED_OBJECTS_REGEX,
                                           summary_str)
        if match_degraded_objects:
            metrics['ceph.cluster.objects.degraded_count'] = int(
                match_degraded_objects.group(1))
            return metrics

        match_misplaced_objects = re.search(
            _MISPLACED_OBJECTS_REGEX, summary_str)
        if match_misplaced_objects:
            metrics['ceph.cluster.objects.misplaced_count'] = int(
                match_misplaced_objects.group(1))
            return metrics

        return metrics

    def _get_usage_metrics(self, ceph_df):
        """Parse the 'ceph df' dictionary and returns a dictionary with metrics
        regarding the usage of the cluster in the format
        {'metric1': value1, ...}
        """
        metrics = {}
        stats = ceph_df['stats']
        metrics['ceph.cluster.total_bytes'] = stats['total_bytes']
        metrics['ceph.cluster.total_used_bytes'] = stats['total_used_bytes']
        metrics['ceph.cluster.total_avail_bytes'] = stats['total_avail_bytes']
        metrics['ceph.cluster.objects.total_count'] = stats['total_objects']
        metrics['ceph.cluster.utilization_perc'] = 1 - (float(metrics[
            'ceph.cluster.total_avail_bytes']) / metrics[
                'ceph.cluster.total_bytes'])
        return metrics

    def _get_stats_metrics(self, ceph_status, ceph_status_plain):
        """Parse the ceph_status dictionary and returns a dictionary with
        metrics regarding the status of the cluster in the format
        {'metric1': value1, ...}
        """
        metrics = {}
        ceph_status_health = ceph_status['health']
        metrics['ceph.cluster.health_status'] = self._parse_ceph_status(
            ceph_status_health['overall_status'])

        for s in ceph_status_health['summary']:
            metrics.update(self._get_summary_metrics(s['summary']))

        osds = ceph_status['osdmap']['osdmap']
        metrics['ceph.cluster.osds.total_count'] = osds['num_osds']
        metrics['ceph.cluster.osds.up_count'] = osds['num_up_osds']
        metrics['ceph.cluster.osds.in_count'] = osds['num_in_osds']
        metrics['ceph.cluster.pgs.remapped_count'] = osds['num_remapped_pgs']

        metrics['ceph.cluster.osds.down_count'] = metrics[
            'ceph.cluster.osds.total_count'] - metrics[
                'ceph.cluster.osds.up_count']
        metrics['ceph.cluster.osds.out_count'] = metrics[
            'ceph.cluster.osds.total_count'] - metrics[
                'ceph.cluster.osds.in_count']

        metrics.update({'ceph.cluster.pgs.scrubbing_count': 0,
                        'ceph.cluster.pgs.deep_scrubbing_count': 0})
        for state in ceph_status['pgmap']['pgs_by_state']:
            metrics['ceph.cluster.pgs.' +
                    state['state_name'].encode('ascii', 'ignore')] = state[
                        'count']
            if 'scrubbing' in state['state_name']:
                if 'deep' in state['state_name']:
                    metrics['ceph.cluster.pgs.deep_scrubbing_count'] += state[
                        'count']
                else:
                    metrics['ceph.cluster.pgs.scrubbing_count'] += state[
                        'count']
        metrics['ceph.cluster.pgs.total_count'] = ceph_status['pgmap'][
            'num_pgs']
        metrics['ceph.cluster.pgs.avg_per_osd'] = metrics[
            'ceph.cluster.pgs.total_count'] / metrics[
                'ceph.cluster.osds.total_count']

        ceph_status_plain = ceph_status_plain.split('\n')
        for l in ceph_status_plain:
            line = l.strip(' ')
            if line.startswith('recovery io'):
                metrics.update(self._get_recovery_io(line))
            elif line.startswith('client io'):
                metrics.update(self._get_client_io(line))
            elif line.startswith('cache io'):
                metrics.update(self._get_cache_io(line))

        metrics['ceph.cluster.quorum_size'] = len(ceph_status['quorum'])
        return metrics

    def _get_mon_metrics(self, ceph_status):
        """Parse the ceph_status dictionary and returns a dictionary
        with metrics regarding each monitor found, in the format
        {'monitor1': {metric1': value1, ...}, 'monitor2': {metric1': value1}}
        """
        mon_metrics = {}
        for health_service in ceph_status['health']['health'][
                'health_services']:
            for mon in health_service['mons']:
                store_stats = mon['store_stats']
                mon_metrics[mon['name'].encode('ascii', 'ignore')] = {
                    'ceph.monitor.total_bytes': mon['kb_total'] * 1e3,
                    'ceph.monitor.used_bytes': mon['kb_used'] * 1e3,
                    'ceph.monitor.avail_bytes': mon['kb_avail'] * 1e3,
                    'ceph.monitor.avail_perc': mon['avail_percent'],
                    'ceph.monitor.store.total_bytes': store_stats[
                        'bytes_total'],
                    'ceph.monitor.store.sst_bytes': store_stats['bytes_sst'],
                    'ceph.monitor.store.log_bytes': store_stats['bytes_log'],
                    'ceph.monitor.store.misc_bytes': store_stats['bytes_misc']
                }
        # monitor timechecks are available only when there are at least 2
        # monitors configured on the cluster
        if len(mon_metrics) > 1:
            for mon in ceph_status['health']['timechecks']['mons']:
                mon_metrics[mon['name'].encode('ascii', 'ignore')].update({
                    'ceph.monitor.skew': mon['skew'],
                    'ceph.monitor.latency': mon['latency']
                })
        return mon_metrics

    def _get_osd_metrics(self, ceph_osd_df, ceph_osd_perf, ceph_osd_dump):
        """Parse the ceph_osd_df/ceph_osd_perf/ceph_osd_dump dictionaries
        and returns a dictionary with metrics regarding each osd found, in the
        format {'osd.0': {metric1': value1, ...}, 'osd.1': {metric1': value1}}
        """
        osd_metrics = {}
        for node in ceph_osd_df['nodes']:
            osd_metrics[node['name'].encode('ascii', 'ignore')] = {
                'ceph.osd.crush_weight': node['crush_weight'],
                'ceph.osd.depth': node['depth'],
                'ceph.osd.reweight': node['reweight'],
                'ceph.osd.total_bytes': node['kb'] * 1e3,
                'ceph.osd.used_bytes': node['kb_used'] * 1e3,
                'ceph.osd.avail_bytes': node['kb_avail'] * 1e3,
                'ceph.osd.utilization_perc': node['utilization'],
                'ceph.osd.variance': node['var'],
                'ceph.osd.pgs_count': node['pgs']
            }

        for perf_info in ceph_osd_perf['osd_perf_infos']:
            osd_metrics['osd.' + str(perf_info['id'])].update({
                'ceph.osd.perf.commit_latency_seconds': perf_info[
                    'perf_stats']['commit_latency_ms'] / 1e3,
                'ceph.osd.perf.apply_latency_seconds': perf_info['perf_stats'][
                    'apply_latency_ms'] / 1e3
            })

        for dump_info in ceph_osd_dump['osds']:
            osd_metrics['osd.' + str(dump_info['osd'])].update({
                'ceph.osd.up': dump_info['up'],
                'ceph.osd.in': dump_info['in']
            })
        return osd_metrics

    def _get_osd_summary_metrics(self, ceph_osd_df):
        """Parse the ceph_osd_df dictionary and returns a dictionary
        with metrics regarding the osds in the cluster, in the format
        {metric1': value1, ...}
        """
        metrics = {}
        osd_summary = ceph_osd_df['summary']
        metrics['ceph.osds.total_bytes'] = osd_summary['total_kb'] * 1e3
        metrics['ceph.osds.total_used_bytes'] = osd_summary[
            'total_kb_used'] * 1e3
        metrics['ceph.osds.total_avail_bytes'] = osd_summary[
            'total_kb_avail'] * 1e3
        metrics['ceph.osds.avg_utilization_perc'] = osd_summary[
            'average_utilization']
        return metrics

    def _get_pool_metrics(self, ceph_df):
        """Parse the ceph_df dictionary and returns a dictionary
        with metrics regarding each pool found, in the format
        {'pool1': {metric1': value1, ...}, 'pool2': {metric1': value1}}.
        """
        pool_metrics = {}
        for pool in ceph_df['pools']:
            stats = pool['stats']
            total_bytes = stats['bytes_used'] + stats['max_avail']
            utilization_perc = float(stats['bytes_used']) / total_bytes
            pool_metrics[pool['name'].encode('ascii', 'ignore')] = {
                'ceph.pool.used_bytes': stats['bytes_used'],
                'ceph.pool.used_raw_bytes': stats['raw_bytes_used'],
                'ceph.pool.max_avail_bytes': stats['max_avail'],
                'ceph.pool.objects_count': stats['objects'],
                'ceph.pool.dirty_objects_count': stats['dirty'],
                'ceph.pool.read_io': stats['rd'],
                'ceph.pool.read_bytes': stats['rd_bytes'],
                'ceph.pool.write_io': stats['wr'],
                'ceph.pool.write_bytes': stats['wr_bytes'],
                'ceph.pool.quota_max_bytes': stats['quota_bytes'],
                'ceph.pool.quota_max_objects': stats['quota_objects'],
                'ceph.pool.total_bytes': total_bytes,
                'ceph.pool.utilization_perc': utilization_perc
            }
        return pool_metrics

    def _get_pool_stats_metrics(self, ceph_osd_pool_stats):
        """Parse the ceph_osd_pool_stats dictionary and returns a dictionary
        with metrics regarding each pool found, in the format
        {'pool1': {metric1': value1, ...}, 'pool2': {metric1': value1}}.
        """
        pool_metrics = {}
        for pool in ceph_osd_pool_stats:
            pool_name = pool['pool_name']
            for metric, value in pool['client_io_rate'].iteritems():
                if pool_name in pool_metrics:
                    pool_metrics[pool_name].update({
                        'ceph.pool.client.' + metric: value})
                else:
                    pool_metrics[pool_name] = {
                        'ceph.pool.client.' + metric: value}
            for metric, value in pool['recovery_rate'].iteritems():
                if pool_name in pool_metrics:
                    pool_metrics[pool_name].update({
                        'ceph.pool.recovery.' + metric: value})
                else:
                    pool_metrics[pool_name] = {
                        'ceph.pool.recovery.' + metric: value}
        return pool_metrics
