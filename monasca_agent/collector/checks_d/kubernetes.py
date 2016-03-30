"""kubernetes check
Collects metrics from cAdvisor instance
"""
# stdlib
import numbers
from fnmatch import fnmatch
import re
import traceback
import time
import os

# 3rd party
import requests

# project
import monasca_agent.collector.checks.services_checks as services_checks
from monasca_agent.collector.checks.kubeutil import set_kube_settings, get_kube_settings, get_kube_labels


def retrieve_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def _is_affirmative(s):
    # int or real bool
    if isinstance(s, int):
        return bool(s)
    # try string cast
    return s.lower() in ('yes', 'true', '1')


NAMESPACE = "kubernetes"
DEFAULT_MAX_DEPTH = 10
DEFAULT_PUBLISH_ALIASES = False
DEFAULT_ENABLED_RATES = [
    'diskio.io_service_bytes.stats.total',
    'network.??_bytes',
    'cpu.*.total']

NET_ERRORS = ['rx_errors', 'tx_errors', 'rx_dropped', 'tx_dropped']

DEFAULT_ENABLED_GAUGES = [
    'memory.usage',
    'filesystem.usage']


class Kubernetes(services_checks.ServicesCheck):
    """ Collect metrics and events from kubelet """

    pod_names_by_container = {}

    def __init__(self, name, init_config, agent_config, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes check only supports one configured instance.')
        super(Kubernetes, self).__init__(name, init_config, agent_config, instances)
        self.kube_settings = set_kube_settings(instances[0])
        self.max_depth = instances[0].get('max_depth', DEFAULT_MAX_DEPTH)

    def _check(self, instance):
        kube_settings = get_kube_settings()
        # self.log.info("kube_settings: %s" % kube_settings)
        if not kube_settings.get("host"):
            raise Exception('Unable to get default router and host parameter is not set')

        self.publish_aliases = _is_affirmative(instance.get('publish_aliases', DEFAULT_PUBLISH_ALIASES))
        enabled_gauges = instance.get('enabled_gauges', DEFAULT_ENABLED_GAUGES)
        self.enabled_gauges = ["{0}.{1}".format(NAMESPACE, x) for x in enabled_gauges]
        enabled_rates = instance.get('enabled_rates', DEFAULT_ENABLED_RATES)
        self.enabled_rates = ["{0}.{1}".format(NAMESPACE, x) for x in enabled_rates]
        self.publish_aliases = _is_affirmative(instance.get('publish_aliases', DEFAULT_PUBLISH_ALIASES))

        # kubelet metrics
        self._update_metrics(instance, kube_settings)

    def _publish_raw_metrics(self, metric, dat, dims, depth=0):
        if depth >= self.max_depth:
            self.log.warning('Reached max depth on metric=%s' % metric)
            return

        if isinstance(dat, numbers.Number):
            if self.enabled_rates and any([fnmatch(metric, pat) for pat in self.enabled_rates]):
                # self.log.info("rate: numbers float: {0}, {1}, {2}".format(metric, dat, dims))
                self.rate(metric, float(dat), dimensions=dims)
            elif self.enabled_gauges and any([fnmatch(metric, pat) for pat in self.enabled_gauges]):
                # self.log.info("gauge: numbers gauge: {0}, {1}, {2}".format(metric, dat, dims))
                self.gauge(metric, float(dat), dimensions=dims)

        if isinstance(dat, dict):
            for k, v in dat.iteritems():
                # self.log.info("_publish_raw_metrics dat dict: {0}, {1}, {2}".format(metric, (k.lower(), v), dims))
                self._publish_raw_metrics(metric + '.%s' % k.lower(), v, dims)

        elif isinstance(dat, list):
            # self.log.info("_publish_raw_metrics dat list: {0}, {1}, {2}".format(metric, dat[-1], dims))
            self._publish_raw_metrics(metric, dat[-1], dims)

    @staticmethod
    def _shorten_name(name):
        # shorten docker image id
        return re.sub('([0-9a-fA-F]{64,})', lambda x: x.group(1)[0:12], name)

    @staticmethod
    def _normalize_name(name):
        # remove invalid characters
        return re.sub(r'[\\x2, \\x7]', '', name)

    @staticmethod
    def _convert_timestamp(timestamp):
        # convert from string '2016-03-16T16:48:59.900524303Z' to a float monasca can handle 164859.900524
        # conversion using strptime() works only for 6 digits in microseconds so the timestamp is limited to 26 characters
        ts = time.strptime(timestamp[:25] + timestamp[-1], "%Y-%m-%dT%H:%M:%S.%fZ")
        os.environ['TZ'] = 'UTC'
        time.tzset()
        return time.mktime(ts)

    def _update_container_metrics(self, instance, subcontainer, kube_labels):
        dims = instance.get('dimensions', {})  # add support for custom dims
        if len(subcontainer.get('aliases', [])) >= 1:
            # The first alias seems to always match the docker container name
            container_name = subcontainer['aliases'][0]
        else:
            # We default to the container id
            container_name = subcontainer['name']

        dims['container_name'] = self._normalize_name(container_name)

        pod_name_set = False
        try:
            for label_name, label in subcontainer['spec']['labels'].items():
                label_name = label_name.replace('io.kubernetes.pod.name', 'pod_name')
                if label_name == "pod_name":
                    pod_name_set = True
                    pod_labels = kube_labels.get(label)

                    if pod_labels:
                        if isinstance(pod_labels, dict):
                            pod_labels.update(dims)
                        elif isinstance(pod_labels, list):
                            pod_labels[0] = dims['container_name']
                        if "-" in label:
                            replication_controller = "-".join(
                                label.split("-")[:-1])
                        if "/" in replication_controller:
                            namespace, replication_controller = replication_controller.split("/", 1)
                            dims["kube_namespace"] = self._normalize_name(namespace)
                            dims["kube_replication_controller"] = self._normalize_name(
                                replication_controller)  ## image name? io.kubernetes.pod.name monasca/monasca-elasticsearch-data2-thjsx
                            # dims[label_name] = self._normalize_name(label)
        except KeyError:
            pass

        if not pod_name_set and len(subcontainer.get('label_name', [])) >= 1:
            dims['pod_name'] = self._normalize_name(label_name)

        if self.publish_aliases and subcontainer.get("aliases"):
            for alias in subcontainer['aliases'][1:]:
                # we don't add the first alias as it will be the container_name
                dims['container_alias'] = self._normalize_name(self._shorten_name(alias))

        stats = subcontainer['stats'][-1]  # take the latest
        self._publish_raw_metrics(NAMESPACE, stats, dims)

        time = self._convert_timestamp(stats.get('timestamp'))

        subcontainer_spec = subcontainer.get("spec", {})

        if len(subcontainer.get('aliases', [])) >= 1:
            if subcontainer_spec.get("has_filesystem"):
                fs = stats['filesystem'][-1]
                fs_utilization = float(fs['usage']) / float(fs['capacity'])
                self.log.info(
                    "filesystem for subcontainer get: {0}, {1}.filesystem.usage_pct, {2}".format(NAMESPACE,
                                                                                                 fs_utilization,
                                                                                                 dims))
                self.gauge(NAMESPACE + '.filesystem.usage_pct', fs_utilization, dims, timestamp=time)

            if subcontainer_spec.get("has_network"):
                net = stats['network']
                self.log.info("network for subcontainer get: {0}, {1}".format(net, dims))
                self.rate(NAMESPACE + '.network_errors', sum(float(net[x]) for x in NET_ERRORS), dims)

            if subcontainer_spec.get("has_cpu"):
                cpu = stats['cpu']
                self.log.info("cpu for subcontainer get: {0}, {1}".format(cpu, dims))
                self.rate(NAMESPACE + '.cpu.usage.total', float(cpu['usage']['total']), dims)
                self.rate(NAMESPACE + '.cpu.usage.user', float(cpu['usage']['user']), dims)
                self.rate(NAMESPACE + '.cpu.usage.system', float(cpu['usage']['system']), dims)

            if subcontainer_spec.get("has_memory"):
                mem = stats['memory']
                self.log.info("memory for subcontainer get: {0}, {1}".format(mem, dims))
                self.gauge(NAMESPACE + '.memory.usage', float(mem['usage']), dims, timestamp=time)

            if subcontainer_spec.get("has_diskio"):
                diskio = stats.get('diskio')
                if diskio:
                    io_service_bytes = diskio.get('io_service_bytes')[-1]
                    if io_service_bytes:
                        io_service_bytes_stats = io_service_bytes.get('stats')
                        if io_service_bytes_stats:
                            io_service_bytes_stats_total = io_service_bytes_stats.get('Total')
                            self.log.info("diskio.io_service_bytes.stats.total for subcontainer get: {0}, {1}".format(
                                io_service_bytes_stats_total, dims))
                            self.rate(NAMESPACE + '.diskio.io_service_bytes.stats.total',
                                      float(io_service_bytes_stats_total), dims)

    @staticmethod
    def _retrieve_metrics(url):
        return retrieve_json(url)

    @property
    def _retrieve_kube_labels(self):
        return get_kube_labels()

    def _update_metrics(self, instance, kube_settings):
        metrics = self._retrieve_metrics(kube_settings["metrics_url"])
        kube_labels = self._retrieve_kube_labels
        if not metrics:
            raise Exception('No metrics retrieved cmd=%s' % self.metrics_cmd)

        for subcontainer in metrics:
            try:
                self._update_container_metrics(instance, subcontainer, kube_labels)
            except Exception, e:
                self.log.error("Unable to collect metrics for container: {0} ({1}".format(
                    subcontainer.get('name'), e))
            traceback.print_exc()
