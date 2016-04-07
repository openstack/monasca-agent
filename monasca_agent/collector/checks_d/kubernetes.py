"""kubernetes check
Collects metrics from cAdvisor instance
"""
# stdlib
from datetime import datetime
import calendar
import re
import traceback
import monasca_agent.collector.checks.utils as utils

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


KUBERNETES_PREFIX = "kubernetes"
DEFAULT_MAX_DEPTH = 10
DEFAULT_PUBLISH_ALIASES = False
DEFAULT_MAPPING = {
      'dimensions': {
          'index': 'index',
          'k8s_namespace': {
              'source_key': 'io.kubernetes.pod.name',
              'regex': '(.*)/.*'
          },
          'k8s_pod': {
              'source_key': 'io.kubernetes.pod.name',
              'regex': '.*/(.*)'
          },
          'k8s_container': 'io.kubernetes.container.name',
          'k8s_subcontainer_id': 'io.kubernetes.subcontainer.name'
      },
      'groups': {
          'diskio': {
              'rates': [ '(io_service_bytes)_stats_total' ]
          },
          'cpu': {
              'rates': [ '(.*)_total' ]
          },
          'filesystem': {
              'gauges': [ 'usage' ]
          },
          'memory': {
              'gauges': [ 'usage' ]
          },
          'network': {
              'rates': [ '.._bytes', '.._errors', '.._dropped' ]
          },
          'task_stats': {
              'gauges': [ 'nr_.*' ]
          },
          'machine': {
              'k8s_machine_id': 'machine_id',
              'k8s_boot_id': 'boot_id',
              'mac_address': 'mac_address',
              'device': 'device',
              'name': 'name',
              'type': 'type',
              'gauges': [ 'size', 'capacity', 'memory' ]
          }
          # dimensions should be inherited from above
      }
}


class Kubernetes(services_checks.ServicesCheck):
    """ Collect metrics and events from kubelet """

    pod_names_by_container = {}

    def __init__(self, name, init_config, agent_config, instances=None):
        if instances is not None and len(instances) > 1:
            raise Exception('Kubernetes check only supports one configured instance.')
        super(Kubernetes, self).__init__(name, init_config, agent_config, instances)
        self._kube_settings = set_kube_settings(instances[0])
        self._publisher = utils.DynamicCheckHelper(self, 'kubernetes', DEFAULT_MAPPING)

    def _check(self, instance):
        kube_settings = get_kube_settings()

        if not kube_settings.get("host"):
            raise Exception('Unknown Kubernetes node (host attribute missing)')

        # kubelet metrics
        self._update_metrics(instance, kube_settings)

    @staticmethod
    def _convert_timestamp(timestamp):
        # convert from string '2016-03-16T16:48:59.900524303Z' to a float monasca can handle 164859.900524
        # conversion using strptime() works only for 6 digits in microseconds so the timestamp is limited to 26 characters
        ts = datetime.strptime(timestamp[:25] + timestamp[-1], "%Y-%m-%dT%H:%M:%S.%fZ")
        return calendar.timegm(datetime.timetuple(ts))

    def _update_container_metrics(self, instance, subcontainer, kube_labels):
        dims = instance.get('dimensions', {})  # add support for custom dims
        dims['hostname'] = get_kube_settings()['host']
        klabels = { 'io.kubernetes.subcontainer.name': subcontainer['name'] }
        for i, alias in enumerate(subcontainer.get('aliases', [])):
            klabels['alias#'+str(i)] = alias
        kspec = subcontainer['spec']
        klabels.update(kspec.get('labels', {}))

        kstats = subcontainer['stats'][-1]  # take the latest
        ktime = self._convert_timestamp(kstats.get('timestamp'))

        # filesystem metrics are computed
        if kspec.get("has_filesystem"):
           fs = kstats['filesystem'][-1]
           fs_utilization = float(fs['usage']) / float(fs['capacity'])
           self._publisher.push_metric(instance, 'usage_perc', fs_utilization, klabels, group='filesystem', timestamp=ktime, fixed_dimensions=dims)

        # other metrics are just mapped
        self._publisher.push_metric_dict(instance, kstats.get('network', {}), klabels, group='network', timestamp=ktime, fixed_dimensions=dims)
        self._publisher.push_metric_dict(instance, kstats.get('cpu', {}), klabels, group='cpu', timestamp=ktime, fixed_dimensions=dims, max_depth=1)
        self._publisher.push_metric_dict(instance, kstats.get('memory', {}), klabels, group='memory', timestamp=ktime, fixed_dimensions=dims, max_depth=0)
        self._publisher.push_metric_dict(instance, kstats.get('task_stats', {}), klabels, group='task_stats', timestamp=ktime, fixed_dimensions=dims, max_depth=1)
        self._publisher.push_metric_dict(instance, kstats.get('diskio', {}), klabels, group='diskio', timestamp=ktime, fixed_dimensions=dims, max_depth=4)        # deeply nested

    @staticmethod
    def _retrieve_metrics(url):
        return retrieve_json(url)

    @property
    def _retrieve_kube_labels(self):
        return get_kube_labels()

    def _update_metrics(self, instance, kube_settings):
        kube_labels = self._retrieve_kube_labels

        subcontainers = self._retrieve_metrics(get_kube_settings()["subcontainers_url"])
        if not subcontainers:
            raise Exception('No metrics retrieved from URL %s' % get_kube_settings()["subcontainers_url"])

        for subcontainer in subcontainers:
            try:
                self._update_container_metrics(instance, subcontainer, kube_labels)
            except Exception as e:
                self.log.exception("Unable to collect metrics for container: %s - %s", subcontainer.get('name'), repr(e))

        machine = self._retrieve_metrics(get_kube_settings()["machine_url"])
        if not machine:
            raise Exception('No metrics retrieved from URL %s' % kube_settings["metrics_url"])

        try:
            dims = instance.get('dimensions', {})  # add support for custom dims
            dims['hostname'] = get_kube_settings()['host']
            klabels = {
                'machine_id': machine['machine_id'],
                'boot_id': machine['boot_id']
            }
            self._publisher.push_metric_dict(instance, machine, klabels, group='machine', fixed_dimensions=dims, max_depth=3)
        except Exception as e:
            self.log.exception("Unable to collect metrics for container: %s - %s", subcontainer.get('name'), repr(e))
