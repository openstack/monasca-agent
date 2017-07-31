# (C) Copyright 2015,2017 Hewlett Packard Enterprise Development LP
# (C) Copyright 2017 KylinCloud

import base64
import json
import logging
import math
from numbers import Number
import os
import re
import requests

from monasca_agent.common import exceptions
from monasca_agent.common import keystone

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20


def add_basic_auth(request, username, password):
    """A helper to add basic authentication to a urllib2 request.

    We do this across a variety of checks so it's good to have this in one place.
    """
    auth_str = base64.encodestring('%s:%s' % (username, password)).strip()
    request.add_header('Authorization', 'Basic %s' % auth_str)
    return request


def get_tenant_name(tenants, tenant_id):
    tenant_name = None
    for tenant in tenants:
        if tenant.id == tenant_id:
            tenant_name = tenant.name
            break
    return tenant_name


def get_tenant_list(config, log):
    tenants = []
    try:
        log.debug("Retrieving Keystone tenant list")
        client = keystone.get_client(**config)
        if 'v2' in client.__module__:
            tenants = client.tenants.list()
        else:
            tenants = client.projects.list()
    except Exception as e:
        msg = "Unable to get tenant list from keystone: {0}"
        log.error(msg.format(e))

    return tenants


def convert_memory_string_to_bytes(memory_string):
    """Conversion from memory represented in string format to bytes"""
    if "m" in memory_string:
        memory = float(memory_string.split('m')[0])
        return memory / 1000
    elif "K" in memory_string:
        memory = float(memory_string.split('K')[0])
        return _compute_memory_bytes(memory_string, memory, 1)
    elif "M" in memory_string:
        memory = float(memory_string.split('M')[0])
        return _compute_memory_bytes(memory_string, memory, 2)
    elif "G" in memory_string:
        memory = float(memory_string.split('G')[0])
        return _compute_memory_bytes(memory_string, memory, 3)
    elif "T" in memory_string:
        memory = float(memory_string.split('T')[0])
        return _compute_memory_bytes(memory_string, memory, 4)
    else:
        return float(memory_string)


def _compute_memory_bytes(memory_string, memory, power):
    if "i" in memory_string:
        return memory * math.pow(1024, power)
    return memory * math.pow(1000, power)


class KubernetesConnector(object):
    """Class for connecting to Kubernetes API from within a container running
    in a Kubernetes environment
    """
    CACERT_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    TOKEN_PATH = '/var/run/secrets/kubernetes.io/serviceaccount/token'

    def __init__(self, connection_timeout):
        self.api_url = None
        self.api_verify = None
        self.api_request_header = None
        if connection_timeout is None:
            self.connection_timeout = DEFAULT_TIMEOUT
        else:
            self.connection_timeout = connection_timeout
        self._set_kubernetes_api_connection_info()
        self._set_kubernetes_service_account_info()

    def _set_kubernetes_api_connection_info(self):
        """Set kubernetes API string from default container environment
        variables
        """
        api_host = os.environ.get('KUBERNETES_SERVICE_HOST', "kubernetes.default")
        api_port = os.environ.get('KUBERNETES_SERVICE_PORT', "443")
        self.api_url = "https://{}:{}".format(api_host, api_port)

    def _set_kubernetes_service_account_info(self):
        """Set cert and token info to included on requests to the API"""
        try:
            with open(self.TOKEN_PATH) as token_file:
                token = token_file.read()
        except Exception as e:
            log.error("Unable to read token - {}. Defaulting to using no token".format(e))
            token = None
        self.api_request_header = {'Authorization': 'Bearer {}'.format(token)} if token else None
        self.api_verify = self.CACERT_PATH if os.path.exists(self.CACERT_PATH) else False

    def get_agent_pod_host(self, return_host_name=False):
        """Obtain host the agent is running on in Kubernetes.
        Used when trying to connect to services running on the node (Kubelet, cAdvisor)
        """
        # Get pod name and namespace from environment variables
        pod_name = os.environ.get("AGENT_POD_NAME")
        pod_namespace = os.environ.get("AGENT_POD_NAMESPACE")
        if not pod_name:
            raise exceptions.MissingEnvironmentVariables(
                "pod_name is not set as environment variables cannot derive"
                " host from Kubernetes API")
        if not pod_namespace:
            raise exceptions.MissingEnvironmentVariables(
                "pod_namespace is not set as environment variables cannot "
                "derive host from Kubernetes API")
        pod_url = "/api/v1/namespaces/{}/pods/{}".format(pod_namespace, pod_name)
        try:
            agent_pod = self.get_request(pod_url)
        except Exception as e:
            exception_message = "Could not get agent pod from Kubernetes API" \
                                " to get host IP with error - {}".format(e)
            log.exception(exception_message)
            raise exceptions.KubernetesAPIConnectionError(exception_message)
        if not return_host_name:
            return agent_pod['status']['hostIP']
        else:
            return agent_pod['spec']['nodeName']

    def get_request(self, request_endpoint, as_json=True, retried=False):
        """Sends request to Kubernetes API with given endpoint.
        Will retry the request once, with updated token/cert, if unauthorized.
        """
        request_url = "{}/{}".format(self.api_url, request_endpoint)
        result = requests.get(request_url,
                              timeout=self.connection_timeout,
                              headers=self.api_request_header,
                              verify=self.api_verify)
        if result.status_code >= 300:
            if result.status_code == 401 and not retried:
                log.info("Could not authenticate with Kubernetes API at the"
                         " first time. Rereading in cert and token.")
                self._set_kubernetes_service_account_info()
                return self.get_request(request_endpoint, as_json=as_json,
                                        retried=True)
            exception_message = "Could not obtain data from {} with the " \
                                "given status code {} and return text {}".\
                format(request_url, result.status_code, result.text)
            raise exceptions.KubernetesAPIConnectionError(exception_message)
        return result.json() if as_json else result


