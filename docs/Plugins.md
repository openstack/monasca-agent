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
  - [Apache](#apache)
  - [Cacti](#cacti)
  - [Check_MK_Local](#check_mk_local)
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
  - [IIS](#iis)
  - [Jenkins](#jenkins)
  - [Kafka Checks](#kafka-checks)
  - [KyotoTycoon](#kyototycoon)
  - [Libvirt VM Monitoring](#libvirt-vm-monitoring)
  - [Open vSwitch Neutron Router Monitoring](#open-vswitch-neutron-router-monitoring)
  - [Lighttpd](#lighttpd)
  - [Mcache](#mcache)
  - [MK Livestatus](#mk-livestatus)
  - [Mongo](#mongo)
  - [MySQL Checks](#mysql-checks)
  - [Nagios Wrapper](#nagios-wrapper)
  - [Nginx](#nginx)
  - [NTP](#ntp)
  - [Postfix Checks](#postfix-checks)
  - [PostgreSQL](#postgresql)
  - [Process Checks](#process-checks)
  - [RabbitMQ Checks](#rabbitmq-checks)
  - [RedisDB](#redisdb)
  - [Riak](#riak)
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
  - [Win32 Event Log](#win32-event-log)
  - [WMI Check](#wmi-check)
  - [ZooKeeper](#zookeeper)
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
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Standard Plugins
Plugins are the way to extend the Monasca Agent.  Plugins add additional functionality that allow the agent to perform checks on other applications, servers or services.  Some plugins may have corresponding [Detection Plugins](#detection-plugins) to automatically detect, configure, and activate certain Agent plugins. This section describes the standard plugins that are delivered by default.

** Standard location for plugin YAML config files **
> /etc/monasca/agent/conf.d/

The following plugins are delivered via setup as part of the standard plugin checks.  See [Customizations.md](https://github.com/openstack/monasca-agent/blob/master/docs/Customizations.md) for how to write new plugins.

| Setup Plugin Name | Dot File  | Detail                 |
| ----------------- | --------- | ---------------------- |
| apache | /root/.apache.cnf | Apache web server |
| cacti |  |  |
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
| gearmand |  |  |
| gunicorn |  |  |
| haproxy |  |  |
| hdfs |  |  |
| host_alive |  |  |
| http_check |  |  |
| http_metrics |  |  |
| iis |  | Microsoft Internet Information Services |
| jenkins |  |  |
| kafka_consumer |  |  |
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
| rabbitmq | /root/.rabbitmq.cnf |
| redisdb |  |  |
| riak |  |  |
| sqlserver |  |  |
| supervisord |  |  |
| swift_diags |  |  |
| tcp_check |  |  |
| varnish |  |  |
| vcenter |  |  |
| vertica | /root/.vertica.cnf |
| win32_event_log |  |  |
| wmi_check |  |  |
| zk |  | Apache Zookeeper |


## Dot File Configuration

Dot files, as referenced above, provide an added level of configuration to some component plugins.  Here are a few examples:

> **apache**
```
[client]
user=root
password=pass
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
This class covers both processes and HTTP endpoints, primarily used for monitoring OpenStack components.

## List of Detection Plugins
These are the detection plugins included with the Monasca Agent.  See [Customizations.md](https://github.com/openstack/monasca-agent/blob/master/docs/Customizations.md) for how to write new detection plugins.

| Detection Plugin Name | Type                 |
| --------------------- | ---------------------- |
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
| glance | ServicePlugin |
| haproxy | Plugin |
| heat | ServicePlugin |
| host_alive | ArgsPlugin |
| http_check | ArgsPlugin |
| ironic | ServicePlugin |
| kafka_consumer | Plugin |
| keystone | ServicePlugin |
| libvirt | Plugin |
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
| rabbitmq | Plugin |
| supervisord | Plugin |
| swift | ServicePlugin |
| system | Plugin |
| trove | ServicePlugin |
| vcenter | Plugin |
| vertica | Plugin |
| zookeeper | Plugin |


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
| load.avg_1_min  |  | The average system load over a 1 minute period
| load.avg_5_min  |  | The average system load over a 5 minute period
| load.avg_15_min  |  | The average system load over a 15 minute period

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
```
monasca-setup -d system -a 'cpu_idle_only=true net_bytes_only=true send_io_stats=false' --overwrite
```
By default, all metrics are enabled.

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

## Certificate Expiration (HTTPS)
An extension to the Agent provides the ability to determine the expiration date of the certificate for the URL. The metric is days until the certificate expires

 default dimensions:
    url: url

A YAML file (cert_check.yaml) contains the list of urls to check. It also contains

The configuration of the certicate expiration check is done in YAML, and consists of two keys:

* init_config
* instances

The init_config section lists the global configuration settings, such as the Certificate Authority Certificate file, the ciphers to use, the period at which to output the metric and the url connection timeout (in seconds, floating-point number)

```
ls -l `which ping` -rwsr-xr-x 1 root root 35712 Nov 8 2011 /bin/ping
```

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

monasca-setup -d CertificateCheck -a urls=https://somehost.somedomain.net:8333,https://somehost.somedomain.net:9696

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

 default dimensions:
    observer_host: fqdn
    hostname: fqdn | supplied
    test_type: ping | ssh | Unrecognized alive_test

 default value_meta
    error: error_message

* ping (ICMP)
* SSH (banner test, port 22 by default)

Of the two, the SSH check provides a more comprehensive test of a remote system's availability, since it checks the banner returned by the remote host. A server in the throes of a kernel panic may still respond to ping requests, but would not return an SSH banner. It is suggested, therefore, that the SSH check be used instead of the ping check when possible.

A YAML file (host_alive.yaml) contains the list of remote hosts to check, including the host name and testing method (either 'ping' or 'ssh'). A Python script (host_alive.py) runs checks against each host in turn, returning a 0 on success and a 1 on failure in the result sent through the Forwarder and on the Monitoring API.

Because the Agent itself does not run as root, it relies on the system ping command being suid root in order to function.

The configuration of the host alive check is done in YAML, and consists of two keys:

* init_config
* instances

The init_config section lists the global configuration settings, such as SSH port, SSH connection timeout (in seconds, floating-point number), and ping timeout (in seconds, integer).

```
ls -l `which ping` -rwsr-xr-x 1 root root 35712 Nov 8 2011 /bin/ping
```

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

The host alive checks return the following metrics

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| host_alive_status | observer_host=fqdn, hostname=supplied hostname being checked, test_type=ping or ssh | Status of remote host(device) is online or not. (0=online, 1=offline)

Also in the case of an error the value_meta contains an error message.

## HTTP (endpoint status)
This section describes the http endpoint check that can be performed by the Agent. Http endpoint checks are checks that perform simple up/down checks on services, such as HTTP/REST APIs. An agent, given a list of URLs, can dispatch an http request and report to the API success/failure as a metric.

 default dimensions:
    url: endpoint

 default value_meta
    error: error_message

The Agent supports additional functionality through the use of Python scripts. A YAML file (http_check.yaml) contains the list of URLs to check (among other optional parameters). A Python script (http_check.py) runs checks each host in turn, returning a 0 on success and a 1 on failure in the result sent through the Forwarder and on the Monitoring API.

Similar to other checks, the configuration is done in YAML, and consists of two keys: init_config and instances.  The former is not used by http_check, while the later contains one or more URLs to check, plus optional parameters like a timeout, username/password, pattern to match against the HTTP response body, whether or not to include the HTTP response in the metric (as a 'detail' dimension), whether or not to also record the response time, and more.
If the endpoint being checked requires authentication, there are two options. First, a username and password supplied in the instance options will be used by the check for authentication. Alternately, the check can retrieve a keystone token for authentication. Specific keystone information can be provided for each check, otherwise the information from the agent config will be used.

Sample config:

```
init_config:

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

## IIS
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/iis.yaml.example) for how to configure the IIS plugin.

## Jenkins
See [the example configuration](https://github.com/openstack/monasca-agent/blob/master/conf.d/jenkins.yaml.example) for how to configure the Jenkins plugin.

## Kafka Checks
This section describes the Kafka check that can be performed by the Agent.  The Kafka check requires a configuration file called kafka.yaml to be available in the agent conf.d configuration directory.

Sample config:

```
init_config:

instances:
- consumer_groups:
    '1_alarm-state-transitions':
        'alarm-state-transitions': ['3', '2', '1', '0']
    '1_metrics':
        'metrics': &id001 ['3', '2', '1', '0']
        'test':
            'healthcheck': ['1', '0']
        'thresh-event':
            'events': ['3', '2', '1', '0']
        'thresh-metric':
            'metrics': *id001
  kafka_connect_str: localhost:9092
  zk_connect_str: localhost:2181
```

The Kafka checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| kafka.broker_offset | topic, service, component, partition, hostname | broker offset |
| kafka.consumer_offset | topic, service, component, partition, consumer_group, hostname | consumer offset |
| kafka.consumer_lag | topic, service, component, partition, consumer_group, hostname | consumer offset lag from broker offset |

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

Sample config:
defaults_file: /root/.my.cnf
	host=padawan-ccp-c1-m1-mgmt
	user=root
	password=pass

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
  - service_name: load
    check_command: check_load -r -w 2,1.5,1 -c 10,5,4

  - service_name: disk
    check_command: check_disk -w 15\% -c 5\% -A -i /srv/node
    check_interval: 300
```

* service_name is the name of the metric
* check_command is the full command to run.  Specifying the full path is optional if the checks are located somewhere in check_path.  These above examples are a copy-and-paste from existing service checks in /etc/cron.d/servicecheck-* files, so migration is fairly easy.

* check_interval (optional) If unspecified, the checks will be run at the regular collector interval, which is 60 seconds by default. You may not want to run some checks that frequently, especially if they are resource-intensive, so check_interval lets you force a delay, in seconds, between iterations of that particular check.  The state for these are stored in temp_file_path with file names like nagios_wrapper_19fe42bc7cfdc37a2d88684013e66c7b.pck where the hash is an md5sum of the service_name (to accommodate odd characters that the filesystem may not like).

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
| ntp.offset | hostname | Time offset in seconds |

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

```
init_config:

instances:
 - name: ssh
   search_string: ['ssh', 'sshd']

 - name: mysql
   search_string: ['mysql']
   exact_match: True

 - name: kafka
   search_string: ['kafka']
   detailed: true

 - name: monasca_agent
   username: mon-agent
   detailed: true
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

If you want the monasca-setup program to detect and auto-configure the plugin for you, you must create the file /root/.rabbitmq.cnf with the information needed in the configuration yaml file before running the setup program.  It should look something like this:

```
[client]
user=guest
password=pass
nodes=rabbit@devstack
queues=conductor
exchanges=nova,cinder,ceilometer,glance,keystone,neutron,heat
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
| vertica.connection_status | hostname, node_name, service=vertica | Value of DB connection status (0=Healthy). |
| vertica.node_status | hostname, node_name, service=vertica| Status of node connection (0=UP). |
| vertica.projection.ros_count | hostname, node_name, projection_name, service=vertica| 	The number of ROS containers in the projection. |
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

## Win32 Event Log

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

=======

# License
(C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
