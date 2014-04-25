import calendar
import datetime
from copy import deepcopy
from mon_lib.mon_api import MonAPI
from mon_lib.mon_normalizer import MonNormalizer

discard = "DISCARD"
        
def emitter(payload, logger, config):
    logger.debug("Starting the mon_api.emitter")
    logger.debug("Payload ==> ", str(payload))
    config = config
    mon_api_config = config['MonApi']
    mon_api_url = mon_api_config['url']
    aggregate_metrics = mon_api_config['aggregate_metrics']
    mapping_file_path = mon_api_config['mapping_file']
    MonNormalizer(logger, mapping_file_path)
    host_tags = get_standard_dimensions(payload, config, logger)

    api = MonAPI(mon_api_config, logger)

    logger.debug('mon_api_http_emitter: attempting postback to ' + mon_api_url)
    metrics_list = []
    for agent_metric in payload:
        try:
            api_metric = get_api_metric(agent_metric, payload, host_tags, logger)
            if aggregate_metrics:
                metrics_list.extend(api_metric)
            else:
                api.post_metrics(api_metric)

            if len(api_metric) > 0:
                logger.debug("Sending metric to API: %s", str(api_metric))
            else:
                logger.debug("Discarding metric: %s", str(agent_metric))

        except Exception as ex:
            logger.exception("Error sending message to mon-api")

    if len(metrics_list) > 0:
        api.post_metrics(metrics_list)

def get_api_metric(agent_metric, payload, host_tags, logger):
    normalizer = MonNormalizer()
    timestamp = get_timestamp(payload)
    metrics_list = []
    dimensions = deepcopy(host_tags)
    name = MonNormalizer().normalize_name(agent_metric)
    if name != discard:
        value = payload[agent_metric]
        logger.debug("Agent Metric Name Received: " + str(name))
        logger.debug("Agent Metric Value Received: " + str(value))
        if isinstance(value, str):
            metric = {"name": normalizer.normalize_name(name), "timestamp": timestamp, "value": normalizer.encode(value), "dimensions": dimensions}
            metrics_list.append(metric)
        elif isinstance(value, dict):
            metrics_list.extend(process_dict(name, timestamp, value, host_tags))
        elif isinstance(value, list):
            metrics_list.extend(process_list(name, timestamp, value, host_tags, logger))
        elif isinstance(value, tuple):
            metrics_list.extend(process_list(name, timestamp, value, host_tags, logger))
        elif isinstance(value, int) or isinstance(value, float):
            metric = {"name": normalizer.normalize_name(name), "timestamp": timestamp, "value": value, "dimensions": dimensions}
            metrics_list.append(metric)
    return metrics_list

def get_timestamp(message):
    if "collection_timestamp" in message:
        timestamp = message["collection_timestamp"]
    elif "timestamp" in message:
        timestamp = message["timestamp"]
    else:
        timestamp = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
    return timestamp

def process_dict(name, timestamp, values, host_tags):
    metrics = []
    normalizer = MonNormalizer()
    if name == "ioStats":
        for key in values.iterkeys():
            return process_dict(key, timestamp, values[key], host_tags)
    else:
        for key in values.iterkeys():
            metric_name = normalizer.normalize_name(key)
            if metric_name != discard:
                dimensions = deepcopy(host_tags)
                dimensions.update({"device": normalizer.encode(name)})
                metric = {"name": metric_name, "timestamp": timestamp, "value": normalizer.encode(values[key]), "dimensions": dimensions}
                metrics.append(metric)
    return metrics

def process_list(name, timestamp, values, host_tags, logger):
    metrics = []
    normalizer = MonNormalizer()
    if name == "disk_usage" or name == "inodes":
        for item in values:
            if name != discard:
                dimensions = deepcopy(host_tags)
                dimensions.update({"device": normalizer.encode(item[0])})
                if len(item) >= 9:
                     dimensions.update({"mountpoint": normalizer.encode(item[8])})
                metric = {"name": name, "timestamp": timestamp, "value": normalizer.encode(item[4].rstrip("%")), "dimensions": dimensions}
                metrics.append(metric)
    elif name == "metrics":
        # These are metrics sent in a format we know about from checks
        for item in values:
            dimensions = deepcopy(host_tags)
            for name2 in item[3].iterkeys():
                 value2 = item[3][name2]
                 if name2 == discard or name2 == "type" or name2 == "interval" or value2 == None:
                     continue
                 if name2 == "tags":
                     dimensions.update(process_tags(value2))
                 else:
                     dimensions.update({normalizer.encode(name2) : normalizer.encode(value2)})
            metric_name = normalizer.normalize_name(item[0])
            if metric_name == discard:
                continue
            metric = {"name": metric_name, "timestamp": timestamp, "value": item[2], "dimensions": dimensions}
            metrics.append(metric)
    elif name == "series":
        # These are metrics sent in a format we know about from dogstatsd
        for item in values:
            dimensions = deepcopy(host_tags)
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
                    dimensions.update(process_tags(value2))
                 elif name2 == "metric":
                     metric_name = normalizer.normalize_name(value2)
                 else:
                     dimensions.update({normalizer.encode(name2) : normalizer.encode(value2)})
            if metric_name != discard:
                for point in points:
                    metric_timestamp = point[0]
                    metric_value = point[1]
                    metric = {"name": metric_name, "timestamp": metric_timestamp, "value": metric_value, "dimensions": dimensions}
                    metrics.append(metric)
    else:
        # We don't know what this metric list is.  Just add it as dimensions
        counter = 0
        dimensions = deepcopy(host_tags)
        logger.info("Found an unknown metric...")
        for item in values:
            dimensions.update({"Value" + str(counter) : item})
            counter+= 1
        metric = {"name": name, "timestamp": timestamp, "value": 0, "dimensions": dimensions}
        metrics.append(metric)
    return metrics

def process_tags(tags):
    # This will process tag strings in the format "name:value" and put them in a dictionary to be added as dimensions
    normalizer = MonNormalizer()
    processed_tags = {}
    # Metrics tags are a list of strings
    for tag in tags:
        if(tag.find(':') != -1):
            tag_parts = tag.split(':',1)
            name = normalizer.encode(tag_parts[0].strip())
            value = normalizer.encode(tag_parts[1].strip())
            if name == 'detail':
                chars = ['\\', '"']
                value = value.translate(None, ''.join(chars)).lstrip('{')
            processed_tags.update({name : value})
        else:
            processed_tags.update({normalizer.encode(tag) : normalizer.encode(tag)})
    return processed_tags

def get_standard_dimensions(payload, config, logger):
    normalizer = MonNormalizer()
    dimension_list = {}
    if "internalHostname" in payload:
        dimension_list.update({"hostname": normalizer.encode(payload["internalHostname"])})
    if "dimensions" in config:
        dimension_string = config["dimensions"]
        if dimension_string:
            logger.debug("Dimensions: " + str(dimension_string))
            dimensions = dimension_string.split(',')
            dimension_list.update(process_tags(dimensions))
    return dimension_list

