import time
from copy import deepcopy
from monapi import MonAPI
from config import _is_affirmative

class MonApiEmitter(object):

    def __init__(self, payload, logger, config):
        self.logger = logger
        self.logger.debug("Configuration Info: " + str(config))
        self.mapping_key = "_mapping"
        self.config = config
        self.payload = payload
        self.project_id = config['mon_api_project_id']
        self.mon_api_url = config['mon_api_url']
        self.user_id = config['mon_api_username']
        self.password = config['mon_api_password']
        self.use_keystone = config['use_keystone']
        self.keystone_url = config['keystone_url']
        self.aggregate_metrics = config['aggregate_metrics']
        self.host_tags = self.get_standard_dimensions()
        self.discard = "DISCARD"
        self.sendToAPI()
        
    def sendToAPI(self):
        api = MonAPI(self.mon_api_url, self.use_keystone, self.keystone_url, self.project_id, self.user_id, self.password, self.logger)
    
        self.logger.debug('mon_api_http_emitter: attempting postback to ' + self.mon_api_url)
        metrics_list = []
        for agent_metric in self.payload:
            try:
                self.logger.debug("Agent Metric to Process: " + str(agent_metric))
                api_metric = self.get_api_metric(agent_metric, self.project_id)
                self.logger.debug("API Metric to Send: " + str(api_metric))
                if _is_affirmative(self.aggregate_metrics):
                    metrics_list.extend(api_metric)
                else:
                    api.create_or_update_metric(api_metric)
                self.logger.debug("Sending metric to API: %s", str(api_metric))
               
                #self.logger.debug('mon_api_http_emitter: postback response: ' + str(response.read()))
            except Exception as ex:
                self.logger.exception("Error sending message to mon-api")
    
        if len(metrics_list) > 0:
            api.create_or_update_metric(metrics_list)
    
    def get_api_metric(self, agent_metric, project_id):
        timestamp = self.get_timestamp(self.payload)
        metrics_list = []
        dimensions = deepcopy(self.host_tags)
        name = self.normalize_name(agent_metric)
        if name != self.discard:
            value = self.payload[agent_metric]
            if isinstance(value, int) or isinstance(value, float):
                metric = {"name": name, "timestamp": timestamp, "value": value, "dimensions": dimensions}
                metrics_list.append(metric)
            elif isinstance(value, dict):
                metrics_list.extend(self.process_dict(name, timestamp, value))
            elif isinstance(value, list):
                metrics_list.extend(self.process_list(name, timestamp, value))
        return metrics_list
    
    def get_timestamp(self, message):
        if "collection_timestamp" in message:
            timestamp = message["collection_timestamp"]
        else:
            timestamp = time.gmtime()
        return timestamp

    def process_dict(self, name, timestamp, values):
        metrics = []
        if name == "ioStats" or name == "system_metrics":
            for key in values.iterkeys():
                self.device_name = key
                metrics.extend(self.process_dict(key, timestamp, values[key]))
        else:
            for key in values.iterkeys():
                metric_name = self.normalize_name(key)
                if metric_name != self.discard:
                    dimensions = deepcopy(self.host_tags)
                    dimensions.update({"device": self.device_name})
                    metric = {"name": metric_name, "timestamp": timestamp, "value": values[key], "dimensions": dimensions}
                    metrics.append(metric)
        return metrics

    def process_list(self, name, timestamp, values):
        metrics = []
        if name == "diskUsage" or name == "inodes":
            for item in values:
                if name != self.discard:
                    dimensions = deepcopy(self.host_tags)
                    dimensions.update({"device": item[0]})
                    if len(item) >= 9:
                         dimensions.update({"mountpoint": item[8]})
                    metric = {"name": name, "timestamp": timestamp, "value": item[4], "dimensions": dimensions}
                    metrics.append(metric)
        elif name == "metrics":
            # These are metrics sent in a format we know about from checks
            for item in values:
                dimensions = deepcopy(self.host_tags)
                for item2 in item[3]:
                    if item2[0] == "tags":
                        dimensions.update(self.process_tags(item2))
                    else:
                        dimensions.update({item2[0] : item2[1]})
                metric = {"name": item[0], "timestamp": timestamp, "value": item[2], "dimensions": dimensions}
                metrics.append(metric)
        else:
            # We don't know what this metric list is.  Just add it as dimensions
            counter = 0
            dimensions = deepcopy(self.host_tags)
            for item in values:
                dimensions.update({"Value" + str(counter) : item})
                counter+= 1
            metric = {"name": name, "timestamp": timestamp, "value": 0, "dimensions": dimensions}
            metrics.append(metric)
        return metrics
                
    def process_tags(self, tags):
        # This will process tag strings in the format "name:value" and put them in a dictionary to be added as dimensions
        processed_tags = {}
        # Metrics tags are a list of strings
        for tag in tags:
            tag_parts = tag.split(':')
            name = tag_parts[0].strip()
            value = tag_parts[1].strip()
            processed_tags.update({name.encode('ascii','ignore') : value.encode('ascii','ignore')})
        return processed_tags

    def normalize_name(self, key):
        name = key
        lookup = key.lower() + self.mapping_key
        if lookup in self.config:
            name = self.config[lookup]
        return name
    
    def get_standard_dimensions(self):
        dimensions = {}
        if "internalHostname" in self.payload:
            dimensions.update({"hostname": self.payload["internalHostname"]})
        if "host-tags" in self.payload:
            self.logger.debug("Host-Tags" + str(self.payload["host-tags"]))
            host_tags = self.payload["host-tags"]
            if host_tags and "system" in host_tags:
                taglist = host_tags["system"]
                for tag in taglist:
                    tags = tag.split(',')
                    dimensions.update(self.process_tags(tags))
        return dimensions
