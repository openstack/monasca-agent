# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Redis checks.

"""
import re
import time

from monasca_agent.collector.checks import AgentCheck


class Redis(AgentCheck):
    db_key_pattern = re.compile(r'^db\d+')
    subkeys = ['keys', 'expires']
    GAUGE_KEYS = {
        # Append-only metrics
        'aof_last_rewrite_time_sec': 'redis.aof.last_rewrite_time',
        'aof_rewrite_in_progress': 'redis.aof.rewrite',
        'aof_current_size': 'redis.aof.size',
        'aof_buffer_length': 'redis.aof.buffer_length',

        # Network
        'connected_clients': 'redis.net.clients',
        'connected_slaves': 'redis.net.slaves',
        'rejected_connections': 'redis.net.rejected',

        # clients
        'blocked_clients': 'redis.clients.blocked',
        'client_biggest_input_buf': 'redis.clients.biggest_input_buf',
        'client_longest_output_list': 'redis.clients.longest_output_list',

        # Keys
        'evicted_keys': 'redis.keys.evicted',
        'expired_keys': 'redis.keys.expired',

        # stats
        'keyspace_hits': 'redis.stats.keyspace_hits',
        'keyspace_misses': 'redis.stats.keyspace_misses',
        'latest_fork_usec': 'redis.perf.latest_fork_usec',

        # pubsub
        'pubsub_channels': 'redis.pubsub.channels',
        'pubsub_patterns': 'redis.pubsub.patterns',

        # rdb
        'rdb_bgsave_in_progress': 'redis.rdb.bgsave',
        'rdb_changes_since_last_save': 'redis.rdb.changes_since_last',
        'rdb_last_bgsave_time_sec': 'redis.rdb.last_bgsave_time',

        # memory
        'mem_fragmentation_ratio': 'redis.mem.fragmentation_ratio',
        'used_memory': 'redis.mem.used',
        'used_memory_lua': 'redis.mem.lua',
        'used_memory_peak': 'redis.mem.peak',
        'used_memory_rss': 'redis.mem.rss',

        # replication
        'master_last_io_seconds_ago': 'redis.replication.last_io_seconds_ago',
        'master_sync_in_progress': 'redis.replication.sync',
        'master_sync_left_bytes': 'redis.replication.sync_left_bytes',
    }

    RATE_KEYS = {
        # cpu
        'used_cpu_sys': 'redis.cpu.sys',
        'used_cpu_sys_children': 'redis.cpu.sys_children',
        'used_cpu_user': 'redis.cpu.user',
        'used_cpu_user_children': 'redis.cpu.user_children',
    }

    def __init__(self, name, init_config, agent_config):
        AgentCheck.__init__(self, name, init_config, agent_config)
        self.connections = {}

    @staticmethod
    def get_library_versions():
        try:
            import redis

            version = redis.__version__
        except ImportError:
            version = "Not Found"
        except AttributeError:
            version = "Unknown"

        return {"redis": version}

    def _parse_dict_string(self, string, key, default):
        """Take from a more recent redis.py, parse_info.

        """
        try:
            for item in ','.split():
                k, v = item.rsplit('=', 1)
                if k == key:
                    try:
                        return int(v)
                    except ValueError:
                        return v
            return default
        except Exception:
            self.log.exception("Cannot parse dictionary string: %s" % string)
            return default

    @staticmethod
    def _generate_instance_key(instance):
        if 'unix_socket_path' in instance:
            return (instance.get('unix_socket_path'), instance.get('db'))
        else:
            return (instance.get('host'), instance.get('port'), instance.get('db'))

    def _get_conn(self, instance):
        import redis

        key = self._generate_instance_key(instance)
        if key not in self.connections:
            try:

                # Only send useful parameters to the redis client constructor
                list_params = ['host', 'port', 'db', 'password', 'socket_timeout',
                               'connection_pool', 'charset', 'errors', 'unix_socket_path']

                connection_params = dict((k, instance[k]) for k in list_params if k in instance)

                self.connections[key] = redis.Redis(**connection_params)

            except TypeError:
                raise Exception(
                    "You need a redis library that supports authenticated connections."
                    "Try sudo easy_install redis.")

        return self.connections[key]

    def _check_db(self, instance):
        conn = self._get_conn(instance)
        dimensions = self._set_dimensions(None, instance)

        if 'unix_socket_path' in instance:
            dimensions.update({'unix_socket_path': instance.get("unix_socket_path")})
        else:
            dimensions.update({'redis_host': instance.get('host')})
            dimensions.update({'redis_port': instance.get('port')})

        if instance.get('db') is not None:
            dimensions.update({'db': instance.get('db')})

        # Ping the database for info, and track the latency.
        start = time.time()
        try:
            info = conn.info()
        except ValueError:
            # This is likely a know issue with redis library 2.0.0
            # See https://github.com/DataDog/dd-agent/issues/374 for details
            import redis

            raise Exception(
                """Unable to run the info command. This is probably an issue with your version
                of the python-redis library.
                Minimum required version: 2.4.11
                Your current version: %s
                Please upgrade to a newer version by running sudo easy_install redis""" %
                redis.__version__)

        latency_ms = round((time.time() - start) * 1000, 2)
        self.gauge('redis.info.latency_ms', latency_ms, dimensions=dimensions)

        # Save the database statistics.
        db_dimensions = dimensions.copy()
        for key in info.keys():
            if self.db_key_pattern.match(key):
                db_dimensions.update({'redis_db': key})
                for subkey in self.subkeys:
                    # Old redis module on ubuntu 10.04 (python-redis 0.6.1) does not
                    # returns a dict for those key but a string: keys=3,expires=0
                    # Try to parse it (see lighthouse #46)
                    val = -1
                    try:
                        val = info[key].get(subkey, -1)
                    except AttributeError:
                        val = self._parse_dict_string(info[key], subkey, -1)
                    metric = '.'.join(['redis', subkey])
                    self.gauge(metric, val, dimensions=db_dimensions)

        # Save a subset of db-wide statistics
        [self.gauge(self.GAUGE_KEYS[k], info[k], dimensions=dimensions)
         for k in self.GAUGE_KEYS if k in info]
        [self.rate(self.RATE_KEYS[k], info[k], dimensions=dimensions)
         for k in self.RATE_KEYS if k in info]

        # Save the number of commands.
        self.rate('redis.net.commands', info['total_commands_processed'], dimensions=dimensions)

    def check(self, instance):
        try:
            import redis  # noqa
        except ImportError:
            raise Exception(
                'Python Redis Module can not be imported. Please check the installation'
                'instruction on the Datadog Website')

        if ("host" not in instance or "port" not in instance) \
                and "unix_socket_path" not in instance:
            raise Exception("You must specify a host/port couple or a unix_socket_path")
        self._check_db(instance)
