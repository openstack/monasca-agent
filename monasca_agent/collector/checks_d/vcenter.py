# (C) Copyright 2016-2017 Hewlett Packard Enterprise Development LP
"""VCenter Only.

Generic VCenter check. This check allows you to specify particular metrics that
you want from vCenter in your configuration.
"""

import json
import logging as log
from monasca_agent.collector.checks import AgentCheck
from monasca_agent.common.config import Config
from oslo_vmware import api
from oslo_vmware import vim_util
import requests
import traceback

CLUSTER_COMPUTE_PROPERTIES = ["name", "host", "datastore"]
CLUSTER_HOST_PROPERTIES = ['runtime.connectionState',
                           'runtime.inMaintenanceMode',
                           'summary.hardware.numCpuThreads',
                           'summary.hardware.memorySize',
                           'summary.hardware.cpuMhz']
CLUSTER_PERF_COUNTERS = [
    "cpu.usagemhz.average",
    "cpu.totalmhz.average",
    "mem.usage.average",
    "mem.consumed.average",
    "mem.totalmb.average"]
STORAGE_VOLUME_PROPERTIES = ["host",
                             "summary.capacity",
                             "summary.freeSpace",
                             "summary.name",
                             "summary.multipleHostAccess",
                             "summary.accessible",
                             "summary.maintenanceMode",
                             "summary.type"]

CPU_TOTAL_MHZ = "vcenter.cpu.total_mhz"
CPU_USED_MHZ = "vcenter.cpu.used_mhz"
CPU_USED_PERCENT = "vcenter.cpu.used_perc"
CPU_TOTAL_LOGICAL_CORES = "vcenter.cpu.total_logical_cores"
MEMORY_TOTAL_MB = "vcenter.mem.total_mb"
MEMORY_USED_MB = "vcenter.mem.used_mb"
MEMORY_USED_PERCENT = "vcenter.mem.used_perc"
DISK_TOTAL_SPACE_MB = "vcenter.disk.total_space_mb"
DISK_TOTAL_USED_SPACE_MB = "vcenter.disk.total_used_space_mb"
DISK_TOTAL_USED_SPACE_PERCENT = "vcenter.disk.total_used_space_perc"

PERF_MANAGER_TYPE = "PerformanceManager"
PERF_RESOURCE = 'ClusterResource'
NUM_SAMPLES = 15
SAMPLE_RATE = 300
ALLOWED_DATASTORE_TYPES = ['VMFS', 'NFS']


