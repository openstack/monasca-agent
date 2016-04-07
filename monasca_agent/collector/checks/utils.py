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
                mapf = lambda x: DynamicCheckHelper._normalize_dim_value(cregex.match(x).group(1))
            else:
                label = spec
                regex = '(.*)'
                mapf = lambda x: DynamicCheckHelper._normalize_dim_value(x)

            # note: source keys can be mapped to multiple dimensions
            arr = result.get(label, [])
            arr.append({'dimension': dim, 'regex': regex, 'mapf': mapf})
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

    def push_metric_dict(self, instance, metric_dict, labels={}, group=None, timestamp=None, fixed_dimensions={}, default_dimensions={}, max_depth=0, curr_depth=0, prefix=''):
        for element, child in metric_dict.iteritems():
            if isinstance(child, dict) and curr_depth < max_depth:
                self.push_metric_dict(instance, child, labels, group, timestamp, fixed_dimensions, default_dimensions, max_depth, curr_depth+1, prefix+element+'_')
            elif isinstance(child, Number):
                self.push_metric(instance, prefix+element, float(child), labels, group, timestamp, fixed_dimensions, default_dimensions)
            elif isinstance(child, list):
                for i, child_element in enumerate(child):
                    if isinstance(child_element, dict):
                        if curr_depth < max_depth:
                            self.push_metric_dict(instance, child_element, labels, group, timestamp, fixed_dimensions, default_dimensions, max_depth, curr_depth+1, prefix+element+'#'+str(i)+'_')
                    elif isinstance(child_element, Number):
                        self.push_metric(instance, prefix+element+'#'+str(i), float(child_element), labels, group, timestamp, fixed_dimensions, default_dimensions)
                    else:
                        log.debug('nested arrays are not supported for configurable extraction of element %s', element)

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
            # obtain mappings
            # check group-specific ones first
            if group:
                mapping_arr = self._grp_dimension_map[instance_name].get(group, {}).get(labelname, [])
            else:
                mapping_arr = []
            # fall-back to global ones
            mapping_arr.extend(self._dimension_map[instance_name].get(labelname, []))

            target_dim = None
            for map_spec in mapping_arr:
                try:
                    # map the dimension name
                    target_dim = map_spec.get('dimension')
                    # apply the mapping function to the value
                    if not target_dim in dims:      # do not overwrite
                        dims[target_dim] = map_spec['mapf'](labelvalue)
                except (IndexError, AttributeError):  # probably the regex was faulty
                    log.exception(
                        'dimension %s value could not be mapped from %s: regex for mapped dimension %s does not match %s',
                        target_dim, labelvalue, labelname, map_spec['regex'])
        return dims

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
        return Check.normalize(re.sub('(?!^)([A-Z]+)', r'_\1', metric.replace('.', '_')).lower())
