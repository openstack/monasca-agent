#!/bin/env python

# (C) Copyright 2014, 2015 Hewlett Packard Enterprise Development Company LP
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
import subprocess
import time
import yaml

from calendar import timegm
from datetime import datetime
from distutils.version import LooseVersion
from monasca_agent.collector.checks import AgentCheck
from monasca_agent.collector.virt import inspector


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
        from novaclient import client

        id_cache = {}
        flavor_cache = {}
        # Get a list of all instances from the Nova API
        nova_client = client.Client(2, self.init_config.get('admin_user'),
                                    self.init_config.get('admin_password'),
                                    self.init_config.get('admin_tenant_name'),
                                    self.init_config.get('identity_uri'),
                                    endpoint_type='internalURL',
                                    service_type="compute",
                                    region_name=self.init_config.get('region_name'))
        instances = nova_client.servers.list(search_opts={'all_tenants': 1,
                                                          'host': self.hostname})

        for instance in instances:
            inst_name = instance.__getattr__('OS-EXT-SRV-ATTR:instance_name')
            inst_az = instance.__getattr__('OS-EXT-AZ:availability_zone')
            if instance.flavor['id'] in flavor_cache:
                inst_flavor = flavor_cache[instance.flavor['id']]
            else:
                inst_flavor = nova_client.flavors.get(instance.flavor['id'])
                flavor_cache[instance.flavor['id']] = inst_flavor
            id_cache[inst_name] = {'instance_uuid': instance.id,
                                   'hostname': instance.name,
                                   'zone': inst_az,
                                   'created': instance.created,
                                   'tenant_id': instance.tenant_id,
                                   'vcpus': inst_flavor.vcpus,
                                   'ram': inst_flavor.ram,
                                   'disk': inst_flavor.disk}
            # Try to add private_ip to id_cache[inst_name].  This may fail on ERROR'ed VMs.
            try:
                id_cache[inst_name]['private_ip'] = instance.addresses['private'][0]['addr']
            except KeyError:
                pass

        id_cache['last_update'] = int(time.time())

        # Write the updated cache
        try:
            with open(self.instance_cache_file, 'w') as cache_yaml:
                yaml.safe_dump(id_cache, cache_yaml)
            if stat.S_IMODE(os.stat(self.instance_cache_file).st_mode) != 0o600:
                os.chmod(self.instance_cache_file, 0o600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".format(self.instance_cache_file, e))

        return id_cache

    def _load_instance_cache(self):
        """Load the cache map of instance names to Nova data.

           If the cache does not yet exist or is damaged, (re-)build it.
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
        except (IOError, TypeError):
            # The file may not exist yet, or is corrupt.  Rebuild it now.
            self.log.warning("Instance cache missing or corrupt, rebuilding.")
            instance_cache = self._update_instance_cache()
            pass

        return instance_cache

    def _is_cache_corrupt(self, cache):
        """Verify that the cache contains a valid dictionary
        """
        if cache.__class__.__name__ != 'dict':
            self.log.warning("Corrupt metrics cache detected.  Will rebuild.")
            return True
        return False

    def _load_metric_cache(self):
        """Load the counter metrics from the previous collection iteration
        """
        metric_cache = {}
        try:
            with open(self.metric_cache_file, 'r') as cache_yaml:
                metric_cache = yaml.safe_load(cache_yaml)
            if self._is_cache_corrupt(metric_cache):
                metric_cache = {}
        except IOError:
            # The file may not exist yet.
            metric_cache = {}
            pass

        return metric_cache

    def _update_metric_cache(self, metric_cache):
        try:
            with open(self.metric_cache_file, 'w') as cache_yaml:
                yaml.safe_dump(metric_cache, cache_yaml)
            if stat.S_IMODE(os.stat(self.metric_cache_file).st_mode) != 0o600:
                os.chmod(self.metric_cache_file, 0o600)
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".format(self.metric_cache_file, e))

    def _inspect_network(self, insp, inst, instance_cache, metric_cache, dims_customer, dims_operations):
        """Inspect network metrics for an instance"""

        inst_name = inst.name()
        for vnic in insp.inspect_vnics(inst):
            sample_time = time.time()
            vnic_dimensions = {'device': vnic[0].name}
            for metric in vnic[1]._fields:
                metric_name = "net.{0}".format(metric)
                if metric_name not in metric_cache[inst_name]:
                    metric_cache[inst_name][metric_name] = {}

                value = int(vnic[1].__getattribute__(metric))
                if vnic[0].name in metric_cache[inst_name][metric_name]:
                    val_diff = value - metric_cache[inst_name][metric_name][vnic[0].name]['value']
                    if val_diff < 0:
                        # Bad value, save current reading and skip
                        self.log.warn("Ignoring negative network sample for: "
                                      "{0} new value: {1} old value: {2}"
                                      .format(inst_name, value,
                                              metric_cache[inst_name][metric_name][vnic[0].name]['value']))
                        metric_cache[inst_name][metric_name][vnic[0].name] = {
                            'timestamp': sample_time,
                            'value': value}
                        continue
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

    def _inspect_cpu(self, insp, inst, instance_cache, metric_cache, dims_customer, dims_operations):
        """Inspect cpu metrics for an instance"""

        inst_name = inst.name()
        sample_time = float("{:9f}".format(time.time()))
        if 'cpu.time' in metric_cache[inst_name]:
            # I have a prior value, so calculate the rate & push the metric
            cpu_diff = insp.inspect_cpus(inst).time - metric_cache[inst_name]['cpu.time']['value']
            time_diff = sample_time - float(metric_cache[inst_name]['cpu.time']['timestamp'])
            # Convert time_diff to nanoseconds, and calculate percentage
            rate = (cpu_diff / (time_diff * 1000000000)) * 100
            if rate < 0:
                # Bad value, save current reading and skip
                self.log.warn("Ignoring negative CPU sample for: "
                              "{0} new cpu time: {1} old cpu time: {2}"
                              .format(inst_name, insp.inspect_cpus(inst).time,
                                      metric_cache[inst_name]['cpu.time']['value']))
                metric_cache[inst_name]['cpu.time'] = {'timestamp': sample_time,
                                                       'value': insp.inspect_cpus(inst).time}
                return

            self.gauge('cpu.utilization_perc', int(round(rate, 0)),
                       dimensions=dims_customer,
                       delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                       hostname=instance_cache.get(inst_name)['hostname'])
            self.gauge('vm.cpu.utilization_perc', int(round(rate, 0)),
                       dimensions=dims_operations)

        metric_cache[inst_name]['cpu.time'] = {'timestamp': sample_time,
                                               'value': insp.inspect_cpus(inst).time}

    def _inspect_disks(self, insp, inst, instance_cache, metric_cache, dims_customer, dims_operations):
        """Inspect disk metrics for an instance"""

        inst_name = inst.name()
        for disk in insp.inspect_disks(inst):
            sample_time = time.time()
            disk_dimensions = {'device': disk[0].device}
            for metric in disk[1]._fields:
                metric_name = "io.{0}".format(metric)
                if metric_name not in metric_cache[inst_name]:
                    metric_cache[inst_name][metric_name] = {}

                value = int(disk[1].__getattribute__(metric))
                if disk[0].device in metric_cache[inst_name][metric_name]:
                    val_diff = value - metric_cache[inst_name][metric_name][disk[0].device]['value']
                    if val_diff < 0:
                        # Bad value, save current reading and skip
                        self.log.warn("Ignoring negative disk sample for: "
                                      "{0} new value: {1} old value: {2}"
                                      .format(inst_name, value,
                                              metric_cache[inst_name][metric_name][disk[0].device]['value']))
                        metric_cache[inst_name][metric_name][disk[0].device] = {
                            'timestamp': sample_time,
                            'value': value}
                        continue
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

            # Build customer dimensions
            try:
                dims_customer = dims_base.copy()
                dims_customer['resource_id'] = instance_cache.get(inst_name)['instance_uuid']
                dims_customer['zone'] = instance_cache.get(inst_name)['zone']
                # Add dimensions that would be helpful for operations
                dims_operations = dims_customer.copy()
                dims_operations['tenant_id'] = instance_cache.get(inst_name)['tenant_id']
                # Remove customer 'hostname' dimension, this will be replaced by the VM name
                del(dims_customer['hostname'])
            except TypeError:
                # Nova can potentially get into a state where it can't see an
                # instance, but libvirt can.  This would cause TypeErrors as
                # incomplete data is cached for this instance.  Log and skip.
                self.log.error("{0} is not known to nova after instance cache update -- skipping this ghost VM.".format(inst_name))
                continue

            # Skip instances that are inactive
            if inst.isActive() == 0:
                detail = 'Instance is not active'
                self.gauge('host_alive_status', 2, dimensions=dims_customer,
                           delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                           hostname=instance_cache.get(inst_name)['hostname'],
                           value_meta={'detail': detail})
                self.gauge('vm.host_alive_status', 2, dimensions=dims_operations,
                           value_meta={'detail': detail})
                continue
            if inst_name not in metric_cache:
                metric_cache[inst_name] = {}

            # Skip instances created within the probation period
            vm_probation_remaining = self._test_vm_probation(instance_cache.get(inst_name)['created'])
            if (vm_probation_remaining >= 0):
                self.log.info("Libvirt: {0} in probation for another {1} seconds".format(instance_cache.get(inst_name)['hostname'].encode('utf8'),
                                                                                         vm_probation_remaining))
                continue

            # Test instance's general responsiveness (ping check) if so configured
            if self.init_config.get('ping_check') and 'private_ip' in instance_cache.get(inst_name):
                detail = 'Ping check OK'
                ping_cmd = self.init_config.get('ping_check').split()
                ping_cmd.append(instance_cache.get(inst_name)['private_ip'])
                with open(os.devnull, "w") as fnull:
                    try:
                        res = subprocess.call(ping_cmd,
                                              stdout=fnull,
                                              stderr=fnull)
                        if res > 0:
                            detail = 'Host failed ping check'
                        self.gauge('host_alive_status', res, dimensions=dims_customer,
                                   delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                                   hostname=instance_cache.get(inst_name)['hostname'],
                                   value_meta={'detail': detail})
                        self.gauge('vm.host_alive_status', res, dimensions=dims_operations,
                                   value_meta={'detail': detail})
                        # Do not attempt to process any more metrics for offline hosts
                        if res > 0:
                            continue
                    except OSError as e:
                        self.log.warn("OS error running '{0}' returned {1}".format(ping_cmd, e))

            # Skip the remainder of the checks if ping_only is True in the config
            if self.init_config.get('ping_only'):
                continue

            # Accumulate aggregate data
            for gauge in agg_gauges:
                if gauge in instance_cache.get(inst_name):
                    agg_values[gauge] += instance_cache.get(inst_name)[gauge]

            self._inspect_cpu(insp, inst, instance_cache, metric_cache, dims_customer, dims_operations)
            self._inspect_disks(insp, inst, instance_cache, metric_cache, dims_customer, dims_operations)
            self._inspect_network(insp, inst, instance_cache, metric_cache, dims_customer, dims_operations)

            # Memory utilizaion
            # (req. balloon driver; Linux kernel param CONFIG_VIRTIO_BALLOON)
            try:
                mem_metrics = {'mem.free_mb': float(inst.memoryStats()['unused']) / 1024,
                               'mem.swap_used_mb': float(inst.memoryStats()['swap_out']) / 1024,
                               'mem.total_mb': float(inst.memoryStats()['available'] - inst.memoryStats()['unused']) / 1024,
                               'mem.used_mb': float(inst.memoryStats()['available'] - inst.memoryStats()['unused']) / 1024,
                               'mem.free_perc': float(inst.memoryStats()['unused']) / float(inst.memoryStats()['available']) * 100}
                for name in mem_metrics:
                    self.gauge(name, mem_metrics[name], dimensions=dims_customer,
                               delegated_tenant=instance_cache.get(inst_name)['tenant_id'],
                               hostname=instance_cache.get(inst_name)['hostname'])
                    self.gauge("vm.{0}".format(name), mem_metrics[name],
                               dimensions=dims_operations)
            except KeyError:
                self.log.debug("Balloon driver not active/available on guest {0} ({1})".format(inst_name,
                                                                                               instance_cache.get(inst_name)['hostname']))

        # Save these metrics for the next collector invocation
        self._update_metric_cache(metric_cache)

        # Publish aggregate metrics
        for gauge in agg_gauges:
            self.gauge(agg_gauges[gauge], agg_values[gauge], dimensions=dims_base)