class VCenterCheck(AgentCheck):

    def __init__(self, name, init_config, agent_config):
        AgentCheck.__init__(self, name, init_config, agent_config)
        self._max_objects = 1000
        self.session = None
        self.is_new_session = True
        self._resource_moid_dict = {}

    def stop(self):
        """To be executed when the agent is being stopped to clean resources.
        """
        if self.session is not None:
            self.session.logout()
            self.session = None
            self.is_new_session = True

    def _propset_dict(self, propset):
        """Turns a propset list into a dictionary

        PropSet is an optional attribute on ObjectContent objects
        that are returned by the VMware API.
        :param propset: a property 'set' from ObjectContent
        :return: dictionary representing property set
        """
        if propset is None:
            return {}
        return {prop.name: prop.val for prop in propset}

    def _get_api_session(self):
        api_session = api.VMwareAPISession(
            self.vcenter_ip,
            self.user,
            self.password,
            3,  # retry count
            0.5,  # task_poll_interval
            port=self.port,
            scheme="https")
        return api_session

    def _find_entity_mor(self, entity_list, entity_name):
        for object_contents in entity_list:
            for obj_content in object_contents[1]:
                for dyn_props in obj_content.propSet:
                    if dyn_props.val == entity_name.decode('utf-8'):
                        return obj_content

    def _get_resource_dict_by_name(self, resource_name):
        """Return moid from the specified resource"""
        self._get_cluster_info_dict()
        self.log.debug("Loaded MORs for clusters %s" %
                       str(self._resource_moid_dict.keys()))
        return self._resource_moid_dict.get(resource_name)

    def _build_resource_dict(self, object_content):
        """Method to build the resource dictionary. Cluster_name is the key,
        and its host and datastore names are the values
        {'cluster_name': {
            'moid': 'cluster1',
            'host': ['h1', 'h2'],
            'datastore': ['ds1', 'ds2']
            }
        }
        """
        cluster_moid = str(object_content.obj.value)
        # extract host and datastore names
        host_names = []
        datastore_names = []
        dict_key = None
        propSet = object_content.propSet
        for dynamic_prop in propSet:
            mor_array = dynamic_prop.val
            if dynamic_prop.name == 'name':
                dict_key = dynamic_prop.val
            else:
                for obj in mor_array:
                    for mor in obj[1]:
                        if dynamic_prop.name == 'datastore':
                            datastore_names.append(str(mor.value))
                        elif dynamic_prop.name == 'host':
                            host_names.append(str(mor.value))
        if dict_key:
            self._resource_moid_dict[str(dict_key)] = {
                'moid': cluster_moid,
                'host': host_names,
                'datastore': datastore_names,
            }

    def _get_cluster_info_dict(self):
        """Load configured cluster moids from the vCenter"""
        self.log.debug("Inside _get_cluster_info_dict")
        if self.session is None:
            self.session = self._get_api_session()
        result = self.session.invoke_api(vim_util,
                                         "get_objects",
                                         self.session.vim,
                                         "ClusterComputeResource",
                                         self._max_objects,
                                         CLUSTER_COMPUTE_PROPERTIES)
        for name in self.clusters:
            mor = self._find_entity_mor(result, name)
            if mor:
                self._build_resource_dict(mor)

    def _get_sample(self, samples, counter_name, is_summation=False):
            res = 0
            num_samples = 0

            for cn in samples:
                if cn.startswith(counter_name):
                    vals = samples[cn]
                    if vals:
                        for val in vals:
                            i_val = int(val)
                            if i_val != -1:
                                res += i_val
                                num_samples += 1

            if not is_summation and num_samples:
                res /= num_samples

            return res

    def _get_shared_datastores(self, datastore_stats, managed_cluster):
        """Method to find the shared datastores associated with the cluster
        Also handles cluster having single host with a non-shared datastore.
        """
        shared_datastores_ids = []
        res_dict = self._get_resource_dict_by_name(managed_cluster)
        host_set = set(res_dict.get('host'))
        for object_contents in datastore_stats:
            for object_content in object_contents[1]:
                ds_mor = object_content.obj.value
                datastore_host_ids = []
                if ds_mor in res_dict.get('datastore'):
                    propSets = object_content.propSet
                    for propSet in propSets:
                        if propSet.name == 'host':
                            ds_hm_array = propSet.val
                            host_mounts = ds_hm_array[0]
                            for host_mount in host_mounts:
                                datastore_host_ids.append(host_mount.key.value)
                    if host_set.issubset(set(datastore_host_ids)):
                        shared_datastores_ids.append(ds_mor)
                    self.log.debug("Cluster host list ==" + str(host_set))
                    self.log.debug("Datastore host list ==" +
                                   str(datastore_host_ids))
        self.log.debug("shared_datastores_ids==" +
                       str(shared_datastores_ids))
        return shared_datastores_ids

    def _is_valid_datastore(self, propSets):
        propdict = self._propset_dict(propSets)
        return (propdict.get('summary.accessible') and
                (propdict.get('summary.maintenanceMode') is None or
                 propdict.get('summary.maintenanceMode') == 'normal') and
                propdict['summary.type'] in ALLOWED_DATASTORE_TYPES)

    def _process_storage_data(self, datastore_stats, managed_cluster):
        shared_ds = self._get_shared_datastores(datastore_stats,
                                                managed_cluster)
        capacity = 0L
        freeSpace = 0L
        self.log.info("Polling for the datastores: " + str(shared_ds))
        for object_contents in datastore_stats:
            for object_content in object_contents[1]:
                ds_mor = object_content.obj.value
                if ds_mor in shared_ds:
                    propSets = object_content.propSet
                    if self._is_valid_datastore(propSets):
                        for propSet in propSets:
                            if propSet.name == 'summary.capacity':
                                self.log.debug("Calculating capacity "
                                               "of datastore: %s in cluster: "
                                               "%s" %
                                               (ds_mor, managed_cluster))
                                capacity += long(propSet.val)
                            elif propSet.name == 'summary.freeSpace':
                                self.log.debug("Calculating freeSpace of "
                                               "datastore: %s in cluster: %s"
                                               % (ds_mor, managed_cluster))
                                freeSpace += long(propSet.val)
        usedSpace = capacity - freeSpace
        self.log.debug("Total capacity:" + str(capacity) +
                       " used:" + str(usedSpace) + " free:" + str(freeSpace))
        return (capacity, usedSpace)

    def _get_properties_for_a_collection_of_objects(self, vim, type, obj_list,
                                                    properties):
        """Gets the list of properties for the collection of
        objects of the type specified.
        """
        client_factory = vim.client.factory
        if len(obj_list) == 0:
            return []
        prop_spec = vim_util.build_property_spec(client_factory,
                                                 type,
                                                 properties)
        lst_obj_specs = []
        for obj in obj_list:
            lst_obj_specs.append(vim_util.build_object_spec(
                client_factory,
                obj, []))
        prop_filter_spec = vim_util.build_property_filter_spec(client_factory,
                                                               [prop_spec],
                                                               lst_obj_specs)
        options = client_factory.create('ns0:RetrieveOptions')
        options.maxObjects = self._max_objects
        return vim.RetrievePropertiesEx(
            vim.service_content.propertyCollector,
            specSet=[prop_filter_spec],
            options=options)

    def _is_valid_host(self, propSets):
        propdict = self._propset_dict(propSets)
        return ((propdict.get('runtime.inMaintenanceMode') is not True) and
                propdict.get('runtime.connectionState') == 'connected')

    def _process_host_data(self, host_stats, managed_cluster):
        shared_hosts = self._find_entity_mor(host_stats, managed_cluster)
        cluster_hosts_data = {'numCpuThreads': 0,
                              'memorySizeMb': 0,
                              'cpuMhz': 0}
        self.log.debug("Polling for the hosts: %s" % (str(shared_hosts)))
        if shared_hosts:
            propSets = shared_hosts.propSet
            for propSet in propSets:
                if propSet.name == 'host':
                    host_ret = propSet.val
                    host_mors = host_ret.ManagedObjectReference
        if host_mors:
            method_call = '_get_properties_for_a_collection_of_objects'
            result = self.session.invoke_api(self,
                                             method_call,
                                             self.session.vim,
                                             "HostSystem",
                                             host_mors,
                                             CLUSTER_HOST_PROPERTIES)
        for obj_contents in result:
            for obj_content in obj_contents[1]:
                propSets = obj_content.propSet
                if self._is_valid_host(propSets):
                    for propSet in propSets:
                        if propSet.name == "summary.hardware.numCpuThreads":
                            cluster_hosts_data['numCpuThreads'] += propSet.val
                        elif propSet.name == 'summary.hardware.memorySize':
                            cluster_hosts_data['memorySizeMb'] += int(
                                (propSet.val) / (1024 * 1024))
                        elif propSet.name == 'summary.hardware.cpuMhz':
                            cluster_hosts_data['cpuMhz'] += propSet.val
        return cluster_hosts_data

    def check(self, instance):
        try:
            if self.is_new_session:
                self.instance = instance
                self.vcenter_ip = instance.get('vcenter_ip', None)
                self.user = instance.get('username', None)
                self.password = instance.get('password', None)
                self.port = instance.get('port', 443)
                self.clusters = instance.get('clusters', None)
                if not self.vcenter_ip:
                    self.log.warn("vCenter not configured")
                    return
                if not self.clusters:
                    self.log.warn("No clusters configured to monitor")
                    return
                self.session = self._get_api_session()
                self.vc_uuid = (self.session.vim.service_content.
                                about.instanceUuid)
                self._ops = VcenterOperations(self.session,
                                              self._max_objects,
                                              self.log)
                self._ops._properties_updated_event()
                self.perf_query_specs = self._ops._get_perf_query_spec(
                    CLUSTER_PERF_COUNTERS,
                    SAMPLE_RATE,
                    NUM_SAMPLES)
                self.is_new_session = False
            for managed_cluster in self.clusters:
                try:
                    res_dict = self._get_resource_dict_by_name(managed_cluster)
                    if not res_dict:
                        self.log.error("Configured cluster not found "
                                       "in vCenter")
                        continue
                    self.log.debug("=" * 30 + " Start of cycle" + "=" * 30)
                    self.log.debug("Collecting for cluster: %s (%s)" %
                                   (managed_cluster,
                                    str(res_dict.get('moid'))))
                    cluster_samples = self._ops.\
                        _get_perf_stats(res_dict,
                                        self.perf_query_specs)
                    if not cluster_samples:
                        self.log.error("Activated cluster not found in"
                                       " vCenter")
                        continue

                    host_stats = self._ops._get_host_stats_from_cluster()
                    cluster_host_stats = self._process_host_data(
                        host_stats,
                        managed_cluster)
                    cpu_total_logical_cores = cluster_host_stats.get(
                        'numCpuThreads')

                    cpu_usage = self._get_sample(cluster_samples,
                                                 'cpu.usagemhz.average')
                    cpu_total = self._get_sample(cluster_samples,
                                                 'cpu.totalmhz.average')
                    cpu_usage_percent = float(0.0)
                    if cpu_total > 0:
                        cpu_usage_percent = round(
                            (float(cpu_usage) / cpu_total) * 100, 2)

                    # Considering host level stats for RAM
                    mem_mb_total = cluster_host_stats.get('memorySizeMb')
                    mem_kb_consumed = self._get_sample(cluster_samples,
                                                       'mem.consumed.average')
                    # convert this to MB
                    mem_mb_consumed = mem_kb_consumed / 1024
                    mem_used_percent = float(0.0)
                    if mem_mb_total > 0:
                        mem_used_percent = round(
                            (float(mem_mb_consumed) / mem_mb_total) * 100, 2)

                    datastore_stats = self._ops._read_storage_data()
                    (capacity_bytes, usedSpace_bytes) = \
                        self._process_storage_data(
                            datastore_stats,
                            managed_cluster)
                    storage_used_percent = float(0.0)
                    if capacity_bytes > 0:
                        storage_used_percent = round(
                            float(usedSpace_bytes) / capacity_bytes, 2) * 100
                    capacity_mb = capacity_bytes / (1024 * 1024)
                    usedSpace_mb = usedSpace_bytes / (1024 * 1024)

                    self.log.debug(managed_cluster +
                                   ", CPU used (avg MHz): %s" % str(cpu_usage))
                    self.log.debug(managed_cluster +
                                   ", CPU total (avg MHz): %s" %
                                   str(cpu_total))
                    self.log.debug(managed_cluster +
                                   ", Memory total (MB): %s" %
                                   str(mem_mb_total))
                    self.log.debug(managed_cluster +
                                   ", Memory consumed (MB): %s" %
                                   str(mem_mb_consumed))
                    self.log.debug(managed_cluster +
                                   ", Storage total (MB): %s" %
                                   str(capacity_mb))
                    self.log.debug(managed_cluster +
                                   ", Storage used (MB): %s" %
                                   str(usedSpace_mb))
                    self.log.debug(managed_cluster +
                                   ", CPU cores : %s" %
                                   str(cpu_total_logical_cores))
                    self.log.debug(managed_cluster +
                                   ", CPU cores: %s" %
                                   str(cpu_total_logical_cores) +
                                   ", CPU usage percent: %s" %
                                   str(cpu_usage_percent) +
                                   ", Memory usage percent: %s" %
                                   str(mem_used_percent) +
                                   ", Storage usage percent: %s" %
                                   str(storage_used_percent))

                    data = {
                        CPU_TOTAL_MHZ: cpu_total,
                        CPU_USED_MHZ: cpu_usage,
                        CPU_USED_PERCENT: cpu_usage_percent,
                        CPU_TOTAL_LOGICAL_CORES: cpu_total_logical_cores,
                        MEMORY_TOTAL_MB: mem_mb_total,
                        MEMORY_USED_MB: mem_mb_consumed,
                        MEMORY_USED_PERCENT: mem_used_percent,
                        DISK_TOTAL_SPACE_MB: capacity_mb,
                        DISK_TOTAL_USED_SPACE_MB: usedSpace_mb,
                        DISK_TOTAL_USED_SPACE_PERCENT: storage_used_percent
                    }

                    self._set_metrics(managed_cluster,
                                      data,
                                      res_dict.get("moid"))
                    self.log.debug("=" * 30 + " End of cycle" + "=" * 30)
                except Exception:
                    self.log.error(traceback.format_exc())
                    self.log.error("Exception occurred while polling for %s"
                                   % managed_cluster)
        except Exception as e:
            self.is_new_session = False
            self.log.error("Exception: %s" % str(e))
            try:
                self.session.close()
            except Exception:
                self.log.error(traceback.format_exc())
            raise e

    def _set_metrics(self, managed_cluster, data, mor_id):
        dimensions = self._get_dims(managed_cluster, mor_id)

        for key in data.keys():
            self.gauge(key, data.get(key), dimensions=dimensions)
            self.log.debug("Post metric data for %s,  %s: %d" %
                           (managed_cluster, key, data.get(key)))

    def _get_dims(self, cluster, mor_id):
        cluster_id = mor_id + "." + self.vc_uuid
        local_dimensions = {
            "vcenter_ip": self.vcenter_ip,
            "esx_cluster_id": cluster_id
        }
        final_dimensions = self._set_dimensions(local_dimensions,
                                                self.instance)
        return final_dimensions

    @staticmethod
    def parse_agent_config(agentConfig):
        if not agentConfig.get('vcenter_ip'):
            return False

        vcenter_ip = agentConfig.get('vcenter_ip')
        user = agentConfig.get('username')
        paswd = agentConfig.get('password')
        config = {
            'instances': [{
                'vcenter_ip': vcenter_ip,
                'username': user,
                'password': paswd,
            }]
        }
        return config


