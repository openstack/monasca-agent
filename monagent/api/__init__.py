import json
import logging
import requests
from keystone import Keystone
from normalizer import MonNormalizer
from emitter import *

log = logging.getLogger(__name__)


class MonAPI(object):
    def __init__(self, mon_api_config):
        """
        Initialize Mon api connection.
        """
        self.url = mon_api_config['url']
        use_keystone = mon_api_config['use_keystone']
        keystone_url = mon_api_config['keystone_url']
        project_id = mon_api_config['project_id']
        user_id = mon_api_config['username']
        password = mon_api_config['password']
        self.aggregate_metrics = mon_api_config['aggregate_metrics']
        self.mapping_file = mon_api_config['mapping_file']
        if 'dimensions' in mon_api_config:
            self.dimensions = mon_api_config['dimensions']
        else:
            self.dimensions = None

        if use_keystone:
            self.keystone = Keystone(keystone_url)
            self.token = self.keystone.get_token_password_auth(user_id, password, project_id)
            self.headers = {'content-type': 'application/json',
                            'X-Auth-Token': self.token}
        else:
            self.headers = {'content-type': 'application/json',
                            'X-Tenant-Id': project_id}

    def _post(self, payload):
        try:
            data = json.dumps(payload)
            response = requests.post(self.url, data=data, headers=self.headers)
            if response:
                if 200 <= response.status_code <= 299:
                    # Good status from web service
                    log.debug("Message sent successfully: {0}".format(str(data)))
                elif 400 <= response.status_code <= 499:
                    # Good status from web service but some type of issue with the data
                    log.warn("Successful web service call but there were issues (Status: {0}, Status Message: {1}, Message Content: {1})".format(response.status_code, response.text, response.str(payload)))
                else:
                    # Not a good status
                    self.response.raise_for_status()
            else:
                log.error("Unable to connect to mon-api at " + self.url)

        except Exception:
            log.exception("Error sending message to mon-api: ")
        
        return

    def post_metrics(self, payload):
        #todo this is hack to just get things working as a standard emitter rather than a custom emitter
        log.debug("Starting the mon_api.emitter")
        log.debug("Payload ==> %s" % payload)
        MonNormalizer(log, self.mapping_file)
        host_tags = get_standard_dimensions(payload, self.dimensions, log)

        log.debug('mon_api_http_emitter: attempting postback to ' + self.url)
        metrics_list = []
        for agent_metric in payload:
            try:
                api_metric = get_api_metric(agent_metric, payload, host_tags, log)
                if self.aggregate_metrics:
                    metrics_list.extend(api_metric)
                else:
                    self._post(api_metric)

                if len(api_metric) > 0:
                    log.debug("Sending metric to API: %s", str(api_metric))
                else:
                    log.debug("Discarding metric: %s", str(agent_metric))

            except Exception as ex:
                log.exception("Error sending message to mon-api")

        if len(metrics_list) > 0:
            self._post(metrics_list)
