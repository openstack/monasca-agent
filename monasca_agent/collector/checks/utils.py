# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import base64
import logging
import re
from numbers import Number

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.collector.checks.check import Check
from monasca_agent.common.exceptions import CheckException

log = logging.getLogger(__name__)
normalizer_re = re.sub
GAUGE = 1
RATE = 2
SKIP = 0

def add_basic_auth(request, username, password):
    """A helper to add basic authentication to a urllib2 request.

    We do this across a variety of checks so it's good to have this in one place.
    """
    auth_str = base64.encodestring('%s:%s' % (username, password)).strip()
    request.add_header('Authorization', 'Basic %s' % auth_str)
    return request


class DynamicCheckHelper:
    """
    Supplements existing check class with reusable functionality to transform third-party metrics into Monasca ones
    in a configurable way
    """

    @staticmethod
    def _build_metric_map(config):
        return {'rates': config.get('rates', []),
                'gauges': config.get('gauges', [])}

    @staticmethod
    def _normalize_dim_value(value):
        """
        :param value:
        :return:
        Replace \\x?? values with _
        Replace the following characters with _: > < = { } ( ) , ' " \ ; &
        Truncate to 255 chars
        """

        return re.sub(r'["\']', '|', re.sub(r'[(}]', ']', re.sub(r'[({]', '[', re.sub(r'[\><=,;&]', '-', value.replace(r'\x2d', '-').replace(r'\x7e', '~')))))[:255]

    @staticmethod
    def _build_dimension_map(config):
        result = {}
        for dim, spec in config.get('dimensions', {}).iteritems():
            if isinstance(spec, dict):
                label = spec.get('source_key', dim)
                regex = spec.get('regex', '(.*)')
                cregex = re.compile(regex)
            else:
                label = spec
                regex = '(.*)'
                cregex = None

            # note: source keys can be mapped to multiple dimensions
            arr = result.get(label, [])
            mapping = {'dimension': dim, 'regex': regex}
            if cregex:
                mapping['cregex'] = cregex
            arr.append(mapping)
            result[label] = arr

        return result

    def __init__(self, check, prefix, default_mapping=None):
        """
        :param check: Target check instance to filter and map metrics from a separate data source. The mapping
        procedure involves a filtering, renaming and classification of metrics and filtering and mapping of
        labels to dimensions.

        To support all these capabilities, an element 'mapping' needs to be added to the instance config or a default
        has to be supplied.

        For metrics the filtering and renaming stage is identical. The metric filter is specified as regular
        expression with zero or more match groups. If match groups are specified, the match group values are
        concatenated with '_'. If no match group is specified, the name is taken as is. The resulting name is
        normalized according to Monasca naming standards for metrics. This implies that dots are replaced by underscores
        and *CamelCase* is transformed into *lower_case*. Special characters are eliminated, too.

        a) Simple mapping:

           rates: [ 'FilesystemUsage' ]             # map metric 'FileystemUsage' to 'filesystem_usage'

        b) Mapping with simple regular expression

           rates: [ '.*Usage' ]                     # map metrics ending with 'Usage' to '..._usage'

        b) Mapping with regular expression and match-groups

           rates: [ '(.*Usage)\.stats\.(total)' ]   # map metrics ending with 'Usage.stats.total' to '..._usage_total'

        Mapping of labels to dimensions is a little more complex. For each dimension, an
        entry of the following format is required:

        a) Simple mapping

            <dimension>: <source_key>                # map key <source_key> to dimension <dimension>

        b) Complex mapping:

            <dimension>:
               source_key: <source_key>             # key as provided by metric source
               regex: <mapping_pattern>             # regular expression with a single match-group in braces

        Example:

        instances:
            - name: kubernetes
              mapping
                dimensions:
                    pod_name: io.kubernetes.pod.name    # simple mapping
                    pod_basename:
                        source_key: label_name
                        regex: k8s_.*_.*\._(.*)_[0-9a-z\-]*
                rates:
                - io.*
                gauges:
                - .*_avg
                - .*_max
                groups:
                    engine:
                        dimensions:

        """
        self._check = check
        self._prefix = prefix
        self._metric_map = {}
        self._dimension_map = {}
        self._metric_cache = {}
        self._grp_metric_map = {}
        self._grp_dimension_map = {}
        self._grp_metric_cache = {}
        for inst in self._check.instances:
            iname = inst['name']
            mappings = inst.get('mapping', default_mapping)
            if mappings:
                # build global name filter and rate/gauge assignment
                self._metric_map[iname] = DynamicCheckHelper._build_metric_map(mappings)
                self._metric_cache[iname] = {}
                # build global dimension map
                self._dimension_map[iname] = DynamicCheckHelper._build_dimension_map(mappings)
                # check if groups are used
                groups = mappings.get('groups')
                if groups:
                    self._grp_metric_map[iname] = {}
                    self._grp_metric_cache[iname] = {}
                    self._grp_dimension_map[iname] = {}
                    for grp, gspec in groups.iteritems():
                        self._grp_metric_map[iname][grp] = DynamicCheckHelper._build_metric_map(gspec)
                        self._grp_metric_cache[iname][grp] = {}
                        self._grp_dimension_map[iname][grp] = DynamicCheckHelper._build_dimension_map(gspec)
            else:
                raise CheckException('instance %s is not supported: no element "mapping" found!', iname)

    def _fetch_metric_spec(self, instance, metric, group=None):
        """
        check whether a metric is enabled by the instance configuration

        :param instance: instance containing the check configuration
        :param metric: metric as reported from metric data source (before mapping)
        :param group: optional metric group, will be used as dot-separated prefix
        """

        instance_name = instance['name']

        # filter and classify the metric
        if group:
            metric_cache = self._grp_metric_cache[instance_name].get(group, {})
            metric_map = self._grp_metric_map[instance_name].get(group, {})
        else:
            metric_cache = self._metric_cache[instance_name]
            metric_map = self._metric_map[instance_name]

        return DynamicCheckHelper._lookup_metric(metric, metric_cache, metric_map)

    def is_enabled_metric(self, instance, metric, group=None):
        type, _ = self._fetch_metric_spec(instance, metric, group)
        return type != SKIP

    def push_metric_dict(self, instance, metric_dict, labels={}, group=None, timestamp=None, fixed_dimensions={}, default_dimensions={}, max_depth=0, curr_depth=0, prefix='', index=-1):
        """
        This will extract metrics and dimensions from a dictionary.

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
                    rates:
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
                    rates:
                        - server_requests

            Result:

                server_requests{server_no=0} = 1500.0
                server_requests{server_no=1} = 1000.0
                server_requests{server_no=2} = 500.0


        :param instance:
        :param metric_dict:
        :param labels:
        :param group:
        :param timestamp:
        :param fixed_dimensions:
        :param default_dimensions:
        :param max_depth:
        :param curr_depth:
        :param prefix:
        :param index:
        :return:
        """
        if index != -1:
            ext_labels = self.extract_dist_labels(instance['name'], group, metric_dict, labels, index)
            if not ext_labels:
                log.debug("skipping array due to lack of mapped dimensions for group %s (at least 'index' should be supported)", group if group else '<root>')
                return

        else:
            ext_labels = labels

        for element, child in metric_dict.iteritems():
            if isinstance(child, dict) and curr_depth < max_depth:
                self.push_metric_dict(instance, child, ext_labels, group, timestamp, fixed_dimensions, default_dimensions, max_depth, curr_depth+1, prefix+element+'_')
            elif isinstance(child, Number):
                self.push_metric(instance, prefix+element, float(child), ext_labels, group, timestamp, fixed_dimensions, default_dimensions)
            elif isinstance(child, list):
                for i, child_element in enumerate(child):
                    if isinstance(child_element, dict):
                        if curr_depth < max_depth:
                            self.push_metric_dict(instance, child_element, ext_labels, group, timestamp, fixed_dimensions, default_dimensions, max_depth, curr_depth+1, prefix+element+'_', index=i)
                    elif isinstance(child_element, Number):
                        if len(self._get_mappings(instance['name'], group, 'index')) > 0:
                            idx_labels=ext_labels.copy()
                            idx_labels['index'] = str(i)
                            self.push_metric(instance, prefix+element, float(child_element), idx_labels, group, timestamp, fixed_dimensions, default_dimensions)
                        else:
                           log.debug("skipping array due to lack of mapped 'index' dimensions for group %s", group if group else '<root>')
                    else:
                        log.debug('nested arrays are not supported for configurable extraction of element %s', element)

    def extract_dist_labels(self, instance_name, group, metric_dict, labels, index):
        """

        :param instance_name: instance to be used
        :param group: metric group or None for root group
        :param metric_dict: dictionary with metrics and labels
        :param labels: labels dictionary to extend
        :param index: index value to be used as fallback if no labels can be derived from string-valued attributes
            or the derived labels are not mapped in the config.
        :return:
        """
        ext_labels = None
        # collect additional dimensions first from non-metrics
        for element, child in metric_dict.iteritems():
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

    def push_metric(self, instance, metric, value, labels={}, group=None, timestamp=None, fixed_dimensions={}, default_dimensions={}):
        """
        push a meter using the configured mapping information to determine type and map the name and dimensions

        :param instance: instance containing the check configuration
        :param value: metric value (float)
        :param metric: metric as reported from metric data source (before mapping)
        :param labels: labels/tags as reported from the metric data source (before mapping)
        :param timestamp: optional timestamp to handle rates properly
        :param group: optional metric group, will be used as dot-separated prefix
        :param fixed_dimensions:
        :param default_dimensions:
        """

        metric_type, metric_name = self._fetch_metric_spec(instance, metric, group)
        if metric_type == SKIP:
            return False

        metric_prefix = self._prefix + '.'
        if group:
            metric_prefix += group + '.'
        metric_name = metric_prefix + metric_name
        dims = self._map_dimensions(default_dimensions, group, instance['name'], labels)
        dims.update(fixed_dimensions)

        log.debug('push %s %s = %s {%s}', metric_type, metric_name, dims)

        if metric_type == RATE:
            self._check.rate(metric_name, float(value), dimensions=dims)
        elif metric_type == GAUGE:
            self._check.gauge(metric_name, float(value), timestamp=timestamp, dimensions=dims)

        return True

    def _map_dimensions(self, default_dimensions, group, instance_name, labels):
        dims = default_dimensions.copy()
        #  map all specified dimension all keys
        for labelname, labelvalue in labels.iteritems():
            mapping_arr = self._get_mappings(instance_name, group, labelname)

            target_dim = None
            for map_spec in mapping_arr:
                try:
                    # map the dimension name
                    target_dim = map_spec.get('dimension')
                    # apply the mapping function to the value
                    if not target_dim in dims:      # do not overwrite
                        cregex = map_spec.get('cregex')
                        if cregex:
                            dims[target_dim] = DynamicCheckHelper._normalize_dim_value(cregex.match(labelvalue).group(1))
                        else:
                            dims[target_dim] = DynamicCheckHelper._normalize_dim_value(labelvalue)
                except (IndexError, AttributeError):  # probably the regex was faulty
                    log.exception(
                        'dimension %s value could not be mapped from %s: regex for mapped dimension %s does not match %s',
                        target_dim, labelvalue, labelname, map_spec['regex'])

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
    def _lookup_metric(metric, metric_cache, metric_map):
        metric_entry = metric_cache.get(metric)
        if metric_entry is None:
            all_gauges_re = metric_map.get('gauges', [])
            for rx in all_gauges_re:
                groups = re.match(rx, metric)
                if groups:
                    metric_entry = { 'type': GAUGE, 'name': DynamicCheckHelper._normalize_metricname(metric, groups)}
                    metric_cache[metric] = metric_entry
                    return metric_entry['type'], metric_entry['name']
            all_rates_re = metric_map.get('rates', [])
            for rx in all_rates_re:
                groups = re.match(rx, metric)
                if groups:
                    metric_entry = { 'type': RATE, 'name': DynamicCheckHelper._normalize_metricname(metric, groups)}
                    metric_cache[metric] = metric_entry
                    return metric_entry['type'], metric_entry['name']
            metric_entry = { 'type': SKIP, 'name': DynamicCheckHelper._normalize_metricname(metric, groups)}
            metric_cache[metric] = metric_entry
            return SKIP, metric
        else:
            return metric_entry['type'], metric_entry['name']

    @staticmethod
    def _normalize_metricname(metric, groups):
        # map metric name first
        if groups and groups.lastindex > 0:
            metric = '_'.join(groups.groups())
        return Check.normalize(re.sub('(?!^)([A-Z]+)', r'_\1', metric.replace('.', '_')).replace('__', '_').lower())
