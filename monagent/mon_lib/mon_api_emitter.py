import calendar
import datetime
from copy import deepcopy
from mon_lib.mon_api import MonAPI
from mon_lib.mon_normalizer import MonNormalizer
from config import _is_affirmative

class MonApiEmitter(object):

    def __init__(self, payload, logger, config):
        self.logger = logger
        self.logger.debug("Initializing the mon-api emitter...")
        self.mapping_key = "_mapping"
        self.config = config
        self.project_id = config['mon_api_project_id']
        self.mon_api_url = config['mon_api_url']
        self.user_id = config['mon_api_username']
        self.password = config['mon_api_password']
        self.use_keystone = config['use_keystone']
        self.keystone_url = config['keystone_url']
        self.aggregate_metrics = config['aggregate_metrics']
        self.discard = "DISCARD"
        self.payload = payload
        self.device_name = ""
        self.normalizer = MonNormalizer(logger, config['mon_mapping_file'])
        if self.normalizer.is_initialized():
            self.emitter()
        
    def emitter(self):
        self.logger.debug("Beginning metrics processing in mon-api emitter...")
        self.host_tags = self.get_standard_dimensions()

        api = MonAPI(self.mon_api_url, self.use_keystone, self.keystone_url, self.project_id, self.user_id, self.password, self.logger)
    
        self.logger.debug('mon_api_http_emitter: attempting postback to ' + self.mon_api_url)
        metrics_list = []
        self.logger.debug("Payload", self.payload)
        for agent_metric in self.payload:
            try:
                self.logger.debug("Agent Metric to Process: " + str(agent_metric))
                api_metric = self.get_api_metric(agent_metric, self.project_id)
                if _is_affirmative(self.aggregate_metrics):
                    metrics_list.extend(api_metric)
                else:
                    api.create_or_update_metric(api_metric)

                self.logger.debug("Sending metric to API: %s", str(api_metric))

            except Exception as ex:
                self.logger.exception("Error sending message to mon-api")
    
        if len(metrics_list) > 0:
            api.create_or_update_metric(metrics_list)
    
    def get_api_metric(self, agent_metric, project_id):
        timestamp = self.get_timestamp(self.payload)
        metrics_list = []
        dimensions = deepcopy(self.host_tags)
        name = self.normalizer.normalize_name(agent_metric)
        if name != self.discard:
            value = self.payload[agent_metric]
            if isinstance(value, str):
                metric = {"name": self.normalizer.normalize_name(name), "timestamp": timestamp, "value": self.normalizer.encode(value), "dimensions": dimensions}
                metrics_list.append(metric)
            elif isinstance(value, dict):
                metrics_list.extend(self.process_dict(name, timestamp, value))
            elif isinstance(value, list):
                metrics_list.extend(self.process_list(name, timestamp, value))
            elif isinstance(value, tuple):
                metrics_list.extend(self.process_list(name, timestamp, value))
            elif isinstance(value, tuple):
                metrics_list.extend(self.process_list(name, timestamp, value))
            elif isinstance(value, int) or isinstance(value, float):
                metric = {"name": self.normalizer.normalize_name(name), "timestamp": timestamp, "value": value, "dimensions": dimensions}
                metrics_list.append(metric)
        return metrics_list
    
    def get_timestamp(self, message):
        if "collection_timestamp" in message:
            timestamp = message["collection_timestamp"]
        elif "timestamp" in message:
            timestamp = message["timestamp"]
        else:
            timestamp = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
        return timestamp

    def process_dict(self, name, timestamp, values):
        metrics = []
        if name == "ioStats":
            for key in values.iterkeys():
                return self.process_dict(key, timestamp, values[key])
        else:
            for key in values.iterkeys():
                metric_name = self.normalizer.normalize_name(key)
                if metric_name != self.discard:
                    dimensions = deepcopy(self.host_tags)
                    dimensions.update({"device": self.normalizer.encode(name)})
                    metric = {"name": metric_name, "timestamp": timestamp, "value": self.normalizer.encode(values[key]), "dimensions": dimensions}
                    metrics.append(metric)
        return metrics

    def process_list(self, name, timestamp, values):
        metrics = []
        if name == "disk_usage" or name == "inodes":
            for item in values:
                if name != self.discard:
                    dimensions = deepcopy(self.host_tags)
                    dimensions.update({"device": self.normalizer.encode(item[0])})
                    if len(item) >= 9:
                         dimensions.update({"mountpoint": self.normalizer.encode(item[8])})
                    metric = {"name": name, "timestamp": timestamp, "value": self.normalizer.encode(item[4].rstrip("%")), "dimensions": dimensions}
                    metrics.append(metric)
        elif name == "metrics":
            # These are metrics sent in a format we know about from checks
            for item in values:
                dimensions = deepcopy(self.host_tags)
                for name2 in item[3].iterkeys():
                     value2 = item[3][name2]
                     if name2 == "type" or name2 == "interval" or value2 == None:
                         continue
                     if name2 == "tags":
                         dimensions.update(self.process_tags(value2))
                     else:
                         dimensions.update({self.normalizer.encode(name2) : self.normalizer.encode(value2)})
                metric = {"name": self.normalizer.normalize_name(item[0]), "timestamp": timestamp, "value": item[2], "dimensions": dimensions}
                metrics.append(metric)
        elif name == "series":
            # These are metrics sent in a format we know about from dogstatsd
            for item in values:
                dimensions = deepcopy(self.host_tags)
                metric_name = ""
                metric_timestamp = 0
                metric_value = 0
                points = []
                for name2 in item.iterkeys():
                     value2 = item[name2]
                     if name2 == "type" or name2 == "interval" or value2 == None:
                         continue
                     if name2 == "points":
                         points = value2
                     elif name2 == "tags":
                        dimensions.update(self.process_tags(value2))
                     elif name2 == "metric":
                         metric_name = self.normalizer.normalize_name(value2)
                     else:
                         dimensions.update({self.normalizer.encode(name2) : self.normalizer.encode(value2)})
                for point in points:
                    metric_timestamp = point[0]
                    metric_value = point[1]
                    metric = {"name": metric_name, "timestamp": metric_timestamp, "value": metric_value, "dimensions": dimensions}
                    metrics.append(metric)
        else:
            # We don't know what this metric list is.  Just add it as dimensions
            counter = 0
            dimensions = deepcopy(self.host_tags)
            self.logger.info("Found an unknown metric...")
            for item in values:
                dimensions.update({"Value" + str(counter) : item})
                counter+= 1
            metric = {"name": name, "timestamp": timestamp, "value": 0, "dimensions": dimensions}
            metrics.append(metric)
        return metrics
                
    def process_tags(self, tags):
        # This will process tag strings in the format "name:value" and put them in a dictionary to be added as dimensions
        processed_tags = {}
        index = 0
        # Metrics tags are a list of strings
        for tag in tags:
            if(tag.find(':') != -1):
                tag_parts = tag.split(':')
                name = tag_parts[0].strip()
                value = tag_parts[1].strip()
                processed_tags.update({self.normalizer.encode(name) : self.normalizer.encode(value)})
            else:
                processed_tags.update({"tag" + str(index) : self.normalizer.encode(tag)})
                index += 1
        return processed_tags

    def get_standard_dimensions(self):
        dimensions = {}
        if "internalHostname" in self.payload:
            dimensions.update({"hostname": self.normalizer.encode(self.payload["internalHostname"])})
        if "host-tags" in self.payload:
            self.logger.debug("Host-Tags" + str(self.payload["host-tags"]))
            host_tags = self.payload["host-tags"]
            if host_tags and "system" in host_tags:
                taglist = host_tags["system"]
                for tag in taglist:
                    tags = tag.split(',')
                    dimensions.update(self.process_tags(tags))
        return dimensions

