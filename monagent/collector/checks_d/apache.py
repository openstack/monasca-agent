import urllib2

from monagent.collector.checks import AgentCheck
from monagent.collector.checks.utils import add_basic_auth
from monagent.common.util import headers


class Apache(AgentCheck):

    """Tracks basic connection/requests/workers metrics

    See http://httpd.apache.org/docs/2.2/mod/mod_status.html for more details
    """
    GAUGES = {
        'IdleWorkers': 'apache.performance.idle_workers',
        'BusyWorkers': 'apache.performance.busy_workers',
        'CPULoad': 'apache.performance.cpu_load',
        'Uptime': 'apache.performance.uptime',
        'Total kBytes': 'apache.net.bytes',
        'Total Accesses': 'apache.net.hits',
    }

    RATES = {
        'Total kBytes': 'apache.net.bytes_per_s',
        'Total Accesses': 'apache.net.request_per_s'
    }

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config, agent_config, instances)
        self.assumed_url = {}

    def check(self, instance):
        if 'apache_status_url' not in instance:
            raise Exception("Missing 'apache_status_url' in Apache config")

        url = self.assumed_url.get(instance['apache_status_url'], instance['apache_status_url'])

        dimensions = instance.get('dimensions', {})
        req = urllib2.Request(url, None, headers(self.agent_config))
        if 'apache_user' in instance and 'apache_password' in instance:
            add_basic_auth(req, instance['apache_user'], instance['apache_password'])
        request = urllib2.urlopen(req)
        response = request.read()

        metric_count = 0
        # Loop through and extract the numerical values
        for line in response.split('\n'):
            values = line.split(': ')
            if len(values) == 2:  # match
                metric, value = values
                try:
                    value = float(value)
                except ValueError:
                    continue

                # Special case: kBytes => bytes
                if metric == 'Total kBytes':
                    value *= 1024

                # Send metric as a gauge, if applicable
                if metric in self.GAUGES:
                    metric_count += 1
                    metric_name = self.GAUGES[metric]
                    self.gauge(metric_name, value, dimensions=dimensions)

                # Send metric as a rate, if applicable
                if metric in self.RATES:
                    metric_count += 1
                    metric_name = self.RATES[metric]
                    self.rate(metric_name, value, dimensions=dimensions)

        if metric_count == 0:
            if self.assumed_url.get(
                    instance['apache_status_url'], None) is None and url[-5:] != '?auto':
                self.assumed_url[instance['apache_status_url']] = '%s?auto' % url
                self.warning("Assuming url was not correct. Trying to add ?auto suffix to the url")
                self.check(instance)
            else:
                raise Exception(
                    "No metrics were fetched for this instance. Make sure that %s is the proper url." %
                    instance['apache_status_url'])

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('apache_status_url'):
            return False

        return {
            'instances': [{'apache_status_url': agentConfig.get('apache_status_url')}]
        }