class DynamicCheckHelper(object):
    """Supplements existing check class with reusable functionality to transform third-party metrics into Monasca ones
    in a configurable way
    """

    COUNTERS_KEY = 'counters'
    RATES_KEY = 'rates'
    GAUGES_KEY = 'gauges'
    CONFIG_SECTIONS = [GAUGES_KEY, RATES_KEY, COUNTERS_KEY]

    GAUGE = 0
    RATE = 1
    COUNTER = 2
    SKIP = 3
    METRIC_TYPES = [GAUGE, RATE, COUNTER]

    DEFAULT_GROUP = ""

    class MetricSpec(object):
        """Describes how to filter and map input metrics to Monasca metrics
        """

        def __init__(self, metric_type, metric_name):
            """Construct a metric-specification
            :param metric_type: one of GAUGE, RATE, COUNTER, SKIP
            :param metric_name: normalized name of the metric as reported to Monasca
            """
            self.metric_type = metric_type
            self.metric_name = metric_name

    @staticmethod
    def _normalize_dim_value(value):
        """Normalize an input value

        * Replace \\x?? values with _
        * Replace illegal characters
          - according to ANTLR grammar: ( '}' | '{' | '&' | '|' | '>' | '<' | '=' | ',' | ')' | '(' | ' ' | '"' )
          - according to Python API validation: "<>={}(),\"\\\\|;&"
        * Truncate to 255 chars
        :param value: input value
        :return: valid dimension value
        """

        return re.sub(r'[|\\;,&=\']', '-', re.sub(r'[(}>]', ']', re.sub(r'[({<]', '[', value.replace(r'\x2d', '-').
                                                                        replace(r'\x7e', '~'))))[:255]

    class DimMapping(object):
        """Describes how to transform dictionary like metadata attached to a metric into Monasca dimensions
        """

        def __init__(self, dimension, regex='(.*)', separator=None):
            """C'tor
            :param dimension to be mapped to
            :param regex: regular expression used to extract value from source value
            :param separator: used to concatenate match-groups
            """
            self.dimension = dimension
            self.regex = regex
            self.separator = separator
            self.cregex = re.compile(regex) if regex != '(.*)' else None

        def map_value(self, source_value):
            """Transform source value into target dimension value
            :param source_value: label value to transform
            :return: transformed dimension value or None if the regular expression did not match. An empty
            result (caused by the regex having no match-groups) indicates that the label is used for filtering
            but not mapped to a dimension.
            """
            if self.cregex:
                match_groups = self.cregex.match(source_value)
                if match_groups:
                    return DynamicCheckHelper._normalize_dim_value(self.separator.join(match_groups.groups()))
                else:
                    return None
            else:
                return DynamicCheckHelper._normalize_dim_value(source_value)

    @staticmethod
    def _build_dimension_map(config):
        """Builds dimension mappings for the given configuration element
        :param config: 'mappings' element of config
        :return: dictionary mapping source labels to applicable DimMapping objects
        """
        result = {}
        for dim, spec in config.get('dimensions', {}).items():
            if isinstance(spec, dict):
                label = spec.get('source_key', dim)
                sepa = spec.get('separator', '-')
                regex = spec.get('regex', '(.*)')
            else:
                label = spec
                regex = '(.*)'
                sepa = None

            # note: source keys can be mapped to multiple dimensions
            arr = result.get(label, [])
            mapping = DynamicCheckHelper.DimMapping(dimension=dim, regex=regex, separator=sepa)
            arr.append(mapping)
            result[label] = arr

        return result

    def __init__(self, check, prefix=None, default_mapping=None):
        """C'tor
        :param check: Target check instance
        """
        self._check = check
        self._prefix = prefix
        self._groups = {}
        self._metric_map = {}
        self._dimension_map = {}
        self._metric_cache = {}
        self._grp_metric_map = {}
        self._grp_dimension_map = {}
        self._grp_metric_cache = {}
        self._metric_to_group = {}
        for inst in self._check.instances:
            iname = inst['name']
            mappings = inst.get('mapping', default_mapping)
            if mappings:
                # build global name filter and rate/gauge assignment
                self._metric_map[iname] = mappings
                self._metric_cache[iname] = {}
                # build global dimension map
                self._dimension_map[iname] = DynamicCheckHelper._build_dimension_map(mappings)
                # check if groups are used
                groups = mappings.get('groups')
                self._metric_to_group[iname] = {}
                self._groups[iname] = []
                if groups:
                    self._groups[iname] = groups.keys()
                    self._grp_metric_map[iname] = {}
                    self._grp_metric_cache[iname] = {}
                    self._grp_dimension_map[iname] = {}
                    for grp, gspec in groups.items():
                        self._grp_metric_map[iname][grp] = gspec
                        self._grp_metric_cache[iname][grp] = {}
                        self._grp_dimension_map[iname][grp] = DynamicCheckHelper._build_dimension_map(gspec)
                    # add the global mappings as pseudo group, so that it is considered when searching for metrics
                    self._groups[iname].append(DynamicCheckHelper.DEFAULT_GROUP)
                    self._grp_metric_map[iname][DynamicCheckHelper.DEFAULT_GROUP] = self._metric_map[iname]
                    self._grp_metric_cache[iname][DynamicCheckHelper.DEFAULT_GROUP] = self._metric_cache[iname]
                    self._grp_dimension_map[iname][DynamicCheckHelper.DEFAULT_GROUP] = self._dimension_map[iname]

            else:
                raise exceptions.CheckException('instance %s is not supported: no element "mapping" found!', iname)

    def _get_group(self, instance, metric):
        """Search the group for a metric. Can be used only when metric names unambiguous across groups.

        :param metric: input metric
        :return: group name or None (if no group matches)
        """
        iname = instance['name']
        group = self._metric_to_group[iname].get(metric)
        if group is None:
            for g in self._groups[iname]:
                spec = self._fetch_metric_spec(instance, metric, g)
                if spec and spec.metric_type != DynamicCheckHelper.SKIP:
                    self._metric_to_group[iname][metric] = g
                    return g

        return group

    def _fetch_metric_spec(self, instance, metric, group=None):
        """Checks whether a metric is enabled by the instance configuration

        :param instance: instance containing the check configuration
        :param metric: metric as reported from metric data source (before mapping)
        :param group: optional metric group, will be used as dot-separated prefix
        """

        instance_name = instance['name']

        # filter and classify the metric

        if group is not None:
            metric_cache = self._grp_metric_cache[instance_name].get(group, {})
            metric_map = self._grp_metric_map[instance_name].get(group, {})
            return DynamicCheckHelper._lookup_metric(metric, metric_cache, metric_map)
        else:
            metric_cache = self._metric_cache[instance_name]
            metric_map = self._metric_map[instance_name]
            return DynamicCheckHelper._lookup_metric(metric, metric_cache, metric_map)

    def is_enabled_metric(self, instance, metric, group=None):
        return self._fetch_metric_spec(instance, metric, group).metric_type != DynamicCheckHelper.SKIP

    def push_metric_dict(self, instance, metric_dict, labels=None, group=None, timestamp=None, fixed_dimensions=None,
                         default_dimensions=None, max_depth=0, curr_depth=0, prefix='', index=-1):
        """This will extract metrics and dimensions from a dictionary.

        The following mappings are applied:

        Simple recursive composition of metric names:

            Input:

                {
                    'server': {
                        'requests': 12
                    }
                }

            Configuration:

                mapping:
                    counters:
                        - server_requests

            Output:

                server_requests=12

        Mapping of textual values to dimensions to distinguish array elements. Make sure that tests attributes
        are sufficient to distinguish the array elements. If not use the build-in 'index' dimension.

            Input:

            {
                'server': [
                    {
                        'role': 'master,
                        'node_name': 'server0',
                        'requests': 1500
                    },
                    {
                        'role': 'slave',
                        'node_name': 'server1',
                        'requests': 1000
                    },
                    {
                        'role': 'slave',
                        'node_name': 'server2',
                        'requests': 500
                    }
                }
            }

            Configuration:

                mapping:
                    dimensions:
                        server_role: role
                        node_name: node_name
                    rates:
                        - requests

            Output:

                server_requests{server_role=master, node_name=server0} = 1500.0
                server_requests{server_role=slave, node_name=server1} = 1000.0
                server_requests{server_role=slave, node_name=server2} = 500.0


        Distinguish array elements where no textual attribute are available or no mapping has been configured for them.
        In that case an 'index' dimension will be attached to the metric which has to be mapped properly.

            Input:

                {
                    'server': [
                        {
                            'requests': 1500
                        },
                        {
                            'requests': 1000
                        },
                        {
                            'requests': 500
                        }
                    }
                }

            Configuration:

                mapping:
                    dimensions:
                        server_no: index          # index is a predefined label
                    counters:
                        - server_requests

            Result:

                server_requests{server_no=0} = 1500.0
                server_requests{server_no=1} = 1000.0
                server_requests{server_no=2} = 500.0


        :param instance: Instance to submit to
        :param metric_dict: input data as dictionary
        :param labels: labels to be mapped to dimensions
        :param group: group to use for mapping labels and prefixing
        :param timestamp: timestamp to report for the measurement
        :param fixed_dimensions: dimensions which are always added with fixed values
        :param default_dimensions: dimensions to be added, can be overwritten by actual data in metric_dict
        :param max_depth: max. depth to recurse
        :param curr_depth: depth of recursion
        :param prefix: prefix to prepend to any metric
        :param index: current index when traversing through a list
        """

        # when traversing through an array, each element must be distinguished with dimensions
        # therefore additional dimensions need to be calculated from the siblings of the actual number valued fields
        if default_dimensions is None:
            default_dimensions = {}
        if fixed_dimensions is None:
            fixed_dimensions = {}
        if labels is None:
            labels = {}
        if index != -1:
            ext_labels = self.extract_dist_labels(instance['name'], group, metric_dict, labels.copy(), index)
            if not ext_labels:
                log.debug(
                    "skipping array due to lack of mapped dimensions for group %s "
                    "(at least 'index' should be supported)",
                    group if group else '<root>')
                return

        else:
            ext_labels = labels.copy()

        for element, child in metric_dict.items():
            # if child is a dictionary, then recurse
            if isinstance(child, dict) and curr_depth < max_depth:
                self.push_metric_dict(instance, child, ext_labels, group, timestamp, fixed_dimensions,
                                      default_dimensions, max_depth, curr_depth + 1, prefix + element + '_')
            # if child is a number, assume that it is a metric (it will be filtered out by the rate/gauge names)
            elif isinstance(child, Number):
                self.push_metric(instance, prefix + element, float(child), ext_labels, group, timestamp,
                                 fixed_dimensions,
                                 default_dimensions)
            # if it is a list, then each array needs to be added. Additional dimensions must be found in order to
            # distinguish the measurements.
            elif isinstance(child, list):
                for i, child_element in enumerate(child):
                    if isinstance(child_element, dict):
                        if curr_depth < max_depth:
                            self.push_metric_dict(instance, child_element, ext_labels, group, timestamp,
                                                  fixed_dimensions, default_dimensions, max_depth, curr_depth + 1,
                                                  prefix + element + '_', index=i)
                    elif isinstance(child_element, Number):
                        if len(self._get_mappings(instance['name'], group, 'index')) > 0:
                            idx_labels = ext_labels.copy()
                            idx_labels['index'] = str(i)
                            self.push_metric(instance, prefix + element, float(child_element), idx_labels, group,
                                             timestamp, fixed_dimensions, default_dimensions)
                        else:
                            log.debug("skipping array due to lack of mapped 'index' dimensions for group %s",
                                      group if group else '<root>')
                    else:
                        log.debug('nested arrays are not supported for configurable extraction of element %s', element)

    def extract_dist_labels(self, instance_name, group, metric_dict, labels, index):
        """Extract additional distinguishing labels from metric dictionary. All top-level attributes which are
        strings and for which a dimension mapping is available will be transformed into dimensions.
        :param instance_name: instance to be used
        :param group: metric group or None for root/unspecified group
        :param metric_dict: input dictionary containing the metric at the top-level
        :param labels: labels dictionary to extend with the additional found metrics
        :param index: index value to be used as fallback if no labels can be derived from string-valued attributes
            or the derived labels are not mapped in the config.
        :return: Extended labels, already including the 'labels' passed into this method
        """
        ext_labels = None
        # collect additional dimensions first from non-metrics
        for element, child in metric_dict.items():
            if isinstance(child, str) and len(self._get_mappings(instance_name, group, element)) > 0:
                if not ext_labels:
                    ext_labels = labels.copy()
                ext_labels[element] = child
        # if no additional labels supplied just take the index (if it is mapped)
        if not ext_labels and len(self._get_mappings(instance_name, group, 'index')) > 0:
            if not ext_labels:
                ext_labels = labels.copy()
            ext_labels['index'] = str(index)

        return ext_labels

    def push_metric(self, instance, metric, value, labels=None, group=None, timestamp=None, fixed_dimensions=None,
                    default_dimensions=None):
        """Pushes a meter using the configured mapping information to determine metric_type and map the name and dimensions

        :param instance: instance containing the check configuration
        :param value: metric value (float)
        :param metric: metric as reported from metric data source (before mapping)
        :param labels: labels/tags as reported from the metric data source (before mapping)
        :param timestamp: optional timestamp to handle rates properly
        :param group: specify the metric group, otherwise it will be determined from the metric name
        :param fixed_dimensions:
        :param default_dimensions:
        """

        # determine group automatically if not specified
        if fixed_dimensions is None:
            fixed_dimensions = {}
        if labels is None:
            labels = {}
        if default_dimensions is None:
            default_dimensions = {}
        if group is None:
            group = self._get_group(instance, metric)

        metric_entry = self._fetch_metric_spec(instance, metric, group)
        if metric_entry.metric_type == DynamicCheckHelper.SKIP:
            return False

        if self._prefix:
            metric_prefix = self._prefix + '.'
        else:
            metric_prefix = ''

        if group:
            metric_prefix += group + '.'

        # determine the metric name
        metric_name = metric_prefix + metric_entry.metric_name
        # determine the target dimensions
        dims = self._map_dimensions(instance['name'], labels, group, default_dimensions)
        if dims is None:
            # regex for at least one dimension filtered the metric out
            return True

        # apply fixed default dimensions
        if fixed_dimensions:
            dims.update(fixed_dimensions)

        log.debug('push %s %s = %s {%s}', metric_entry.metric_type, metric_entry.metric_name, value, dims)

        if metric_entry.metric_type == DynamicCheckHelper.RATE:
            self._check.rate(metric_name, float(value), dimensions=dims)
        elif metric_entry.metric_type == DynamicCheckHelper.GAUGE:
            self._check.gauge(metric_name, float(value), timestamp=timestamp, dimensions=dims)
        elif metric_entry.metric_type == DynamicCheckHelper.COUNTER:
            self._check.increment(metric_name, float(value), dimensions=dims)

        return True

    def get_mapped_metrics(self, instance):
        """Returns input metric names or regex for which a mapping has been defined
        :param instance: instance to consider
        :return: array of metrics
        """
        metric_list = []
        iname = instance['name']
        # collect level-0 metrics
        metric_map = self._metric_map[iname]
        metric_list.extend(metric_map.get(DynamicCheckHelper.GAUGES_KEY, []))
        metric_list.extend(metric_map.get(DynamicCheckHelper.RATES_KEY, []))
        metric_list.extend(metric_map.get(DynamicCheckHelper.COUNTERS_KEY, []))
        # collect group specific metrics
        grp_metric_map = self._grp_metric_map.get(iname, {})
        for gname, gmmap in grp_metric_map.items():
            metric_list.extend(gmmap.get(DynamicCheckHelper.GAUGES_KEY, []))
            metric_list.extend(gmmap.get(DynamicCheckHelper.RATES_KEY, []))
            metric_list.extend(gmmap.get(DynamicCheckHelper.COUNTERS_KEY, []))

        return metric_list

    def _map_dimensions(self, instance_name, labels, group, default_dimensions):
        """Transforms labels attached to input metrics into Monasca dimensions
        :param default_dimensions:
        :param group:
        :param instance_name:
        :param labels:
        :return: mapped dimensions or None if the dimensions filter did not match and the metric needs to be filtered
        """
        dims = default_dimensions.copy()
        #  map all specified dimension all keys
        for labelname, labelvalue in labels.items():
            mapping_arr = self._get_mappings(instance_name, group, labelname)

            target_dim = None
            for map_spec in mapping_arr:
                try:
                    # map the dimension name
                    target_dim = map_spec.dimension
                    # apply the mapping function to the value
                    if target_dim not in dims:  # do not overwrite
                        mapped_value = map_spec.map_value(labelvalue)
                        if mapped_value is None:
                            # None means: filter it out based on dimension value
                            return None
                        elif mapped_value != '':
                            dims[target_dim] = mapped_value
                            # else the dimension will not map
                except (IndexError, AttributeError):  # probably the regex was faulty
                    log.exception(
                        'dimension %s value could not be mapped from %s: regex for mapped dimension %s '
                        'does not match %s',
                        target_dim, labelvalue, labelname, map_spec.regex)
                    return None

        return dims

    def _get_mappings(self, instance_name, group, labelname):
        # obtain mappings
        # check group-specific ones first
        if group:
            mapping_arr = self._grp_dimension_map[instance_name].get(group, {}).get(labelname, [])
        else:
            mapping_arr = []
        # fall-back to global ones
        mapping_arr.extend(self._dimension_map[instance_name].get(labelname, []))
        return mapping_arr

    @staticmethod
    def _create_metric_spec(metric, metric_type, metric_map):
        """Get or create MetricSpec if metric is in list for metric_type

        :param metric: incoming metric name
        :param metric_type: GAUGE, RATE, COUNTER
        :param metric_map: dictionary with mapping configuration for a metric group or the entire instance
        :return: new MetricSpec entry or None if metric is not listed as metric_type
        """
        re_list = metric_map.get(DynamicCheckHelper.CONFIG_SECTIONS[metric_type], [])
        for rx in re_list:
            match_groups = re.match(rx, metric)
            if match_groups:
                metric_entry = DynamicCheckHelper.MetricSpec(metric_type=metric_type,
                                                             metric_name=DynamicCheckHelper._normalize_metricname(
                                                                 metric,
                                                                 match_groups))
                return metric_entry

        return None

    @staticmethod
    def _lookup_metric(metric, metric_cache, metric_map):
        """Search cache for a MetricSpec and create if missing
        :param metric: input metric name
        :param metric_cache: cache to use
        :param metric_map: mapping config element to consider
        :return: MetricSpec for the output metric
        """
        i = DynamicCheckHelper.GAUGE
        metric_entry = metric_cache.get(metric, None)
        while not metric_entry and i < len(DynamicCheckHelper.METRIC_TYPES):
            metric_entry = DynamicCheckHelper._create_metric_spec(metric, DynamicCheckHelper.METRIC_TYPES[i],
                                                                  metric_map)
            i += 1

        if not metric_entry:
            # fall-through
            metric_entry = DynamicCheckHelper.MetricSpec(metric_type=DynamicCheckHelper.SKIP,
                                                         metric_name=DynamicCheckHelper._normalize_metricname(metric))

        metric_cache[metric] = metric_entry

        return metric_entry

    @staticmethod
    def _normalize_metricname(metric, match_groups=None):
        # map metric name first
        if match_groups and match_groups.lastindex > 0:
            metric = '_'.join(match_groups.groups())

        metric = re.sub('(?!^)([A-Z]+)', r'_\1', metric.replace('.', '_')).replace('__', '_').lower()
        metric = re.sub(r"[,+*\-/()\[\]{}]", "_", metric)
        # Eliminate multiple _
        metric = re.sub(r"__+", "_", metric)
        # Don't start/end with _
        metric = re.sub(r"^_", "", metric)
        metric = re.sub(r"_$", "", metric)
        # Drop ._ and _.
        metric = re.sub(r"\._", ".", metric)
        metric = re.sub(r"_\.", ".", metric)

        return metric


