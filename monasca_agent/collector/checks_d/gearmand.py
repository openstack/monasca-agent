# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

from monasca_agent.collector.checks import AgentCheck


class Gearman(AgentCheck):

    @staticmethod
    def get_library_versions():
        try:
            import gearman
            version = gearman.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"gearman": version}

    def _get_client(self, host, port):
        try:
            import gearman
        except ImportError:
            raise Exception(
                "Cannot import Gearman module. Check the instructions to install" +
                "this module at https://app.datadoghq.com/account/settings#integrations/gearman")

        self.log.debug("Connecting to gearman at address %s:%s" % (host, port))
        return gearman.GearmanAdminClient(["%s:%s" % (host, port)])

    def _get_metrics(self, client, dimensions):
        data = client.get_status()
        running = 0
        queued = 0
        workers = 0

        for stat in data:
            running += stat['running']
            queued += stat['queued']
            workers += stat['workers']

        unique_tasks = len(data)

        self.gauge("gearman.unique_tasks", unique_tasks, dimensions=dimensions)
        self.gauge("gearman.running", running, dimensions=dimensions)
        self.gauge("gearman.queued", queued, dimensions=dimensions)
        self.gauge("gearman.workers", workers, dimensions=dimensions)

        self.log.debug("running %d, queued %d, unique tasks %d, workers: %d" %
                       (running, queued, unique_tasks, workers))

    def _get_conf(self, instance):
        host = instance.get('server', None)
        port = instance.get('port', None)

        if host is None:
            self.log.warn("Host not set, assuming 127.0.0.1")
            host = "127.0.0.1"

        if port is None:
            self.log.warn("Port is not set, assuming 4730")
            port = 4730

        dimensions = self._set_dimensions(None, instance)

        return host, port, dimensions

    def check(self, instance):
        self.log.debug("Gearman check start")

        host, port, dimensions = self._get_conf(instance)
        client = self._get_client(host, port)
        self.log.debug("Connected to gearman")
        self._get_metrics(client, dimensions)
