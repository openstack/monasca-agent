<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [System Checks](#system-checks)
  - [System Metrics](#system-metrics)
      - [Limiting System Metrics](#limiting-system-metrics)
- [Standard Plugins](#standard-plugins)
  - [Dot File Configuration](#dot-file-configuration)
  - [Default Plugin Detection](#default-plugin-detection)
  - [Plugin Configuration](#plugin-configuration)
      - [init_config](#init_config)
      - [instances](#instances)
      - [dimensions](#dimensions)
      - [Plugin Documentation](#plugin-documentation)
  - [Nagios Checks](#nagios-checks)
    - [Nagios Wrapper](#nagios-wrapper)
    - [Check_MK_Agent Local](#check_mk_agent-local)
    - [MK Livestatus](#mk-livestatus)
  - [Host Alive Checks](#host-alive-checks)
  - [Process Checks](#process-checks)
  - [Http Endpoint Checks](#http-endpoint-checks)
  - [Http Metrics](#http-metrics)
  - [MySQL Checks](#mysql-checks)
  - [ZooKeeper Checks](#zookeeper-checks)
  - [Kafka Checks](#kafka-checks)
  - [RabbitMQ Checks](#rabbitmq-checks)
  - [Apache Web Server Checks](#apache-web-server-checks)
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
  - [Libvirt VM Monitoring](#libvirt-vm-monitoring)
    - [Overview](#overview)
    - [Configuration](#configuration)
    - [Instance Cache](#instance-cache)
    - [Metrics Cache](#metrics-cache)
    - [Per-Instance Metrics](#per-instance-metrics)
    - [VM Dimensions](#vm-dimensions)
    - [Aggregate Metrics](#aggregate-metrics)
  - [Crash Dump Monitoring](#crash-dump-monitoring)
    - [Overview](#overview-1)
    - [Metrics](#metrics-1)
    - [Configuration](#configuration-1)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


# System Checks
This section documents all the checks that are supported by the Agent.

## System Metrics
This section documents the system metrics that are sent by the Agent.  This section includes checks by the network plugin as these are considered more system level checks.

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| cpu.idle_perc  | | Percentage of time the CPU is idle when no I/O requests are in progress |
| cpu.wait_perc | | Percentage of time the CPU is idle AND there is at least one I/O request in progress |
| cpu.stolen_perc | | Percentage of stolen CPU time, i.e. the time spent in other OS contexts when running in a virtualized environment |
| cpu.system_perc | | Percentage of time the CPU is used at the system level |
| cpu.user_perc  | | Percentage of time the CPU is used at the user level |
| cpu.total_logical_cores  | | Total number of logical cores available for an entire node (Includes hyper threading).  **NOTE: This is an optional metric that is only sent when send_rollup_stats is set to true.** |
| disk.inode_used_perc | device, mount_point | The percentage of inodes that are used on a device |
| disk.space_used_perc | device, mount_point | The percentage of disk space that is being used on a device |
| disk.total_space_mb | | The total amount of disk space in Mbytes aggregated across all the disks on a particular node.  **NOTE: This is an optional metric that is only sent when send_rollup_stats is set to true.** |
| disk.total_used_space_mb | | The total amount of used disk space in Mbytes aggregated across all the disks on a particular node.  **NOTE: This is an optional metric that is only sent when send_rollup_stats is set to true.** |
| io.read_kbytes_sec | device | Kbytes/sec read by an io device
| io.read_req_sec | device   | Number of read requests/sec to an io device
| io.read_time_sec | device   | Amount of read time in seconds to an io device
| io.write_kbytes_sec |device | Kbytes/sec written by an io device
| io.write_req_sec   | device | Number of write requests/sec to an io device
| io.write_time_sec | device   | Amount of write time in seconds to an io device
| load.avg_1_min  | | The average system load over a 1 minute period
| load.avg_5_min  | | The average system load over a 5 minute period
| load.avg_15_min  | | The average system load over a 15 minute period
| mem.free_mb | | Mbytes of free memory
| mem.swap_free_perc | | Percentage of free swap memory that is free
| mem.swap_free_mb | | Mbytes of free swap memory that is free
| mem.swap_total_mb | | Mbytes of total physical swap memory
| mem.swap_used_mb | | Mbytes of total swap memory used
| mem.total_mb | | Total Mbytes of memory
| mem.usable_mb | | Total Mbytes of usable memory
| mem.usable_perc | | Percentage of total memory that is usable
| mem.used_buffers | | Number of buffers in Mbytes being used by the kernel for block io
| mem.used_cached | | Mbytes of memory used for the page cache
| mem.used_shared  | | Mbytes of memory shared between separate processes and typically used for inter-process communication
| net.in_bytes_sec  | device | Number of network bytes received per second
| net.out_bytes_sec  | device | Number of network bytes sent per second
| net.in_packets_sec  | device | Number of network packets received per second
| net.out_packets_sec  | device | Number of network packets sent per second
| net.in_errors_sec  | device | Number of network errors on incoming network traffic per second
| net.out_errors_sec  | device | Number of network errors on outgoing network traffic per second
| net.in_packets_dropped_sec  | device | Number of inbound network packets dropped per second
| net.out_packets_dropped_sec  | device | Number of inbound network packets dropped per second
| monasca.thread_count  | service=monitoring component=monasca-agent | Number of threads that the collector is consuming for this collection run
| monasca.emit_time_sec  | service=monitoring component=monasca-agent | Amount of time that the forwarder took to send metrics to the Monasca API.
| monasca.collection_time_sec  | service=monitoring component=monasca-agent | Amount of time that the collector took for this collection run

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

# Standard Plugins
Plugins are the way to extend the Monasca Agent.  Plugins add additional functionality that allow the agent to perform checks on other applications, servers or services.  This section describes the standard plugins that are delivered by default.

** Standard location for plugin YAML config files **
> /etc/monasca/agent/conf.d

The following plugins are delivered via setup as part of the standard plugin checks.  If a corresponding service is found on the system where the Monasca Agent is being installed then a plugin configuration will be created.

| Setup Plugin Name | Dot File  | Detail                 |
| ----------------- | --------- | ---------------------- |
| apache | /root/.apache.cnf | Apache web server |
| cacti | | |
| ceilometer | | OpenStack component |
| cinder | | OpenStack component |
| couch | | |
| couchbase | | |
| cpu | | |
| crash | | |
| directory | | |
| disk | | |
| docker | | |
| elastic | | |
| gearmand | | |
| glance | | OpenStack component |
| gunicorn | | |
| haproxy | | |
| hdfs | | |
| host_alive | | |
| http_check | | |
| iis | | Microsoft Internet Information Services |
| jenkins | | |
| kafka_consumer | | |
| keystone | | OpenStack component | |
| kyototycoon | | |
| libvirt | | |
| lighttpd | | |
| load | | |
| mcache | | |
| memory | | |
| mongo | | |
| mysql | /root/.my.cnf | |
| nagios_wrapper | | |
| network | | |
| neutron | | OpenStack component |
| nginx | | Ngix proxy web server |
| nova | | OpenStack component |
| ntp | | |
| postfix | | |
| postgres | | |
| process | | |
| rabbitmq | /root/.rabbitmq.cnf |
| redisdb | | |
| riak | | |
| sqlserver | | |
| swift | | OpenStack component |
| tcp_check | | |
| varnish | | |
| win32_event_log | | |
| wmi_check | | |
| zk | | Apache Zookeeper |


## Dot File Configuration

Dot files provide an added level of configuration to the component plugins

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


## Default Plugin Detection

The following plugin groups are detected by setup with the default command line switches.

> monasca_setup.detection.plugins.init


| Setup Plugin Group | Cmoponents                             |
| ------------------ | -------------------------------------- |
| Apache | |
| Ceilometer | |
| Cinder | |
| Crash | |
| Glance | |
| Kafka | |
| Keystone | |
| Libvirt | |
| MonAPI | |
| MonPersister | |
| MonThresh | Monasca API, Persister, Threshold Engine |
| MySQL | |
| Neutron | |
| Nova | |
| Ntp | |
| Postfix | |
| RabbitMQ | |
| Swift | |
| System | network, disk, load, memory, cpu |
| Zookeeper | |


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

## Nagios Checks
### Nagios Wrapper
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

### Check_MK_Agent Local
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

### MK Livestatus
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

## Host Alive Checks
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

## Process Checks
Process checks can be performed to verify that a set of named processes are running on the local system. The YAML file `process.yaml` contains the list of processes that are checked. The processes can be identified using a pattern match or exact match on the process name. A Python script `process.py` runs each execution cycle to check that required processes are alive. If the process is running a value of 0 is sent, otherwise a value of 1 is sent to the Monasca API.

Each process entry consists of two primary keys: name and search_string. Optionally, if an exact match on name is required, the exact_match boolean can be added to the entry and set to True.

```
init_config:
 
instances: 
 - name: ssh
   search_string: ['ssh', 'sshd']
 
 - name: mysql
   search_string: ['mysql']
   exact_match: True
``` 
The process checks return the following metrics:

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| process.mem.real_mbytes  | process_name, service, component | Amount of physical memory allocated to a process minus shared libraries in Mbytes
| process.mem.rss_mbytes  | process_name, service, component | Amount of physical memory allocated to a process, including memory from shared libraries in Mbytes
| process.mem.vsz_mbytes  | process_name, service, component | Amount of all the memory a process can access, including swapped, physical, and shared in Mbytes
| process.io.read_count  | process_name, service, component | Number of reads by a process
| process.io.write_count  | process_name, service, component | Number of writes by a process
| process.io.read_kbytes  | process_name, service, component | Kbytes read by a process
| process.io.write_kbytes  | process_name, service, component | Kbytes written by a process
| process.thread_count  | process_name, service, component | Number of threads a process is using
| process.cpu_perc  | process_name, service, component | Percentage of cpu being consumed by a process
| process.open_file_descriptors  | process_name, service, component | Number of files being used by a process
| process.open_file_descriptors_perc  | process_name, service, component | Number of files being used by a process as a percentage of the total file descriptors allocated to the process
| process.involuntary_ctx_switches  | process_name, service, component | Number of involuntary context switches for a process
| process.voluntary_ctx_switches  | process_name, service, component | Number of voluntary context switches for a process
| process.pid_count  | process_name, service, component | Number of processes that exist with this process name


## Http Endpoint Checks
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


## Http Metrics
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
    
## MySQL Checks
This section describes the mySQL check that can be performed by the Agent.  The mySQL check also supports MariaDB.  The mySQL check requires a configuration file called mysql.yaml to be available in the agent conf.d configuration directory.

Sample config:

```
init_config:

instances:
	defaults_file: /root/.my.cnf
	server: localhost
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


## ZooKeeper Checks
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

 
The RabbitMQ checks return the following metrics:

| Metric Name | Dimensions | Check Type |
| ----------- | ---------- | --------- |
| rabbitmq.node.fd_used | hostname, node, service=rabbitmq | Node |
| rabbitmq.node.sockets_used | hostname, node, service=rabbitmq | Node |
| rabbitmq.node.run_queue | hostname, node, service=rabbitmq | Node |
| rabbitmq.node.mem_used | hostname, node, service=rabbitmq | Node |
| rabbitmq.exchange.messages.received_count | hostname, exchange, vhost, type, service=rabbitmq | Exchange |
| rabbitmq.exchange.messages.received_rate | hostname, exchange, vhost, type, service=rabbitmq | Exchange |
| rabbitmq.exchange.messages.published_count | hostname, exchange, vhost, type, service=rabbitmq | Exchange |
| rabbitmq.exchange.messages.published_rate | hostname, exchange, vhost, type, service=rabbitmq | Exchange |
| rabbitmq.queue.consumers | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.memory | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.active_consumers | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.ready | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.ready_rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.publish_count | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.publish_rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.deliver_count | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.deliver_rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.redeliver_count | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.redeliver_rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.unacknowledged | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.unacknowledged_rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.deliver_get_count | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.deliver_get_rate | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.ack_count | hostname, queue, vhost, service=rabbitmq | Queue |
| rabbitmq.queue.messages.ack_rate | hostname, queue, vhost, service=rabbitmq | Queue |


## Apache Web Server Checks
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

## Libvirt VM Monitoring

### Overview
The Libvirt plugin provides metrics for virtual machines when run on the hypervisor server.  It provides two sets of metrics per measurement: one designed for the owner of the VM, and one intended for the owner of the hypervisor server.

### Configuration
The `monasca-setup` program will configure the Libvirt plugin if `nova-api` is running, `/etc/nova/nova.conf` exists, and `python-novaclient` is installed.

In order to fetch data on hosted compute instances, the Libvirt plugin needs to be able to talk to the Nova API.  It does this using credentials found in `/etc/nova/nova.conf` under `[keystone_authtoken]`, obtained when `monasca-setup` is run, and stored in `/etc/monasca/agent/conf.d/libvirt.yaml` as `admin_user`, `admin_password`, `admin_tenant_name`, and `admin_password`.  These credentials are only used to build and update the [Instance Cache](#instance-cache).

The Libvirt plugin uses a cache directory to persist data, which is `/dev/shm` by default.  On non-Linux systems (BSD, Mac OSX), `/dev/shm` may not exist, so `cache_dir` would need to be changed accordingly, either in `monasca_setup/detection/plugins/libvirt.py` prior to running `monasca-setup`, or `/etc/monasca/agent/conf.d/libvirt.yaml` afterwards.

If the owner of the VM is in a different tenant the Agent Cross-Tenant Metric Submission can be setup. See this [documentation](https://github.com/stackforge/monasca-agent/blob/master/docs/MonascaMetrics.md#cross-tenant-metric-submission) for details.

`nova_refresh` specifies the number of seconds between calls to the Nova API to refresh the instance cache.  This is helpful for updating VM hostname and pruning deleted instances from the cache.  By default, it is set to 14,400 seconds (four hours).  Set to 0 to refresh every time the Collector runs, or to None to disable regular refreshes entirely (though the instance cache will still be refreshed if a new instance is detected).

`vm_probation` specifies a period of time (in seconds) in which to suspend metrics from a newly-created VM.  This is to prevent quickly-obsolete metrics in an environment with a high amount of instance churn (VMs created and destroyed in rapid succession).  The default probation length is 300 seconds (five minutes).  Setting to 0 disables VM probation, and metrics will be recorded as soon as possible after a VM is created.

`ping_check` includes the command line (sans the IP address) used to perform a ping check against instances.  Set to False (or omit altogether) to disable ping checks.  This is automatically populated during `monasca-setup` from a list of possible `ping` command lines.  Generally, `fping` is preferred over `ping` because it can return a failure with sub-second resolution, but if `fping` does not exist on the system, `ping` will be used instead.  If ping_check is disabled, the `host_alive_status` metric will not be published unless that VM is inactive.  This is because the host status is inconclusive without a ping check.

`ping_only` will suppress all per-VM metrics aside from `host_alive_status` and `vm.host_alive_status`, including all I/O, network, memory, and CPU metrics.  [Aggregate Metrics](#aggregate-metrics), however, would still be enabled if `ping_only` is true.  By default, `ping_only` is false.  If both `ping_only` and `ping_check` are set to false, the only metrics published by the Libvirt plugin would be the Aggregate Metrics.

Example config:
```
init_config:
    admin_password: pass
    admin_tenant_name: service
    admin_user: nova
    identity_uri: 'http://192.168.10.5:35357/v2.0'
    region_name: 'region1'
    cache_dir: /dev/shm
    nova_refresh: 14400
    vm_probation: 300
    ping_check: /usr/bin/fping -n -c1 -t250 -q
    ping_only: false
instances:
    - {}
```
`instances` are null in `libvirt.yaml`  because the libvirt plugin detects and runs against all provisioned VM instances; specifying them in `libvirt.yaml` is unnecessary.

Note: If the Nova service login credentials are changed, `monasca-setup` would need to be re-run to use the new credentials.  Alternately, `/etc/monasca/agent/conf.d/libvirt.yaml` could be modified directly.

Example `monasca-setup` usage:
```
monasca-setup -d libvirt -a 'ping_check=false ping_only=false'
```

### Instance Cache
The instance cache (`/dev/shm/libvirt_instances.yaml` by default) contains data that is not available to libvirt, but queried from Nova.  To limit calls to the Nova API, the cache is only updated if a new instance is detected (libvirt sees an instance not already in the cache), or every `nova_refresh` seconds (see Configuration above).

Example cache:
```
instance-00000003: {created: '2015-06-26T23:25:06Z', disk: 1, hostname: vm03.testboy.net,
  instance_uuid: 821994dd-bd88-41ae-89e0-6034cc4f4b67, private_ip: 172.31.1.4, ram: 512,
  tenant_id: 121cc3c1d9014c6c89daae90b57213ff, vcpus: 1, zone: nova}
instance-00000004: {created: '2015-06-26T23:29:21Z', disk: 1, hostname: vm04.testboy.net,
  instance_uuid: 6fb6e51c-b9b0-4933-9b70-48acfd82e1f3, private_ip: 172.31.1.5, ram: 512,
  tenant_id: 121cc3c1d9014c6c89daae90b57213ff, vcpus: 1, zone: nova}
last_update: 1436281527
```

### Metrics Cache
The libvirt inspector returns *counters*, but it is much more useful to use *rates* instead.  To convert counters to rates, a metrics cache is used, stored in `/dev/shm/libvirt_metrics.yaml` by default.  For each measurement gathered, the current value and timestamp (UNIX epoch) are recorded in the cache.  The subsequent run of the Monasca Agent Collector compares current values against prior ones, and computes the rate.

Since CPU Time is provided in nanoseconds, the timestamp recorded has nanosecond resolution.  Otherwise, integer seconds are used.

Example cache (excerpt, see next section for complete list of available metrics):
```
instance-00000003:
  cpu.time: {timestamp: 1413327252.150278, value: 191890000000}
  io.read_bytes:
    hdd: {timestamp: 1413327252, value: 139594}
    vda: {timestamp: 1413327252, value: 1604608}
  net.rx_packets:
    vnet0: {timestamp: 1413327252, value: 24}
instance-00000004:
  cpu.time: {timestamp: 1413327252.196404, value: 34870000000}
  io.write_requests:
    hdd: {timestamp: 1413327252, value: 0}
    vda: {timestamp: 1413327252, value: 447}
  net.tx_bytes:
    vnet1: {timestamp: 1413327252, value: 2260}
```
### Per-Instance Metrics

| Name                 | Description                            | Associated Dimensions  |
| -------------------- | -------------------------------------- | ---------------------- |
| cpu.utilization_perc | Overall CPU utilization (percentage)   |                        |
| host_alive_status    | Returns status: 0=OK, 1=fails ping check, 2=inactive  |         |
| io.read_ops_sec      | Disk I/O read operations per second    | 'device' (ie, 'hdd')   |
| io.write_ops_sec     | Disk I/O write operations per second   | 'device' (ie, 'hdd')   |
| io.read_bytes_sec    | Disk I/O read bytes per second         | 'device' (ie, 'hdd')   |
| io.write_bytes_sec   | Disk I/O write bytes per second        | 'device' (ie, 'hdd')   |
| io.errors_sec        | Disk I/O errors per second             | 'device' (ie, 'hdd')   |
| net.in_packets_sec   | Network received packets per second    | 'device' (ie, 'vnet0') |
| net.out_packets_sec  | Network transmitted packets per second | 'device' (ie, 'vnet0') |
| net.in_bytes_sec     | Network received bytes per second      | 'device' (ie, 'vnet0') |
| net.out_bytes_sec    | Network transmitted bytes per second   | 'device' (ie, 'vnet0') |
| mem.free_mb          | Free memory in Mbytes               |                        |
| mem.total_mb         | Total memory in Mbytes              |                        |
| mem.used_mb          | Used memory in Mbytes               |                        |
| mem.free_perc        | Percent of memory free                 |                        |
| mem.swap_used_mb     | Used swap space in Mbytes           |                        |

Memory statistics require a balloon driver on the VM.  For the Linux kernel, this is the `CONFIG_VIRTIO_BALLOON` configuration parameter, active by default in Ubuntu, and enabled by default as a kernel module in Debian, CentOS, and SUSE.

Since separate metrics are sent to the VM's owner as well as Operations, all metric names designed for Operations are prefixed with "vm." to easily distinguish between VM metrics and compute host's metrics.

### VM Dimensions
All metrics include `resource_id` and `zone` (availability zone) dimensions.  Because there is a separate set of metrics for the two target audiences (VM customers and Operations), other dimensions may differ.

| Dimension Name | Customer Value            | Operations Value        |
| -------------- | ------------------------- | ----------------------- |
| hostname       | name of VM as provisioned | hypervisor's hostname   |
| zone           | availability zone         | availability zone       |
| resource_id    | resource ID of VM         | resource ID of VM       |
| service        | "compute"                 | "compute"               |
| component      | "vm"                      | "vm"                    |
| device         | name of net or disk dev   | name of net or disk dev |
| tenant_id      | (N/A)                     | owner of VM             |

### Aggregate Metrics

In addition to per-instance metrics, the Libvirt plugin will publish aggregate metrics across all instances.

| Name                            | Description                                        |
| ------------------------------- | -------------------------------------------------- |
| nova.vm.cpu.total_allocated     | Total CPUs allocated across all VMs                |
| nova.vm.disk.total_allocated_gb | Total Gbytes of disk space allocated to all VMs |
| nova.vm.mem.total_allocated_mb  | Total Mbytes of memory allocated to all VMs     |

Aggregate dimensions include hostname and component from the Operations Value column above.

## Crash Dump Monitoring

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

# License
Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