def get_pod_dimensions(kubernetes_connector, pod_metadata, kubernetes_labels):
    pod_name = pod_metadata['name']
    pod_dimensions = {'pod_name': pod_name, 'namespace': pod_metadata['namespace']}
    if "labels" in pod_metadata:
        pod_labels = pod_metadata['labels']
        for label in kubernetes_labels:
            if label in pod_labels:
                pod_dimensions[label] = pod_labels[label]
    # Get owner of pod to set as a dimension
    # Try to get from pod owner references
    pod_owner_references = pod_metadata.get('ownerReferences', None)
    if pod_owner_references:
        try:
            if len(pod_owner_references) > 1:
                log.warn("More then one owner for pod {}".format(pod_name))
            pod_owner_reference = pod_owner_references[0]
            pod_owner_type = pod_owner_reference['kind']
            pod_owner_name = pod_owner_reference['name']
            _set_pod_owner_dimension(kubernetes_connector, pod_dimensions, pod_owner_type, pod_owner_name)
        except Exception:
            log.info("Could not get pod owner from ownerReferences for pod {}".format(pod_name))
    # Try to get owner from annotations
    else:
        try:
            pod_created_by = json.loads(pod_metadata['annotations']['kubernetes.io/created-by'])
            pod_owner_type = pod_created_by['reference']['kind']
            pod_owner_name = pod_created_by['reference']['name']
            _set_pod_owner_dimension(kubernetes_connector, pod_dimensions, pod_owner_type, pod_owner_name)
        except Exception:
            log.info("Could not get pod owner from annotations for pod {}".format(pod_name))
    return pod_dimensions


