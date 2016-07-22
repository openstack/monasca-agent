# (C) Copyright 2015,2016 Hewlett Packard Enterprise Development Company LP

import re
import types

from monasca_agent.collector.checks import AgentCheck


# When running with pymongo < 2.0
# Not the full spec for mongo URIs -- just extract username and password
# http://www.mongodb.org/display/DOCS/connections6
mongo_uri_re = re.compile(r'mongodb://(?P<username>[^:@]+):(?P<password>[^:@]+)@.*')

DEFAULT_TIMEOUT = 10


class MongoDb(AgentCheck):

    GAUGES = [
        "indexCounters.btree.missRatio",
        "globalLock.ratio",
        "connections.current",
        "connections.available",
        "mem.resident",
        "mem.virtual",
        "mem.mapped",
        "cursors.totalOpen",
        "cursors.timedOut",
        "uptime",

        "stats.indexes",
        "stats.indexSize",
        "stats.objects",
        "stats.dataSize",
        "stats.storageSize",

        "replSet.health",
        "replSet.state",
        "replSet.replicationLag",
        "metrics.repl.buffer.count",
        "metrics.repl.buffer.maxSizeBytes",
        "metrics.repl.buffer.sizeBytes",
    ]

    RATES = [
        "indexCounters.btree.accesses",
        "indexCounters.btree.hits",
        "indexCounters.btree.misses",
        "opcounters.insert",
        "opcounters.query",
        "opcounters.update",
        "opcounters.delete",
        "opcounters.getmore",
        "opcounters.command",
        "asserts.regular",
        "asserts.warning",
        "asserts.msg",
        "asserts.user",
        "asserts.rollovers",
        "metrics.document.deleted",
        "metrics.document.inserted",
        "metrics.document.returned",
        "metrics.document.updated",
        "metrics.getLastError.wtime.num",
        "metrics.getLastError.wtime.totalMillis",
        "metrics.getLastError.wtimeouts",
        "metrics.operation.fastmod",
        "metrics.operation.idhack",
        "metrics.operation.scanAndOrder",
        "metrics.queryExecutor.scanned",
        "metrics.record.moves",
        "metrics.repl.apply.batches.num",
        "metrics.repl.apply.batches.totalMillis",
        "metrics.repl.apply.ops",
        "metrics.repl.network.bytes",
        "metrics.repl.network.getmores.num",
        "metrics.repl.network.getmores.totalMillis",
        "metrics.repl.network.ops",
        "metrics.repl.network.readersCreated",
        "metrics.repl.oplog.insert.num",
        "metrics.repl.oplog.insert.totalMillis",
        "metrics.repl.oplog.insertBytes",
        "metrics.ttl.deletedDocuments",
        "metrics.ttl.passes",
    ]

    METRICS = GAUGES + RATES

    def __init__(self, name, init_config, agent_config):
        AgentCheck.__init__(self, name, init_config, agent_config)
        self._last_state_by_server = {}

    @staticmethod
    def get_library_versions():
        try:
            import pymongo
            version = pymongo.version
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"pymongo": version}

    def check(self, instance):
        """Returns a dictionary that looks a lot like what's sent back by db.serverStatus().

        """
        if 'server' not in instance:
            self.log.warn("Missing 'server' in mongo config")
            return

        server = instance['server']

        ssl_params = {
            'ssl': instance.get('ssl', None),
            'ssl_keyfile': instance.get('ssl_keyfile', None),
            'ssl_certfile': instance.get('ssl_certfile', None),
            'ssl_cert_reqs': instance.get('ssl_cert_reqs', None),
            'ssl_ca_certs': instance.get('ssl_ca_certs', None)
        }

        for key, param in ssl_params.items():
            if param is None:
                del ssl_params[key]

        dimensions = self._set_dimensions({'server': server}, instance)

        try:
            from pymongo import Connection
        except ImportError:
            self.log.error(
                'mongo.yaml exists but pymongo module can not be imported. Skipping check.')
            raise Exception(
                'Python PyMongo Module can not be imported. Please check the installation instruction on the Datadog Website')

        try:
            from pymongo import uri_parser
            # Configuration a URL, mongodb://user:pass@server/db
            parsed = uri_parser.parse_uri(server)
        except ImportError:
            # uri_parser is pymongo 2.0+
            matches = mongo_uri_re.match(server)
            if matches:
                parsed = matches.groupdict()
            else:
                parsed = {}
        username = parsed.get('username')
        password = parsed.get('password')
        db_name = parsed.get('database')

        if not db_name:
            self.log.info('No MongoDB database found in URI. Defaulting to admin.')
            db_name = 'admin'

        do_auth = True
        if username is None or password is None:
            self.log.debug("Mongo: cannot extract username and password from config %s" % server)
            do_auth = False

        conn = Connection(server, network_timeout=DEFAULT_TIMEOUT,
                          **ssl_params)
        db = conn[db_name]
        if do_auth:
            if not db.authenticate(username, password):
                self.log.error("Mongo: cannot connect with config %s" % server)

        status = db["$cmd"].find_one({"serverStatus": 1})
        status['stats'] = db.command('dbstats')

        # Handle replica data, if any
        # See
        # http://www.mongodb.org/display/DOCS/Replica+Set+Commands#ReplicaSetCommands-replSetGetStatus
        try:
            data = {}

            replSet = db.command('replSetGetStatus')
            if replSet:
                primary = None
                current = None

                # find nodes: master and current node (ourself)
                for member in replSet.get('members'):
                    if member.get('self'):
                        current = member
                    if int(member.get('state')) == 1:
                        primary = member

                # If we have both we can compute a lag time
                if current is not None and primary is not None:
                    lag = current['optimeDate'] - primary['optimeDate']
                    # Python 2.7 has this built in, python < 2.7 don't...
                    if hasattr(lag, 'total_seconds'):
                        data['replicationLag'] = lag.total_seconds()
                    else:
                        data['replicationLag'] = (
                            lag.microseconds + (lag.seconds + lag.days * 24 * 3600) * 10 ** 6) / 10.0 ** 6

                if current is not None:
                    data['health'] = current['health']

                data['state'] = replSet['myState']
                status['replSet'] = data
        except Exception as e:
            if "OperationFailure" in repr(e) and "replSetGetStatus" in str(e):
                pass
            else:
                raise e

        # If these keys exist, remove them for now as they cannot be serialized
        try:
            status['backgroundFlushing'].pop('last_finished')
        except KeyError:
            pass
        try:
            status.pop('localTime')
        except KeyError:
            pass

        # Go through the metrics and save the values
        for m in self.METRICS:
            # each metric is of the form: x.y.z with z optional
            # and can be found at status[x][y][z]
            value = status
            try:
                for c in m.split("."):
                    value = value[c]
            except KeyError:
                continue

            # value is now status[x][y][z]
            assert type(value) in (types.IntType, types.LongType, types.FloatType)

            # Check if metric is a gauge or rate
            if m in self.GAUGES:
                m = self.normalize(m.lower(), 'mongodb')
                self.gauge(m, value, dimensions=dimensions)

            if m in self.RATES:
                m = self.normalize(m.lower(), 'mongodb') + "ps"
                self.rate(m, value, dimensions=dimensions)
