#!/bin/env python

import datetime
import json
import logging
import math
import os
import re
import socket
import stat
import subprocess
import time

from copy import deepcopy
from monasca_agent.collector.checks import AgentCheck
from neutronclient.v2_0 import client as neutron_client

OVS_CMD = """\
%s --columns=name,external_ids,statistics,options \
--format=json --data=json list Interface\
"""

"""Monasca Agent interface for ovs router metrics"""


class OvsCheck(AgentCheck):

    """This check gathers open vswitch router metrics.
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config,
                            agent_config, instances=[{}])

        cache_dir = self.init_config.get('cache_dir')
        self.ctr_cache_file = os.path.join(cache_dir, 'ovs_metrics.json')
        self.rtr_cache_file = os.path.join(cache_dir, 'ovs_routers.json')

        self.use_bits = self.init_config.get('network_use_bits')
        self.check_router_ha = self.init_config.get('check_router_ha')
        self.ovs_cmd = OVS_CMD % self.init_config.get('ovs_cmd')

    def check(self, instance):
        time_start = time.time()
        interface_data = self._get_ovs_data()
        sample_time = float("{:9f}".format(time.time()))

        if not interface_data:
            #
            # No OVS data, nothing to do here.
            #
            return

        rtr_cache = self._load_router_cache()
        ctr_cache = self._load_counter_cache()

        dims_base = self._set_dimensions({'service': 'networking',
                                          'component': 'ovs'},
                                         instance)

        ifx_deltas = {}
        for ifx in interface_data:
            if not re.match(r"^qg-", ifx):
                continue

            if ifx not in ctr_cache:
                ctr_cache[ifx] = {}

            for metric_name, idx in self._get_metrics_map().iteritems():
                value = interface_data[ifx]['statistics'][idx]

                if metric_name in ctr_cache[ifx]:
                    cache_time = ctr_cache[ifx][metric_name]['timestamp']
                    time_diff = sample_time - float(cache_time)
                    try:
                        cache_value = ctr_cache[ifx][metric_name]['value']
                        val_diff = (value - cache_value) / time_diff
                    except ZeroDivisionError:
                        #
                        # Being extra safe here, in case we divide by zero
                        # just skip this reading with check below.
                        #
                        val_diff = -1

                    if val_diff < 0:
                        #
                        # Bad value, save current reading and skip
                        #
                        self.log.warn("Ignoring negative router sample for: "
                                      "{0} new value: {1} old value: {2}"
                                      .format(ifx, value,
                                              ctr_cache[ifx][metric_name]))
                        ctr_cache[ifx][metric_name] = {
                            'timestamp': sample_time,
                            'value': value}
                        continue

                    if ifx not in ifx_deltas:
                        uuid = interface_data[ifx]['external_ids']['iface-id']
                        ifx_deltas.update({ifx: {'port_uuid': uuid}})

                    if self.use_bits and 'bytes' in idx:
                        val_diff = val_diff * 8

                    ifx_deltas[ifx][idx] = val_diff

                #
                # Save the current counter for this metric to the cache
                # for the next time we wake up
                #
                ctr_cache[ifx][metric_name] = {
                    'timestamp': sample_time,
                    'value': value}

        #
        # Done collecting current rates and updating the cache file,
        # let's publish.
        #
        tried_one_update = False
        for ifx, value in ifx_deltas.iteritems():

            port_uuid = value['port_uuid']
            if port_uuid not in rtr_cache and not tried_one_update:
                #
                # Only attempt to update router cache
                # file for a missing port uuid once per wakeup.
                #
                tried_one_update = True
                log_msg = "port_uuid {0} not in router cache -- updating."
                self.log.info(log_msg.format(port_uuid))
                rtr_cache = self._update_router_cache()

            router_info = rtr_cache.get(port_uuid)

            if not router_info:
                log_msg = "port_uuid {0} not known to neutron -- ghost port?"
                self.log.error(log_msg.format(port_uuid))
                continue

            router_uuid = router_info['router_uuid']
            router_name = router_info['router_name']
            tenant_id = router_info['tenant_id']

            if not self._is_active_router(router_uuid):
                continue

            ifx_dimensions = {'resource_id': router_uuid,
                              'router_name': router_name}

            this_dimensions = dims_base.copy()
            this_dimensions.update(ifx_dimensions)
            for metric_name, idx in self._get_metrics_map().iteritems():
                # POST to customer project
                customer_dimensions = this_dimensions.copy()
                del customer_dimensions['hostname']
                self.gauge(metric_name, value[idx],
                           dimensions=customer_dimensions,
                           delegated_tenant=tenant_id,
                           hostname='SUPPRESS')

                # POST to operations project with "ovs." prefix
                ops_dimensions = this_dimensions.copy()
                ops_dimensions.update({'tenant_id': tenant_id})
                self.gauge("ovs.{0}".format(metric_name), value[idx],
                           dimensions=ops_dimensions)

        self._update_counter_cache(ctr_cache,
                                   math.ceil(time.time() - time_start))

    def _get_ovs_data(self):

        data_columns = ['name', 'external_ids', 'statistics', 'options']
        output = self._process_command(self.ovs_cmd)

        parsed_ovs_data = {}
        if not output:
            return parsed_ovs_data

        try:
            raw_ovs_json_data = json.loads(output)
        except ValueError:
            #
            # Make sure we got valid json
            #
            return {}

        # There are multiple lines returned, one for each device
        for line in raw_ovs_json_data['data']:

            ifx_data = {}
            ifx_name = None

            # There is one entry in each line for every data_column
            # print "Row:"
            for column_num in range(0, len(data_columns)):
                # Two choices here, it's either a value or a (sub) map
                # If it's a value it becomes a key in the hierarchy
                if line[column_num][0] == "map":
                    map_data = {}
                    for value in line[column_num][1]:
                        map_data.update({value[0]: value[1]})
                    ifx_data.update({data_columns[column_num]: map_data})
                else:
                    # In this specific case name (interface) is our main key
                    # How this would generalize, I don't know.
                    if data_columns[column_num] == "name":
                        ifx_name = line[column_num]

            # Put the interface data in the main dictionary,
            # ensuring we actually built something with the output.
            if ifx_name and ifx_data:
                parsed_ovs_data.update({ifx_name: ifx_data})

        return parsed_ovs_data

    def _get_os_info(self, uuid, all_data):
        for data in all_data:
            if data['id'] == uuid:
                return data
        return None

    def _get_neutron_client(self):

        username = self.init_config.get('admin_user')
        password = self.init_config.get('admin_password')
        tenant_name = self.init_config.get('admin_tenant_name')
        auth_url = self.init_config.get('identity_uri')
        region_name = self.init_config.get('region_name')

        return neutron_client.Client(username=username,
                                     password=password,
                                     tenant_name=tenant_name,
                                     auth_url=auth_url,
                                     region_name=region_name,
                                     endpoint_type='internalURL')

    def _run_command(self, command, input=None):
        self.log.debug("Executing command - {0}".format(command))

        errcode = None
        stdout = None
        stderr = None

        try:
            process = subprocess.Popen(command,
                                       shell=True,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE,
                                       stdin=subprocess.PIPE)
            stdout, stderr = process.communicate(input=input)
            errcode = process.returncode

            self.log.debug('errcode - {0}, stdout - {1}, stderr - {2}'.
                           format(errcode,
                                  stdout,
                                  stderr))

        except Exception:
            self.log.error("Failure while executing command - {0}".
                           format(command))

        return errcode, stdout, stderr

    def _process_command(self, command):
        """Runs the command and returns json output
        """
        errcode, stdout, stderr = self._run_command(command)
        cmd_output = ''
        if stdout:
            for line in stdout:
                cmd_output = cmd_output + line
        return cmd_output

    def _load_counter_cache(self):
        """Load the counter metrics from the previous collection iteration
        """
        ctr_cache = {}
        try:
            with open(self.ctr_cache_file, 'r') as cache_json:
                ctr_cache = json.load(cache_json)
        except (IOError, TypeError, ValueError):
            #
            # Couldn't load a cache file, or it's invalid json
            # and is corrupt.  By returning an empty dict we'll ensure
            # that the cache gets rebuilt.
            #
            self.log.warning("Counter cache missing or corrupt, rebuilding.")
            ctr_cache = {}

        return ctr_cache

    def _update_counter_cache(self, ctr_cache, run_time):
        # Remove migrated or deleted routers from the counter cache
        write_ctr_cache = deepcopy(ctr_cache)

        #
        # Grab the first metric name and see if it's in the cache.
        #
        metric_name = self._get_metrics_map().keys()[0]

        for ifx in ctr_cache:
            if metric_name not in ctr_cache[ifx]:
                self.log.info("Expiring old/empty {0} from cache".format(ifx))
                del(write_ctr_cache[ifx])
        try:
            with open(self.ctr_cache_file, 'w') as cache_json:
                json.dump(write_ctr_cache, cache_json)
            if stat.S_IMODE(os.stat(self.ctr_cache_file).st_mode) != 0o600:
                os.chmod(self.ctr_cache_file, 0o600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".
                           format(self.ctr_cache_file, e))

    def _get_metrics_map(self):
        if self.use_bits:
            measure = 'bits'
        else:
            measure = 'bytes'

        metrics_map = {"vrouter.out_%s_sec" % measure: "tx_bytes",
                       "vrouter.in_%s_sec" % measure: "rx_bytes",
                       "vrouter.in_packets_sec": "rx_packets",
                       "vrouter.out_packets_sec": "tx_packets",
                       "vrouter.in_dropped_sec": "rx_dropped",
                       "vrouter.out_dropped_sec": "tx_dropped",
                       "vrouter.in_errors_sec": "rx_errors",
                       "vrouter.out_errors_sec": "tx_errors"}

        return metrics_map

    def _update_router_cache(self):
        """Collect port_uuid, router_uuid, router_name, and tenant_id
        for all routers.
        """
        if not hasattr(self, 'neutron_client'):
            self.neutron_client = self._get_neutron_client()
        router_cache = {}

        try:
            self.log.debug("Retrieving Neutron port data")
            all_ports_data = self.neutron_client.list_ports()
            self.log.debug("Retrieving Neutron router data")
            all_routers_data = self.neutron_client.list_routers()
        except Exception as e:
            self.log.error("Unable to get neutron data: {0}".format(e))
            return router_cache

        all_ports_data = all_ports_data['ports']
        all_routers_data = all_routers_data['routers']

        for port_data in all_ports_data:
            port_uuid = port_data['id']
            router_uuid = port_data['device_id']
            router_info = self._get_os_info(router_uuid, all_routers_data)
            #
            # If we don't have router info for the port, let's not
            # cache it.
            #
            if not router_info:
                continue
            router_name = router_info['name']
            tenant_id = router_info['tenant_id']
            router_cache[port_uuid] = {'router_uuid': router_uuid,
                                       'router_name': router_name,
                                       'tenant_id': tenant_id}

        router_cache['last_update'] = int(time.time())

        # Write the updated cache
        try:
            with open(self.rtr_cache_file, 'w') as cache_json:
                json.dump(router_cache, cache_json)
            if stat.S_IMODE(os.stat(self.rtr_cache_file).st_mode) != 0o600:
                os.chmod(self.rtr_cache_file, 0o600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".
                           format(self.rtr_cache_file, e))
        return router_cache

    def _load_router_cache(self):
        """Load the cache map of router port uuids to router uuid, name,
        and tenant name.
        """
        router_cache = {}
        try:
            with open(self.rtr_cache_file, 'r') as cache_json:
                router_cache = json.load(cache_json)

                # Is it time to force a refresh of this data?
                if self.init_config.get('neutron_refresh') is not None:
                    time_diff = time.time() - router_cache['last_update']
                    if time_diff > self.init_config.get('neutron_refresh'):
                        self.log.warning("Time to update neutron cache file")
                        self._update_router_cache()
        except (IOError, TypeError, ValueError):
            # The file may not exist yet, or is corrupt.  Rebuild it now.
            self.log.warning("Router cache missing or corrupt, rebuilding.")
            router_cache = self._update_router_cache()

        return router_cache

    def _is_active_router(self, uuid):

        if not self.check_router_ha:
            #
            # We're not configured to check router ha -- let's not bother
            # making the additional neutron calls.
            #
            return True

        active_host = None
        local_host = socket.gethostname()
        try:
            if not hasattr(self, 'neutron_client'):
                self.neutron_client = self._get_neutron_client()
            result = self.neutron_client.list_l3_agent_hosting_routers(uuid)
        except Exception as e:
            #
            # Failed to get the hosting l3 agent, we'll default to calling
            # the router active.
            #
            self.log.error("Unable to get the hosting agent: {0}".format(e))
            return False
        for agent in result['agents']:
            if 'ha_state' not in agent.keys() or agent['ha_state'] is None:
                #
                # HA isn't enabled for this router,
                # so it's active if we've made it this far.
                #
                return True
            if agent['ha_state'] == 'active':
                active_host = agent['host']

        if not active_host:
            #
            # Somehow we didn't find the host above, assume
            # it is active.
            #
            return True

        if active_host != local_host:
            return False

        return True