def _get_deployment_name(kubernetes_connector, pod_owner_name, pod_namespace):
    replica_set_endpoint = "/apis/extensions/v1beta1/namespaces/{}/replicasets/{}".format(pod_namespace, pod_owner_name)
    try:
        replica_set = kubernetes_connector.get_request(replica_set_endpoint)
        replica_set_annotations = replica_set['metadata']['annotations']
        if "deployment.kubernetes.io/revision" in replica_set_annotations:
            return "-".join(pod_owner_name.split("-")[:-1])
    except Exception as e:
        log.warn("Could not connect to api to get replicaset data - {}".format(e))
        return None
    return None


def _set_pod_owner_dimension(kubernetes_connector, pod_dimensions, pod_owner_type, pod_owner_name):
    if pod_owner_type == "ReplicationController":
        pod_dimensions['replication_controller'] = pod_owner_name
    elif pod_owner_type == "ReplicaSet":
        if not kubernetes_connector:
            log.error("Can not set deployment name as connection information to API is not set. "
                      "Setting ReplicaSet as dimension")
            deployment_name = None
        else:
            deployment_name = _get_deployment_name(kubernetes_connector, pod_owner_name, pod_dimensions['namespace'])
        if not deployment_name:
            pod_dimensions['replica_set'] = pod_owner_name
        else:
            pod_dimensions['deployment'] = deployment_name
    elif pod_owner_type == "DaemonSet":
        pod_dimensions['daemon_set'] = pod_owner_name
    else:
        log.info("Unsupported pod owner kind {} as a dimension for pod {}".format(pod_owner_type,
                                                                                  pod_dimensions))
