# (C) Copyright 2016 Hewlett Packard Enterprise Development LP


from copy import deepcopy
import errno
import fcntl
import json
import os
import time

from monasca_agent.collector import checks


OK = 0
FAIL = 1

# name used for metrics reported directly by this module
PLUGIN_METRIC_NAME = 'monasca.json_plugin.status'

# Assumes metrics file written every 60 seconds
DEFAULT_STALE_AGE = 60 * 4                # These are too old to report

# Valid attributes of a metric
METRIC_KEYS = ['name', 'metric', 'timestamp', 'value', 'dimensions',
               'value_meta']


def _now():
    """Makes unit testing easier"""
    return time.time()


class JsonPlugin(checks.AgentCheck):
    """Read measurements from JSON-formatted files

    This plugin reads measurements from JSON-formatted files.

    The format of the file is shown in the following example:

    {
        "stale_age": 300,
        "replace_timestamps": false,
        "measurements: [
            {
                "metric": "a_metric",
                "dimensions: ["dim1": "val1"],
                "value: 30.0,
                "timestamp": 1474644040
            },
            {
                "metric": "second_metric",
                "dimensions: ["dim2": "val2"],
                "value: 22.4,
                "timestamp": 1474644040
            },
        ]
    }

    In effect, the file contains a header and a list of measurements. The
    header has the following fields:

    stale_age:

        A time in seconds. If the timestamp of a measurement is
        older than this, this plugin reports a json_plugin.check metric
        with a value of 1. The value_meta contains the name of
        the JSON file that is aged.

        This header is optional. It defaults to 4 minutes

    replace_timestamps:

        A boolean. If set, the next time the plugin is called, it will
        send all the measurements with a timestamp equal to the current
        time (ignoring the timestamp in the measurements list). The
        stale_age value is ignored with this setting.

        This header is optional. It defaults to false.

    measurements:

        This is a list of the measurements, formatted in the same way
        that measurements are presented to the Monasca API. However,
        if replace_timestamps is set, the timestamp key can be omitted
        (since it is set to current time).

    An alternate format for the file is that the header is omitted, i.e.,
    if the first item in the file is a list, it is assumed this is the
    measurement list and the header values are defaulted.
    """

    def __init__(self, name, init_config, agent_config, instances=None,
                 logger=None):
        super(JsonPlugin, self).__init__(name, init_config, agent_config,
                                         instances)
        self.log = logger or self.log
        self.plugin_failures = {}
        self.now = time.time()
        self.posted_metrics = {}

    def _plugin_failed(self, file_name, msg):
        self.plugin_failures[file_name] = msg
        self.log.warn('%s: %s' % (file_name, msg))

    def _plugin_check_metric(self):
        """Generate metric to report status of the plugin"""
        plugin_metric = dict(metric=PLUGIN_METRIC_NAME,
                             dimensions={},
                             value=OK,
                             timestamp=self.now)
        # If there were any failures, put the path
        # and error message into value_meta.
        errors = []
        for path, err in self.plugin_failures.items():
            if err:
                errors.append('%s: %s' % (path, err))
        msg = ''
        if errors:
                msg = ', '.join(errors)
        if msg:
            if len(msg) > 1024:  # keep well below length limit
                msg = msg[:-1021] + '...'
            plugin_metric.update(dict(value_meta=dict(msg=msg),
                                      value=FAIL))
        return plugin_metric

    @staticmethod
    def _take_shared_lock(fd):
        """Take shared lock on a file descriptor

        Assuming the writer of the JSON file also takes a lock, this
        function locks a file descriptor so that we can read the file
        without worrying that the content is changing as we read.

        Raises IOError if lock cannot be taken after a number of attempts.

        :param fd: the file descriptor of the file being read
        """
        max_retries = 5
        delay = 0.02
        attempts = 0
        while True:
            attempts += 1
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                break
            except IOError as err:
                if (err.errno not in [errno.EWOULDBLOCK, errno.EACCES] or
                        attempts > max_retries):
                    raise
                time.sleep(delay * attempts)

    def _load_measurements_from_file(self, file_name):
        handling = {}
        file_data = {'measurements': []}
        try:
            with open(file_name, 'r') as f:
                self._take_shared_lock(f)
                f.seek(0)
                file_data = json.load(f)
        except (ValueError, TypeError) as e:
            self._plugin_failed(file_name,
                                'failed parsing json: %s' % e)
        except Exception as e:  # noqa
            self._plugin_failed(file_name,
                                'loading error: %s' % e)
        try:
            if isinstance(file_data, list):
                metrics = file_data
                handling['stale_age'] = DEFAULT_STALE_AGE
                handling['replace_timestamps'] = False
            else:
                metrics = file_data.get('measurements', [])
                handling['stale_age'] = file_data.get('stale_age',
                                                      DEFAULT_STALE_AGE)
                handling['replace_timestamps'] = file_data.get(
                    'replace_timestamps', False)
        except Exception as e:  # noqa
            self._plugin_failed(file_name,
                                'unable to process file contents: %s' % e)
            metrics = []

        metrics = self._filter_metrics(metrics, file_name)
        return self._remove_duplicate_metrics(handling, metrics, file_name)

    def _filter_metrics(self, metrics, file_name):
        """Remove invalid metrics from the metric list

        Validate and clean up so the metric is suitable for passing to
        AgentCheck.gauge(). The metric might be invalid (e.g., value_meta too
        long), but that's not our concern here.
        """
        invalid_metric = None
        valid_metrics = []
        for metric in metrics:
            if not isinstance(metric, dict):
                invalid_metric = metric  # not a dict
                continue
            for key in metric.keys():
                if key not in METRIC_KEYS:
                    invalid_metric = metric  # spurious attribute
                    continue
            if 'name' not in metric.keys() and 'metric' not in metric.keys():
                invalid_metric = metric  # missing name
                continue
            if 'value' not in metric.keys():
                invalid_metric = metric  # missing value
                continue

            if 'name' in metric:
                # API use 'name'; AgentCheck uses 'metric'
                metric['metric'] = metric.get('name')
                del metric['name']
            if not metric.get('dimensions', None):
                metric['dimensions'] = {}
            valid_metrics.append(metric)

        if invalid_metric:
            # Only report one invalid metric per file
            self._plugin_failed(file_name, 'invalid metric found: %s' % metric)
        return valid_metrics

    def _remove_duplicate_metrics(self, handling, metrics, file_name):
        """Remove metrics if we've already reported them

        We track the metrics we've posted to the Monasca Agent This allows us
        to discard duplicate metrics. The most common cause of duplicates is
        that the agent runs more often than the update period of the JSON file.

        We also discard metrics that seem stale. This can occur when the
        program creating the metrics file has died, so the JSON file
        does not update with new metrics.

        :param: handling: options for how measurements are handled
        :param metrics: The metrics we found in the JSON file
        :param file_name: the path of the JSON file
        :returns: A list of metrics that should be posted
        """

        # Set timestamp if asked
        if handling['replace_timestamps']:
            for metric in metrics:
                metric['timestamp'] = self.now
            # Since we've set the timestamp, these are unique (not duplicate)
            # so no further processing is required
            return metrics

        # Remove metrics we've already posted. Also remove stale metrics.
        if file_name not in self.posted_metrics:
            self.posted_metrics[file_name] = []
        stale_metrics = False
        for metric in deepcopy(metrics):
            if ((self.now - metric.get('timestamp', 0)) >
                    handling.get('stale_age')):
                metrics.remove(metric)  # too old
                stale_metrics = True
            elif metric in self.posted_metrics[file_name]:
                metrics.remove(metric)  # already sent to Monasca
            else:
                # New metric; not stale.
                self.posted_metrics[file_name].append(metric)

        # Purge really old metrics from posted
        for metric in list(self.posted_metrics[file_name]):
            if ((self.now - metric.get('timestamp', 0)) >=
                    handling.get('stale_age') * 2):
                self.posted_metrics[file_name].remove(metric)

        if stale_metrics:
            self._plugin_failed(file_name, 'Metrics are older than %s seconds;'
                                           ' file not updating?' %
                                handling.get('stale_age'))
        return metrics

    def _get_metrics(self):
        reported = []
        for file_name in self.metrics_files:
            metrics = self._load_measurements_from_file(file_name)
            for metric in metrics:
                reported.append(metric)
        return reported

    def _load_instance_config(self, instance):
        self.metrics_files = []
        self.metrics_dir = instance.get('metrics_dir', '')
        if self.metrics_dir:
            self.plugin_failures[self.metrics_dir] = ''
            try:
                file_names = os.listdir(self.metrics_dir)
                for name in [os.path.join(self.metrics_dir, name) for
                             name in file_names]:
                    # .json extension protects from reading .swp and similar
                    if os.path.isfile(name) and name.lower().endswith('.json'):
                        self.metrics_files.append(name)
            except OSError as err:
                self._plugin_failed(self.metrics_dir,
                                    'Error processing: %s' % err)
        else:
            metric_file = instance.get('metrics_file', '')
            if metric_file:
                self.metrics_files = [metric_file]
        self.log.debug('Using metrics files %s' % ','.join(self.metrics_files))
        for file_name in self.metrics_files:
            self.plugin_failures[file_name] = ''

    def check(self, instance):
        self._load_instance_config(instance)
        all_metrics = []
        self.now = _now()

        # Load measurements from files
        metrics = self._get_metrics()
        all_metrics.extend(metrics)

        # Add this plugin status
        all_metrics.append(self._plugin_check_metric())

        for metric in all_metrics:
            # apply any instance dimensions that may be configured,
            # overriding any dimension with same key that check has set.
            metric['dimensions'] = self._set_dimensions(metric['dimensions'],
                                                        instance)
            self.log.debug('Posting metric: %s' % metric)
            try:
                self.gauge(**metric)
            except Exception as e:  # noqa
                self.log.exception('Exception while reporting metric: %s' % e)
