<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Standard Plugins](#standard-plugins)
  - [Dot File Configuration](#dot-file-configuration)
  - [Plugin Configuration](#plugin-configuration)
      - [init_config](#init_config)
      - [instances](#instances)
      - [dimensions](#dimensions)
      - [Plugin Documentation](#plugin-documentation)
- [Detection Plugins](#detection-plugins)
  - [Plugin](#plugin)
  - [ArgsPlugin](#argsplugin)
  - [ServicePlugin](#serviceplugin)
  - [List of Detection Plugins](#list-of-detection-plugins)
- [Agent Plugin Detail](#agent-plugin-detail)
  - [System Metrics](#system-metrics)
    - [CPU](#cpu)
    - [Load](#load)
    - [Memory](#memory)
    - [Disk](#disk)
    - [Network](#network)
    - [Monasca Agent](#monasca-agent)
    - [Limiting System Metrics](#limiting-system-metrics)
  - [A10](#a10)
  - [Apache](#apache)
  - [Cacti](#cacti)
  - [cAdvisor_host](#cadvisor_host)
  - [Check_MK_Local](#check_mk_local)
  - [Ceph](#ceph)
  - [Certificate Expiration (HTTPS)](#certificate-expiration-https)
  - [Couch](#couch)
  - [Couchbase](#couchbase)
  - [Crash](#crash)
    - [Overview](#overview)
    - [Metrics](#metrics)
    - [Configuration](#configuration)
  - [Directory Checks](#directory-checks)
  - [Docker](#docker)
  - [Elasticsearch Checks](#elasticsearch-checks)
    - [Additional links](#additional-links)
  - [File Size](#file-size)
  - [GearmanD](#gearmand)
  - [Gunicorn](#gunicorn)
  - [HAProxy](#haproxy)
  - [HDFS](#hdfs)
  - [Host Alive](#host-alive)
  - [HTTP (endpoint status)](#http-endpoint-status)
  - [HTTP Metrics](#http-metrics)
  - [InfluxDB](#influxdb)
  - [InfluxDB-Relay](#influxdb-relay)
  - [IIS](#iis)
  - [Jenkins](#jenkins)
  - [JsonPlugin](#jsonplugin)
    - [Simple Reporting](#simple-reporting)
    - [Writing and Locking the Metrics File](#writing-and-locking-the-metrics-file)
    - [Additional Directives](#additional-directives)
    - [Custom JSON file locations](#custom-json-file-locations)
    - [The monasca.json_plugin.status Metric](#the-monascajson_pluginstatus-metric)
  - [Kafka Checks](#kafka-checks)
  - [Kubernetes](#kubernetes)
  - [Kubernetes API](#kubernetes_api)
  - [KyotoTycoon](#kyototycoon)
  - [Libvirt VM Monitoring](#libvirt-vm-monitoring)
  - [Open vSwitch Neutron Router Monitoring](#open-vswitch-neutron-router-monitoring)
  - [Lighttpd](#lighttpd)
  - [Mcache](#mcache)
  - [MK Livestatus](#mk-livestatus)
  - [Mongo](#mongo)
  - [MySQL Checks](#mysql-checks)
        - [Note](#note)
  - [Nagios Wrapper](#nagios-wrapper)
  - [Nginx](#nginx)
  - [NTP](#ntp)
  - [Postfix Checks](#postfix-checks)
  - [PostgreSQL](#postgresql)
  - [Process Checks](#process-checks)
  - [Prometheus](#prometheus)
  - [RabbitMQ Checks](#rabbitmq-checks)
  - [RedisDB](#redisdb)
  - [Riak](#riak)
  - [SolidFire](#solidfire)
  - [SQLServer](#sqlserver)
  - [Supervisord](#supervisord)
  - [Swift Diags](#swift-diags)
  - [TCP Check](#tcp-check)
  - [Varnish](#varnish)
  - [VCenter](#vcenter)
    - [Sample Config](#sample-config)
    - [ESX Cluster Metrics](#esx-cluster-metrics)
    - [ESX Cluster Dimensions](#esx-cluster-dimensions)
  - [Vertica Checks](#vertica-checks)
  - [WMI Check](#wmi-check)
  - [ZooKeeper](#zookeeper)
  - [Kibana](#kibana)
  - [OpenStack Monitoring](#openstack-monitoring)
    - [Nova Checks](#nova-checks)
        - [Nova Processes Monitored](#nova-processes-monitored)
        - [Example Nova Metrics](#example-nova-metrics)
    - [Swift Checks](#swift-checks)
        - [Swift Processes Monitored](#swift-processes-monitored)
        - [Example Swift Metrics](#example-swift-metrics)
    - [Glance Checks](#glance-checks)
        - [Glance Processes Monitored](#glance-processes-monitored)
        - [Example Glance Metrics](#example-glance-metrics)
    - [Cinder Checks](#cinder-checks)
        - [Cinder Processes Monitored](#cinder-processes-monitored)
        - [Example Cinder Metrics](#example-cinder-metrics)
    - [Neutron Checks](#neutron-checks)
        - [Neutron Processes Monitored](#neutron-processes-monitored)
        - [Example Neutron Metrics](#example-neutron-metrics)
    - [Keystone Checks](#keystone-checks)
        - [Keystone Processes Monitored](#keystone-processes-monitored)
        - [Example Keystone Metrics](#example-keystone-metrics)
    - [Ceilometer Checks](#ceilometer-checks)
        - [Ceilometer Processes Monitored](#ceilometer-processes-monitored)
        - [Example Ceilometer Metrics](#example-ceilometer-metrics)
    - [Freezer Checks](#freezer-checks)
        - [Freezer Processes Monitored](#freezer-processes-monitored)
        - [Example Freezer Metrics](#example-freezer-metrics)
    - [Magnum Checks](#magnum-checks)
        - [Magnum Processes Monitored](#magnum-processes-monitored)
        - [Example Magnum Metrics](#example-magnum-metrics)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Standard Plugins
Plugins are the way to extend the Monasca Agent.  Plugins add additional functionality that allow the agent to perform checks on other applications, servers or services.  Some plugins may have corresponding [Detection Plugins](#detection-plugins) to automatically detect, configure, and activate certain Agent plugins. This section describes the standard plugins that are delivered by default.

** Standard location for plugin YAML config files **
> /etc/monasca/agent/conf.d/

The following plugins are delivered via setup as part of the standard plugin checks.  See [Customizations.md](https://github.com/openstack/monasca-agent/blob/master/docs/Customizations.md) for how to write new plugins.

| Setup Plugin Name | Dot File  | Detail                 |
| ----------------- | --------- | ---------------------- |
| a10 |  |  |
| apache | /root/.apache.cnf | Apache web server |
| cacti |  |  |
| cAdvisor_host |  |  |
| cert_check |  |  |
| check_mk_local |  |  |
| couch |  |  |
| couchbase |  |  |
| cpu |  |  |
| crash |  |  |
| directory |  |  |
| disk |  |  |
| docker |  |  |
| elastic |  |  |
| file_size |  |  |
| gunicorn |  |  |
| haproxy |  |  |
| hdfs |  |  |
| host_alive |  |  |
| http_check |  |  |
| http_metrics |  |  |
| iis |  | Microsoft Internet Information Services |
| jenkins |  |  |
| json_plugin | | |
| kafka_consumer |  |  |
| kibana | **kibana_install_dir**/kibana.yml | Integration to Kibana |
| kubernetes |  |  |
| kubernetes_api |  |  |
| kyototycoon |  |  |
| libvirt |  |  |
| lighttpd |  |  |
| load |  |  |
| mcache |  |  |
| memory |  |  |
| mk_livestatus |  |  |
| mongo |  |  |
| mysql | /root/.my.cnf |  |
| nagios_wrapper |  |  |
| network |  |  |
| nginx |  | Tracks basic nginx metrics via the status module |
| ntp |  | Uses ntplib to grab a metric for the ntp offset |
| postfix |  | Provides metrics on the number of messages in a given postfix queue|
| postgres |  |  |
| process |  |  |
| prometheus |  |  |
| rabbitmq | /root/.rabbitmq.cnf |
| redisdb |  |  |
| riak |  |  |
| solidfire |  | Track cluster health and use stats |
| sqlserver |  |  |
| supervisord |  |  |
| swift_diags |  |  |
| tcp_check |  |  |
| varnish |  |  |
| vcenter |  |  |
| vertica | /root/.vertica.cnf |
| wmi_check |  |  |
| zk |  | Apache Zookeeper |


## Dot File Configuration

Dot files, as referenced above, provide an added level of configuration to some component plugins.  Here are a few examples:

> **apache**
```
Example for apache process and server-status metrics (secure)
[client]
user=root
password=pass
url=https://localhost/server-status?auto
or
Example for apache process and server-status metrics (non-secure)
[client]
url=http://localhost/server-status?auto
or
Example for apache process metrics only
[client]
use_server_status_metrics=false
```

> **mysql**
```
[client]
user=root
password=pass
host=server
socket=/var/run/mysqld/mysqld.sock
ssl_ca=/etc/ssl/certs/ca-certificates.crt
```

> **rabbitmq**
```
[client]
user=guest
password=pass
nodes=rabbit@devstack
queues=conductor
exchanges=nova,cinder,ceilometer,glance,keystone,neutron,heat,ironic,openstack
```

## Plugin Configuration
Each plugin has a corresponding YAML configuration file with the same stem name as the plugin script file.

The configuration file has the following structure:

```
init_config:
    key1: value1
    key2: value2

instances:
    - username: john_smith
      password: 123456
      dimensions:
          node_type: test
    - username: jane_smith
      password: 789012
      dimensions:
          node_type: production
```

#### init_config
In the init_config section you can specify an arbitrary number of global name:value pairs that will be available on every run of the check in self.init_config.
Here you can specify a collection frequency specific to the plugin by setting collect_period.
The global frequency at which all plugins are run is specified by the variable "check_frequency" defined in https://github.com/openstack/monasca-agent/blob/master/docs/Agent.md.
Under normal and default conditions when a plugin runs all the metrics are collected and sent. For example, if check_frequency=30, by default the plugin will be run every 30 seconds and the metrics will be sent.
The variable "collect_period" allows each plugins collect period to be further adjusted to a value greater than the frequency at which the plugin is run specified by "check_frequency", such that when the collection run starts, the plugin might not be called. For example, if check_frequency=30 and collect_period=600, the plugin will be called and metrics sent every 600 seconds. This allows fewer metrics to be sent.
The "collect_period" should be evenly divisible by the "check_frequency". For example, if you want the plugin to collect and send metrics every 600 seconds (10 minutes), and the global check_frequency=30, then the collect_period should be set to 600.
If the "collect_period" is not evenly divisible by the "check_frequency" then the "collect_period" will get rounded up to the nearest multiple of the "check_frequency". For example, if the collect_period=45 and the global check_frequency=30, then the "collect_period" will get rounded up to 60 and the plugin will get called and send metrics every 60 seconds.

#### instances
The instances section is a list of instances that this check will be run against. Your actual check() method is run once per instance. The name:value pairs for each instance specify details about the instance that are necessary for the check.

#### dimensions
The instances section can also contain optional dimensions. These dimensions will be added to any metrics generated by the check for that instance.

#### Plugin Documentation
Your plugin should include an example YAML configuration file to be placed in /etc/monasca/agent/conf.d/ which has the name of the plugin YAML file plus the extension '.example', so the example configuration file for the process plugin would be at /usr/local/share/monasca/agent/conf.d/process.yaml.example. This file should include a set of example init_config and instances clauses that demonstrate how the plugin can be configured.

# Detection Plugins
The `monasca_setup` library contains a number of detection plugins, which are located within the library at

> monasca_setup/detection/plugins/

Some detection plugins activate a specific Agent plugin of the same name, and some leverage other general-purpose Agent plugins to monitor a particular service.  There are three classes in total:

## Plugin
The base class of detection plugins requires a separate Agent plugin of the same name.

## ArgsPlugin
Any plugins which are configured by passing arguments, rather than relying on detection, may use the ArgsPlugin class.

## ServicePlugin
This class covers Process, HTTP endpoints, Directory, and File monitoring.  It is primarily used for monitoring OpenStack components.
Note: There are existing default detection plugins for http_check.py, directory.py, and file_size.py that only require configuration.

A process can be monitored by process_names or by process_username. Pass in the process_names list argument when watching process by name.  Pass in the process_username argument and component_name arguments when watching process by username. Watching by username is useful for groups of processes that
are owned by a specific user.  For process monitoring by process_username the component_name is required since it is used to initialize the instance name in process.yaml.
component_name is optional for monitoring by process_name and all other checks.

An http endpoint connection can be checked by passing in the service_api_url and optional search_pattern parameters.
The http check can be skipped by specifying the argument 'disable_http_check'

Directory size can be checked by passing in a directory_names list.

File size can be checked by passing in a file_dirs_names list where each directory name item includes a list of files.
example: 'file_dirs_names': [('/var/log/monasca/api', ['monasca-api'])]

Note: service_name and component_name are optional (except component_name is required with process_username) arguments used for metric dimensions by all checks.

## List of Detection Plugins
These are the detection plugins included with the Monasca Agent.  See [Customizations.md](https://github.com/openstack/monasca-agent/blob/master/docs/Customizations.md) for how to write new detection plugins.

| Detection Plugin Name | Type                 |
| --------------------- | ---------------------- |
| a10 | Plugin |
| apache | Plugin |
| barbican | ServicePlugin |
| bind | Plugin |
| ceilometer | ServicePlugin |
| ceph | Plugin |
| cert_check | ArgsPlugin |
| check_mk_local | Plugin |
| cinder | ServicePlugin |
| crash | Plugin |
| cue | ServicePlugin |
| designate | ServicePlugin |
| directory | ServicePlugin |
| file_size | ServicePlugin |
| freezer | Plugin (multiple) |
| glance | ServicePlugin |
| haproxy | Plugin |
| heat | ServicePlugin |
| host_alive | ArgsPlugin |
| http_check | ArgsPlugin |
| ironic | ServicePlugin |
| kafka_consumer | Plugin |
| keystone | ServicePlugin |
| libvirt | Plugin |
| magnum | ServicePlugin |
| mk_livestatus | Plugin |
| mon | Plugin (multiple) |
| mysql | Plugin |
| neutron | ServicePlugin |
| nova | ServicePlugin |
| ntp | Plugin |
| octavia | ServicePlugin |
| ovsvapp | ServicePlugin |
| postfix | Plugin |
| powerdns | Plugin |
| process | Plugin |
| rabbitmq | Plugin |
| supervisord | Plugin |
| swift | ServicePlugin |
| system | Plugin |
| trove | ServicePlugin |
| vcenter | Plugin |
| vertica | Plugin |
| zookeeper | Plugin |
| kibana | Plugin |


# Agent Plugin Detail
This section documents all the checks that are supplied by the Agent.

## System Metrics
This section documents the system metrics that are sent by the Agent.

### CPU
| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| cpu.idle_perc  |  | Percentage of time the CPU is idle when no I/O requests are in progress |
| cpu.wait_perc |  | Percentage of time the CPU is idle AND there is at least one I/O request in progress |
| cpu.stolen_perc |  | Percentage of stolen CPU time, i.e. the time spent in other OS contexts when running in a virtualized environment |
| cpu.system_perc |  | Percentage of time the CPU is used at the system level |
| cpu.user_perc  |  | Percentage of time the CPU is used at the user level |
| cpu.total_logical_cores  |  | Total number of logical cores available for an entire node (Includes hyper threading).  **NOTE: This is an optional metric that is only sent when send_rollup_stats is set to true.** |
| cpu.percent  |  | Percentage of time the CPU is used in total |
| cpu.idle_time  |  | Time the CPU is idle when no I/O requests are in progress |
| cpu.wait_time  |  | Time the CPU is idle AND there is at least one I/O request in progress |
| cpu.user_time  |  | Time the CPU is used at the user level |
| cpu.system_time  |  | Time the CPU is used at the system level |
| cpu.frequency_mhz |  | Maximum MHz value for the cpu frequency. **NOTE: This value is dynamic, and driven by CPU governor depending on current resource need .** |

### Load
| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| load.avg_1_min  |  | The normalized (by number of logical cores) average system load over a 1 minute period
| load.avg_5_min  |  | The normalized (by number of logical cores) average system load over a 5 minute period
| load.avg_15_min  |  | The normalized (by number of logical cores) average system load over a 15 minute period

### Memory
| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| mem.free_mb |  | Mbytes of free memory
| mem.swap_free_perc |  | Percentage of free swap memory that is free
| mem.swap_free_mb |  | Mbytes of free swap memory that is free
| mem.swap_total_mb |  | Mbytes of total physical swap memory
| mem.swap_used_mb |  | Mbytes of total swap memory used
| mem.total_mb |  | Total Mbytes of memory
| mem.usable_mb |  | Total Mbytes of usable memory
| mem.usable_perc |  | Percentage of total memory that is usable
| mem.used_buffers |  | Number of buffers in Mbytes being used by the kernel for block io
| mem.used_cached |  | Mbytes of memory used for the page cache
| mem.used_shared  |  | Mbytes of memory shared between separate processes and typically used for inter-process communication
| mem.used_real_mb |  | Mbytes of memory currently in use less mem.used_buffers and mem.used_cached

### Disk
| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| disk.inode_used_perc | device, mount_point | The percentage of inodes that are used on a device |
| disk.space_used_perc | device, mount_point | The percentage of disk space that is being used on a device |
| disk.total_space_mb |  | The total amount of disk space in Mbytes aggregated across all the disks on a particular node.  **NOTE: This is an optional metric that is only sent when send_rollup_stats is set to true.** |
| disk.total_used_space_mb |  | The total amount of used disk space in Mbytes aggregated across all the disks on a particular node.  **NOTE: This is an optional metric that is only sent when send_rollup_stats is set to true.** |
| io.read_kbytes_sec | device | Kbytes/sec read by an io device
| io.read_req_sec | device   | Number of read requests/sec to an io device
| io.read_time_sec | device   | Amount of read time in seconds to an io device
| io.write_kbytes_sec |device | Kbytes/sec written by an io device
| io.write_req_sec   | device | Number of write requests/sec to an io device
| io.write_time_sec | device   | Amount of write time in seconds to an io device

### Network
The network check can be configured to submit its metrics in either bytes/sec or bits/sec.  The default behavior is to submit bytes.  To submit `net.in_bits_sec` and `net.out_bits_sec` rather than `net.in_bytes_sec` and `net.out_bytes_sec`, set the config option `use_bits` to true for the instance you want to configure.

Example configuration:
```
init_config: null
instances:
- built_by: System
  excluded_interface_re: lo.*|vnet.*|tun.*|ovs.*|br.*|tap.*|qbr.*|qvb.*|qvo.*
  name: network_stats
  send_rollup_stats: true
  use_bits: false
```

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| net.in_bytes_sec  | device | Number of network bytes received per second
| net.out_bytes_sec  | device | Number of network bytes sent per second
| net.in_packets_sec  | device | Number of network packets received per second
| net.out_packets_sec  | device | Number of network packets sent per second
| net.in_errors_sec  | device | Number of network errors on incoming network traffic per second
| net.out_errors_sec  | device | Number of network errors on outgoing network traffic per second
| net.in_packets_dropped_sec  | device | Number of inbound network packets dropped per second
| net.out_packets_dropped_sec  | device | Number of outbound network packets dropped per second
| net.int_status | device | Network interface status

### Monasca Agent
The Monasca Agent itself generates a small number of metrics.

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| monasca.thread_count  | service=monitoring component=monasca-agent | Number of threads that the collector is consuming for this collection run |
| monasca.emit_time_sec  | service=monitoring component=monasca-agent | Amount of time that the forwarder took to send metrics to the Monasca API. |
| monasca.collection_time_sec  | service=monitoring component=monasca-agent | Amount of time that the collector took for this collection run |

### Limiting System Metrics
It is possible to reduce the number of system metrics with certain configuration parameters.

| Config Option  | Values     | Description                                                                                |
| -------------- | ---------- | ------------------------------------------------------------------------------------------ |
| net_bytes_only | true/false | Sends bytes/sec metrics only, disabling packets/sec, packets_dropped/sec, and errors/sec.  |
| cpu_idle_only  | true/false | Sends idle_perc only, disabling wait/stolen/system/user metrics                            |
| send_io_stats  | true/false | If true, sends I/O metrics for each disk device.  If false, sends only disk space metrics. |

These parameters may added to `instances` in the plugin `.yaml` configuration file, or added via `monasca-setup` like this:

    $ monasca-setup -d system -a 'cpu_idle_only=true net_bytes_only=true send_io_stats=false' --overwrite

By default, all metrics are enabled.

## A10
This section describes the A10 System Check.

```
init_config:

instances:
    - name: a10_system_check
        a10_device: a10_device_ip
        a10_username: admin
        a10_password: password
```

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| a10.memory_total_mb | a10_device, service=networking  | Total memory presented in MB
| a10.memory_used_mb |  a10_device, service=networking   | Memory used presented in  MB
| a10.memory_free_mb |  a10_device, service=networking   | Free memory presented in MB
| a10.memory_used |  a10_device, service=networking   | Realtime Memory Usage

## Apache
This section describes the Apache Web Server check that can be performed by the Agent.  The Apache check gathers metrics on the Apache Web Server.  The Apache check requires a configuration file called apache.yaml to be available in the agent conf.d configuration directory.  The config file must contain the server url, username and password (If you are using authentication) that you are interested in monitoring.

Sample config:

```
init_config:

instances:
  - apache_status_url: http://localhost/server-status?auto
    apache_user: root
    apache_password: password
```

If you want the monasca-setup program to detect and auto-configure the plugin for you, you must create the file /root/.apache.cnf with the information needed in the configuration yaml file before running the setup program.  It should look something like this:

```
[client]
url=http://localhost/server-status?auto
user=root
password=password
```

The Apache checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| apache.performance.idle_worker_count | hostname, service=apache component=apache | The number of idle workers |
| apache.performance.busy_worker_count | hostname, service=apache component=apache | The number of workers serving requests |
| apache.performance.cpu_load_perc | hostname, service=apache component=apache | The current percentage of CPU used by each worker and in total by all workers combined |
| apache.net.total_kbytes | hostname, service=apache component=apache | Total Kbytes |
| apache.net.hits | hostname, service=apache component=apache | Total accesses |
| apache.net.kbytes_sec | hostname, service=apache component=apache | Total Kbytes per second |
| apache.net.requests_sec | hostname, service=apache component=apache | Total accesses per second |

## Cacti
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/cacti.yaml.example) for how to configure the Cacti plugin.

## cAdvisor_host
This plugin collects metrics about a host from a given cAdvisor instance. This is useful in a container environment where
the agent is running in a container but still wants to monitor the underlying hosts.

It connects to the cAdvisor instance and queries the stats API about the host.

There are two ways to configure the plugin.
* Set cAdvisor url
* Set kubernetes detect url to True. If true, the assumption is that the Agent is running in a Kubernetes
container. The agent will obtain the cAdvisor url by first querying the Kubernetes API to ask which node it is running on and
then from there hit the local cAdvisor on that node that is included in the kubelet.

As a result the plugin only supports getting data from one cAdvisor endpoint. So the config yaml file must
only have one instance defined under instances. (Example shown below)

Sample config (passing in cAdvisor url):

```
init_config:
    # Timeout on GET requests to the cAdvisor endpoints
    connection_timeout: 3
instances:
    # Set to the url of the cAdvisor instance you want to connect to
    - cadvisor_url: "127.0.0.1:4194"
```

Sample config (setting Kubernetes detect cAdvisor url):
```
init_config:
    # Timeout on GET requests to the cAdvisor endpoints
    connection_timeout: 3
instances:
    # Set to the url of the cAdvisor instance you want to connect to
    - kubernetes_detect_cadvisor: True
```

**Note if both a url and detect cAdvisor are both set it will by default use the url**


The cAdvisor host check returns the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| cpu.system_time | hostname, unit | Cumulative system CPU time consumed in core seconds
| cpu.system_time_sec | hostname, unit | Rate of system CPU time consumed in core seconds per second
| cpu.total_time | hostname, unit | Cumulative CPU time consumed in core seconds
| cpu.total_time_sec | hostname, unit | Rate of CPU time consumed in core seconds per second
| cpu.user_time | hostname, unit | Cumulative user cpu time consumed in core seconds
| cpu.user_time_sec | hostname, unit | Rate of user CPU time consumed in core seconds per second
| fs.total_bytes | hostname, device, unit | Number of bytes available
| fs.usage_bytes | hostname, device, unit | Number of bytes consumed
| io.read_bytes | hostname, unit | Total number of bytes read by all devices
| io.read_bytes_sec | hostname, unit | Total number of bytes read by all devices per second
| io.write_bytes | hostname, unit | Total number of bytes written by all devices
| io.write_bytes_sec | hostname, unit | Total number of bytes written by all devices per second
| mem.cache_bytes | hostname, unit | Number of bytes of page cache memory
| mem.swap_bytes | hostname, unit | Swap usage in memory in bytes
| mem.used_bytes | hostname, unit | Current memory in use in bytes
| net.in_bytes | hostname, interface, unit | Total network bytes received by all interfaces
| net.in_bytes_sec | hostname, interface, unit | Total number of network bytes received by all interfaces per second
| net.in_dropped_packets | hostname, interface, unit | Total inbound network packets dropped by all interfaces
| net.in_dropped_packets_sec | hostname, interface, unit | Total number of inbound network packets dropped by all interfaces per second
| net.in_errors | hostname, interface, unit  | Total network errors on incoming network traffic by all interfaces
| net.in_errors_sec | hostname, interface, unit | Total number of network errors on incoming network traffic by all interfaces per second
| net.in_packets | hostname, interface, unit | Total network packets received by all interfaces
| net.in_packets_sec | hostname, interface, unit | Total number of network packets received by all interfaces per second
| net.out_bytes | hostname, interface, unit | Total network bytes sent by all interfaces
| net.out_bytes_sec | hostname, interface, unit | Total number of network bytes sent by all interfaces per second
| net.out_dropped_packets | hostname, interface, unit | Total outbound network packets dropped by all interfaces
| net.out_dropped_packets_sec | hostname, interface, unit | Total number of outbound network packets dropped by all interfaces per second
| net.out_errors | hostname, interface, unit | Total network errors on outgoing network traffic by all interfaces
| net.out_errors_sec | hostname, interface, unit | Total number of network errors on outgoing network traffic by all interfaces per second
| net.out_packets | hostname, interface, unit | Total network packets sent by all interfaces
| net.out_packets_sec | hostname, interface, unit | Total number of network packets sent by all interfaces per second

## Check_MK_Local
The [Check_MK](http://mathias-kettner.com/check_mk.html) [Agent](http://mathias-kettner.com/checkmk_linuxagent.html) can be extended through a series of [local checks](http://mathias-kettner.com/checkmk_localchecks.html).  This plugin parses the `<<<local>>>` output of `check_mk_agent` and converts them into Monasca metrics.  It is installed by `monasca-setup` automatically when the `check_mk_agent` script is found to be installed on the system.

The default configuration is to submit metrics from all local checks returned by `check_mk_agent`.  One metric will be submitted for the status code, and one additional metric for each performance measurement included in the result.  The basic format of `check_mk_agent` local check output is:
```
<status> <item name> <performance data> <check output>
```
So if the output line is:
```
0 glance_registry response_time=0.004 glance_registry: status UP http://0.0.0.0:9191
```
the `check_mk_local` plugin for the Monasca Agent will return these metrics:
```
 Timestamp:  1430848955
 Name:       check_mk.glance_registry.status
 Value:      0
 Dimensions: hostname=devstack
             service=monitoring
 Value Meta: detail=glance_registry: status UP http://0.0.0.0:9191
```
and
```
 Timestamp:  1430852467
 Name:       check_mk.glance_registry.response_time
 Value:      0.006
 Dimensions: hostname=devstack
             service=monitoring
 Value Meta: None
```
The name of the metric starts with `check_mk.`, includes the check_mk item name, and is followed by either `status` for the Nagios status code (0, 1, 2, or 3), or the name of the performance metric.  The free-form output from the check is included in the meta field of the check status.

You may override these defaults in the configuration, which by default is `/etc/monasca/agent/conf.d/check_mk_local.yaml`.
```
init_config:
    mk_agent_path: /usr/bin/check_mk_agent

    custom:
      - mk_item: sirius-api
        discard: false
        dimensions: {'component': 'sirius'}
        metric_name_base: check_mk.sirius_api
      - mk_item: eon-api
        discard: true

instances:
    - {}
```
The `custom` section of `init_config` is optional and may be blank or removed entirely.  In this section, you may add custom rules to Monasca metrics based on the check_mk item name.
  * *mk_item* -  This is the name (2nd field) returned by check_mk_agent
  * *discard* -  Exclude the metric from Monasca, True or False (if *discard* is not specified, the default is False)
  * *dimensions* - Extra dimensions to include, in `{'name': 'value'}` format.
  * *metric_name_base* - This represents the leftmost part of the metric name to use.  Status and any performance metrics are appended following a dot, so ".status" and ".response_time" would be examples.

Because `check_mk_agent` can only return all local metrics at once, the `check_mk_local` plugin requires no instances to be defined in the configuration.  It runs `check_mk_agent` once and processes all the results.  This way, new `check_mk` local scripts can be added without having to modify the plugin configuration.

## Ceph
This section describes the Ceph check that can be performed by the Agent. The Ceph check gathers metrics from multiple ceph clusters. The Ceph check requires a configuration file called `ceph.yaml` to be available in the agent conf.d configuration directory. The config file must contain the cluster name that you are interested in monitoring (defaults to `ceph`). Also, it is possible to configure the agent to collect only specific metrics about the cluster (usage, stats, monitors, osds or pools).

Requirements:
  * ceph-common
  * The user running monasca-agent must be able to execute ceph commands. This can be done by adding the monasca-agent user to the ceph group, and giving group read permission on the `ceph.client.admin.keyring` file.

```
  usermod -a -G ceph monasca-agent
  chmod 0640 /etc/ceph/ceph.client.admin.keyring
```

Alternatively, you can configure monasca-agent to use sudo using the `use_sudo`
option. The example configuration below assumes you added the `monasca-agent`
user to the `ceph` group which does not require using sudo.

Sample config:

```
init_config:

instances:
  - cluster_name: ceph
    use_sudo: False
    collect_usage_metrics: True
    collect_stats_metrics: True
    collect_mon_metrics: True
    collect_osd_metrics: True
    collect_pool_metrics: True
```

The Ceph checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| ceph.cluster.total_bytes | hostname, ceph_cluster, service=ceph | Total capacity of the cluster in bytes |
| ceph.cluster.total_used_bytes | hostname, ceph_cluster, service=ceph | Capacity of the cluster currently in use in bytes |
| ceph.cluster.total_avail_bytes | hostname, ceph_cluster, service=ceph | Available space within the cluster in bytes |
| ceph.cluster.objects.total_count | hostname, ceph_cluster, service=ceph | No. of rados objects within the cluster |
| ceph.cluster.utilization_perc | hostname, ceph_cluster, service=ceph | Percentage of available storage on the cluster |
| ceph.cluster.health_status | hostname, ceph_cluster, service=ceph | Health status of cluster, can vary between 3 states (err:2, warn:1, ok:0) |
| ceph.cluster.osds.down_count | hostname, ceph_cluster, service=ceph | Number of OSDs that are in DOWN state |
| ceph.cluster.osds.out_count | hostname, ceph_cluster, service=ceph | Number of OSDs that are in OUT state |
| ceph.cluster.osds.up_count | hostname, ceph_cluster, service=ceph | Number of OSDs that are in UP state |
| ceph.cluster.osds.in_count | hostname, ceph_cluster, service=ceph | Number of OSDs that are in IN state |
| ceph.cluster.osds.total_count | hostname, ceph_cluster, service=ceph | Total number of OSDs in the cluster |
| ceph.cluster.objects.degraded_count | hostname, ceph_cluster, service=ceph | Number of degraded objects across all PGs, includes replicas |
| ceph.cluster.objects.misplaced_count | hostname, ceph_cluster, service=ceph | Number of misplaced objects across all PGs, includes replicas |
| ceph.cluster.pgs.avg_per_osd | hostname, ceph_cluster, service=ceph | Average number of PGs per OSD in the cluster |
| ceph.cluster.pgs.total_count | hostname, ceph_cluster, service=ceph | Total no. of PGs in the cluster |
| ceph.cluster.pgs.scrubbing_count | hostname, ceph_cluster, service=ceph | Number of scrubbing PGs in the cluster |
| ceph.cluster.pgs.deep_scrubbing_count | hostname, ceph_cluster, service=ceph | Number of deep scrubbing PGs in the cluster |
| ceph.cluster.pgs.degraded_count | hostname, ceph_cluster, service=ceph | Number of PGs in a degraded state |
| ceph.cluster.pgs.stuck_degraded_count | hostname, ceph_cluster, service=ceph | No. of PGs stuck in a degraded state |
| ceph.cluster.pgs.unclean_count | hostname, ceph_cluster, service=ceph | Number of PGs in an unclean state |
| ceph.cluster.pgs.stuck_unclean_count | hostname, ceph_cluster, service=ceph | Number of PGs stuck in an unclean state |
| ceph.cluster.pgs.undersized_count | hostname, ceph_cluster, service=ceph | Number of undersized PGs in the cluster |
| ceph.cluster.pgs.stuck_undersized_count | hostname, ceph_cluster, service=ceph | Number of stuck undersized PGs in the cluster |
| ceph.cluster.pgs.stale_count | hostname, ceph_cluster, service=ceph | Number of stale PGs in the cluster |
| ceph.cluster.pgs.stuck_stale_count | hostname, ceph_cluster, service=ceph | Number of stuck stale PGs in the cluster |
| ceph.cluster.pgs.remapped_count | hostname, ceph_cluster, service=ceph | Number of PGs that are remapped and incurring cluster-wide movement |
| ceph.cluster.recovery.bytes_per_sec | hostname, ceph_cluster, service=ceph | Rate of bytes being recovered in cluster per second |
| ceph.cluster.recovery.keys_per_sec | hostname, ceph_cluster, service=ceph | Rate of keys being recovered in cluster per second |
| ceph.cluster.recovery.objects_per_sec | hostname, ceph_cluster, service=ceph | Rate of objects being recovered in cluster per second |
| ceph.cluster.client.read_bytes_per_sec | hostname, ceph_cluster, service=ceph | Rate of bytes being read by all clients per second |
| ceph.cluster.client.write_bytes_per_sec | hostname, ceph_cluster, service=ceph | Rate of bytes being written by all clients per second |
| ceph.cluster.client.read_ops | hostname, ceph_cluster, service=ceph | Total client read I/O ops on the cluster measured per second |
| ceph.cluster.client.write_ops | hostname, ceph_cluster, service=ceph | Total client write I/O ops on the cluster measured per second |
| ceph.cluster.cache.flush_bytes_per_sec | hostname, ceph_cluster, service=ceph | Rate of bytes being flushed from the cache pool per second |
| ceph.cluster.cache.evict_bytes_per_sec | hostname, ceph_cluster, service=ceph | Rate of bytes being evicted from the cache pool per second |
| ceph.cluster.cache.promote_ops | hostname, ceph_cluster, service=ceph | Total cache promote operations measured per second |
| ceph.cluster.slow_requests_count | hostname, ceph_cluster, service=ceph | Number of slow requests |
| ceph.cluster.quorum_size | hostname, ceph_cluster, service=ceph | Number of monitors in quorum |
| ceph.monitor.total_bytes | hostname, ceph_cluster, monitor, service=ceph | Total storage capacity of the monitor node |
| ceph.monitor.used_bytes | hostname, ceph_cluster, monitor, service=ceph | Storage of the monitor node that is currently allocated for use |
| ceph.monitor.avail_bytes | hostname, ceph_cluster, monitor, service=ceph | Total unused storage capacity that the monitor node has left |
| ceph.monitor.avail_perc | hostname, ceph_cluster, monitor, service=ceph | Percentage of total unused storage capacity that the monitor node has left |
| ceph.monitor.store.total_bytes | hostname, ceph_cluster, monitor, service=ceph | Total capacity of the FileStore backing the monitor daemon |
| ceph.monitor.store.sst_bytes | hostname, ceph_cluster, monitor, service=ceph | Capacity of the FileStore used only for raw SSTs |
| ceph.monitor.store.log_bytes | hostname, ceph_cluster, monitor, service=ceph | Capacity of the FileStore used only for logging |
| ceph.monitor.store.misc_bytes | hostname, ceph_cluster, monitor, service=ceph | Capacity of the FileStore used only for storing miscellaneous information |
| ceph.monitor.skew | hostname, ceph_cluster, monitor, service=ceph | Monitor clock skew |
| ceph.monitor.latency | hostname, ceph_cluster, monitor, service=ceph | Monitor's latency |
| ceph.osd.crush_weight | hostname, ceph_cluster, osd, service=ceph | OSD crush weight |
| ceph.osd.depth | hostname, ceph_cluster, osd, service=ceph | OSD depth |
| ceph.osd.reweight | hostname, ceph_cluster, osd, service=ceph | OSD reweight |
| ceph.osd.total_bytes | hostname, ceph_cluster, osd, service=ceph | OSD total bytes |
| ceph.osd.used_bytes | hostname, ceph_cluster, osd, service=ceph | OSD used storage in bytes |
| ceph.osd.avail_bytes | hostname, ceph_cluster, osd, service=ceph | OSD available storage in bytes |
| ceph.osd.utilization_perc | hostname, ceph_cluster, osd, service=ceph | OSD utilization |
| ceph.osd.variance | hostname, ceph_cluster, osd, service=ceph | OSD variance |
| ceph.osd.pgs_count | hostname, ceph_cluster, osd, service=ceph | OSD placement group count |
| ceph.osd.perf.commit_latency_seconds | hostname, ceph_cluster, osd, service=ceph | OSD commit latency in seconds |
| ceph.osd.perf.apply_latency_seconds | hostname, ceph_cluster, osd, service=ceph | OSD apply latency in seconds |
| ceph.osd.up | hostname, ceph_cluster, osd, service=ceph | OSD up status (up: 1, down: 0) |
| ceph.osd.in | hostname, ceph_cluster, osd, service=ceph | OSD in status (in: 1, out: 0) |
| ceph.osds.total_bytes | hostname, ceph_cluster, service=ceph | OSDs total storage in bytes |
| ceph.osds.total_used_bytes | hostname, ceph_cluster, service=ceph | OSDs total used storage in bytes |
| ceph.osds.total_avail_bytes | hostname, ceph_cluster, service=ceph | OSDs total available storage in bytes |
| ceph.osds.avg_utilization_perc | hostname, ceph_cluster, osd, service=ceph | OSDs average utilization in percent |
| ceph.pool.used_bytes | hostname, ceph_cluster, pool, service=ceph | Capacity of the pool that is currently under use |
| ceph.pool.used_raw_bytes | hostname, ceph_cluster, pool, service=ceph | Raw capacity of the pool that is currently under use, this factors in the size |
| ceph.pool.max_avail_bytes | hostname, ceph_cluster, pool, service=ceph | Free space for this ceph pool |
| ceph.pool.objects_count | hostname, ceph_cluster, pool, service=ceph | Total no. of objects allocated within the pool |
| ceph.pool.dirty_objects_count | hostname, ceph_cluster, pool, service=ceph | Total no. of dirty objects in a cache-tier pool |
| ceph.pool.read_io | hostname, ceph_cluster, pool, service=ceph | Total read i/o calls for the pool |
| ceph.pool.read_bytes | hostname, ceph_cluster, pool, service=ceph | Total read throughput for the pool |
| ceph.pool.write_io | hostname, ceph_cluster, pool, service=ceph | Total write i/o calls for the pool |
| ceph.pool.write | hostname, ceph_cluster, pool, service=ceph | Total write throughput for the pool |
| ceph.pool.quota_max_bytes | hostname, ceph_cluster, pool, service=ceph | Quota maximum bytes for the pool |
| ceph.pool.quota_max_objects | hostname, ceph_cluster, pool, service=ceph | Quota maximum objects for the pool |
| ceph.pool.total_bytes | hostname, ceph_cluster, pool, service=ceph | Total capacity of the pool in bytes |
| ceph.pool.utilization_perc | hostname, ceph_cluster, pool, service=ceph | Percentage of used storage for the pool |
| ceph.pool.client.read_bytes_sec | hostname, ceph_cluster, pool, service=ceph | Read bytes per second on the pool |
| ceph.pool.client.write_bytes_sec | hostname, ceph_cluster, pool, service=ceph | Write bytes per second on the pool |
| ceph.pool.client.read_ops | hostname, ceph_cluster, pool, service=ceph | Read operations per second on the pool |
| ceph.pool.client.write_ops | hostname, ceph_cluster, pool, service=ceph | Write operations per second on the pool |
| ceph.pool.recovery.objects_per_sec | hostname, ceph_cluster, pool, service=ceph | Objects recovered per second on the pool |
| ceph.pool.recovery.bytes_per_sec | hostname, ceph_cluster, pool, service=ceph | Bytes recovered per second on the pool |
| ceph.pool.recovery.keys_per_sec | hostname, ceph_cluster, pool, service=ceph | Keys recovered per second on the pool |
| ceph.pool.recovery.objects | hostname, ceph_cluster, pool, service=ceph | Objects recovered on the pool |
| ceph.pool.recovery.bytes | hostname, ceph_cluster, pool, service=ceph | Bytes recovered on the pool |
| ceph.pool.recovery.keys | hostname, ceph_cluster, pool, service=ceph | Keys recovered on the pool |
| ceph.pools.count | hostname, ceph_cluster, service=ceph | Number of pools on the cluster |

## Certificate Expiration (HTTPS)
An extension to the Agent provides the ability to determine the expiration date of the certificate for the URL. The metric is days until the certificate expires

 default dimensions:
    url: url

A YAML file (cert_check.yaml) contains the list of urls to check. It also contains

The configuration of the certificate expiration check is done in YAML, and consists of two keys:

* init_config
* instances

The init_config section lists the global configuration settings, such as the Certificate Authority Certificate file, the ciphers to use, the period at which to output the metric and the url connection timeout (in seconds, floating-point number)

    $ ls -l `which ping` -rwsr-xr-x 1 root root 35712 Nov 8 2011 /bin/ping

```
init_config:
  ca_certs: /etc/ssl/certs/ca-certificates.crt
  ciphers: HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5
  collect_period: 3600
  timeout: 1.0
```

The instances section contains the urls to check.

```
instances:
- built_by: CertificateCheck
  url: https://somehost.somedomain.net:8333
- built_by: CertificateCheck
  url: https://somehost.somedomain.net:9696
```

The certicate expiration checks return the following metrics

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| https.cert_expire_days | url=supplied url being checked | The number of days until the certificate expires


There is a detection plugin that should be used to configure this extension. It is invoked as:

    $ monasca-setup -d CertificateCheck -a urls=https://somehost.somedomain.net:8333,https://somehost.somedomain.net:9696

The urls option is a comma separated list of urls to check.

These options can be set if desired:
* ca_certs: file containing the certificates for Certificate Authorities. The default is /etc/ssl/certs/ca-certificates.crt
* ciphers: list of ciphers to use.  default is HIGH:-aNULL:-eNULL:-PSK:RC4-SHA:RC4-MD5
* collect_period: Integer time in seconds between outputting the metric.  Since the metric is in days, it makes sense to output it at a slower rate. The default is 3600, once per hour
* timeout: Float time in seconds before timing out the connect to the url.  Increase if needed for very slow servers, but making this too long will increase the time this plugin takes to run if the server for the url is down. The default is 1.0 seconds


## Couch
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/couch.yaml.example) for how to configure the Couch plugin.

## Couchbase
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/couchbase.yaml.example) for how to configure the Couchbase plugin.

## Crash

### Overview
The crash plugin provides metrics for crash dumps present on the system. Currently, it only returns the number of crash dumps found plus the date-/timestamp of the most recent crash in a `value_meta` dictionary.

### Metrics
Only one metric is provided at the moment with a `hostname` dimension.

| Name             | Description                 | value_meta                       |
|------------------|-----------------------------|----------------------------------|
| crash.dump_count | Number of crash dumps found | {'latest': u'<date-/timestamp>'} |

### Configuration
The `monasca-setup` program will configure the Crash plugin if a crash kernel is loaded. The default directory where the plugin will look for crash dumps is /var/crash.

Sample config:

```
init_config:
  crash_dir: /var/crash

instances:
  - name: crash_stats

```


## Directory Checks
This section describes the directory check that can be performed by the Agent. Directory checks are used for gathering the total size of all the files under a specific directory. A YAML file (directory.yaml) contains the list of directory names to check. A Python script (directory.py) runs checks each host in turn to gather stats. Note: for sparse file, directory check is using its resident size instead of the actual size.

Similar to other checks, the configuration is done in YAML, and consists of two keys: init_config and instances. The former is not used by directory check, while the later contains one or more sets of directory names to check on. Directory check will sum the size of all the files under the given directory recursively.

Sample config:

```
init_config: null
instances:
- built_by: Directory
  directory: /var/log/monasca/agent
- built_by: Directory
  directory: /etc/monasca/agent
```

The directory checks return the following metrics:

| Metric Name | Dimensions |
| ----------- | ---------- |
| directory.size_bytes  | path, hostname, service |
| directory.files_count  | path, hostname, service |

## Docker
This plugin gathers metrics on docker containers.

A YAML file (docker.yaml) contains the url of the docker api to connect to and the root of docker that is used for looking for docker proc metrics.

For this check the user that is running the monasca agent (usually the mon-agent user) must be a part of the docker group

Also if you want to want to attach kubernetes dimensions to each metric you can set add_kubernetes_dimensions to true in the yaml file. This will set the pod_name and namespace.

Sample config:

Without kubernetes dimensions

```
init_config:
  docker_root: /
  socket_timeout: 5
instances:
  - url: "unix://var/run/docker.sock"
```

With kubernetes dimensions
```
init_config:
  docker_root: /
  socket_timeout: 5
instances:
  - url: "unix://var/run/docker.sock"
    add_kubernetes_dimensions: True
```

Note this plugin only supports one instance in the config file.

The docker check return the following metrics:

| Metric Name | Metric Type | Dimensions | Optional_dimensions (set if add_kubernetes_dimensions is true and container is running under kubernetes) | Semantics |
| ----------- | ----------- | ---------- | -------------------------------------------------------------------------------------------------------- | --------- |
| container.containers.running_count | Gauge | hostname | | Number of containers running on the host |
| container.cpu.system_time  | Gauge| hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The total time the CPU has executed system calls on behalf of the processes in the container |
| container.cpu.system_time_sec  | Rate | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The rate the CPU is executing system calls on behalf of the processes in the container |
| container.cpu.user_time  | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The total time the CPU is under direct control of the processes in this container |
| container.cpu.user_time_sec  | Rate | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The rate the CPU is under direct control of the processes in this container |
| container.cpu.utilization_perc | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The percentage of CPU used by the container |
| container.io.read_bytes  | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The total amount bytes read from the processes in the container |
| container.io.read_bytes_sec  | Rate | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The rate of bytes read from the processes in the container |
| container.io.write_bytes  | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The total amount bytes written from the processes in the container |
| container.io.write_bytes_sec  | Rate | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The rate of bytes written from the processes in the container |
| container.mem.cache | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace |The amount of cached memory that belongs to the container's processes |
| container.mem.rss  | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The amount of non-cached memory used by the container's processes |
| container.mem.swap  | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The amount of swap memory used by the processes in the container |
| container.mem.used_perc | Gauge | hostname, name, image | kubernetes_pod_name, kubernetes_namespace | The percentage of memory used out of the given limit of the container |
| container.net.in_bytes  | Gauge | hostname, name, image, interface | kubernetes_pod_name, kubernetes_namespace | The total amount of bytes received by the container per interface |
| container.net.in_bytes_sec  | Rate | hostname, name, image, interface | kubernetes_pod_name, kubernetes_namespace | The rate of bytes received by the container per interface |
| container.net.out_bytes  | Gauge | hostname, name, image, interface | kubernetes_pod_name, kubernetes_namespace | The total amount of bytes sent by the container per interface |
| container.net.out_bytes_sec  | Rate | hostname, name, image, interface | kubernetes_pod_name, kubernetes_namespace | The rate of bytes sent by the container per interface |


## Elasticsearch Checks
This section describes the Elasticsearch check that can be performed by the Agent.  The Elasticsearch check requires a configuration file called elastic.yaml to be available in the agent conf.d configuration directory.

Sample config:

```
init_config:
instances:
-   url: http://127.0.0.1:9200

```

The Elasticsearch checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| elasticsearch.docs.count | url, hostname, service=monitoring | The total number of docs including nested documents. |
| elasticsearch.docs.deleted | url, hostname, service=monitoring | The number of deleted docs. |
| elasticsearch.store.size | url, hostname, service=monitoring | The filesystem storage size. |
| elasticsearch.indexing.index.total | url, hostname, service=monitoring |  |
| elasticsearch.indexing.index.time | url, hostname, service=monitoring |  |
| elasticsearch.indexing.index.current | url, hostname, service=monitoring |  |
| elasticsearch.indexing.delete.total | url, hostname, service=monitoring |  |
| elasticsearch.indexing.delete.time | url, hostname, service=monitoring |  |
| elasticsearch.indexing.delete.current | url, hostname, service=monitoring |  |
| elasticsearch.get.total | url, hostname, service=monitoring |  |
| elasticsearch.get.time | url, hostname, service=monitoring |  |
| elasticsearch.get.current | url, hostname, service=monitoring |  |
| elasticsearch.get.exists.total | url, hostname, service=monitoring |  |
| elasticsearch.get.exists.time | url, hostname, service=monitoring |  |
| elasticsearch.get.missing.total | url, hostname, service=monitoring |  |
| elasticsearch.get.missing.time | url, hostname, service=monitoring |  |
| elasticsearch.search.query.total | url, hostname, service=monitoring |  |
| elasticsearch.search.query.time | url, hostname, service=monitoring |  |
| elasticsearch.search.query.current | url, hostname, service=monitoring |  |
| elasticsearch.search.fetch.total | url, hostname, service=monitoring |  |
| elasticsearch.search.fetch.time | url, hostname, service=monitoring |  |
| elasticsearch.search.fetch.current | url, hostname, service=monitoring |  |
| elasticsearch.merges.current | url, hostname, service=monitoring |  |
| elasticsearch.merges.current.docs | url, hostname, service=monitoring |  |
| elasticsearch.merges.current.size | url, hostname, service=monitoring |  |
| elasticsearch.merges.total | url, hostname, service=monitoring |  |
| elasticsearch.merges.total.time | url, hostname, service=monitoring |  |
| elasticsearch.merges.total.docs | url, hostname, service=monitoring |  |
| elasticsearch.merges.total.size | url, hostname, service=monitoring |  |
| elasticsearch.refresh.total | url, hostname, service=monitoring |  |
| elasticsearch.refresh.total.time | url, hostname, service=monitoring |  |
| elasticsearch.flush.total | url, hostname, service=monitoring |  |
| elasticsearch.flush.total.time | url, hostname, service=monitoring | The elasticsearch flush time. |
| elasticsearch.process.open_fd | url, hostname, service=monitoring | The number of open files descriptors on the machine. |
| elasticsearch.transport.rx_count | url, hostname, service=monitoring |  |
| elasticsearch.transport.tx_count | url, hostname, service=monitoring |  |
| elasticsearch.transport.rx_size | url, hostname, service=monitoring |  |
| elasticsearch.transport.tx_size | url, hostname, service=monitoring |  |
| elasticsearch.transport.server_open | url, hostname, service=monitoring |  |
| elasticsearch.thread_pool.bulk.active | url, hostname, service=monitoring | The number of active threads for bulk operations. |
| elasticsearch.thread_pool.bulk.threads | url, hostname, service=monitoring | The total number of threads for bulk operations. |
| elasticsearch.thread_pool.bulk.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for bulk operations. |
| elasticsearch.thread_pool.bulk.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for bulk operations. |
| elasticsearch.thread_pool.flush.active | url, hostname, service=monitoring | The number of active threads for flush operations. |
| elasticsearch.thread_pool.flush.threads | url, hostname, service=monitoring | The total number of threads for flush operations. |
| elasticsearch.thread_pool.flush.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for flush operations. |
| elasticsearch.thread_pool.flush.rejected | url, hostname, service=monitoring |  The number of rejected tasks of thread pool used for flush operations. |
| elasticsearch.thread_pool.generic.active | url, hostname, service=monitoring | The number of active threads for generic operations (i.e. node discovery). |
| elasticsearch.thread_pool.generic.threads | url, hostname, service=monitoring | The total number of threads for generic operations (i.e. node discovery). |
| elasticsearch.thread_pool.generic.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for generic operations. |
| elasticsearch.thread_pool.generic.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for generic operations. |
| elasticsearch.thread_pool.get.active | url, hostname, service=monitoring | The number of active threads for get operations. |
| elasticsearch.thread_pool.get.threads | url, hostname, service=monitoring | The total number of threads for get operations. |
| elasticsearch.thread_pool.get.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for get operations. |
| elasticsearch.thread_pool.get.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for get operations. |
| elasticsearch.thread_pool.index.active | url, hostname, service=monitoring | The number of active threads for indexing operations. |
| elasticsearch.thread_pool.index.threads | url, hostname, service=monitoring | The total number of threads for indexing operations. |
| elasticsearch.thread_pool.index.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for indexing operations. |
| elasticsearch.thread_pool.index.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for indexing operations. |
| elasticsearch.thread_pool.management.active | url, hostname, service=monitoring | The number of active threads for management operations. |
| elasticsearch.thread_pool.management.threads | url, hostname, service=monitoring | The total number of threads for management operations. |
| elasticsearch.thread_pool.management.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for management operations. |
| elasticsearch.thread_pool.management.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for management operations. |
| elasticsearch.thread_pool.merge.active | url, hostname, service=monitoring | The number of active threads for merging operation. |
| elasticsearch.thread_pool.merge.threads | url, hostname, service=monitoring | The total number of threads for merging operation. |
| elasticsearch.thread_pool.merge.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for merge operations. |
| elasticsearch.thread_pool.merge.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for merge operations. |
| elasticsearch.thread_pool.percolate.active | url, hostname, service=monitoring | The number of active threads for percolate operations. |
| elasticsearch.thread_pool.percolate.threads | url, hostname, service=monitoring | The total number of threads for percolate operations. |
| elasticsearch.thread_pool.percolate.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for percolate operations. |
| elasticsearch.thread_pool.percolate.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for percolate operations. |
| elasticsearch.thread_pool.refresh.active | url, hostname, service=monitoring | The number of active threads for refresh operations. |
| elasticsearch.thread_pool.refresh.threads | url, hostname, service=monitoring | The total number of threads for refresh operations. |
| elasticsearch.thread_pool.refresh.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for refresh operations. |
| elasticsearch.thread_pool.refresh.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for refresh operations. |
| elasticsearch.thread_pool.search.active | url, hostname, service=monitoring | The number of active threads for search operations. |
| elasticsearch.thread_pool.search.threads | url, hostname, service=monitoring | The total number of threads for search operations. |
| elasticsearch.thread_pool.search.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for search operations. |
| elasticsearch.thread_pool.search.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for search operations. |
| elasticsearch.thread_pool.snapshot.active | url, hostname, service=monitoring | The number of active threads for snapshot operations. |
| elasticsearch.thread_pool.snapshot.threads | url, hostname, service=monitoring | The total number of threads for snapshot operations. |
| elasticsearch.thread_pool.snapshot.queue | url, hostname, service=monitoring | The number of tasks in queue of thread pool used for snapshot operations. |
| elasticsearch.thread_pool.snapshot.rejected | url, hostname, service=monitoring | The number of rejected tasks of thread pool used for snapshot operations. |
| elasticsearch.http.current_open | url, hostname, service=monitoring | Current number of opened HTTP connections. |
| elasticsearch.http.total_opened | url, hostname, service=monitoring | Max number of HTTP connections. |
| jvm.gc.concurrent_mark_sweep.count | url, hostname, service=monitoring |  |
| jvm.gc.concurrent_mark_sweep.collection_time | url, hostname, service=monitoring |  |
| jvm.gc.par_new.count | url, hostname, service=monitoring | ParNew count. |
| jvm.gc.par_new.collection_time | url, hostname, service=monitoring | ParNew pauses time. |
| jvm.mem.heap_committed | url, hostname, service=monitoring | The allocated amount of heap memory. |
| jvm.mem.heap_used | url, hostname, service=monitoring | The amount of heap memory which is actually in use. |
| jvm.mem.non_heap_committed | url, hostname, service=monitoring | The allocated amount of non-heap memory. |
| jvm.mem.non_heap_used | url, hostname, service=monitoring | The amount of non-heap memory which is actually in use. |
| jvm.threads.count | url, hostname, service=monitoring | Current number of live daemon and non-daemon threads. |
| jvm.threads.peak_count | url, hostname, service=monitoring | Peak live thread count since the JVM started or the peak was reset. |
| elasticsearch.number_of_nodes | url, hostname, service=monitoring | Number of nodes. |
| elasticsearch.number_of_data_nodes | url, hostname, service=monitoring | Number of data nodes. |
| elasticsearch.active_primary_shards | url, hostname, service=monitoring | Indicates the number of primary shards in your cluster. This is an aggregate total across all indices. |
| elasticsearch.active_shards | url, hostname, service=monitoring |  Aggregate total of all shards across all indices, which includes replica shards. |
| elasticsearch.relocating_shards | url, hostname, service=monitoring | Shows the number of shards that are currently moving from one node to another node. |
| elasticsearch.initializing_shards | url, hostname, service=monitoring | The count of shards that are being freshly created. |
| elasticsearch.unassigned_shards | url, hostname, service=monitoring | The number of unassigned shards from the master node. |
| elasticsearch.cluster_status | url, hostname, service=monitoring | Cluster health status. |

### Additional links

* [List of available thread pools](https://www.elastic.co/guide/en/elasticsearch/reference/current/modules-threadpool.html)

## File Size
This section describes the file size check that can be performed by the Agent. File size checks are used for gathering the size of individual files or the size of each file under a specific directory. The agent supports additional functionality through the use of Python scripts. A YAML file (file_size.yaml) contains the list of file directory names and file names to check. A Python script (file_size.py) runs checks each host in turn to gather stats.

Similar to other checks, the configuration is done in YAML, and consists of two keys: init_config and instances. The former is not used by file_size, while the later contains one or more sets of file directory name and file names to check, plus optional parameter recursive. When recursive is true and file_name is set to '*', file_size check will take all the files under the given directory recursively.

Sample config:

```
init_config: null
instances:
- built_by: FileSize
  directory_name: /var/log/monasca/agent/
  file_names:
  - '*'
  recursive: false
- built_by: FileSize
  directory_name: /var/log/monasca/api
  file_names:
  - monasca-api.log
  - request.log
  recursive: false
- built_by: FileSize
  directory_name: /var/log/monasca/notification
  file_names:
  - notification.log
  recursive: false
```

The file_size checks return the following metrics:

| Metric Name | Dimensions |
| ----------- | ---------- |
| file.size_bytes  | file_name, directory_name, hostname, service |

## GearmanD
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/gearmand.yaml.example) for how to configure the GearmandD plugin.

## Gunicorn
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/gunicorn.yaml.example) for how to configure the Gunicorn plugin.

## HAProxy
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/haproxy.yaml.example) for how to configure the HAProxy plugin.

## HDFS
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/hdfs.yaml.example) for how to configure the HDFS plugin.

## Host Alive
An extension to the Agent can provide basic "aliveness" checks of other systems, verifying that the remote host (or device) is online. This check currently provides two methods of determining connectivity:

* ping (ICMP)
* SSH (banner test, port 22 by default)

Of the two, the SSH check provides a more comprehensive test of a remote system's availability, since it checks the banner returned by the remote host. A server in the throes of a kernel panic may still respond to ping requests, but would not return an SSH banner. It is suggested, therefore, that the SSH check be used instead of the ping check when possible.

A YAML file (host_alive.yaml) contains the list of remote hosts to check, including the host name and testing method (either 'ping' or 'ssh'). A Python script (host_alive.py) runs checks against each host in turn, returning a 0 on success and a 1 on failure in the result sent through the Forwarder and on the Monitoring API.

Because the Agent itself does not run as root, it relies on the system ping command being suid root in order to function.

The configuration of the host alive check is done in YAML, and consists of two keys:

* init_config
* instances

The init_config section lists the global configuration settings, such as SSH port, SSH connection timeout (in seconds, floating-point number), and ping timeout (in seconds, integer).

    $ ls -l `which ping` -rwsr-xr-x 1 root root 35712 Nov 8 2011 /bin/ping

```
init_config:
    ssh_port: 22

    # ssh_timeout is a floating-point number of seconds
    ssh_timeout: 0.5

    # ping_timeout is an integer number of seconds
    ping_timeout: 1
```

The instances section contains the hostname/IP to check, and the type of check to perform, which is either ssh or ping.

```
    # alive_test can be either "ssh" for an SSH banner test (port 22)
    # or "ping" for an ICMP ping test instances:
  - name: ssh to somehost
    host_name: somehost.somedomain.net
    alive_test: ssh

  - name: ping gateway
    host_name: gateway.somedomain.net
    alive_test: ping

  - name: ssh to 192.168.0.221
    host_name: 192.168.0.221
    alive_test: ssh
```

To handle the case where the target system has multiple IP Addresses and the network name to be used for
liveness checking is not the same as the usual name used to identify the server in Monasca,
an additional target_hostname parameter can be configured. It is the network hostname or IP
Address to check instead of host_name. The hostname dimension will always be set to the value of
host_name even if target_hostname is specified. A dimension target_hostname will be added
with the value of target_hostname if it is different from host_name.

To simplify configuring multiple checks, when the host_alive detection plugin is configured, hostname can
be a comma separated list. Instances will be created for each value. target_hostname can also
be a comma separated list, however, empty values for an individual entry can be given if there is
no target_hostname for a given hostname entry.

Here is an example of configuring target_hostname :
```
  - name: ping somenode
    host_name: somenode
    target_hostname: somenode.mgmt.net
    alive_test: ssh
```

The host alive checks return the following metrics

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| host_alive_status | observer_host=fqdn of checking host, hostname=supplied hostname being checked, target_hostname=the network hostname or IP Address to check instead of host_name; only added if different than hostname, test_type=ping or ssh | Status of remote host(device) is online or not. (0=online, 1=offline)


Also in the case of an error the value_meta contains an error message.

The default dimensions are:
   observer_host: fqdn
   hostname: fqdn | supplied
   target_hostname: Set to target_hostname only if that is different than host_name
   test_type: ping | ssh | Unrecognized alive_test

default value_meta
   error: error_message

## HTTP (endpoint status)
This section describes the http endpoint check that can be performed by the Agent. Http endpoint checks are checks that perform simple up/down checks on services, such as HTTP/REST APIs. An agent, given a list of URLs, can dispatch an http request and report to the API success/failure as a metric.

 default dimensions:
    url: endpoint

 default value_meta
    error: error_message

The Agent supports additional functionality through the use of Python scripts. A YAML file (http_check.yaml) contains the list of URLs to check (among other optional parameters). A Python script (http_check.py) runs checks each host in turn, returning a 0 on success and a 1 on failure in the result sent through the Forwarder and on the Monitoring API.

Similar to other checks, the configuration is done in YAML, and consists of two
keys: `init_config` and `instances`. In the former, you can provide Keystone
configuration for checks to retrieve token for authentication that will be used
for all checks. While the later contains one or more URLs to check, plus
optional parameters like a timeout, username/password, pattern to match against
the HTTP response body, whether or not to include the HTTP response
in the metric (as a 'detail' dimension), whether or not to also record
the response time, and more.
If the endpoint being checked requires authentication, there are two options.
First, a username and password supplied in the instance options will be used
by the check for authentication. Alternately, the check can retrieve
a keystone token for authentication. Specific keystone information can
be provided for all checks in `init_config` section, or if it's not
provided there, the information from the agent config will be used.
DEPRECATED: providing Keystone configuration in each instance.

Sample config:

```
init_config:
    keystone_config:
        keystone_url: http://endpoint.com/v3/
        project_name: project
        username: user
        password: password

instances:
    url: http://192.168.0.254/healthcheck
    timeout: 1
    include_content: true
    collect_response_time: true
    match_pattern: '.*OK.*OK.*OK.*OK.*OK'
```

The http_status checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| http_status  | url, detail | The status of the http endpoint call (0 = success, 1 = failure)
| http_response_time  | url | The response time in seconds of the http endpoint call


## HTTP Metrics
This section describes the http metrics check that can be performed by the agent. Http metrics checks are checks that retrieve metrics from any url returning a json formatted response. An agent, given a list of URLs, can dispatch an http request and parse the desired metrics from the json response.

 default dimensions:
    url: endpoint

 default value_meta
    error: error_message

Similar to other checks, the configuration is done in YAML (http_metrics.yaml), and consists of two keys: init_config and instances.  The former is not used by http_metrics, while the later contains one or more URLs to check, plus optional parameters like a timeout, username/password, whether or not to also record the response time, and a whitelist of metrics to collect. The whitelist should consist of a name, path, and type for each metric to be collected. The name is what the metric will be called when it is reported. The path is a string of keys separated by '/' where the metric value resides in the json response. The type is how you want the metric to be recorded (gauge, counter, histogram, rate, set). A gauge will store and report the value it find with no modifications. A counter will increment itself by the value it finds. A histogram will store values and return the calculated max, median, average, count, and percentiles. A rate will return the difference between the last two recorded samples divided by the interval between those samples in seconds. A set will record samples and return the number of unique values in the set.
If the endpoint being checked requires authentication, there are two options. First, a username and password supplied in the instance options will be used by the check for authentication. Alternately, the check can retrieve a keystone token for authentication. Specific keystone information can be provided for each check, otherwise the information from the agent config will be used.

```
init_config:

instances:
       url: http://192.168.0.254/metrics
       timeout: 1
       collect_response_time: true
       whitelist:
              name: jvm.memory.total.max,
              path: gauges/jvm.memory.total.max/value
              type: gauge
```

## InfluxDB

Auto-detection for InfluxDB plugin comes with two checks enabled:

* process monitoring with following configuration
```python
{
    'detailed': True,
    'search_string': ['influxd'],
    'exact_match': False,
    'name': 'influxd',
    'dimensions': {
        'component': 'influxdb',
        'service': 'influxdb'
    }
}
```
* http_check monitoring
```python
{
    'name': 'influxdb',
    'url': 'http://127.0.0.1:8086/ping'
}
```

    InfluxDB does expose internal metrics on its own, however
    they are subject to extend influxdb auto-detection capabilities
    in future

## InfluxDB-Relay
**InfluxDB-Relay** does not expose any internal metrics on its own, however
auto-detection plugin configures two checks on behalf of it:


* process monitoring with following configuration
```python
{
    'detailed': True,
    'search_string': ['influxdb-relay'],
    'exact_match': False,
    'name': 'influxdb-relay',
    'dimensions': {
        'component': 'influxdb-relay',
        'service': 'influxdb'
    }
}
```
* http_check monitoring
```python
{
    'name': 'influxdb-relay',
    'url': 'http://127.0.0.1:9096/ping'
}
```

## IIS
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/iis.yaml.example) for how to configure the IIS plugin.

## Jenkins
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/jenkins.yaml.example) for how to configure the Jenkins plugin.

## JsonPlugin
This plugin allows you to report metrics by simply writing the metrics to a file. The plugin reads the file
and sends the metrics to Monasca.

### Simple Reporting

The simplest approach is to create a file in the /var/cache/monasca_json_plugin directory. The file should
contain a list of metrics in JSON format as shown in the following example. The file must have
a ".json" extension in the name.

Simple Example -- /var/cache/monasca_json_plugin/my-metrics-file.json:
```
[
   {"name": "metric1", "value": 10.1, "timestamp": 1475596165},
   {"name": "metric2", "value": 12.3, "timestamp": 1475596165}
]
```

In the above example, the "name", "value" and "timestamp" of each measurement is reported. The following keys are available:

| Key | Description |
| ----------- | ---------- |
| name  | Required. The name of the metric. The key "metric" may be used instead of "name". |
| value | Required. The value of the measurement. This is a floating point number. |
| timestamp | Optional (if replace_timestamps is true; see below); otherwise required. The time of the measurement. Uses UNIX time epoch value. Note: this is seconds, not mulliseconds, since the epoch.|
| dimensions | Optional. Dimensions of the metric as a set of key/value pairs. |
| value_meta | Optional. Value meta of the metric as a set of key/value pairs. |

### Writing and Locking the Metrics File

You should take an exclusive lock on the file while you write new metrics
(this plugin takes a shared lock). You must close or flush the file
after writing new data to make sure the data is written to the file.

Example of writing metrics file:

```
metric_data = [{"name": "metric1", "value": 10.1, "timestamp": time.time()}]
max_retries = 10
delay = 0.02
attempts = 0
with open('/var/cache/monasca_json_plugin/my-metrics-file.json', 'w') as fd:
    while True:
        attempts += 1
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except IOError as err:
            if (err.errno not in [errno.EWOULDBLOCK, errno.EACCES] or
                    attempts > max_retries):
                raise
        time.sleep(delay * attempts)
    fd.write(json.dumps(metric_data))
```

### Additional Directives

You can add additional directives to the JSON file as shown in the following example:

Additional Directives Example:
```
{
   "replace_timestamps": false,
   "stale_age": 300,
   "measurements": [
      {"name": "metric1", "value": 10.1, "timestamp": 1475596165, "dimensions": {"path": "/tmp"}},
      {"name": "metric2", "value": 12.3, "timestamp": 1475596165, "value_meta": {"msg": "hello world"}}
   ]
}

```

The additional directives are described in the following table. The directives are optional.

| Directive | Description |
| --------- | ----------- |
| replace_timestamps | If true, the timestamps are ignored. Instead, the timestamp of the measurement is set to the current time. Default is false.|
| stale_age | The number of seconds after which metrics are considered stale. This stops measurements from a file that is not updating from being reported to Monasca. It defaults to 4 minutes.|

The main purpose of the stale_age directive is to detect if the JSON file stops updating (e.g., due to a bug or system failure). See the description of the monasca.json_plugin.status metric below.

The main purpose of the replace_timestamps directive is where the mechanism to write the JSON file runs infrequently or erratically. Every time Monasa Agent runs, the metrics
are reported with the current time -- whether or not the file is updated. In this mode, you do not need to supply a timestamp (in fact, any timestamp you include is ignored). Also the
stale_age directive is also ignored.

### Custom JSON file locations

To use the built-in /var/cache/monasca_json_plugin directory, your application must be
able to create and write files to that directory. If this is not possible, you can
write the JSON file(s) to a different file path. An example of this configuration
is in [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/json_plugin.yaml.example).

The Monasca Agent user must be able to read the files.

### The monasca.json_plugin.status Metric

The plugin reports a metric called "monasca.json_plugin.status". A single metric is reported by the
JSON plugin. If there are problems, you can examine the value_meta. It will contain a list
of problem paths/messages. You to create an alarm to trigger if there is
a problem processing any JSON file.

The monasca.json_plugin.status metric has the following information:

| Field     | Description |
| --------- | ----------- |
| name      | "monasca.json_plugin.status" -- the name of the metric |
| value      | A value of 0.0 is normal -- there are no issues processing all JSON files. A value of 1.0 indicates there is a problem. |
| value_meta | Value meta is only present when the value is 1.0. The value meta contains a "msg" key indicating the problem. |

The value_meta/msg reports problems such as:

- Failure to open the JSON file
- Invalid JSON syntax
- That metrics are older than the stale_age


## Kafka Checks
This section describes the Kafka check that can be performed by the Agent.  The Kafka check requires a configuration file called kafka_consumer.yaml to be available in the agent conf.d configuration directory.

Sample config:

```yml
init_config:

instances:
- built_by: Kafka
  consumer_groups:
    1_metrics:
      metrics: []
    thresh-event:
      events: []
    thresh-metric:
      metrics: []
  kafka_connect_str: 192.168.10.6:9092
  name: 192.168.10.6:9092
  per_partition: false
```

The Kafka checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| kafka.broker_offset | topic, service, component, partition, hostname | broker offset |
| kafka.consumer_offset | topic, service, component, partition, consumer_group, hostname | consumer offset |
| kafka.consumer_lag | topic, service, component, partition, consumer_group, hostname | consumer offset lag from broker offset |

## Kubernetes

This plugin collects metrics about containers (optionally) and pods on a kubernetes node.

The plugin collects metrics on a kubernetes node by going to the kubelet on the node to get all pod data. Included in that is containers configured under each pod and metadata about each.

It then goes to cAdvisor to get all docker container metrics and metadata associated with it. The plugin then does a comparison of the containers collected from cAdvisor and the containers defined from the kubelet.

If a container is defined to be apart of a pod it will take the metadata from the kubelet as dimensions (so it can get all of the kuberenetes associated tags), if it is not apart of a pod it will set the dimensions from the cAdvisor metadata.

When setting the kubernetes configuration there is a parameter "kubernetes_labels" where it will look for kubernetes tags that are user defined to use as dimensions for pod/container metrics. By default it will look for the label 'app'.

For each pod that we detect we will also aggregate container metrics that belong to that pod to output pod level metrics.

The kubernetes node that the plugin will connect to can be configured in two different ways. The first being setting the host variable in the instance. The other being setting the derive_host to True under the instance. We derive the host by first using the kubernetes environment variables to get the api url (assuming we are running in a kubernetes container). Next we use the container's pod name and namespace (passed in as environment variables to the agents container - see kubernetes example yaml file) with the api url to hit the api to get the pods metadata including the host it is running on. That is the host we use.

If derive_host is set to true the plugin will also hit the API when the owner of a Kubernetes pod is a replicaset (taken from the kubelet) to see if it is under a deployment.

Also by default we will not report the container metrics due to throughput it generates. If you want the container metrics you can set the configuration parameter "report_container_metrics" to True.

Sample configs:

Without custom labels and host being manually set:

```
init_config:
    # Timeout on GET requests
    connection_timeout: 3
    report_container_metrics: False
instances:
    # Set to the host that the plugin will use when connecting to cAdvisor/kubelet
    - host: "127.0.0.1"
      cadvisor_port: 4194
      kublet_port: 10255
```

With custom labels and host being manually set:

```
init_config:
    # Timeout on GET requests
    connection_timeout: 3
    report_container_metrics: False
instances:
    # Set to the host that the plugin will use when connecting to cAdvisor/kubelet
    - host: "127.0.0.1"
      cadvisor_port: 4194
      kublet_port: 10255
      kubernetes_labels: ['k8s-app', 'version']
```

With custom labels and derive host being set:

```
instances:
    # Set to the host that the plugin will use when connecting to the Kubernetes API
    - host: "127.0.0.1"
      kubernetes_api_port: 8080
      kubernetes_labels: ['k8s-app', 'version']
```

With custom labels and derive api url set to True:

```
init_config:
    # Timeout on GET requests
    connection_timeout: 3
    report_container_metrics: False
instances:
    - derive_host: True
      cadvisor_port: 4194
      kublet_port: 10255
      kubernetes_labels: ['k8s-app', 'version']
```

**Note** this plugin only supports one instance in the config file.

The kubernetes check returns the following metrics (note that for containers running under kubernetes and pod metrics
 can also have dimensions set from the configuration option 'kubernetes_labels' which by default will include 'app')

**Note** the container metrics will only be reported when the report_container_metrics is true

Common Container metrics between containers running underneath kubernetes and standalone:

| Metric Name | Dimensions if owned by a kubernetes pod | Dimensions if running standalone from kubernetes | Semantics |
| ----------- | --------------------------------------- | ------------------------------------------------ | --------- |
| container.cpu.system_time | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Cumulative system CPU time consumed in core seconds
| container.cpu.system_time_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname | Rate of system CPU time consumed in core seconds
| container.cpu.total_time | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Cumulative CPU time consumed in core seconds
| container.cpu.total_time_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Rate of CPU time consumed in core seconds
| container.cpu.user_time | image, container_name, pod_name, namespace, unit | image, container_name, hostname, unit | Cumulative user cpu time consumed in core seconds
| container.cpu.user_time_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Rate of user CPU time consumed in core seconds
| container.fs.total_bytes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of bytes available
| container.fs.usage_bytes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of bytes consumed
| container.fs.writes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Cumulative number of completed writes
| container.fs.writes_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of completed writes per a second
| container.fs.reads | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Cumulative number of completed reads
| container.fs.reads_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit| Number of completed reads per a second
| container.fs.io_current | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of i/o operations in progress
| container.mem.cache_bytes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of bytes of page cache memory
| container.mem.rss_bytes | image, container_name, pod_name, namespace, unit | image, container_name, hostname, unit | Size of rss in bytes
| container.mem.swap_bytes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Swap usage in memory in bytes
| container.mem.used_bytes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Current memory in use in bytes
| container.mem.fail_count | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of memory usage limit hits
| container.net.in_bytes | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Total network bytes received
| container.net.in_bytes_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of network bytes received per second
| container.net.in_dropped_packets | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Total inbound network packets dropped
| container.net.in_dropped_packets_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of inbound network packets dropped per second
| container.net.in_errors | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Total network errors on incoming network traffic
| container.net.in_errors_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of network errors on incoming network traffic per second
| container.net.in_packets | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Total network packets received
| container.net.in_packets_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of network packets received per second
| container.net.out_bytes | image, container_name, pod_name, namespace, unit | image, container_name, hostname, unit | Total network bytes sent
| container.net.out_bytes_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of network bytes sent per second
| container.net.out_dropped_packets | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Total outbound network packets dropped
| container.net.out_dropped_packets_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of outbound network packets dropped per second
| container.net.out_errors | image, container_name, pod_name, namespace, unit | image, container_name, hostname, unit | Total network errors on outgoing network traffic
| container.net.out_errors_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of network errors on outgoing network traffic per second
| container.net.out_packets | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Total network packets sent
| container.net.out_packets_sec | image, container_name, pod_name, namespace, unit  | image, container_name, hostname, unit | Number of network packets sent per second

Container metrics specific to containers running under kubernetes:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| container.ready_status | image, name, pod_name, namespace | Ready status of the container defined by the ready probe
| container.restart_count | image, name, pod_name, namespace | Restart count of the container
| container.cpu.limit | image, name, pod_name, namespace | Limit in CPU cores for the container
| container.memory.limit_bytes | image, name, pod_name, namespace | Limit of memory in bytes for the container
| container.request.cpu | image, name, pod_name, namespace | Amount of CPU cores requested by the container
| container.request.memory_bytes | image, name, pod_name, namespace | Amount of memory in bytes requested by the container

Kubelet Metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| kubelet.health_status | hostname | Health status of the kubelet api

Pod Metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| pod.cpu.system_time | pod_name, namespace | Cumulative system CPU time consumed in core seconds
| pod.cpu.system_time_sec | pod_name, namespace | Rate of system CPU time consumed in core seconds
| pod.cpu.total_time | pod_name, namespace | Cumulative CPU time consumed in core seconds
| pod.cpu.total_time_sec | pod_name, namespace | Rate of CPU time consumed in core seconds
| pod.cpu.user_time | pod_name, namespace | Cumulative user cpu time consumed in core seconds
| pod.cpu.user_time_sec | pod_name, namespace | Rate of user CPU time consumed in core seconds
| pod.mem.cache_bytes | pod_name, namespace | Number of bytes of page cache memory
| pod.mem.fail_count | pod_name, namespace | Number of memory usage limit hits
| pod.mem.rss_bytes | pod_name, namespace | Size of rss in bytes
| pod.mem.swap_bytes | pod_name, namespace | Swap usage in memory in bytes
| pod.mem.used_bytes | pod_name, namespace | Current memory in use in bytes
| pod.net.in_bytes | pod_name, namespace | Total network bytes received
| pod.net.in_bytes_sec | pod_name, namespace | Number of network bytes received per second
| pod.net.in_dropped_packets | pod_name, namespace | Total inbound network packets dropped
| pod.net.in_dropped_packets_sec | pod_name, namespace | Number of inbound network packets dropped per second
| pod.net.in_errors | pod_name, namespace | Total network errors on incoming network traffic
| pod.net.in_errors_sec | pod_name, namespace |  Number of network errors on incoming network traffic per second
| pod.net.in_packets | pod_name, namespace | Total network packets received
| pod.net.in_packets_sec | pod_name, namespace | Number of network packets received per second
| pod.net.out_bytes | pod_name, namespace | Total network bytes sent
| pod.net.out_bytes_sec | pod_name, namespace | Number of network bytes sent per second
| pod.net.out_dropped_packets | pod_name, namespace | Total outbound network packets dropped
| pod.net.out_dropped_packets_sec | pod_name, namespace | Number of outbound network packets dropped per second
| pod.net.out_errors | pod_name, namespace | Total network errors on outgoing network traffic
| pod.net.out_errors_sec | pod_name, namespace | Number of network errors on outgoing network traffic per second
| pod.net.out_packets | pod_name, namespace | Total network packets sent
| pod.net.out_packets_sec | pod_name, namespace | Number of network packets sent per second
| pod.restart_count | pod_name, namespace | Aggregated restart count of the pod's containers
| pod.phase | pod_name, namespace | Current phase of the pod. See table below for mapping


There is also additional Kubernetes dimensions for the Container and Pod metrics depending on the owner for the pod:

| Owner | Dimension Name | Notes |
| ----------- | ---------- | --------- |
| ReplicationController | replication_controller |
| ReplicaSet | replica_set |
| DaemonSet | daemon_set |
| Deployment| deployment | Only will be set if derive_host is set to true as it needs to connect to the API to see if the ReplicaSet is under a deployment

Pod Phase Mapping:

| Metric Value | Phase |
| ------------ | ----- |
| 0 | Succeeded |
| 1 | Running |
| 2 | Pending |
| 3 | Failed |
| 4 | Unknown |

## Kubernetes_API

This plugin collects metrics from the kubernetes api on kubernetes components, nodes, deployments and replication controllers.

When setting the kubernetes configuration there is a parameter "kubernetes_labels" where it will look for kubernetes tags that are user defined to use as dimensions for replication controller and deployment metrics.

There are two ways you can configure the plugin to connect to the kubernetes api. Either by setting the host and port or by setting the derive_api_url to True. If deriving the plugin sets the kubernetes api url by looking at the environment variables. (This should be used if the agent is running in a kubernetes container)

Sample configs:

```
instances:
    - derive api url: True
      kubernetes_labels: ['k8s-app', 'version']
```

Note this plugin only supports one instance in the config file.

Metrics (Note for replication controller and deployment metrics they can also have custom dimensions set from the configuration option 'kubernetes_labels')

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| kubernetes.api.health_status | | Health status of the api
| kubernetes.component_status | component_name | Status of cluster's components
| kubernetes.node.out_of_disk | hostname | The node is out of disk
| kubernetes.node.memory_pressure | hostname | Available memory on the node has satisfied an eviction threshold
| kubernetes.node.disk_pressure | hostname | Available disk space and inodes on either the node’s root filesystem or image filesystem has satisfied an eviction threshold
| kubernetes.node.ready_status | hostname | The ready status of the kubernetes node
| kubernetes.node.allocatable.memory_bytes | hostname, unit | Total allocatable memory in bytes available for scheduling on the node
| kubernetes.node.allocatable.cpu | hostname, unit | Total allocatable cpu cores available for scheduling on the node
| kubernetes.node.allocatable.pods | hostname | Total allocatable pods available for scheduling on the node
| kubernetes.node.capacity.memory_bytes | hostname, unit | Total memory on the node
| kubernetes.node.capacity.cpu | hostname, unit | Total amount of cpu cores on the node
| kubernetes.node.capacity.pods | hostname | Total amount of pods that could be run on the node
| kubernetes.deployment.available_replicas | deployment, namespace  | The number of available replicas for the deployment
| kubernetes.deployment.replicas | deployment, namespace  | The number of replicas for the deployment
| kubernetes.deployment.unavailable_replicas | deployment, namespace  | The number of unavailable replicas for the deployment
| kubernetes.deployment.updated_replicas | deployment, namespace  | The number of updated replicas for the deployment
| kubernetes.replication.controller.ready_replicas | replication_controller, namespace | The number of ready replicas for the replication controller
| kubernetes.replication.controller.replicas | replication_controller, namespace  | The number of replicas for the replication controller

## KyotoTycoon
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/kyototycoon.yaml.example) for how to configure the KyotoTycoon plugin.

## Libvirt VM Monitoring

Complete documentation of the Libvirt VM monitoring plugin can be found in [the Libvirt.md document](https://github.com/openstack/monasca-agent/blob/master/docs/Libvirt.md).

## Open vSwitch Neutron Router Monitoring

Complete documentation of the Open vSwitch Neutron Router monitoring plugin can be found in [the Ovs.md document](https://github.com/openstack/monasca-agent/blob/master/docs/Ovs.md).

## Lighttpd
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/lighttpd.yaml.example) for how to configure the Lighttpd plugin.

## Mcache
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/mcache.yaml.example) for how to configure the Mcache plugin.

## MK Livestatus
[MK Livestatus](http://mathias-kettner.com/checkmk_livestatus.html) is a Nagios Event Broker, allowing access to Nagios host and service data through a socket query.  The Monasca Agent `mk_livestatus` plugin is a way to access Nagios data and commit it to Monasca.  Possible use cases of this plugin include:
  * A way to evaluate Monasca with identical metrics to Nagios, providing an apples-to-apples comparison
  * A gentle migration from Nagios to Monasca, where both monitoring processes can exist simultaneously during Nagios decommissioning
  * A turnkey solution for rapidly converting an existing Nagios installation to Monasca, where the Nagios infrastructure can remain indefinitely

The `mk_livestatus` plugin will be installed during `monasca-setup` if a Nagios/Icinga configuration is found, the MK Livestatus broker_module is installed, and the livestatus socket can be accessed.  The `monasca-agent` user will need read access to the socket file in order to function, and a message to this effect will be included in `monasca-setup` output if the socket exists but `monasca-agent` cannot read it.

The configuration file (`/etc/monasca/agent/conf.d/mk_livestatus.yaml` by default) allows for a level of customization of both host and service checks.
  * Service checks
    * *name* - (Required) Monasca metric name to assign
    * *check_type* - (Required) "service" (as opposed to "host" below)
    * *display_name* - (Required) Name of the check as seen in Nagios
    * *host_name* - (Optional) Limit Monasca metrics of this check to the specified host name (as seen in Nagios).
    * *dimensions* - (Optional) Extra Monasca dimensions to include, in `{'key': 'value'}` format
  * Host checks
    * *name* - (Required) Monasca metric name to assign
    * *check_type* - (Required) "host" (as opposed to "service" above)
    * *host_name* - (Optional) Limit Monasca metrics of this check to the specified host name (as seen in Nagios).
    * *dimensions* - (Optional) Extra Monasca dimensions to include, in `{'key': 'value'}` format

If *host_name* is not specified, metrics for all hosts will be reported.

This configuration example shows several ways to specify instances:
```
init_config:
    # Specify the path to the mk_livestatus socket
    socket_path: /var/lib/icinga/rw/live

instances:

    # One service on one host
    - name:           nagios.check_http_status
      check_type:     service
      display_name:   HTTP
      host_name:      web01.example.net

    # One service on all hosts
    - name:           nagios.process_count_status
      check_type:     service
      display_name:   Total Processes

    # One service on all hosts with extra dimensions
    - name:           nagios.check_http_status
      check_type:     service
      display_name:   HTTP
      dimensions:     { 'group': 'webservers' }

    # All services on all hosts
    # These will be assigned metric names automatically, based on display_name
    - check_type:     service

    # One host
    - name:           nagios.host_status
      check_type:     host
      host_name:      web01.example.net

    # All hosts
    - name:           nagios.host_status
      check_type:     host
```

## Mongo
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/mongo.yaml.example) for how to configure the Mongo plugin.

## MySQL Checks
This section describes the mySQL check that can be performed by the Agent.  The mySQL check also supports MariaDB.  The mySQL check requires a configuration file called mysql.yaml to be available in the agent conf.d configuration directory.

Sample config: defaults_file: /root/.my.cnf
```
[client]
host=padawan-ccp-c1-m1-mgmt
user=root
password=pass
```
##### Note
Be assured that the password is set properly. As default monasca-agent expects password without quotation marks. Otherwise monasca-setup returns an error about inability to connect to MySQL with given password.

Instance variables can be passed via command line arguments
to the monasca-setup -d mysql command.
The instance config files are built by the detection plugin.

```
init_config:
Example clear connect:
instances:
- built_by: MySQL
  name: padawan-ccp-c1-m1-mgmt
  pass: secretpass
  port: 3306
  server: padawan-ccp-c1-m1-mgmt
  user: root

Example ssl connect:
instances:
- built_by: MySQL
  name: padawan-ccp-c1-m1-mgmt
  pass: secretpass
  port: 3306
  server: padawan-ccp-c1-m1-mgmt
  ssl_ca: /etc/ssl/certs/ca-certificates.crt
  user: root
```

Almost metrics show the server status variables in MySQL or MariaDB.  The others are calculated by the server status variables of MySQL or MariaDB.  For details of the server status variables, please refer the documents of MySQL or MariaDB.
The mySQL checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| mysql.performance.questions | hostname, mode, service=mysql | Corresponding to "Question" of the server status variable. |
| mysql.performance.qcache_hits | hostname, mode, service=mysql | Corresponding to "Qcache_hits" of the server status variable. |
| mysql.performance.open_files | hostname, mode, service=mysql | Corresponding to "Open_files" of the server status variable. |
| mysql.performance.created_tmp_tables | hostname, mode, service=mysql | Corresponding to "Created_tmp_tables" of the server status variable. |
| mysql.performance.user_time | hostname, mode, service=mysql | The CPU user time for DB's performance, in seconds. |
| mysql.performance.com_replace_select | hostname, mode, service=mysql | Corresponding to "Com_replace_select" of the server status variable. |
| mysql.performance.kernel_time | hostname, mode, service=mysql | The kernel time for DB's performance, in seconds. |
| mysql.performance.com_insert | hostname, mode, service=mysql | Corresponding to "Com_insert" of the server status variable. |
| mysql.performance.threads_connected | hostname, mode, service=mysql | Corresponding to "Threads_connected" of the server status variable. |
| mysql.performance.com_update_multi | hostname, mode, service=mysql | Corresponding to "Com_update_multi" of the server status variable. |
| mysql.performance.table_locks_waited | hostname, mode, service=mysql | Corresponding to "Table_locks_waited" of the server status variable. |
| mysql.performance.com_insert_select | hostname, mode, service=mysql | Corresponding to "Com_insert_select" of the server status variable. |
| mysql.performance.slow_queries | hostname, mode, service=mysql | Corresponding to "Slow_queries" of the server status variable. |
| mysql.performance.com_delete | hostname, mode, service=mysql | Corresponding to "Com_delete" of the server status variable. |
| mysql.performance.com_select | hostname, mode, service=mysql | Corresponding to "Com_select" of the server status variable. |
| mysql.performance.queries | hostname, mode, service=mysql | Corresponding to "Queries" of the server status variable. |
| mysql.performance.created_tmp_files | hostname, mode, service=mysql | Corresponding to "Created_tmp_files" of the server status variable. |
| mysql.performance.com_update | hostname, mode, service=mysql | Corresponding to "Com_update" of the server status variable. |
| mysql.performance.com_delete_multi | hostname, mode, service=mysql | Corresponding to "Com_delete_multi" of the server status variable. |
| mysql.performance.created_tmp_disk_tables | hostname, mode, service=mysql | Corresponding to "Created_tmp_disk_tables" of the server status variable. |
| mysql.innodb.mutex_spin_rounds | hostname, mode, service=mysql | Corresponding to spinlock rounds of the server status variable. |
| mysql.innodb.current_row_locks | hostname, mode, service=mysql | Corresponding to current row locks of the server status variable. |
| mysql.innodb.mutex_os_waits | hostname, mode, service=mysql | Corresponding to the OS waits of the server status variable. |
| mysql.innodb.buffer_pool_used | hostname, mode, service=mysql | The number of used pages, in bytes. This value is calculated by subtracting "Innodb_buffer_pool_pages_total" away from "Innodb_buffer_pool_pages_free" of the server status variable. |
| mysql.innodb.data_writes | hostname, mode, service=mysql | Corresponding to "Innodb_data_writes" of the server status variable. |
| mysql.innodb.data_reads | hostname, mode, service=mysql | Corresponding to "Innodb_data_reads" of the server status variable. |
| mysql.innodb.row_lock_waits | hostname, mode, service=mysql | Corresponding to "Innodb_row_lock_waits" of the server status variable. |
| mysql.innodb.os_log_fsyncs | hostname, mode, service=mysql | Corresponding to "Innodb_os_log_fsyncs" of the server status variable. |
| mysql.innodb.buffer_pool_total | hostname, mode, service=mysql | The total size of buffer pool, in bytes. This value is calculated by multiplying "Innodb_buffer_pool_pages_total" and "Innodb_page_size" of the server status variable. |
| mysql.innodb.row_lock_time | hostname, mode, service=mysql | Corresponding to "Innodb_row_lock_time" of the server status variable. |
| mysql.innodb.mutex_spin_waits | hostname, mode, service=mysql | Corresponding to the spin waits of the server status variable. |
| mysql.innodb.buffer_pool_free | hostname, mode, service=mysql | The number of free pages, in bytes. This value is calculated by multiplying "Innodb_buffer_pool_pages_free" and "Innodb_page_size" of the server status variable. |
| mysql.net.max_connections | hostname, mode, service=mysql | Corresponding to "Max_used_connections" of the server status variable. |
| mysql.net.connections | hostname, mode, service=mysql | Corresponding to "Connections" of the server status variable. |

## Nagios Wrapper
The Agent can run Nagios plugins. A YAML file (nagios_wrapper.yaml) contains the list of Nagios checks to run, including the check name, command name with parameters, and desired interval between iterations. A Python script (nagios_wrapper.py) runs each command in turn, captures the resulting exit code (0 through 3, corresponding to OK, warning, critical and unknown), and sends that information to the Forwarder, which then sends the Monitoring API. Currently, the Agent can only  send the exit code from a Nagios plugin. Any accompanying text is not sent.

 default dimensions:
    observer_host: fqdn
    target_host: fqdn | supplied

 default value_meta
    0, 1, 2, 3, 4
    OK, Warning, Critical, Unknown
    error: error_message

Similar to all plugins, the configuration is done in YAML, and consists of two keys: init_config and instances.

init_config contains global configuration options:

```
init_config:
  # Directories where Nagios checks (scripts, programs) may live
  check_path: /usr/lib/nagios/plugins:/usr/local/bin/nagios

  # Where to store last-run timestamps for each check
  temp_file_path: /dev/shm/
```

instances contains the list of checks to run

```
instances:
  - name: load
    check_command: check_load -r -w 2,1.5,1 -c 10,5,4

  - name: disk
    check_command: check_disk -w 15\% -c 5\% -A -i /srv/node
    check_interval: 300
```

* 'name' value is the name of the metric
* check_command is the full command to run.  Specifying the full path is optional if the checks are located somewhere in check_path.  These above examples are a copy-and-paste from existing service checks in /etc/cron.d/servicecheck-* files, so migration is fairly easy.

* check_interval (optional) If unspecified, the checks will be run at the regular collector interval, which is 60 seconds by default. You may not want to run some checks that frequently, especially if they are resource-intensive, so check_interval lets you force a delay, in seconds, between iterations of that particular check.  The state for these are stored in temp_file_path with file names like nagios_wrapper_19fe42bc7cfdc37a2d88684013e66c7b.pck where the hash is an md5sum of the 'name' value (to accommodate odd characters that the filesystem may not like).

## Nginx
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/nginx.yaml.example) for how to configure the Nginx plugin.

## NTP
This section describes the Network Time Protocol checks that can be performed by the Agent. The NTP checks monitors time offset between NTP server and your own server. The NTP checks requires a configuration file called ntp.yaml to be available in the agent conf.d configuration directory. The config file must contain the hostname and port number, version information, timeout(These are optional params) that you are interested in monitoring.

Sample config:

```
init_config:

instances:
  - host: pool.ntp.org
    port: ntp
    version: 3
    timeout: 5
```

The NTP checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| ntp.offset | hostname, ntp_server | Time offset in seconds |
| ntp.connection_status | hostname, ntp_server | Value of ntp server connection status (0=Healthy) |

## Postfix Checks
This section describes the Postfix checks that can be performed by the Agent. The Postfix checks gathers metrics on the Postfix. The Postfix checks requires a configuration file called postfix.yaml to be available in the agent conf.d configuration directory. The config file must contain the name, directory and queue that you are interested in monitoring.

NOTE: The user running monasca-agent must have passwordless sudo access for the find command to run the postfix check.  Here's an example:

```
 example /etc/sudoers entry:
          monasca-agent ALL=(ALL) NOPASSWD:/usr/bin/find
```

Sample config:

```
init_config:

instances:
    - name: /var/spool/postfix
      directory: /var/spool/postfix
      queues:
          - incoming
          - active
          - deferred
```

The Postfix return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| postfix.queue_size | queue | A total number of queues |

## PostgreSQL
This section describes the PostgreSQL checks that can be performed by the Agent.  The PostgreSQL checks requires a configuration file called postgres.yaml to be available in the agent conf.d configuration directory.

Sample config:

```
init_config:

instances:
   -   host: localhost
       port: 5432
       username: my_username
       password: my_password
       dbname: db_name
```

If you want to track per-relation (table), you need to add relations keys and specify the list.

```
       relations:
            - my_table
            - my_other_table
```

Each metrics show statistics collected in PostgreSQL. The PostgreSQL checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| postgresql.connections | hostname, db, service=postgres | Value of the "numbackends" of "pg_stat_database". |
| postgresql.commits | hostname, db, service=postgres | Value of the "xact_commit" of "pg_stat_database". |
| postgresql.rollbacks | hostname, db, service=postgres | Value of the "xact_rollback" of "pg_stat_database". |
| postgresql.disk_read | hostname, db, service=postgres | Value of the "blks_read" of "pg_stat_database". |
| postgresql.buffer_hit | hostname, db, service=postgres | Value of the "blks_hit" of "pg_stat_database". |
| postgresql.rows_returned | hostname, db, service=postgres | Value of the "tup_returned" of "pg_stat_database". |
| postgresql.rows_fetched | hostname, db, service=postgres | Value of the "tup_fetched" of "pg_stat_database". |
| postgresql.deadlocks | hostname, db, service=postgres | Value of the "deadlocks" of "pg_stat_database". This is supported only in PostgreSQL 9.2 or later. |
| postgresql.temp_bytes | hostname, db, service=postgres | Value of the "temp_bytes" of "pg_stat_database". This is supported only in PostgreSQL 9.2 or later. |
| postgresql.temp_files | hostname, db, service=postgres | Value of the "temp_files" of "pg_stat_database". This is supported only in PostgreSQL 9.2 or later. |
| postgresql.seq_scans | hostname, db, service=postgres, table | Value of the "seq_scan" of "pg_stat_user_tables" |
| postgresql.seq_rows_read | hostname, db, service=postgres, table | Value of the "seq_tup_read" of "pg_stat_user_tables" |
| postgresql.index_scans | hostname, db, service=postgres, table, index | Value of the "idx_scan" of "pg_stat_user_tables" or "pg_stat_user_indexes" |
| postgresql.index_rows_fetched | hostname, db, service=postgres, table, index | Value of the "idx_tup_fetch" of "pg_stat_user_tables" or "pg_stat_user_indexes" |
| postgresql.rows_inserted | hostname, db, service=postgres, table | Value of the "n_tup_ins" of "pg_stat_user_tables" or "pg_stat_database" |
| postgresql.rows_updated | hostname, db, service=postgres, table | Value of the "n_tup_upd" of "pg_stat_user_tables" or "pg_stat_database" |
| postgresql.rows_deleted | hostname, db, service=postgres, table | Value of the "n_tup_del" of "pg_stat_user_tables" or "pg_stat_database" |
| postgresql.rows_hot_updated | hostname, db, service=postgres, table | Value of the "n_tup_hot_upd" of "pg_stat_user_tables"
| postgresql.live_rows | hostname, db, service=postgres, table | Value of the "n_live_tup" of "pg_stat_user_tables" |
| postgresql.dead_rows | hostname, db, service=postgres, table | Value of the "n_dead_tup" of "pg_stat_user_tables" |
| postgresql.index_rows_read | hostname, db, service=postgres, table, index | Value of the "idx_tup_read" of "pg_stat_user_indexes" |


## Process Checks
Process checks can be performed to both verify that a set of named processes are running on the local system and collect/send system level metrics on those processes. The YAML file `process.yaml` contains the list of processes that are checked.

The processes that are monitored can be filtered using a pattern to specify the matching process names or distinctly identified by process name or by the username that owns the process.

A Python script `process.py` runs each execution cycle to check that required processes are alive. If the process is running a value of 0 is sent, otherwise a value of 1 is sent to the Monasca API.

Each process entry consists of one primary key: name. Either search_string or username must be set but you can not set both. Optionally, if an exact match on search_string is required the exact_match boolean can be added to the entry and set to True.

To grab more process metrics beside the process.pid_count, which only shows that the process is up and running, the configuration option detailed must be set to true.

Sample monasca-setup:
Monitor by process_names:
```
monasca-setup -d ProcessCheck -json \
         '{"process_config":[{"process_names":["monasca-notification","monasca-api"],"dimensions":{"service":"monitoring"}}]}'
```
Monitor by process_username:
```
monasca-setup -d ProcessCheck -json \
         '{"process_config":[{"process_username":"dbadmin","dimensions":{"service":"monitoring","component":"vertica"}}]}'
```
Multiple entries in one call:
```
monasca-setup -d ProcessCheck -json \
         '{"process_config":[{"process_names":["monasca-notification","monasca-api"],"dimensions":{"service":"monitoring"}},
                             {"process_names":["elasticsearch"],"dimensions":{"service":"logging"}},
                             {"process_username":"dbadmin","dimensions":{"service":"monitoring","component":"vertica"}}]}'
```
Using a yaml config file:
```
monasca-setup -d ProcessCheck -a "conf_file_path=/home/stack/myprocess.yaml"
```
Example yaml input file format for process check by process names:
```

process_config:
- process_names:
  - monasca-notification
  - monasca-api
  dimensions:
    service: monitoring
```
Example yaml input file format for multiple process_names entries:
```

process_config:
- process_names:
  - monasca-notification
  - monasca-api
  dimensions:
    service: monitoring
- process_names:
  - elasticsearch
  dimensions:
    service: logging
- process_names:
  - monasca-thresh
  exact_match: 'true'
  dimensions:
    service: monitoring
    component: thresh
```
Sample successfully built process.yaml:
```
init_config: null
instances:
- built_by: ProcessCheck
  detailed: true
  dimensions:
    component: monasca-api
    service: monitoring
  exact_match: false
  name: monasca-api
  search_string:
  - monasca-api

- built_by: ProcessCheck
  detailed: true
  dimensions:
    component: monasca-notification
    service: monitoring
  exact_match: false
  name: monasca-notification
  search_string:
  - monasca-notification

- built_by: ProcessCheck
  detailed: true
  dimensions:
    component: vertica
    service: monitoring
  name: vertica
  username: dbadmin
```
The process checks return the following metrics ( if detailed is set to true, otherwise process.pid_count is only returned ):

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| process.mem.rss_mbytes  | process_name, service, component | Amount of physical memory allocated to a process, including memory from shared libraries in Mbytes
| process.io.read_count  | process_name, service, component | Number of reads by a process
| process.io.write_count  | process_name, service, component | Number of writes by a process
| process.io.read_kbytes  | process_name, service, component | Kbytes read by a process
| process.io.write_kbytes  | process_name, service, component | Kbytes written by a process
| process.thread_count  | process_name, service, component | Number of threads a process is using
| process.cpu_perc  | process_name, service, component | Percentage of cpu being consumed by a process
| process.open_file_descriptors  | process_name, service, component | Number of files being used by a process
| process.pid_count  | process_name, service, component | Number of processes that exist with this process name

On Linux, if the Agent is not run as root or the owner of the process the io metrics and the open_file_descriptors metric will fail to be reported if the mon-agent user does not have permission to get it for the process.

## Prometheus Client
This plugin is for scraping metrics from endpoints that are created by prometheus client libraries - https://prometheus.io/docs/instrumenting/clientlibs/

It can be configured in two ways. One being manually setting all the endpoints that you want to scrape. The other being
running in a Kubernetes environment where we autodetect on either services or pods based on annotations set.

### Manually Configuring Endpoints
In this instance the plugin goes to a configured list of prometheus client endpoints and scrapes the posted metrics from each.

When configuring each endpoint you can define a set of dimensions that is attached to each metric being scraped.

By default we grab the defined labels on each metric as dimensions.

Example yaml file:

```
init_config:
  # Timeout on connections to each endpoint
  timeout: 3
instances:
  - metric_endpoint: "http://127.0.0.1:8000"
    # Dimensions to add to every metric coming out of the plugin
    default_dimensions:
        app: my_app

  - metric_endpoint: "http://127.0.0.1:9000"
```

### Running in a Kubernetes Environment with autodetection
There are two ways for the autodetection to be set up. One for auto detecting based on pods and the other auto detecting
for services. In both cases it is looking for the annotations set for the Kubernetes service or pod.

The annotations the plugin is looking for are -
* prometheus.io/scrape: Only scrape pods that have a value of 'true'
* prometheus.io/path: If the metrics path is not '/metrics' override this.
* prometheus.io/port: Scrape the pod on the indicated port instead of the default of '9102'.

These annotations are pulled from the Kubelet for pod autodetection and the Kubernetes API for the service auto detection

There is also configuration parameter of "kubernetes_labels" where it will look for Kubernetes tags to use as dimensions
for metrics coming out. By default that will be set to "app"

Example yaml file (by pod):

```
init_config:
  timeout: 3
  auto_detect_endpoints: True
  detect_method: "pod"
instances:
- kubernetes_labels: ['app']
```

Example yaml file (by service):

```
init_config:
  timeout: 3
  auto_detect_endpoints: True
  detect_method: "service"
instances:
- kubernetes_labels: ['app']
```

**NOTE** This Plugin can only have one configured instance

## RabbitMQ Checks
This section describes the RabbitMQ check that can be performed by the Agent.  The RabbitMQ check gathers metrics on Nodes, Exchanges and Queues from the rabbit server.  The RabbitMQ check requires a configuration file called rabbitmq.yaml to be available in the agent conf.d configuration directory.  The config file must contain the names of the Exchanges and Queues that you are interested in monitoring.

NOTE: The agent RabbitMQ plugin requires the RabbitMQ Management Plugin to be installed.  The management plugin is included in the RabbitMQ distribution. To enable it, use the rabbitmq-plugins command like this:
```
rabbitmq-plugins enable rabbitmq_management
```
Sample config:

```
init_config:

instances:
  - exchanges: [nova, cinder, ceilometer, glance, keystone, neutron, heat]
    nodes: [rabbit@devstack]
    queues: [conductor]
    rabbitmq_api_url: http://localhost:15672/api
    rabbitmq_user: guest
    rabbitmq_pass: guest
```

If you want the monasca-setup program to detect and auto-configure the plugin for you, you must pass ``watch_api=true`` to the plugin, for example:

```
monasca-setup \
  --detection_plugins rabbitmq \
  --detection_args "watch_api=true"
```

Additionally, you must create the file /root/.rabbitmq.cnf with the information needed in the configuration yaml file before running the setup program.  It should look something like this:

```
[client]
user=guest
password=pass
nodes=rabbit@devstack
queues=conductor
exchanges=nova,cinder,ceilometer,glance,keystone,neutron,heat
```

Alternatively, the arguments can be passed on the command line, but note that all arguments must be passed in this case - the configuration file will not be read:

```
monasca-setup \
  --detection_plugins rabbitmq \
  --detection_args \
    "watch_api=true
     user=guest
     password=pass
     nodes=rabbit@devstack
     queues=conductor
     exchanges=nova,cinder,ceilometer,glance,keystone,neutron,heat"
```

For more details of each metric, please refer the [RabbitMQ documentation](http://www.rabbitmq.com/documentation.html).
The RabbitMQ checks return the following metrics:

| Metric Name | Dimensions | Check Type | Description |
| ----------- | ---------- | ---------- | ----------- |
| rabbitmq.node.fd_used | hostname, node, service=rabbitmq | Node | Value of the "fd_used" field in the response of /api/nodes |
| rabbitmq.node.sockets_used | hostname, node, service=rabbitmq | Node | Value of the "sockets_used" field in the response of /api/nodes |
| rabbitmq.node.run_queue | hostname, node, service=rabbitmq | Node | Value of the "run_queue" field in the response of /api/nodes |
| rabbitmq.node.mem_used | hostname, node, service=rabbitmq | Node | Value of the "mem_used" field in the response of /api/nodes |
| rabbitmq.exchange.messages.received_count | hostname, exchange, vhost, type, service=rabbitmq | Exchange | Value of the "publish_in" field of "message_stats" object |
| rabbitmq.exchange.messages.received_rate | hostname, exchange, vhost, type, service=rabbitmq | Exchange | Value of the "rate" field of "message_stats/publish_in_details" object |
| rabbitmq.exchange.messages.published_count | hostname, exchange, vhost, type, service=rabbitmq | Exchange | Value of the "publish_out" field of "message_stats" object |
| rabbitmq.exchange.messages.published_rate | hostname, exchange, vhost, type, service=rabbitmq | Exchange | Value of the "rate" field of "message_stats/publish_out_details" object |
| rabbitmq.queue.consumers | hostname, queue, vhost, service=rabbitmq | Queue | Number of consumers |
| rabbitmq.queue.memory | hostname, queue, vhost, service=rabbitmq | Queue | Bytes of memory consumed by the Erlang process associated with the queue, including stack, heap and internal structures |
| rabbitmq.queue.active_consumers | hostname, queue, vhost, service=rabbitmq | Queue |  |
| rabbitmq.queue.messages | hostname, queue, vhost, service=rabbitmq | Queue | Sum of ready and unacknowledged messages (queue depth) |
| rabbitmq.queue.messages.rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_details" object |
| rabbitmq.queue.messages.ready | hostname, queue, vhost, service=rabbitmq | Queue | Number of messages ready to be delivered to clients |
| rabbitmq.queue.messages.ready_rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_ready_details" object |
| rabbitmq.queue.messages.publish_count | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "publish" field of "message_stats" object |
| rabbitmq.queue.messages.publish_rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_stats/publish_details" object |
| rabbitmq.queue.messages.deliver_count | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "deliver" field of "message_stats" object |
| rabbitmq.queue.messages.deliver_rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_stats/deliver_details" object |
| rabbitmq.queue.messages.redeliver_count | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "redeliver" field of "message_stats" object |
| rabbitmq.queue.messages.redeliver_rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_stats/redeliver_details" object |
| rabbitmq.queue.messages.unacknowledged | hostname, queue, vhost, service=rabbitmq | Queue | Number of messages delivered to clients but not yet acknowledged |
| rabbitmq.queue.messages.unacknowledged_rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_stats/messages_unacknowledged_details" object |
| rabbitmq.queue.messages.deliver_get_count | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "deliver_get" field of "message_stats" object |
| rabbitmq.queue.messages.deliver_get_rate | hostname, queue, vhost, service=rabbitmq | Queue | Value of the "rate" field of "message_stats/deliver_get_details" object |
| rabbitmq.queue.messages.ack_count | hostname, queue, vhost, service=rabbitmq | Queue |  |
| rabbitmq.queue.messages.ack_rate | hostname, queue, vhost, service=rabbitmq | Queue |  |

## RedisDB
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/.yaml.example) for how to configure the  plugin.

## Riak
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/riak.yaml.example) for how to configure the Riak plugin.

## SolidFire
The SolidFire checks require a matching solidfire.yaml to be present. Currently the checks report a mixture of cluster utilization and health metrics. Multiple clusters can be monitored via separate instance stanzas in the config file.

Sample config:

instances:
    - name: cluster_rack_d
      username: cluster_admin
      password: secret_password
      mvip: 192.168.1.1

The SolidFire checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| solidfire.active_cluster_faults     | service=solidfire, cluster | Amount of active cluster faults, such as failed drives |
| solidfire.cluster_utilization       | service=solidfire, cluster | Overall cluster IOP utilization |
| solidfire.num_iscsi_sessions        | service=solidfire, cluster | Amount of active iSCSI sessions connected to the cluster |
| solidfire.iops.avg_5_sec            | service=solidfire, cluster | Average IOPs over the last 5 seconds |
| solidfire.iops.avg_utc              | service=solidfire, cluster | Average IOPs since midnight UTC |
| solidfire.iops.peak_utc             | service=solidfire, cluster | Peak IOPS since midnight UTC |
| solidfire.iops.max_available        | service=solidfire, cluster | Theoretical maximum amount of IOPs |
| solidfire.active_block_bytes        | service=solidfire, cluster | Amount of space consumed by the block services, including cruft |
| solidfire.active_meta_bytes         | service=solidfire, cluster | Amount of space consumed by the metadata services |
| solidfire.active_snapshot_bytes     | service=solidfire, cluster | Amount of space consumed by the metadata services for snapshots |
| solidfire.provisioned_bytes         | service=solidfire, cluster | Total number of provisioned bytes |
| solidfire.unique_blocks_used_bytes  | service=solidfire, cluster | Amount of space the unique blocks take on the block drives |
| solidfire.max_block_bytes           | service=solidfire, cluster | Maximum amount of bytes allocated to the block services |
| solidfire.max_meta_bytes            | service=solidfire, cluster | Maximum amount of bytes allocated to the metadata services |
| solidfire.max_provisioned_bytes     | service=solidfire, cluster | Max provisionable space if 100% metadata space used |
| solidfire.max_overprovisioned_bytes | service=solidfire, cluster | Max provisionable space * 5, artificial safety limit |
| solidfire.unique_blocks             | service=solidfire, cluster | Number of blocks(not always 4KiB) stored on block drives |
| solidfire.non_zero_blocks           | service=solidfire, cluster | Number of 4KiB blocks with data after the last garbage collection |
| solidfire.zero_blocks               | service=solidfire, cluster | Number of 4KiB blocks without data after the last garbage collection |
| solidfire.thin_provision_factor     | service=solidfire, cluster | Thin provisioning factor, (nonZeroBlocks + zeroBlocks) / nonZeroBlocks |
| solidfire.deduplication_factor      | service=solidfire, cluster | Data deduplication factor, nonZeroBlocks / uniqueBlocks |
| solidfire.compression_factor        | service=solidfire, cluster | Data compression factor, (uniqueBlocks * 4096) / uniqueBlocksUsedSpace |
| solidfire.data_reduction_factor     | service=solidfire, cluster | Aggregate data reduction efficiency, thin_prov * dedup * compression |

## SQLServer
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/sqlserver.yaml.example) for how to configure the SQLServer plugin.

## Supervisord
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/supervisord.yaml.example) for how to configure the Supervisord plugin.

## Swift Diags
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/swift_diags.yaml.example) for how to configure the Swift Diags plugin.

## TCP Check
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/tcp_check.yaml.example) for how to configure the TCP Check plugin.

## Varnish
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/varnish.yaml.example) for how to configure the Varnish plugin.

## VCenter
This plugin provides metrics for VMware ESX clusters. It connects to vCenter server with its credentials and collects the configured cluster's performance data.

### Sample Config
```
init_config: {}
instances:
    - vcenter_ip: <vcenter-ip or fqdn>
        username: <vcenter-user>
        password: <vcenter-password>
        clusters: <[cluster-name-list]> # e.g: [cluster-1, cluster-2]
```

### ESX Cluster Metrics
Below are the list of metrics collected by this plugin from the configured cluster:


| Metric Name | Description |
| ----------- | ---------- |
| vcenter.cpu.total_mhz | Total amount of CPU resources of all hosts in the cluster, as measured in megahertz. ESX counter name: cpu.totalmhz.average |
| vcenter.cpu.used_mhz | Sum of the average CPU usage values, in megahertz, of all virtual machines in the cluster. ESX counter name: cpu.usagemhz.average |
| vcenter.cpu.used_perc | CPU usage in percent, during the interval |
| vcenter.cpu.total_logical_cores | Aggregated number of CPU threads. ESX counter name: numCpuThreads |
| vcenter.mem.total_mb | Total amount of machine memory of all hosts in the cluster that is available for guest memory and guest overhead memory. ESX counter name: mem.consumed.average |
| vcenter.mem.used_mb | A cluster's consumed memory consists of guest consumed memory and overhead memory. It does not include host-specific overhead memory. ESX counter name: mem.consumed.average |
| vcenter.mem.used_perc | A cluster's consumed memory in percentage |
| vcenter.disk.total_space_mb | Aggregation of maximum capacities of datastores connected to the hosts of a cluster, in megabytes. ESX counter name: summary.capacity |
| vcenter.disk.total_used_space_mb | Aggregation of all available capacities of datastores connected to the hosts of a cluster, in megabytes. ESX counter name: summary.freeSpace |
| vcenter.disk.total_used_space_perc | Aggregation of all available capacities of datastores connected to the hosts of a cluster, in percent |

### ESX Cluster Dimensions
```
    "vcenter_ip": <vcenter-ip or fqdn>,
    "cluster": <cluster-name>,
    "host_type": "compute_node",
    "role": "esx",
    "id": <cluster-name>-<vcenter-ip or fqdn>
```

## Vertica Checks
This section describes the vertica check that can be performed by the Agent.  The vertica check requires a configuration file called vertica.yaml to be available in the agent conf.d configuration directory.

Sample config:

```
init_config:

instances:
    user: mon_api
    password: password
    service: monasca (optional, defaults to vertica)
    timeout: 3 (optional, defaults to 3 seconds)
```

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| vertica.license_usage_percent | hostname, service=vertica| Percentage of the license size taken up. |
| vertica.connection_status | hostname, node_name, service=vertica | Value of DB connection status (0=Healthy). |
| vertica.node_status | hostname, node_name, service=vertica| Status of node connection (0=UP). |
| vertica.projection.ros_count | hostname, node_name, projection_name, service=vertica| The number of ROS containers in the projection. |
| vertica.projection.tuple_mover_mergeouts | hostname, node_name, projection_name, service=vertica | Number of current tuple mover mergeouts on this projection. |
| vertica.projection.tuple_mover_moveouts | hostname, node_name, projection_name, service=vertica | Number of current tuple mover moveout on this projection. |
| vertica.projection.wos_used_bytes | hostname, node_name, projection_name, service=vertica | The number of WOS bytes in the projection.). |
| vertica.resource.disk_space_rejections | hostname, node_name, service=vertica | The number of rejected disk write requests. |
| vertica.resource.pool.memory_inuse_kb | hostname, node_name, resource_pool, service=vertica | Amount of memory, in kilobytes, acquired by requests running against this pool. |
| vertica.resource.pool.memory_size_actual_kb | hostname, node_name, resource_pool, service=vertica | Current amount of memory, in kilobytes, allocated to the pool by the resource manager. |
| vertica.resource.pool.rejection_count | hostname, node_name, resource_pool, service=vertica | Number of resource rejections for this pool |
| vertica.resource.pool.running_query_count | hostname, node_name, resource_pool, service=vertica | Number of queries actually running using this pool. |
| vertica.resource.request_queue_depth | hostname, node_name, service=vertica | The cumulative number of requests for threads, file handles, and memory. |
| vertica.resource.resource_rejections | hostname, node_name, service=vertica | The number of rejected plan requests. |
| vertica.resource.wos_used_bytes | hostname, node_name, service=vertica | The size of the WOS in bytes. |

## WMI Check

## ZooKeeper
This section describes the Zookeeper check that can be performed by the Agent.  The Zookeeper check requires a configuration file called zk.yaml to be available in the agent conf.d configuration directory.
The Zookeeper check parses the result of zookeeper's `stat` admin command.

Sample config:

```
init_config:

instances:
    host: localhost
    port: 2181
    timeout: 3
```

The Zookeeper checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| zookeeper.max_latency_sec | hostname, mode, service=zookeeper | Maximum latency in second |
| zookeeper.min_latency_sec | hostname, mode, service=zookeeper | Minimum latency in second |
| zookeeper.avg_latency_sec | hostname, mode, service=zookeeper | Average latency in second |
| zookeeper.out_bytes | hostname, mode, service=zookeeper | Sent bytes |
| zookeeper.outstanding_bytes | hostname, mode, service=zookeeper | Outstanding bytes |
| zookeeper.in_bytes | hostname, mode, service=zookeeper | Received bytes |
| zookeeper.connections_count | hostname, mode, service=zookeeper | Number of connections |
| zookeeper.node_count | hostname, mode, service=zookeeper | Number of nodes |
| zookeeper.zxid_count | hostname, mode, service=zookeeper | Count number |
| zookeeper.zxid_epoch | hostname, mode, service=zookeeper | Epoch number |

## Kibana
This section describes the Kibana check that can be performed by the Agent.
The Kibana check requires a configuration file containing Kibana configuration
(it is the same file Kibana is using).

Check is accessing status endpoint (```curl -XGET http://localhost:5601/api/status```)
of Kibana, which means it can work only with Kibana >= 4.2.x, that was first to introduce
this capability.

Sample config:

```yaml
init_config:
  url: http://localhost:5601/api/status
instances:
- built_by: Kibana
  metrics:
    - heap_size
    - heap_used
    - load
    - req_sec
    - resp_time_avg
    - resp_time_max
```

The Kibana checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| kibana.load_avg_1m | hostnam, version, service=monitoring | The average kibana load over a 1 minute period, for more details see [here](https://nodejs.org/api/os.html#os_os_loadavg) |
| kibana.load_avg_5m | hostnam, version, service=monitoring | The average kibana load over a 5 minutes period, for more details see [here](https://nodejs.org/api/os.html#os_os_loadavg) |
| kibana.load_avg_15m | hostnam, version, service=monitoring | The average kibana load over a 15 minutes period, for more details see [here](https://nodejs.org/api/os.html#os_os_loadavg) |
| kibana.heap_size_mb | hostnam, version, service=monitoring | Total heap size in MB |
| kibana.heap_used_mb | hostnam, version, service=monitoring | Used heap size in MB |
| kibana.req_sec | hostnam, version, service=monitoring | Requests per second to Kibana server |
| kibana.resp_time_avg_ms | hostnam, version, service=monitoring | The average response time of Kibana server in ms |
| kibana.resp_time_max_ms | hostnam, version, service=monitoring | The maximum response time of Kibana server in ms |

## OpenStack Monitoring
The `monasca-setup` script when run on a system that is running OpenStack services, configures the Agent to send the following list of metrics:

* The setup program creates process checks for each process that is part of an OpenStack service.  A few sample metrics from the process check are provided.  For the complete list of process metrics, see the [Process Checks](#Process Checks) section.
* Additionally, an http_status check will be setup on the api for the service, if there is one.

PLEASE NOTE: The monasca-setup program will only install checks for OpenStack services it detects when it is run.  If an additional service is added to a particular node or deleted, monasca-setup must be re-run to add monitoring for the additional service or remove the service that is no longer there.

### Nova Checks
This section documents a *sampling* of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Nova service.

The following nova processes are monitored, if they exist when the monasca-setup script is run:

##### Nova Processes Monitored
* nova-compute
* nova-conductor
* nova-cert
* nova-network
* nova-scheduler
* nova-novncproxy
* nova-xvpncproxy
* nova-consoleauth
* nova-objectstore
* nova-api

##### Example Nova Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| nova-compute | processes.process_pid_count | Gauge | Passive | service=nova, component=nova-compute | process | nova-compute process exists | This is only one of the process checks performed |
| nova-api | processes.process_pid_count | Gauge | Passive | service=nova, component=nova-api | process | nova-api process pid count | This is only one of the process checks performed |
| nova-api | http_status | Gauge | Active | service=nova, component=nova-api url=url_to_nova_api | http_status | nova-api http endpoint is alive | This check should be executed on multiple systems.|


### Swift Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Swift service.

The following swift processes are monitored, if they exist when the monasca-setup script is run:

##### Swift Processes Monitored
* swift-container-updater
* swift-account-auditor
* swift-object-replicator
* swift-container-replicator
* swift-object-auditor
* swift-container-auditor
* swift-account-reaper
* swift-container-sync
* swift-account-replicator
* swift-object-updater
* swift-object-server
* swift-account-server
* swift-container-server
* swift-proxy-server


##### Example Swift Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| swift-container-updater | processes.process_pid_count | Gauge | Passive | service=swift, component=swift-container-updater | process | swift-container-updater process exists | This is only one of the process checks performed |
| swift-proxy-server | processes.process_pid_count | Gauge | Passive | service=swift, component=swift-proxy-server | process | swift-proxy-server process pid count | This is only one of the process checks performed |
| swift-proxy-server | http_status | Gauge | Active | service=swift, component=swift-proxy-server url=url_to_swift_proxy_server | http_status | swift-proxy-server http endpoint is alive | This check should be executed on multiple systems.|

### Glance Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Glance service.

The following glance processes are monitored, if they exist when the monasca-setup script is run:

##### Glance Processes Monitored
* glance-registry
* glance-api

##### Example Glance Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| glance-registry | processes.process_pid_count | Gauge | Passive | service=glance, component=glance-registry | process | glance-registry process exists | This is only one of the process checks performed |
| glance-api | processes.process_pid_count | Gauge | Passive | service=glance, component=glance-api | process | glance-api process pid count | This is only one of the process checks performed |
| glance-api | http_status | Gauge | Active | service=glance, component=glance-api url=url_to_glance_api | http_status | glance-api http endpoint is alive | This check should be executed on multiple systems.|


### Cinder Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Cinder service.

The following cinder processes are monitored, if they exist when the monasca-setup script is run:

##### Cinder Processes Monitored
* cinder-volume
* cinder-scheduler
* cinder-api

##### Example Cinder Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| cinder-volume | processes.process_pid_count | Gauge | Passive | service=cinder, component=cinder-volume | process | cinder-volume process exists | This is only one of the process checks performed |
| cinder-api | processes.process_pid_count | Gauge | Passive | service=cinder, component=cinder-api | process | cinder-api process pid count | This is only one of the process checks performed |
| cinder-api | http_status | Gauge | Active | service=cinder, component=cinder-api url=url_to_cinder_api | http_status | cinder-api http endpoint is alive | This check should be executed on multiple systems.|


### Neutron Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Neutron service.

The following neutron processes are monitored, if they exist when the monasca-setup script is run:

##### Neutron Processes Monitored
* neutron-server
* neutron-openvswitch-agent
* neutron-rootwrap
* neutron-dhcp-agent
* neutron-vpn-agent
* neutron-metadata-agent
* neutron-metering-agent
* neutron-ns-metadata-proxy

##### Example Neutron Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| neutron-server | processes.process_pid_count | Gauge | Passive | service=neutron, component=neutron-server | process | neutron-server process exists | This is only one of the process checks performed |
| neutron-ns-metadata-proxy | processes.process_pid_count | Gauge | Passive | service=neutron, component=neutron-ns-metadata-proxy | process | neutron-ns-metadata-proxy process pid count | This is only one of the process checks performed |
| neutron-ns-metadata-proxy | http_status | Gauge | Active | service=neutron, component=neutron-ns-metadata-proxy url=url_to_neutron_api | http_status | neutron-ns-metadata-proxy http endpoint is alive | This check should be executed on multiple systems.|


### Keystone Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Keystone service.

The following keystone processes are monitored, if they exist when the monasca-setup script is run:

##### Keystone Processes Monitored
* keystone-all

##### Example Keystone Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| keystone-all | processes.process_pid_count | Gauge | Passive | service=keystone, component=keystone-all | process | keystone-all process pid count | This is only one of the process checks performed |
| keystone-all | http_status | Gauge | Active | service=keystone, component=keystone-all url=url_to_keystone_api | http_status | keystone-all http endpoint is alive | This check should be executed on multiple systems.|


### Ceilometer Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Ceilometer service.

The following ceilometer processes are monitored, if they exist when the monasca-setup script is run:

##### Ceilometer Processes Monitored
* ceilometer-agent-compute
* ceilometer-agent-central
* ceilometer-agent-notification
* ceilometer-collector
* ceilometer-alarm-notifier
* ceilometer-alarm-evaluator
* ceilometer-api

##### Example Ceilometer Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| ceilometer-agent-compute | processes.process_pid_count | Gauge | Passive | service=ceilometer, component=ceilometer-agent-compute | process | ceilometer-agent-compute process exists | This is only one of the process checks performed |
| ceilometer-api | processes.process_pid_count | Gauge | Passive | service=ceilometer, component=ceilometer-api | process | ceilometer-api process pid count | This is only one of the process checks performed |
| ceilometer-api | http_status | Gauge | Active | service=ceilometer, component=ceilometer-api url=url_to_ceilometer_api | http_status | ceilometer-api http endpoint is alive | This check should be executed on multiple systems.|


### Freezer Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Freezer service.

The following Freezer processes are monitored, if they exist when the monasca-setup script is run:

##### Freezer Processes Monitored
* freezer-scheduler
* freezer-api

##### Example Freezer Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| freezer-api | processes.process_pid_count | Gauge | Passive | service=backup, component=freezer-api | process | freezer-api process pid count | This is only one of the process checks performed |
| freezer-api | http_status | Gauge | Active | service=backup, component=freezer-api url=url_to_freezer_api | http_status | freezer-api http endpoint is alive | This check should be executed on multiple systems.|
| freezer-scheduler | processes.process_pid_count | Gauge | Passive | service=backup, component=freezer-scheduler | process | freezer-scheduler process pid count | This is only one of the process checks performed |

### Magnum Checks
This section documents a sampling of the metrics generated by the checks setup automatically by the monasca-setup script for the OpenStack Magnum service.

The following Magnum processes are monitored, if they exist when the monasca-setup script is run:

##### Magnum Processes Monitored
* magnum-api
* magnum-controller

##### Example Magnum Metrics

| Component | Metric Name | Metric Type | Check Type | Dimensions | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| magnum-api | processes.process_pid_count | Gauge | Passive | service=container-infra, component=magnum-api | process | magnum-api process pid count | This is only one of the process checks performed |
| magnum-api | http_status | Gauge | Active | service=container-infra, component=magnum-api url=url_to_magnum_api | http_status | magnum-api http endpoint is alive | This check should be executed on multiple systems |
| magnum-controller | processes.process_pid_count | Gauge | Passive | service=container-infra, component=magnum-conductor | process | magnum-conductor process pid count | This is only one of the process checks performed |

# License
(C) Copyright 2015-2017 Hewlett Packard Enterprise Development LP
