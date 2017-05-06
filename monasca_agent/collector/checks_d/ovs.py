#!/bin/env python

# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP
# Copyright 2017 Fujitsu LIMITED

from copy import deepcopy
import json
import math
import os
import re
import socket
import stat
import subprocess
import time

from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client

from monasca_agent.collector.checks import AgentCheck
import monasca_agent.collector.checks.utils as utils
from monasca_agent.common import keystone
from monasca_agent import version as ma_version

OVS_CMD = """\
%s --columns=name,external_ids,statistics,options \
--format=json --data=json list Interface\
"""
DPDK_PORT_PREFIX = 'vhu'
HEALTH_METRICS = ['tx_errors', 'rx_errors', 'tx_dropped', 'rx_dropped']

"""Monasca Agent interface for ovs router port and dhcp metrics"""


class OvsCheck(AgentCheck):

    """This check gathers open vswitch router and dhcp metrics.
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config,
                            agent_config, instances=[{}])

        cache_dir = self.init_config.get('cache_dir')
        self.ctr_cache_file = os.path.join(cache_dir, 'ovs_metrics.json')
        self.port_cache_file = os.path.join(cache_dir, 'ovs_ports.json')

        self.use_bits = self.init_config.get('network_use_bits')
        self.check_router_ha = self.init_config.get('check_router_ha')
        self.ovs_cmd = OVS_CMD % self.init_config.get('ovs_cmd')
        include_re = self.init_config.get('included_interface_re', None)
        self.use_absolute_metrics = self.init_config.get('use_absolute_metrics')
        self.use_rate_metrics = self.init_config.get('use_rate_metrics')
        self.use_health_metrics = self.init_config.get('use_health_metrics')
        self.publish_router_capacity = self.init_config.get('publish_router_capacity')
        if include_re is None:
            include_re = 'qg.*'
        else:
            include_re = include_re + '|' + 'qg.*'
        self.include_iface_re = re.compile(include_re)
        self.session = keystone.get_session(**self.init_config)

    def check(self, instance):
        time_start = time.time()
        interface_data = self._get_ovs_data()
        sample_time = float("{:9f}".format(time.time()))
        measure = self._get_measure()

        if not interface_data:
            #
            # No OVS data, nothing to do here.
            #
            return

        port_cache = self._load_port_cache()
        ctr_cache = self._load_counter_cache()

        dims_base = self._set_dimensions({'service': 'networking',
                                          'component': 'ovs'},
                                         instance)

        ifx_deltas = {}
        for ifx in interface_data:
            if not re.match(self.include_iface_re, ifx):
                self.log.debug("include_iface_re {0} does not match with "
                               "ovs-vsctl interface {1} ".format(self.include_iface_re.pattern, ifx))
                continue

            if ifx not in ctr_cache:
                ctr_cache[ifx] = {}
            for metric_name, idx in self._get_metrics_map(measure).items():
                interface_stats_key = self._get_interface_stats_key(idx, metric_name, measure, ifx)
                statistics_dict = interface_data[ifx]['statistics']
                value = statistics_dict[interface_stats_key] if interface_stats_key in statistics_dict else 0
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

                    if self.use_bits and 'bytes' in interface_stats_key:
                        val_diff = val_diff * 8

                    ifx_deltas[ifx][interface_stats_key] = val_diff

                #
                # Save the current counter for this metric to the cache
                # for the next time we wake up
                #
                ctr_cache[ifx][metric_name] = {
                    'timestamp': sample_time,
                    'value': value}
        # Done collecting current rates and updating the cache file,
        # let's publish.
        #
        tried_one_update = False
        host_router_max_bw = 0
        active_routers = 0
        for ifx, value in ifx_deltas.items():

            port_uuid = value['port_uuid']
            if port_uuid not in port_cache and not tried_one_update:
                #
                # Only attempt to update port cache
                # file for a missing port uuid once per wakeup.
                #
                tried_one_update = True
                log_msg = "port_uuid {0} not in port cache -- updating."
                self.log.info(log_msg.format(port_uuid))
                port_cache = self._update_port_cache()
            if not port_cache:
                self.log.error("port_cache is empty.")
                continue
            port_info = port_cache.get(port_uuid)
            if not port_info:
                log_msg = "port_uuid {0} not known to neutron -- ghost port?"
                self.log.error(log_msg.format(port_uuid))
                continue
            device_uuid = port_info['device_uuid']
            is_router_port = port_info['is_router_port']
            tenant_id = port_info['tenant_id']
            tenant_name = None
            if 'tenant_name' in port_info:
                tenant_name = port_info['tenant_name']
            if is_router_port and not self._is_active_router(device_uuid):
                continue
            if is_router_port:
                router_name = port_info['router_name']
                if not router_name:
                    log_msg = "Missing router name for router_uuid {0} -- skipping."
                    self.log.error(log_msg.format(device_uuid))
                    continue
                ifx_dimensions = {'resource_id': device_uuid,
                                  'port_id': port_uuid,
                                  'router_name': router_name}
                active_routers += 1
            else:
                ifx_dimensions = {'resource_id': device_uuid,
                                  'port_id': port_uuid}

            this_dimensions = dims_base.copy()
            this_dimensions.update(ifx_dimensions)
            customer_dimensions = this_dimensions.copy()
            del customer_dimensions['hostname']
            ops_dimensions = this_dimensions.copy()
            ops_dimensions.update({'tenant_id': tenant_id})
            if tenant_name:
                ops_dimensions.update({'tenant_name': tenant_name})

            for metric_name, idx in self._get_metrics_map(measure).items():
                # POST to customer project
                interface_stats_key = self._get_interface_stats_key(idx, metric_name, measure, ifx)
                if interface_stats_key not in value:
                    #
                    # If we've skipped a given metric above due to
                    # counter rollover/negative value, we won't have
                    # a value to publish for that metric this round.
                    #
                    continue
                if is_router_port:
                    metric_name_rate = "vrouter.{0}_sec".format(metric_name)
                    metric_name_abs = "vrouter.{0}".format(metric_name)
                else:
                    metric_name_rate = "vswitch.{0}_sec".format(metric_name)
                    metric_name_abs = "vswitch.{0}".format(metric_name)
                if not self.use_health_metrics and interface_stats_key in HEALTH_METRICS:
                        continue
                if self.use_rate_metrics:
                    self.gauge(metric_name_rate, value[interface_stats_key],
                               dimensions=customer_dimensions,
                               delegated_tenant=tenant_id,
                               hostname='SUPPRESS')
                    # POST to operations project with "ovs." prefix
                    self.gauge("ovs.{0}".format(metric_name_rate), value[interface_stats_key],
                               dimensions=ops_dimensions)
                if self.use_absolute_metrics:
                    statistics_dict = interface_data[ifx]['statistics']
                    abs_value = statistics_dict[interface_stats_key] if interface_stats_key in statistics_dict else 0
                    if self.use_bits and 'bytes' in interface_stats_key:
                        abs_value = abs_value * 8
                    # POST to customer
                    self.gauge(metric_name_abs, abs_value,
                               dimensions=customer_dimensions,
                               delegated_tenant=tenant_id,
                               hostname='SUPPRESS')
                    # POST to operations project
                    self.gauge("ovs.{0}".format(metric_name_abs), abs_value,
                               dimensions=ops_dimensions)

            self._publish_max_bw_metrics(port_info, customer_dimensions,
                                         ops_dimensions)
            host_router_max_bw += self._get_port_cache_max_bw(port_info)

        if host_router_max_bw > 0:
            self.gauge('ovs.vrouter.host_max_bw_kb', host_router_max_bw,
                       dimensions=dims_base)

        self.gauge('ovs.vrouter.active_routers', active_routers, dimensions=dims_base)
        self._update_counter_cache(ctr_cache,
                                   math.ceil(time.time() - time_start), measure)

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

    def _get_nova_client(self):
        region_name = self.init_config.get('region_name')
        endpoint_type = self.init_config.get("endpoint_type", "publicURL")
        nc = nova_client.Client(2, session=self.session,
                                endpoint_type=endpoint_type,
                                service_type="compute",
                                region_name=region_name,
                                client_name='monasca-agent[ovs]',
                                client_version=ma_version.version_string)

        return nc

    def _get_neutron_client(self):
        region_name = self.init_config.get('region_name')
        endpoint_type = self.init_config.get("endpoint_type", "publicURL")
        return neutron_client.Client(session=self.session,
                                     region_name=region_name,
                                     endpoint_type=endpoint_type,
                                     client_name='monasca-agent[ovs]',
                                     client_version=ma_version.version_string)

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

    def _update_counter_cache(self, ctr_cache, run_time, measure):
        # Remove migrated or deleted ports from the counter cache
        write_ctr_cache = deepcopy(ctr_cache)

        #
        # Grab the first metric name and see if it's in the cache.
        #
        metric_name = self._get_metrics_map(measure).keys()[0]

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

    def _get_metrics_map(self, measure):
        metrics_map = {"out_%s" % measure: "tx_bytes",
                       "in_%s" % measure: "rx_bytes",
                       "in_packets": "rx_packets",
                       "out_packets": "tx_packets",
                       "in_dropped": "rx_dropped",
                       "out_dropped": "tx_dropped",
                       "in_errors": "rx_errors",
                       "out_errors": "tx_errors"}

        return metrics_map

    def _update_port_cache(self):
        """Collect port_uuid, device_uuid, router_name, and tenant_id
        for all routers.
        """
        if not hasattr(self, 'neutron_client'):
            self.neutron_client = self._get_neutron_client()
        port_cache = {}

        try:
            self.log.debug("Retrieving Neutron port data")
            all_ports_data = self.neutron_client.list_ports()
            self.log.debug("Retrieving Neutron router data")
            all_routers_data = self.neutron_client.list_routers()
        except Exception as e:
            self.log.exception("Unable to get neutron data: %s", str(e))
            return port_cache

        all_ports_data = all_ports_data['ports']
        all_routers_data = all_routers_data['routers']

        #
        # Only make the keystone call to get the tenant list
        # if we are configured to publish tenant names.
        #
        if self.init_config.get('metadata') and 'tenant_name' in self.init_config.get('metadata'):
            tenants = utils.get_tenant_list(self.init_config, self.log)
        else:
            tenants = []

        for port_data in all_ports_data:
            port_uuid = port_data['id']
            device_uuid = port_data['device_id']
            router_info = self._get_os_info(device_uuid, all_routers_data)
            if router_info:
                tenant_id = router_info['tenant_id']
                is_router_port = True
                router_name = router_info['name']
            else:
                tenant_id = port_data['tenant_id']
                is_router_port = False
                router_name = ""
            port_cache[port_uuid] = {'device_uuid': device_uuid,
                                     'router_name': router_name,
                                     'is_router_port': is_router_port,
                                     'tenant_id': tenant_id}

            tenant_name = utils.get_tenant_name(tenants, tenant_id)
            if tenant_name:
                port_cache[port_uuid]['tenant_name'] = tenant_name

        port_cache = self._add_max_bw_to_port_cache(port_cache,
                                                    all_ports_data)
        port_cache['last_update'] = int(time.time())

        # Write the updated cache
        try:
            with open(self.port_cache_file, 'w') as cache_json:
                json.dump(port_cache, cache_json)
            if stat.S_IMODE(os.stat(self.port_cache_file).st_mode) != 0o600:
                os.chmod(self.port_cache_file, 0o600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".
                           format(self.port_cache_file, e))
        return port_cache

    def _get_port_cache_max_bw(self, port_info):
        if port_info['is_router_port'] and 'max_bw_kb' in port_info:
            return port_info['max_bw_kb']
        else:
            return 0

    def _publish_max_bw_metrics(self, port_info, cust_dims, ops_dims):
        max_bw_kb = self._get_port_cache_max_bw(port_info)

        if not self.publish_router_capacity or max_bw_kb == 0:
            return

        metric_name = 'vrouter.max_bw_kb'

        self.gauge(metric_name, max_bw_kb, dimensions=cust_dims,
                   delegated_tenant=ops_dims['tenant_id'],
                   hostname='SUPPRESS')

        self.gauge("ovs.{0}".format(metric_name), max_bw_kb,
                   dimensions=ops_dims)

    def _get_max_flavor_bw(self, flavor_keys):
        avg_bw = 0
        peak_bw = 0
        burst_bw = 0

        #
        # we'll sum inbound and outbound for the max possible throughput
        #
        avg_re = re.compile('quota:vif_.*bound_average')
        peak_re = re.compile('quota:vif_.*bound_peak')
        burst_re = re.compile('quota:vif_.*bound_burst')

        for key in flavor_keys:
            if re.match(avg_re, key):
                avg_bw += int(flavor_keys[key])
            elif re.match(peak_re, key):
                peak_bw += int(flavor_keys[key])
            elif re.match(burst_re, key):
                burst_bw += int(flavor_keys[key])

        return max(avg_bw, peak_bw, burst_bw)

    def _add_max_bw_to_port_cache(self, port_cache, all_ports_data):
        if not self.publish_router_capacity:
            return port_cache

        tmp_port_cache = deepcopy(port_cache)
        #
        # No need to do a flavor get multiple times
        # for the same flavor when rebuilding the cache.
        #
        flavor_cache = {}

        try:
            if not hasattr(self, 'nova_client'):
                self.nova_client = self._get_nova_client()

            for uuid in port_cache:
                router_max_bw_kb = 0
                port = port_cache[uuid]

                if not port['is_router_port']:
                    continue

                inst_ids = self._get_instance_ids(all_ports_data, port['device_uuid'])

                for instance_id in inst_ids:
                    instance = self.nova_client.servers.get(instance_id)
                    flavor_id = instance.flavor['id']
                    if flavor_id not in flavor_cache:
                        flavor = self.nova_client.flavors.get(instance.flavor['id'])
                        flavor_cache[flavor_id] = flavor.get_keys()
                    router_max_bw_kb += self._get_max_flavor_bw(flavor_cache[flavor_id])

                if router_max_bw_kb > 0:
                    tmp_port_cache[uuid]['max_bw_kb'] = router_max_bw_kb

        except Exception as e:
            msg = "Unable to get the nova instance and flavor info: {0}"
            self.log.error(msg.format(e))

        return tmp_port_cache

    def _get_instance_ids(self, ports, router_uuid):
        subnet_ids = self._get_port_ids(ports,
                                        'network:router_interface',
                                        [router_uuid],
                                        'device_id',
                                        'network_id')

        instance_ids = self._get_port_ids(ports,
                                          'compute:',
                                          subnet_ids,
                                          'network_id',
                                          'device_id')
        return instance_ids

    def _get_port_ids(self, ports, owner, uuids, match_field, return_field):
        return_uuids = []
        if len(uuids) == 0:
            return return_uuids

        for port in ports:
            if port[match_field] in uuids and owner in port['device_owner']:
                return_uuids.append(port[return_field])

        return return_uuids

    def _load_port_cache(self):
        """Load the cache map of router/dhcp port uuids to router uuid, name,
        and tenant name.
        """
        port_cache = {}
        try:
            with open(self.port_cache_file, 'r') as cache_json:
                port_cache = json.load(cache_json)

                # Is it time to force a refresh of this data?
                if self.init_config.get('neutron_refresh') is not None:
                    time_diff = time.time() - port_cache['last_update']
                    if time_diff > self.init_config.get('neutron_refresh'):
                        self.log.warning("Time to update neutron cache file")
                        self._update_port_cache()
        except (IOError, TypeError, ValueError):
            # The file may not exist yet, or is corrupt. Rebuild it now.
            self.log.warning("Port cache doesn't exists , rebuilding.")
            port_cache = self._update_port_cache()

        return port_cache

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

    def _get_interface_stats_key_for_dpdk(self, metric_name, measure):
        """"Get the interface statistics keys value based on type of port."""
        # The reason for swapping the metric_map value is in DPDK the tx counters
        # given by ovs-vsctl is actually rx counter and vice-versa.
        metrics_map = {"out_%s" % measure: "rx_bytes",
                       "in_%s" % measure: "tx_bytes",
                       "in_packets": "tx_packets",
                       "out_packets": "rx_packets",
                       "out_dropped": "tx_dropped",
                       "in_dropped": "rx_dropped",
                       "out_errors": "tx_errors",
                       "in_errors": "rx_errors"}
        return metrics_map[metric_name]

    def _get_measure(self):
        if self.use_bits:
            measure = 'bits'
        else:
            measure = 'bytes'
        return measure

    def _get_interface_stats_key(self, idx, metric_name, measure, interface):
        """Get the interface statistics key based on the interface."""
        if re.match(r"^" + DPDK_PORT_PREFIX, interface):
            # ovs-vsctl  does not give rx_dropped and tx_error statistics for DPDK ports
            # This check is for DPDK ports.
            return self._get_interface_stats_key_for_dpdk(metric_name,
                                                          measure)
        else:
            # For non DPDK ports return the same idx value.
            return idx