class VcenterOperations(object):
    """Class to invoke vCenter APIs calls.

    vCenter APIs calls are required by various pollsters, collecting data from
    VMware infrastructure.
    """
    def __init__(self, session, max_objects, logger):
        self.session = session
        self.max_objects = max_objects
        self.log = logger
        self.counters = {}

    def _get_perf_counters(self):
        try:
            self.log.info("Loading VmWare performance counters")
            perf_counters = []
            property_dict = {'perf_counter': ['perfCounter']}

            prop_collector = self.session.vim.service_content.propertyCollector
            self.client_factory = self.session.vim.client.factory
            perf_manager = self.session.vim.service_content.perfManager
            options = self.client_factory.create('ns0:RetrieveOptions')
            options.maxObjects = 1

            prop_spec = vim_util.build_property_spec(
                self.client_factory,
                PERF_MANAGER_TYPE,
                property_dict.get('perf_counter'))
            obj_spec = vim_util.build_object_spec(
                self.client_factory,
                perf_manager,
                None)

            filter_spec = vim_util.build_property_filter_spec(
                self.client_factory, [prop_spec], [obj_spec])

            object_contents = self.session.invoke_api(
                self.session.vim,
                "RetrievePropertiesEx",
                prop_collector,
                specSet=[filter_spec],
                options=options)

            if object_contents is not None:
                for object_content in object_contents:
                    dynamic_properties = object_content[1][0].propSet
                    for dynamic_property in dynamic_properties:
                        perf_counters = dynamic_property.val.PerfCounterInfo

            return perf_counters
        except Exception as ex:
            self.log.error("Exception in _get_perf_counters: %s"
                           % str(ex.message))

    def _properties_updated_event(self):
        perfCounters = self._get_perf_counters()

        if perfCounters is None:
            return

        for perfCounter in perfCounters:
            counter_id = perfCounter.key
            counter_group = perfCounter.groupInfo.key
            counter_name = perfCounter.nameInfo.key
            counter_rollup_type = str(perfCounter.rollupType)
            full_counter_name = counter_group + "." + \
                counter_name + "." + counter_rollup_type
            if (full_counter_name in CLUSTER_PERF_COUNTERS):
                self.counters[full_counter_name] = perfCounter
                self.counters[counter_id] = full_counter_name

    def _get_perf_counter_ids(self, counter_names):
        res = []
        for counter_name in counter_names:
            perf_counter_info = self.counters.get(counter_name)
            if perf_counter_info is not None:
                res.append(perf_counter_info.key)
        return res

    def _get_perf_query_spec(self,
                             counter_names,
                             sample_rate,
                             num_samples):
        counter_ids = self._get_perf_counter_ids(counter_names)

        perf_metric_ids = []
        for cid in counter_ids:
            metric = self.client_factory.create('ns0:PerfMetricId')
            metric.counterId = cid
            metric.instance = '*'
            perf_metric_ids.append(metric)
        return perf_metric_ids

    def _get_perf_stats(self, entity, perf_metric_ids):
        perf_query_spec = self.client_factory.create('ns0:PerfQuerySpec')
        perf_query_spec.entity = entity.get('moid')
        perf_query_spec.metricId = perf_metric_ids
        perf_query_spec.intervalId = SAMPLE_RATE
        perf_query_spec.maxSample = NUM_SAMPLES
        perf_manager = self.session.vim.service_content.perfManager
        perf_entity_metric_base = self.session.invoke_api(
            self.session.vim,
            'QueryPerf',
            perf_manager,
            querySpec=[perf_query_spec])

        perf_result = {}
        if perf_entity_metric_base:
            for i in range(0, len(perf_entity_metric_base)):
                perf_entity_metric_csv = perf_entity_metric_base[i]
                perf_metric_series_csvs = []
                perf_metric_series_csvs = perf_entity_metric_csv.value

                if perf_metric_series_csvs is None or \
                        len(perf_metric_series_csvs) == 0:
                    continue

                for j in range(0, len(perf_metric_series_csvs)):
                    perf_metric_series_csv = perf_metric_series_csvs[j]
                    name = self.counters[perf_metric_series_csv.id.counterId]
                    instance = perf_metric_series_csv.id.instance
                    if (instance is not None and
                       len(instance) > 0 and
                       instance is not "*"):
                        name += "." + instance
                    perf_result[name] = perf_metric_series_csv.value

        return perf_result

    def _read_storage_data(self):
        datastore_stats = self.session.invoke_api(
            vim_util,
            "get_objects",
            self.session.vim,
            "Datastore",
            self.max_objects,
            STORAGE_VOLUME_PROPERTIES
        )
        return datastore_stats

    def _get_host_stats_from_cluster(self):
        prop_dict = self.session.invoke_api(vim_util,
                                            "get_objects",
                                            self.session.vim,
                                            "ClusterComputeResource",
                                            self.max_objects,
                                            ['host', 'name'])
        return prop_dict
