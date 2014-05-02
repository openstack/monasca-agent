from copy import deepcopy
import json
import logging
import time

import requests

from keystone import Keystone


log = logging.getLogger(__name__)


class MonAPI(object):
    """MonAPI emitter
        All metrics are sent to the monitoring api via this connection.
    """
    def __init__(self, config):
        """
        Initialize Mon api connection.
        """
        self.url = config['url']
        self.default_dimensions = config['dimensions']

        #todo we should always use keystone, for development the keystone object should just return a dummy token
        if config['use_keystone']:
            self.keystone = Keystone(config['keystone_url'])
            token = self.keystone.get_token_password_auth(config['username'], config['password'],
                                                               config['project_id'])
            self.headers = {'content-type': 'application/json',
                            'X-Auth-Token': token}
        else:
            self.headers = {'content-type': 'application/json',
                            'X-Tenant-Id': config['project_id']}

    @staticmethod
    def _get_timestamp(message):
        if "collection_timestamp" in message:
            timestamp = message["collection_timestamp"]
        elif "timestamp" in message:
            timestamp = message["timestamp"]
        else:
            timestamp = int(time.time())
        return timestamp

    def _post(self, metrics):
        """Does the actual http post
            metrics is a list of metric
        """
        #todo clean up the doc string
        try:
            data = json.dumps(metrics)
            response = requests.post(self.url, data=data, headers=self.headers)
            if response:
                if 200 <= response.status_code <= 299:
                    # Good status from web service
                    log.debug("Message sent successfully: {0}".format(str(data)))
                elif 400 <= response.status_code <= 499:
                    # Good status from web service but some type of issue with the data
                    error_msg = "Successful web service call but there were issues (Status: {0}," + \
                                "Status Message: {1}, Message Content: {1})"
                    log.warn(error_msg.format(response.status_code, response.text, response.str(metrics)))
                else:
                    # Not a good status
                    self.response.raise_for_status()
            else:
                log.error("Unable to connect to mon-api at " + self.url)

        except Exception:
            log.exception("Error sending message to mon-api: ")
        
        return

    # todo I should break out the metrics themself into an object, three objects one for keystone, the api and metrics
    # todo really what I want is a standard metric format across all components of the project, forwarder, collector and dogstatsd
    @staticmethod
    def _process_dict(name, timestamp, value, dimensions):
        # todo What is with the special case, fix it
        if name == "ioStats":
            for key in value.iterkeys():
                return process_dict(key, timestamp, value[key], dimensions)
        else:
            metrics = []
            for metric_name in value.iterkeys():
                metric = {"name": metric_name, "timestamp": timestamp, "value": value[key],
                          "dimensions": dict(dimensions.items() + [("device", name)])}
                metrics.append(metric)
            return metrics

    @staticmethod
    def _process_list(name, timestamp, value, dimensions):
        metrics = []
        # todo generalize this so we don't need to do so much special case processing
        if name == "disk_usage" or name == "inodes":
            for item in value:
                new_dimensions = deepcopy(dimensions)
                new_dimensions.update({"device": normalizer.encode(item[0])})
                if len(item) >= 9:
                    new_dimensions.update({"mountpoint": normalizer.encode(item[8])})
                metric = {"name": name, "timestamp": timestamp, "value": item[4].rstrip("%"),
                          "dimensions": new_dimensions}
                metrics.append(metric)
        elif name == "metrics":
            # These are metrics sent in a format we know about from checks
            for item in value:
                new_dimensions = deepcopy(dimensions)
                for name2 in item[3].iterkeys():
                    value2 = item[3][name2]
                    if name2 == "type" or name2 == "interval" or value2 is None:
                        continue
                    else:
                        new_dimensions.update({name2: value2})
                metric_name = item[0]
                metric = {"name": metric_name, "timestamp": timestamp, "value": item[2], "dimensions": new_dimensions}
                metrics.append(metric)
        elif name == "series":
            # These are metrics sent in a format we know about from dogstatsd
            for item in value:
                new_dimensions = deepcopy(dimensions)
                metric_name = ""
                points = []
                for name2 in item.iterkeys():
                    value2 = item[name2]
                    if name2 == "type" or name2 == "interval" or value2 is None:
                        continue
                    if name2 == "points":
                        points = value2
                    elif name2 == "metric":
                        metric_name = value2
                    else:
                        new_dimensions.update({name2: value2})
                for point in points:
                    metric_timestamp = point[0]
                    metric_value = point[1]
                    metric = {"name": metric_name, "timestamp": metric_timestamp, "value": metric_value, "dimensions": new_dimensions}
                    metrics.append(metric)
        else:
            # We don't know what this metric list is.  Just add it as dimensions
            counter = 0
            new_dimensions = deepcopy(dimensions)
            log.info("Found an unknown metric...")
            for item in value:
                new_dimensions.update({"Value" + str(counter) : item})
                counter += 1
            metric = {"name": name, "timestamp": timestamp, "value": 0, "dimensions": new_dimensions}
            metrics.append(metric)
        return metrics

    @staticmethod
    def _process_metric(self, name, value, timestamp, dimensions):
        """Convert from agent style metrics to that of the api
            Depending on the type of metric payload different processing is done and the result is a list of api metrics
        """
        log.debug("Agent Metric Name Received: %s" % name)
        log.debug("Agent Metric Value Received: %s" % value)
        # todo switch to ducktyping rather than this explicit typing
        if isinstance(value, dict):
            return self._process_dict(name, timestamp, value, dimensions)
        elif isinstance(value, list) or isinstance(value, tuple):
            return self._process_list(name, timestamp, value, dimensions)
        else:  # Covers strings and numbers
            return [{"name": name, "timestamp": timestamp, "value": value, "dimensions": dimensions}]

    def post_metrics(self, payload):
        """post_metrics
            given a metrics payload (list of metrics, format the request and post to the monitoring api
        """
        log.debug("Payload ==> %s" % payload)

        if 'internalHostname' in payload:
            host_dimension = {"hostname": payload["internalHostname"]}
        else:
            # todo is internalHostname required? If not what is the alternative?
            host_dimension = {}

        dimensions = dict(self.default_dimensions.items() + host_dimension.items())
        timestamp = self._get_timestamp(payload)
        metrics_list = [self._process_metric(metric, payload[metric], timestamp, dimensions) for metric in payload]

        if len(metrics_list) > 0:
            log.debug('No valid metrics found in the payload, %s' % payload)
            self._post(metrics_list)
