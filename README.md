<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Introduction](#introduction)
- [Architecture](#architecture)
- [Installing](#installing)
- [Configuring](#configuring)
  - [Configuration Options](#configuration-options)
  - [Configuring Plugins](#configuring-plugins)
  - [monasca-setup](#monasca-setup)
    - [Configuration Options](#configuration-options-1)
  - [Chef Cookbook](#chef-cookbook)
  - [monasca-alarm-manager](#monasca-alarm-manager)
- [Running](#running)
  - [Running from the command-line](#running-from-the-command-line)
  - [Running as a daemon](#running-as-a-daemon)
- [Trouble-shooting](#trouble-shooting)
- [Naming conventions](#naming-conventions)
  - [Common Naming Conventions](#common-naming-conventions)
    - [Metric Names](#metric-names)
    - [Dimensions](#dimensions)
  - [OpenStack Specific Naming Conventions](#openstack-specific-naming-conventions)
    - [Metric Names](#metric-names-1)
    - [Dimensions](#dimensions-1)
- [Checks](#checks)
  - [System Metrics](#system-metrics)
  - [Nagios](#nagios)
  - [Statsd](#statsd)
  - [Log Parsing](#log-parsing)
  - [Host alive](#host-alive)
  - [Process exists](#process-exists)
  - [Http Endpoint checks](#http-endpoint-checks)
  - [MySQL](#mysql)
  - [RabbitMQ](#rabbitmq)
  - [Kafka](#kafka)
  - [Other](#other)
  - [OpenStack](#openstack)
    - [Nova](#nova)
    - [Swift](#swift)
    - [Glance](#glance)
    - [Cinder](#cinder)
    - [Neutron](#neutron)
    - [Keystone](#keystone)
    - [Seed Controller](#seed-controller)
- [Developing New Checks](#developing-new-checks)
  - [AgentCheck Interface](#agentcheck-interface)
  - [ServicesCheck interface](#servicescheck-interface)
  - [Sending Metrics](#sending-metrics)
  - [Plugin Configuration](#plugin-configuration)
    - [init_config](#init_config)
    - [instances](#instances)
  - [Plugin Documentation](#plugin-documentation)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Introduction
The Monasca Agent is a modern Python monitoring agent for gathering metrics and sending them to the Monasca API. The Agent supports collecting metrics from a variety of sources as follows:

* System metrics such as cpu and memory utilization.
* Nagios plugins. The Monasca Agent can run Nagios plugins and send the status code returned by the plugin as a metric to the Monasca API.
* Statsd. The Monasca Agent supports an integrated Statsd daemon which can be used by applications via a statsd client library.
* Retrieving metrics from log files written in a specific format. 
* Host alive. The Monasca Agent can perform active checks on a host to determine if it is alive using ping(ICMP) or SSH.
* Process exists checks. The Monasca Agent can check if a process is up or down.
* Http Endpoint checks. The Monasca Agent can perform active checks on http endpoints by sending an HTTP request to an API.
* Service checks. The Agent can check service such as MySQL, RabbitMQ, and many more.

For the complete list of metrics that the Monasca Agent supports see "Checks" below.

The Agent is extensible through configuration of additional plugins, written in Python.

# Architecture
This section describes the overall architecture of the Monasca Agent.

* Agent
* Checks

This diagram illustrates the monasca-agent architecture, and the table which follows it explains each component.

![alt text](monasca-agent_arch.png)

A metric is identified by a name and dimensions.

The Agent is composed of the following components:

* Supervisor (supervisord): Manages the lifecycle of the Collector, Forwarder and Statsd Daemon.
* Collector (monasca-collector): Collects system and other metrics and sends to the Forwarder.
* Forwarder (monasca-forwarder): Sends metrics to the API.
* Statsd nDaemon (monasca-statsd): Statsd daemon.

| Component Name | Process Name | Description |
| -------------- | ------------ | ----------- |
| Supervisor | supervisord | Runs as root, launches all other processes as the "monasca-agent" user |
| Collector | monasca-collector | Gathers system & application metrics | 
| Monstatsd | monasca-statsd | Statsd engine capable of handling dimensions associated with metrics submitted by a client that supports them. Also supports metrics from the standard statsd client. (udp/8125) | 
| Forwarder | monasca-forwarder | Gathers data from statsd and submits it to Monasca API over SSL (tcp/17123) | 
| Agent Checks | checks.d/*.py | Python-based user-configured checks |


The Agent includes the script "monasca-setup", that can be used for automatically configuring the agent to generate metrics that are sent to the API.  It creates the agent.conf file locate in /etc/monasca/agent directory.  It also sets up additional checks based on what is running locally on that machine.  For instance, if this is a compute node, the agent will setup checks to monitor the Nova processes and setup a http_status check on the nova-api.  It can also detect other servers such as mySQL and Kafka and setup checks for them as well.

The [monasca-alarm-manager](**https://github.com/hpcloud-mon/monasca-alarm-manager**) is a utility that can be used for configuring a default set of alarms when monitoring a OpenStack deployment.

# Installing
The Agent (monasca-agent) is available for installation from the Python Package Index (PyPI). To install it, you first need `pip` installed on the node to be monitored. Instructions on installing pip may be found at https://pip.pypa.io/en/latest/installing.html.  The Agent will NOT run under any flavor of Windows or Mac OS at this time but has been tested thoroughly on Ubuntu and should work under most flavors of Linux.  Support may be added for Mac OS and Windows in the future.  Example of an Ubuntu or Debian based install:

```
sudo apt-get install python-pip
```

To ensure you are running the latest version of pip

```
sudo pip install --upgrade pip
```

Warning, the Agent is known to not install properly under python-pip version 1.0, which is packaged with Ubuntu 12.04 LTS (Precise Pangolin).

The Agent can be installed using pip as follows:

```
sudo pip install monasca-agent
```

# Configuring
The Agent requires configuration in order to run. There are two ways to configure the agent, either using the [monasca-setup](#monasca-setup) script or manually.

## monasca-setup (Recommended)
The Monasca agent has a script, called "monasca-setup", that should be used to automatically configure the Agent to send metrics to a Monasca API. This script will create the agent.conf configuration file as well as any plugin configuration yaml files needed to monitor the processes on the local machine.  The agent configuration files are located in /etc/monasca/agent.  The plugin configuration files are located in located in /etc/monasca/agent/conf.d.

To run monasca-setup:

```
sudo monasca-setup --username KEYSTONE_USERNAME --password KEYSTONE_PASSWORD --project_name KEYSTONE_PROJECT_NAME --service SERVICE_NAME --keystone_url http://URL_OF_KEYSTONE_API:35357/v3 --monasca_url http://URL_OF_MONASCA_API:8080/v2.0 --overwrite
```
### Explanation of monasca-setup command-line parameters:
All parameters require a '--' before the parameter such as '--verbose'

| Parameter | Description | Example Value|
| ----------- | ------------ | ----------- |
| username | This is a required parameter that specifies the username needed to login to Keystone to get a token | myuser |
| password | This is a required parameter that specifies the password needed to login to Keystone to get a token | mypassword |
| project_name | This is a required parameter that specifies the name of the Keystone project name to store the metrics under | myproject |
| keystone_url | This is a required parameter that specifies the url of the keystone api for retrieving tokens | http://192.168.1.5:35357/v3 |
| service | This is a required parameter that specifies the name of the service associated with this particular node | nova, cinder, myservice |
| monasca_url | This is a required parameter that specifies the url of the monasca api for retrieving tokens | http://192.168.1.4:8080/v2.0 |
| config_dir | This is an optional parameter that specifies the directory where the agent configuration files will be stored. | /etc/monasca/agent |
| log_dir | This is an optional parameter that specifies the directory where the agent log files will be stored. | /var/log/monasca/agent |
| template_dir | This is an optional parameter that specifies the directory where the agent template files will be stored. | /usr/local/share/monasca/agent |
| user | This is an optional parameter that specifies the user name to run monasca-agent as | monasca-agent |
| headless | This is an optional parameter that specifies whether monasca-setup should run in a non-interactive mode | |
| skip_enable | This is an optional parameter. By default the service is enabled, which requires the script run as root. Set this parameter to skip that step. | |
| verbose | This is an optional parameter that specifies whether the monasca-setup script will print additional information for debugging purposes | |
| overwrite | This is an optional parameter to overwrite the plugin configuration.  Use this if you don't want to keep the original configuration.  If this parameter is not specified, the configuration will be appended to the existing configuration, possibly creating duplicate checks.  **NOTE:** The agent config file, agent.conf, will always be overwritten, even if this parameter is not specified |  |

### Manual Configuration of the Agent

This is not the recommended way to configure the agent but if you are having trouble running the monasca-setup program, you can manually configure the agent using the steps below:

Start by creating an agent.conf file.  An example configuration file can be found in /usr/local/share/monasca/agent/.

    sudo mkdir -p /etc/monasca/agent
    sudo cp /usr/local/share/monasca/agent/agent.conf.template /etc/monasca/agent/agent.conf

and then edit the file with your favorite text editor (vi, nano, emacs, etc.)

    sudo nano /etc/monasca/agent/agent.conf

In particular, replace any values that have curly braces.
Example:
Change

	username: {args.username}

			to

	username: myuser

You must replace all of the curly brace values and you can also optionally tweak any of the other configuration items as well like a port number in the case of a port conflict.  The config file options are documented in the agent.conf.template file.  You may also specify zero or more dimensions that would be included in every metric generated on that node, using the dimensions: value. Example: (include no extra dimensions on every metric)

    dimensions: (This means no dimensions)
			OR
    dimensions: service:nova (This means one dimension called service with a value of nova)
    		OR
    dimensions: service:nova, group:group_a, zone:2 (This means three dimensions)

Once the configuration file has been updated and saved, monasca-agent must be restarted.

    sudo service monasca-agent restart


### Manual Configuration of Plugins
If you did not run monasca-setup and/or there are additional plugins you would like to activate, follow the steps below:

Agent plugins are activated by placing a valid configuration file in the /etc/monasca/agent/conf.d/ directory. Configuration files are in YAML format, with the file extension .yaml. You may find example configuration files in /usr/local/share/monasca/agent/conf.d/

For example, to activate the http_check plugin:

    sudo mkdir -p /etc/monasca/agent/conf.d
    sudo cp /usr/local/share/monasca/agent/conf.d/http_check.yaml.example /etc/monasca/agent/conf.d/http_check.yaml

and then edit the file as needed for your configuration.

    sudo nano /etc/monasca/agent/conf.d/http_check.yaml

The plugins are annotated and include the possible configuration parameters. In general, though, configuration files are split into two sections:
init_config
   and
instances
The init_config section contains global configuration parameters for the plugin. The instances section contains one or more check to run. For example, multiple API servers can be checked from one http_check.yaml configuration by listing YAML-compatible stanzas in the instances section.

A plugin config is specified something like this:

    init_config:
    	is_jmx: true

    	# Metrics collected by this check. You should not have to modify this.
    	conf:
       	#
       	# Aggregate cluster stats
        	#
        	- include:
            domain: '"kafka.server"'
            bean: '"kafka.server":type="BrokerTopicMetrics",name="AllTopicsBytesOutPerSec"'
            attribute:
                MeanRate:
                    metric_type: counter
                    alias: kafka.net.bytes_out

    instances:
		- 	host: localhost
        	port: 9999
        	name: jmx_instance
        	user: username
        	password: password
        	#java_bin_path: /path/to/java #Optional, should be set if the agent cannot find your java executable
        	#trust_store_path: /path/to/trustStore.jks # Optional, should be set if ssl is enabled
        	#trust_store_password: password
        	dimensions:
             env: stage
             newDim: test



## Chef Cookbook
An example cookbook for Chef configuration of the monitoring agent is at [https://github.com/stackforge/cookbook-monasca-agent](https://github.com/stackforge/cookbook-monasca-agent).  This cookbook can be used as an example of how to automate the install and configuration of the monasca-agent.

## monasca-alarm-manager
To help configure a default set of alarms for monitoring an OpenStack deployment the `monasca-alarm-manager` can be used. The alarm manager is under development in Github at, [https://github.com/hpcloud-mon/monasca-alarm-manager](https://github.com/hpcloud-mon/monasca-alarm-manager).

# Running
The Agent can be run from the command-line or as a daemon.

## Running from the command-line
To run the agent from the command-line, you will need to start at least 2 processes in order to send metrics.  These are the collector and forwarder.  If you have already installed the monasca-agent package and run the monasca-setup configuration script, run the following commands from the Linux command-line:

	* From a terminal window, use netcat to listen for metrics on a local port:
		nc -lk 8080
	* From a second terminal window, launch the forwarder in the background:
		python ddagent.py &
	* From the second terminal window, launch the collector in the foreground:
		python agent.py foreground --use-local-forwarder
	* Metric payloads will start to appear in the first terminal window running netcat

## Running as a daemon
To control the monasca-agent daemon, you can use the init.d commands that are listed below:

	* To start the agent:
		sudo service monasca-agent start
	* To stop the agent:
		sudo service monasca-agent stop
	* To restart the agent if it is already running:
		sudo service monasca-agent restart

# Trouble-shooting
TBD

# Naming conventions

## Common Naming Conventions

### Metric Names
Although metric names in the Monasca API can be any string the Monasca Agent uses several naming conventions as follows:

* All lowercase characters.
* '.' is used to hierarchially group. This is done for compabilty with Graphite as Graphite assumes a '.' as a delimiter.
* '_' is used to separate words in long names that are not meant to be hierarchial.

### Dimensions
Dimensions are a dictionary of (key, value) pairs that can be used to describe metrics. Dimensions are supplied to the API by Agent.

This section documents some of the common naming conventions for dimensions that should observed by the monitoring agents/checks to improve consistency and make it easier to create alarms and perform queries.

All key/value pairs are optional and dependent on the metric.

| Name | Description |
| ---- | ----------- | 
| hostname | The FQDN of the host being measured. |
| observer_hostname | The FQDN of the host that runs a check against another host. |
| url | In the case of the http endpoint check the url of the http endpoint being checked. |
| device | The device name |

## OpenStack Specific Naming Conventions
This section documents some of the naming conventions that are used for monitoring OpenStack.

### Metric Names
Where applicable, each metric name will list the name of the service, such as "compute", component, such as "nova-api", and check that is done, such as "process_exists". For example, "nova.api.process_exists".

### Dimensions
This section documents the list of dimensions that are used in monitoring OpenStack.

| Name | Description | Examples |
| ---- | ----------- | -------- |
| region | An OpenStack region.  | `uswest` and `useast` |
| zone| An OpenStack zone | Examples include `1`, `2` or `3` |
| cloud_tier | Used to identify the tier in the case that TripleO is being used. See http://docs.openstack.org/developer/tripleo-incubator/README.html. | `seed_cloud`, `undercloud`, `overcloud`, `paas` | 
| service | The name of the OpenStack service being measured. | `compute` or `image` or `monitoring` |
| component | The component in the OpenStack service being measured. |`nova-api`, `nova-scheduler`, `mysql` or `rabbitmq`. |
| resource_id | The resource ID of an OpenStack resource. | |
| tenant_id | The tenant/project ID of the owner of an OpenStack resource. | |

# Checks
This section documents all the checks that are supported by the Agent.

## System Metrics
This section documents the system metrics that are sent by the Agent.

| Metric Name | Dimensions | Semantics |
| ----------- | ---------- | --------- |
| system.cpu.idle_perc  | | Percentage of time the CPU is idle when no I/O requests are in progress |
| system.cpu.iowait_perc | | Percentage of time the CPU is idle AND there is at least one I/O request in progress |
| system.cpu.stolen_perc |  | Percentage of stolen CPU time, i.e. the time spent in other OS contexts when running in a virtualized environment |
| system.cpu.system_perc |  | Percentage of time the CPU is used at the system level |
| system.cpu.user_perc  | | Percentage of time the CPU is used at the user level |
| system.disk.usage | device | |
| system.mountpoint | | (OS dependent)  The amount of disk space being used
| system.inodes | device | |
| system.mountpoint | | (OS dependent)  inodes remaining in a filesystem
| system.inodes_perc | device | |
| system.mountpoint | | (OS dependent)  Percentage of inodes remaining in a filesystem
| system.io_read_kbytes_sec device  | | Kbytes/sec read by an io device
| system.io.read_req_sec | device   | Number of read requests/sec to an io device
| system.io.write_kbytes_sec |device | Kbytes/sec written by an io device
| system.io.write_req_sec   | device | Number of write requests/sec to an io device
| system.cpu.load_avg_1min  | | The average system load over a 1 minute period
| system.cpu.load_avg_5min  | | The average system load over a 5 minute period
| system.cpu.load_avg_15min  | | The average system load over a 15 minute period
| system.mem.free_mb | | Megabytes of free memory
| system.mem.swap_free_mb | | Megabytes of free swap memory that is free
| system.mem.swap_total_mb | | Megabytes of total physical swap memory
| system.mem.swap_used_mb | | Megabytes of total swap memory used
| system.mem.total_mb | | Total megabytes of memory
| system.mem.usable_mb | | Total megabytes of usable memory
| system.mem.usable_perc | | Percentage of total memory that is usable
| system.mem.used_buffers | | Number of buffers being used by the kernel for block io
| system.mem_used_cached | | Memory used for the page cache
| system.mem.used_shared  | | Memory shared between separate processes and typically used for inter-process communication

## Nagios
The Agent can run Nagios plugins. A YAML file (nagios_wrapper.yaml) contains the list of Nagios checks to run, including the check name, command name with parameters, and desired interval between iterations. A Python script (nagios_wrapper.py) runs each command in turn, captures the resulting exit code (0 through 3, corresponding to OK, warning, critical and unknown), and sends that information to the Forwarder, which then sends the Monitoring API. Currently, the Agent can only  send the exit code from a Nagios plugin. Any accompanying text is not sent.
 
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

* check_interval (optional) If unspecified, the checks will be run at the regular collector interval, which is 15 seconds by default. You may not want to run some checks that frequently, especially if they are resource-intensive, so check_interval lets you force a delay, in seconds, between iterations of that particular check.  The state for these are stored in temp_file_path with file names like nagios_wrapper_19fe42bc7cfdc37a2d88684013e66c7b.pck where the hash is an md5sum of the service_name (to accommodate odd characters that the filesystem may not like).
 
## Statsd
The Agent ships with a Statsd daemon implementation called monstatsd. A statsd client can be used to send metrics to the Forwarder via the Statsd daemon.

monstatsd will accept metrics submitted by functions in either the standard statsd Python client library, or monasca-agent's monstatsd-python Python client library. The advantage of using the monstatsd-python library is that it is possible to specify dimensions on submitted metrics. Dimensions are not handled by the standard statsd client.

Statsd metrics are not bundled along with the metrics gathered by the Collector, but are flushed to the agent Forwarder on a separate schedule (every 10 seconds by default, rather than 15 seconds for Collector metrics).

Here is an example of metrics submitted using the standard statsd Python client library.

```
import statsd

statsd.increment('processed', 5)        # Increment 'processed' metric by 5
statsd.timing('pipeline', 2468.34)      # Pipeline took 2468.34 ms to execute
statsd.gauge('gaugething', 3.14159265)  # 'gauge' would be the preferred metric type for Monitoring
```

The monstatsd-python library provides client support for dimensions.

Metrics submission to monstatsd using the monstatsd-python Python client library may look like this:

```
from monstatsd import statsd

statsd.gauge('withdimensions', 6.283185, dimensions=['name1:value1', 'name2:value2'])
```

Here are some examples of how code can be instrumented using calls to monstatsd.

```
# Import the module once it's installed.
from monstatsd import statsd

# Optionally, configure the host and port if you're running Statsd on a
# non-standard port.
statsd.connect('localhost', 8125)

# Increment a counter.
statsd.increment('page.views')

# Record a gauge 50% of the time.
statsd.gauge('users.online', 123, sample_rate=0.5)

# Sample a histogram.
statsd.histogram('file.upload.size', 1234)

# Time a function call.
@statsd.timed('page.render')
def render_page():
    # Render things ...

# Tag a metric.
statsd.histogram('query.time', 10, dimensions = ["version:1"])
```

## Log Parsing
TBD

## Host alive
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
  - host_name: somehost.somedomain.net
    alive_test: ssh
 
  - host_name: gateway.somedomain.net
    alive_test: ping
 
  - host_name: 192.168.0.221
    alive_test: ssh
```        

## Process exists
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

## Http Endpoint checks
This section describes the http endpoint check that can be performed by the Agent. Http endpoint checks are checks that perform simple up/down checks on services, such as HTTP/REST APIs. An agent, given a list of URLs can dispatch an http request and report to the API success/failure as a metric.

The Agent supports additional functionality through the use of Python scripts. A YAML file (http_check.yaml) contains the list of URLs to check (among other optional parameters). A Python script (http_check.py) runs checks each host in turn, returning a 0 on success and a 1 on failure in the result sent through the Forwarder and on the Monitoring API.
 
Similar to other checks, the configuration is done in YAML, and consists of two keys: init_config and instances.  The former is not used by http_check, while the later contains one or more URLs to check, plus optional parameters like a timeout, username/password, pattern to match against the HTTP response body, whether or not to include the HTTP response in the metric (as a 'detail' dimension), whether or not to also record the response time, and more.

```
instances:
       url: http://192.168.0.254/healthcheck
       timeout: 1
       include_content: true
       collect_response_time: true
       match_pattern: '.*OK.*OK.*OK.*OK.*OK'
```
 
Example Output

```
    "metrics" : [
      [
         "http_status",
         1394833060,
         0,
         {
            "type" : "gauge",
            "hostname" : "agenthost.domain.net",
            "dimensions" : [
               "url:http://192.168.0.254/healthcheck",
               "detail:\"* deadlocks: OK\\n* mysql-db: OK\\n* rabbitmq-api: OK\\n* rabbitmq-external: OK\\n* rabbitmq-internal: OK\\n\""
            ]
         }
      ],
      [
         "http_response_time",
         1394833060,
         0.251352787017822,
         {
            "type" : "gauge",
            "hostname" : "agenthost.domain.net",
            "dimensions" : [
               "url:http://192.168.0.254/healthcheck"
            ]
         }
      ],
    ],
```
    
## MySQL
## RabbitMQ
## Kafka
## Other
## OpenStack
The `monasca-setup` script when run on a system that is running OpenStack services configures the Agent to send the following list of metrics.

### Nova
This section documents all the checks done for the OpenStack Nova service.

| Component | Metric Name | Metric Type | Check Type | Unit | Plugin | Description | Notes |
| --------- | ----------- | ----------- | ---------- | ---- | ------ | ----------- | ----- |
| nova-api | nova.api.process_exists | Gauge | Passive | Binary | process | nova-api process exists |
| nova-api | nova.api.http_status | Gauge | Passive | Binary | process | nova-api http endpoint is alive | This check should be executed on multiple systems.|
| nova-compute | nova.compute.process_exists | Gauge | Passive | Binary | process | nova-api process exists |


### Swift

### Glance

### Cinder

### Neutron

### Keystone

### Seed Controller

# Developing New Checks

Developers can extend the functionality of the Agent by writing custom plugins. Plugins are written in Python according to the conventions described below. The plugin script is placed in /etc/monasca/agent/checks.d, and a YAML file containing the configuration for the plugin is placed in /etc/monasca/agent/conf.d. The YAML file must have the same stem name as the plugin script.

## AgentCheck Interface
Most monasca-agent plugin code uses the AgentCheck interface. All custom checks inherit from the AgentCheck class found in monagent/collector/checks/__init__.py and require a check() method that takes one argument, instance, which is a dict specifying the configuration of the instance on behalf of the plugin being executed. The check() method is run once per instance defined in the check's configuration (discussed later).

## ServicesCheck interface
Some monasca-agent plugins use the ServicesCheck class found in monagent/collector/services_checks.py. These require a _check() method that is similar to AgentCheck's check(), but instead of being called once per iteration in a linear fashion, it is run against a threadpool to allow concurrent instances to be checked. Also, _check() must return a tuple consisting of either Status.UP or 'Status.DOWN(frommonagent.collector.checks.services_checks`), plus a text description.

The size of the threadpool is either 6 or the total number of instances, whichever is lower. This may be adjusted with the threads_count parameter in the plugin's init_config (see Plugin Configuration below).

## Sending Metrics
Sending metrics in a check is easy, and is very similar to submitting metrics using a statsd client. The following methods are available:

```
self.gauge( ... ) # Sample a gauge metric

self.increment( ... ) # Increment a counter metric

self.decrement( ... ) # Decrement a counter metric

self.histogram( ... ) # Sample a histogram metric

self.rate( ... ) # Sample a point, with the rate calculated at the end of the check
```

All of these methods take the following arguments:

* metric: The name of the metric
* value: The value for the metric (defaults to 1 on increment, -1 on decrement)
* dimensions: (optional) A list of dimensions (name:value pairs) to associate with this metric
* hostname: (optional) A hostname to associate with this metric. Defaults to the current host
* device_name: (optional) A device name to associate with this metric

These methods may be called from anywhere within your check logic. At the end of your check function, all metrics that were submitted will be collected and flushed out with the other Agent metrics.

As part of the parent class, you're given a logger at self.log>. The log handler will be checks.{name} where {name} is the stem filename of your plugin.

Of course, when writing your plugin you should ensure that your code raises meaningful exceptions when unanticipated errors occur.

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
    - username: jane_smith
      password: 789012
```

### init_config
In the init_config section you can specify an arbitrary number of global name:value pairs that will be available on every run of the check in self.init_config.

### instances
The instances section is a list of instances that this check will be run against. Your actual check() method is run once per instance. The name:value pairs for each instance specify details about the instance that are necessary for the check.

## Plugin Documentation
Your plugin should include an example YAML configuration file to be placed in /etc/monasca/agent/conf.d/ which has the name of the plugin YAML file plus the extension '.example', so the example configuration file for the process plugin would be at /etc/monasca/agent/conf.d/process.yaml.example. This file should include a set of example init_config and instances clauses that demonstrate how the plugin can be configured.

# License
Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
