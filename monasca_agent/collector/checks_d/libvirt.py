#!/bin/env python

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Monasca Agent interface for libvirt metrics"""

import os
import stat
import time
import yaml

from calendar import timegm
from datetime import datetime
from distutils.version import LooseVersion
from monasca_agent.collector.virt import inspector
from monasca_agent.collector.checks import AgentCheck


class LibvirtCheck(AgentCheck):

    """Inherit Agent class and gather libvirt metrics"""

    def __init__(self, name, init_config, agent_config):
        AgentCheck.__init__(self, name, init_config, agent_config)
        self.instance_cache_file = "{0}/{1}".format(self.init_config.get('cache_dir'),
                                                    'libvirt_instances.yaml')
        self.metric_cache_file = "{0}/{1}".format(self.init_config.get('cache_dir'),
                                                  'libvirt_metrics.yaml')

    def _test_vm_probation(self, created):
        """Test to see if a VM was created within the probation period.

        Convert an ISO-8601 timestamp into UNIX epoch timestamp from now
        and compare that against configured vm_probation.  Return the
        number of seconds this VM will remain in probation.
        """
        dt = datetime.strptime(created, '%Y-%m-%dT%H:%M:%SZ')
        created_sec = (time.time() - timegm(dt.timetuple()))
        probation_time = self.init_config.get('vm_probation') - created_sec
        return int(probation_time)

    def _update_instance_cache(self):
        """Collect instance_id, project_id, and AZ for all instance UUIDs
        """
        # novaclient module versions were renamed in version 2.22
        try:
            from novaclient.v2 import client
        except ImportError:
            from novaclient.v1_1 import client

        id_cache = {}
        # Get a list of all instances from the Nova API
        nova_client = client.Client(self.init_config.get('admin_user'),
                                    self.init_config.get('admin_password'),
                                    self.init_config.get('admin_tenant_name'),
                                    self.init_config.get('identity_uri'),
                                    service_type="compute",
                                    region_name=self.init_config.get('region_name'))
        instances = nova_client.servers.list(search_opts={'all_tenants': 1})

        for instance in instances:
            inst_name = instance.__getattr__('OS-EXT-SRV-ATTR:instance_name')
            inst_az = instance.__getattr__('OS-EXT-AZ:availability_zone')
            id_cache[inst_name] = {'instance_uuid': instance.id,
                                   'hostname': instance.name,
                                   'zone': inst_az,
                                   'created': instance.created,
                                   'tenant_id': instance.tenant_id,
                                   'vcpus': nova_client.flavors.get(instance.flavor['id']).vcpus,
                                   'ram': nova_client.flavors.get(instance.flavor['id']).ram,
                                   'disk': nova_client.flavors.get(instance.flavor['id']).disk}
        id_cache['last_update'] = int(time.time())

        # Write the updated cache
        try:
            with open(self.instance_cache_file, 'w') as cache_yaml:
                yaml.safe_dump(id_cache, cache_yaml)
            if stat.S_IMODE(os.stat(self.instance_cache_file).st_mode) != 0600:
                os.chmod(self.instance_cache_file, 0600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".format(self.instance_cache_file, e))

        return id_cache

    def _load_instance_cache(self):
        """Load the cache if instance names to IDs.

           If the cache does not yet exist, return an empty one.
        """
        instance_cache = {}
        try:
            with open(self.instance_cache_file, 'r') as cache_yaml:
                instance_cache = yaml.safe_load(cache_yaml)

                # Is it time to force a refresh of this data?
                if self.init_config.get('nova_refresh') is not None:
                    time_diff = time.time() - instance_cache['last_update']
                    if time_diff > self.init_config.get('nova_refresh'):
                        self._update_instance_cache()
        except IOError:
            # The file may not exist yet, and that's OK.  Build it now.
            instance_cache = self._update_instance_cache()
            pass

        return instance_cache

    def _load_metric_cache(self):
        """Load the counter metrics from the previous collection iteration
        """
        metric_cache = {}
        try:
            with open(self.metric_cache_file, 'r') as cache_yaml:
                metric_cache = yaml.safe_load(cache_yaml)
        except IOError:
            # The file may not exist yet.
            pass

        return metric_cache

    def _update_metric_cache(self, metric_cache):
        try:
            with open(self.metric_cache_file, 'w') as cache_yaml:
                yaml.safe_dump(metric_cache, cache_yaml)
            if stat.S_IMODE(os.stat(self.metric_cache_file).st_mode) != 0600:
                os.chmod(self.metric_cache_file, 0600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".format(self.metric_cache_file, e))

    def check(self, instance):
        """Gather VM metrics for each instance"""

        # Load metric cache
        metric_cache = self._load_metric_cache()

        # Load the nova-obtained instance data cache
        instance_cache = self._load_instance_cache()

        # Build dimensions for both the customer and for operations
        dims_base = self._set_dimensions({'service': 'compute', 'component': 'vm'}, instance)

        # Define aggregate gauges, gauge name to metric name
        agg_gauges = {'vcpus': 'nova.vm.cpu.total_allocated',
                      'ram': 'nova.vm.mem.total_allocated_mb',
                      'disk': 'nova.vm.disk.total_allocated_gb'}
        agg_values = {}
        for gauge in agg_gauges.keys():
            agg_values[gauge] = 0

        insp = inspector.get_hypervisor_inspector()
        for inst in insp._get_connection().listAllDomains():
            # Verify that this instance exists in the cache.  Add if necessary.
            inst_name = inst.name()
            if inst_name not in instance_cache:
                instance_cache = self._update_instance_cache()
            if inst_name not in metric_cache:
                metric_cache[inst_name] = {}

            # Skip instances created within the probation period
            vm_probation_remaining = self._test_vm_probation(instance_cache.get(inst_name)['created'])
            if (vm_probation_remaining >= 0):
                self.log.info("Libvirt: {0} in probation for another {1} seconds".format(instance_cache.get(inst_name)['hostname'],
                                                                                         vm_probation_remaining))
                continue

            # Build customer dimensions
            dims_customer = dims_base.copy()
            dims_customer['resource_id'] = instance_cache.get(inst_name)['instance_uuid']
            dims_customer['zone'] = instance_cache.get(inst_name)['zone']
            # Add dimensions that would be helpful for operations
            dims_operations = dims_customer.copy()
            dims_operations['tenant_id'] = instance_cache.get(inst_name)['tenant_id']
            dims_operations['cloud_tier'] = 'overcloud'

            # Accumulate aggregate data
            for gauge in agg_gauges:
                if gauge in instance_cache.get(inst_name):
                    agg_values[gauge] += instance_cache.get(inst_name)[gauge]

            # CPU utilization percentage
            sample_time = float("{:9f}".format(time.time()))
            if 'cpu.time' in metric_cache[inst_name]:
                # I have a prior value, so calculate the rate & push the metric
                cpu_diff = insp.inspect_cpus(inst).time - metric_cache[inst_name]['cpu.time']['value']
                time_diff = sample_time - float(metric_cache[inst_name]['cpu.time']['timestamp'])
                # Convert time_diff to nanoseconds, and calculate percentage
                rate = (cpu_diff / (time_diff * 1000000000)) * 100

                self.gauge('cpu.utilization_perc', int(round(rate, 0)),
                           dimensions=dims_customer,
                           delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                           hostname=instance_cache.get(inst_name)['hostname'])
                self.gauge('vm.cpu.utilization_perc', int(round(rate, 0)),
                           dimensions=dims_operations)

            metric_cache[inst_name]['cpu.time'] = {'timestamp': sample_time,
                                                   'value': insp.inspect_cpus(inst).time}

            # Disk utilization
            for disk in insp.inspect_disks(inst):
                sample_time = time.time()
                disk_dimensions = {'device': disk[0].device}
                for metric in disk[1]._fields:
                    metric_name = "io.{0}".format(metric)
                    if metric_name not in metric_cache[inst_name]:
                        metric_cache[inst_name][metric_name] = {}

                    value = int(disk[1].__getattribute__(metric))
                    if disk[0].device in metric_cache[inst_name][metric_name]:
                        time_diff = sample_time - metric_cache[inst_name][metric_name][disk[0].device]['timestamp']
                        val_diff = value - metric_cache[inst_name][metric_name][disk[0].device]['value']
                        # Change the metric name to a rate, ie. "io.read_requests"
                        # gets converted to "io.read_ops_sec"
                        rate_name = "{0}_sec".format(metric_name.replace('requests', 'ops'))
                        # Customer
                        this_dimensions = disk_dimensions.copy()
                        this_dimensions.update(dims_customer)
                        self.gauge(rate_name, val_diff, dimensions=this_dimensions,
                                   delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                                   hostname=instance_cache.get(inst_name)['hostname'])
                        # Operations (metric name prefixed with "vm."
                        this_dimensions = disk_dimensions.copy()
                        this_dimensions.update(dims_operations)
                        self.gauge("vm.{0}".format(rate_name), val_diff,
                                   dimensions=this_dimensions)
                    # Save this metric to the cache
                    metric_cache[inst_name][metric_name][disk[0].device] = {
                        'timestamp': sample_time,
                        'value': value}

            # Network utilization
            for vnic in insp.inspect_vnics(inst):
                sample_time = time.time()
                vnic_dimensions = {'device': vnic[0].name}
                for metric in vnic[1]._fields:
                    metric_name = "net.{0}".format(metric)
                    if metric_name not in metric_cache[inst_name]:
                        metric_cache[inst_name][metric_name] = {}

                    value = int(vnic[1].__getattribute__(metric))
                    if vnic[0].name in metric_cache[inst_name][metric_name]:
                        time_diff = sample_time - metric_cache[inst_name][metric_name][vnic[0].name]['timestamp']
                        val_diff = value - metric_cache[inst_name][metric_name][vnic[0].name]['value']
                        # Change the metric name to a rate, ie. "net.rx_bytes"
                        # gets converted to "net.rx_bytes_sec"
                        rate_name = "{0}_sec".format(metric_name)
                        # Rename "tx" to "out" and "rx" to "in"
                        rate_name = rate_name.replace("tx", "out")
                        rate_name = rate_name.replace("rx", "in")
                        # Customer
                        this_dimensions = vnic_dimensions.copy()
                        this_dimensions.update(dims_customer)
                        self.gauge(rate_name, val_diff,
                                   dimensions=this_dimensions,
                                   delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                                   hostname=instance_cache.get(inst_name)['hostname'])
                        # Operations (metric name prefixed with "vm."
                        this_dimensions = vnic_dimensions.copy()
                        this_dimensions.update(dims_operations)
                        self.gauge("vm.{0}".format(rate_name), val_diff,
                                   dimensions=this_dimensions)
                    # Save this metric to the cache
                    metric_cache[inst_name][metric_name][vnic[0].name] = {
                        'timestamp': sample_time,
                        'value': value}

        # Save these metrics for the next collector invocation
        self._update_metric_cache(metric_cache)

        # Publish aggregate metrics
        for gauge in agg_gauges:
            self.gauge(agg_gauges[gauge], agg_values[gauge], dimensions=dims_base)
