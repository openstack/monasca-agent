# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP

import socket
import time

from monasca_agent.collector.checks.services_checks import ServicesCheck
from monasca_agent.collector.checks.services_checks import Status


class BadConfException(Exception):
    pass


class TCPCheck(ServicesCheck):

    @staticmethod
    def _load_conf(instance):
        # Fetches the conf

        port = instance.get('port', None)
        timeout = float(instance.get('timeout', 10))
        response_time = instance.get('collect_response_time', False)
        socket_type = None
        try:
            port = int(port)
        except Exception:
            raise BadConfException("%s is not a correct port." % str(port))

        try:
            url = instance.get('host', None)
            split = url.split(":")
        except Exception:  # Would be raised if url is not a string
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8:  # It may then be a IP V6 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("%s is not a correct IPv6 address." % url)

            addr = url
            # It's a correct IP V6 address
            socket_type = socket.AF_INET6

        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                raise BadConfException("URL: %s is not a correct IPv4, IPv6 or hostname" % addr)

        return addr, port, socket_type, timeout, response_time

    def _check(self, instance):
        addr, port, socket_type, timeout, response_time = self._load_conf(instance)
        dimensions = self._set_dimensions(None, instance)
        if instance.get('host'):
            dimensions.update({'url': '%s:%s'.format(instance.get('host'), port)})
        start = time.time()
        try:
            self.log.debug("Connecting to %s %s" % (addr, port))
            sock = socket.socket(socket_type)
            try:
                sock.settimeout(timeout)
                sock.connect((addr, port))
            finally:
                sock.close()

        except socket.timeout as e:
            # The connection timed out because it took more time than the specified
            # value in the yaml config file
            length = int((time.time() - start) * 1000)
            self.log.info("%s:%s is DOWN (%s). Connection failed after %s ms" %
                          (addr, port, str(e), length))
            return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        except socket.error as e:
            length = int((time.time() - start) * 1000)
            if "timed out" in str(e):

                # The connection timed out because it took more time than the system tcp stack allows
                self.log.warning(
                    "The connection timed out because it took more time than the system tcp stack allows. You might want to change this setting to allow longer timeouts")
                self.log.info("System tcp timeout. Assuming that the checked system is down")
                return Status.DOWN, """Socket error: %s.
                 The connection timed out after %s ms because it took more time than the system tcp stack allows.
                 You might want to change this setting to allow longer timeouts""" % (str(e), length)
            else:
                self.log.info("%s:%s is DOWN (%s). Connection failed after %s ms" %
                              (addr, port, str(e), length))
                return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s:%s is DOWN (%s). Connection failed after %s ms" %
                          (addr, port, str(e), length))
            return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        if response_time:
            self.gauge('network.tcp.response_time', time.time() - start,
                       dimensions=dimensions)

        self.log.debug("%s:%s is UP" % (addr, port))
        return Status.UP, "UP"
