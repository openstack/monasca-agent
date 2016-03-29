# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import base64
import logging
import re

from monasca_agent.collector.checks import AgentCheck

log = logging.getLogger(__name__)

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
    def _build_dimension_map(config):
        result = {}
        for dim, spec in config.get('dimensions', {}).iteritems():
            if isinstance(spec, dict):
                label = spec.get('source_label', dim)
                regex = spec.get('regex', '(.*)')
                cregex = re.compile(regex)
                mapf = lambda x: AgentCheck.normalize(cregex.match(x).group(1))
            else:
                label = spec
                regex = '(.*)'
                mapf = lambda x: AgentCheck.normalize(x)

            # note: source keys can be mapped to multiple dimensions
            arr = result.get(label, [])
            arr.append({'dimension': dim, 'regex:': regex, 'mapf': mapf})
            result[label] = arr

        return result

    def __init__(self, check, prefix):
        """
        :param check: Target check instance to decorate

        For an instance to support mapped dimensions an element 'mapped_dimensions' needs to be added. For each dimension, an
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
            mappings = inst.get('mapping')
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
                    for grp, gspec in groups:
                        self._grp_metric_map[iname][grp] = DynamicCheckHelper._build_metric_map(gspec)
                        self._grp_metric_cache[iname][grp] = {}
                        self._grp_dimension_map[iname][grp] = DynamicCheckHelper._build_dimension_map(gspec)

    def push_metric(self, instance, metric, value, labels, group=None, timestamp=None, fixed_dimensions={}, default_dimensions={}):
        """
        push a meter using the configured mapping information to determine type and map the name and dimensions

        :param value: metric value (float)
        :param metric: metric as reported from metric data source (before mapping)
        :param labels: labels/tags as reported from the metric data source (before mapping)
        :param timestamp: optional timestamp to handle rates properly
        :param group: optional metric group, will be used as dot-separated prefix
        :param fixed_dimensions:
        :param default_dimensions:
        """

        instance_name = instance['name']
        metric_prefix = self._prefix + '.'

        # filter and classify the metric
        if group:
            metric_cache = self._grp_metric_cache[instance_name][group]
            metric_map = self._grp_metric_map[instance_name][group]
            metric_prefix += group + '.'
        else:
            metric_cache = self._metric_cache[instance_name]
            metric_map = self._metric_map[instance_name]

        metric_type, metric_name = DynamicCheckHelper._lookup_metric(metric, metric_cache, metric_map)

        if metric_type == SKIP:
            return

        dims = self._map_dimensions(default_dimensions, group, instance_name, labels)
        dims.update(fixed_dimensions)

        log.debug('push %s %s = %s {%s}', metric_type, metric_name, dims)

        if metric_type == RATE:
            self._check.rate(metric_name, float(value), dimensions=dims)
        elif metric_type == GAUGE:
            self._check.gauge(metric_name, float(value), timestamp=timestamp, dimensions=dims)

    def _map_dimensions(self, default_dimensions, group, instance_name, labels):
        dims = default_dimensions
        #  map all specified dimension all keys
        for labelname, labelvalue in labels:
            # obtain mappings
            mapping_arr = None
            # check group-specific ones first
            if group:
                mapping_arr = self._grp_dimension_map[instance_name].get(group)
            # fall-back to global ones afterwards
            if not mapping_arr:
                mapping_arr = self._dimension_map.get(instance_name, {}).get(labelname, [])

            target_dim = None
            for map_spec in mapping_arr:
                try:
                    # map the dimension name
                    target_dim = map_spec.get('dimension')
                    # apply the mapping function to the value
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
                if re.match(rx, metric):
                    metric_entry = { 'type': GAUGE, 'name': re.sub('(?!^)([A-Z]+)', r'_\1',metric).lower() }
                    metric_cache[metric] = metric_entry
                    return metric_entry['type'], metric_entry['name']
            all_rates_re = metric_map.get('rates', [])
            for rx in all_rates_re:
                if re.match(rx, metric):
                    # TODO: convert also first character
                    metric_entry = { 'type': RATE, 'name': re.sub('(?!^)([A-Z]+)', r'_\1',metric).lower() }
                    metric_cache[metric] = metric_entry
                    return metric_entry['type'], metric_entry['name']
            metric_entry = { 'type': SKIP, 'name': re.sub('(?!^)([A-Z]+)', r'_\1',metric).lower() }
            metric_cache[metric] = metric_entry
            return SKIP, metric
        else:
            return metric_entry['type'], metric_entry['name']
