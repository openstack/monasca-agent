import time
from monapi import MonAPI

class MonApiEmitter(object):

    def __init__(self, payload, logger, config):
        self.payload = payload
        self.logger = logger
        self.mon_api_url = config['mon_api_url']
        self.project_id = config['mon_api_project_id']
        self.user_id = config['mon_api_username']
        self.password = config['mon_api_password']
        self.use_keystone = bool(config['use_keystone'])
        self.keystone_url = config['keystone_url']
        self.aggregate_metrics = bool(config['aggregate_metrics'])
        self.sendToAPI()
        
    def sendToAPI(self):
        api = MonAPI(self.mon_api_url, self.use_keystone, self.keystone_url, self.project_id, self.user_id, self.password, self.logger)
    
        self.logger.debug('mon_api_http_emitter: attempting postback to ' + self.mon_api_url)
        
        metrics_list = []

        for body in self.get_metric(self.payload, self.project_id):
            try:
                if self.aggregate_metrics:
                    metrics_list.append(body)
                else:
                    print body
                    api.create_or_update_metric(body)
                
                #logger.debug('mon_api_http_emitter: postback response: ' + str(response.read()))
            except Exception as ex:
                self.logger.error("Error sending message to mon-api", ex)
    
        if len(metrics_list) > 0:
            print metrics_list
            api.create_or_update_metric(metrics_list)
    
    def get_metric(self, message, project_id):
        blacklist = ["collection_timestamp"]
        timestamp = self.get_timestamp(message)
        for key in message:
            if key not in blacklist:
                value = message[key]
                if isinstance(value, int) or isinstance(value, float):
                    metric = {"name": key, "timestamp": timestamp, "value": value, "dimensions": {"origin": "hpcs.collector", "OS": message["os"]}}
                    yield metric
    
    def get_timestamp(self, message):
        if "collection_timestamp" in message:
            timestamp = message["collection_timestamp"]
        else:
            timestamp = time.gmtime()
        return timestamp
    