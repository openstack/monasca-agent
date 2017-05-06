<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Architecture](#architecture)
- [Installing](#installing)
- [Configuring](#configuring)
  - [monasca-setup (Recommended)](#monasca-setup-recommended)
    - [Explanation of primary monasca-setup command-line parameters:](#explanation-of-primary-monasca-setup-command-line-parameters)
    - [Providing Arguments to Detection plugins](#providing-arguments-to-detection-plugins)
  - [Manual Configuration of the Agent](#manual-configuration-of-the-agent)
  - [Dimension Precedence](#dimension-precedence)
  - [Manual Configuration of Plugins](#manual-configuration-of-plugins)
- [Running](#running)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Architecture
The Monasca Agent is the component of the [Monasca](https://wiki.openstack.org/wiki/Monasca) monitoring system that collects metrics from the system it is running on and sends them to the Monasca API.

A metric is identified by a name and dimensions.  The fields required in a metric are name, timestamp, and value.  A metric can also have 0..n dimensions.  Some standard dimensions are sent with all metrics that are sent by the agent.

<img src="https://github.com/openstack/monasca-agent/raw/master/docs/monasca-agent_arch.png" alt="Monasca Agent Diagram">

The flow of the agent application goes like this:

* The collector runs based on a configurable interval and collects system metrics such as cpu or disk utilization as well as any metrics from additional configured plugins such as mySQL or Kafka.
* The statsd daemon allows users to send statsd type messages to the agent at any time.  These messages are flushed periodically to the forwarder.
* The forwarder takes the metrics from the collector and statsd daemon and forwards them on to the Monasca-API.
* Once sent to the Monasca-API, the metrics continue through the Monasca pipeline and end up in the Metrics Database.
* The collector then waits for the configured interval and restarts the collection process.

The Agent is composed of the following components:

| Component Name | Process Name | Description |
| -------------- | ------------ | ----------- |
| Supervisor | supervisord | Runs as root, launches all other processes as the user configured to run monasca-agent.  This process manages the lifecycle of the Collector, Forwarder and Statsd Daemon.  It allows Start, Stop and Restart of all the agent processes together. |
| Collector | monasca-collector | Gathers system & application metrics on a configurable interval and sends them to the Forwarder process. The collector runs various plugins for collection of different plugins.|
| Forwarder | monasca-forwarder | Gathers data from the collector and statsd and submits it to Monasca API over SSL (tcp/17123) |
| Statsd Daemon | monasca-statsd | Statsd engine capable of handling dimensions associated with metrics submitted by a client that supports them. Also supports metrics from the standard statsd client. (udp/8125) |
| Monasca Setup | monasca-setup | The monasca-setup script configures the agent.  The Monasca Setup program can also auto-detect and configure certain agent plugins |

# Installing
The Agent (monasca-agent) is available for installation from the Python Package Index (PyPI). To install it, you first need `pip` installed on the node to be monitored. Instructions on installing pip may be found at https://pip.pypa.io/en/latest/installing.html.  The Agent will NOT run under any flavor of Windows or Mac OS at this time but has been tested thoroughly on Ubuntu and should work under most flavors of Linux.  Support may be added for Mac OS and Windows in the future.  Example of an Ubuntu or Debian based install:

    $ sudo apt-get install python-pip

To ensure you are running the latest version of pip

    $ sudo pip install --upgrade pip

Warning, the Agent is known to not install properly under python-pip version 1.0, which is packaged with Ubuntu 12.04 LTS (Precise Pangolin).

The Agent can be installed using pip as follows:

    $ sudo pip install monasca-agent

# Configuring
The Agent requires configuration in order to run. There are two ways to configure the agent, either using the [monasca-setup](#monasca-setup) script or manually.

## monasca-setup (Recommended)
The Monasca agent has a script, called "monasca-setup", that should be used to automatically configure the Agent to send metrics to a Monasca API. This script will create the agent.yaml configuration file as well as any plugin configuration yaml files needed to monitor the processes on the local machine. Additionally this will create an appropriate startup script for the system and enable the agent to start on boot. The monasca-setup script will then auto-detect certain applications and OpenStack processes that are running on the machine. Lastly it will start the agent.

The agent configuration files are located in /etc/monasca/agent.

The plugin configuration files are located in /etc/monasca/agent/conf.d.

monasca-setup is located in `[installed prefix dir]/bin/monasca-setup` and can be run as follows:

    $ sudo monasca-setup --username KEYSTONE_USERNAME \
      --password KEYSTONE_PASSWORD --project_name KEYSTONE_PROJECT_NAME \
      --keystone_url http://URL_OF_KEYSTONE_API:35357/v3

It is also possible to skip most detection plugins in monasca-setup with the `--system_only` flag. You can then come back later and run individual detection plugins without additional arguments,
for example `monasca-setup -d mysql`. This allows a base install to setup the agent and required credentials then later easily add additional services and monitoring.

Alternatively you can disable selected detection plugins with the `--skip_detection_plugins` parameter.

### Explanation of primary monasca-setup command-line parameters:
All parameters require a '--' before the parameter such as '--verbose'. Run `monasca-setup --help` for a full listing of options.

| Parameter | Description | Example Value|
| --------- | ----------- | ------------ |
| username | This is a required parameter that specifies the username needed to login to Keystone to get a token | myuser |
| password | This is a required parameter that specifies the password needed to login to Keystone to get a token | mypassword |
| user_domain_id | User domain id for username scoping | dcff2e7ede243eb7b3c2c1d57cfc46d1 |
| user_domain_name | User domain name for username scoping | MyDomain |
| project_name | Specifies the name of the Keystone project name to store the metrics under, defaults to users default project. | myproject |
| project_domain_id | Project domain id for keystone authentication | |
| project_domain_name | Project domain name for keystone authentication | |
| project_id | Keystone project id  for keystone authentication | |
| check_frequency | How often to run metric collection in seconds | 60 |
| num_collector_threads | Number of threads to use in collector for running checks | 1 |
| pool_full_max_retries | Maximum number of collection cycles where all of the threads in the pool are still running plugins before the collector will exit| 4 |
| plugin_collect_time_warn | Number of seconds a plugin collection time exceeds that causes a warning to be logged for that plugin| 6 |
| keystone_url | This is a required parameter that specifies the url of the keystone api for retrieving tokens. It must be a v3 endpoint. | http://192.168.1.5:35357/v3 |
| dimensions | A comma separated list of key:value pairs to include as dimensions in all submitted metrics| region:a,az:1 |
| service | This is an optional parameter that specifies the name of the service associated with this particular node | nova, cinder, myservice |
| monasca_url | This is an optional parameter that specifies the url of the monasca api for retrieving tokens. By default this is obtained from the registered service in keystone. | http://192.168.1.4:8080/v2.0 |
| skip_enable | This is an optional parameter. By default the service is enabled, which requires the script run as root. Set this parameter to skip that step. | |
| verbose | This is an optional parameter that specifies whether the monasca-setup script will print additional information for debugging purposes | |
| dry_run | If specified no config changes will be made but what changes will happen will be reported. | |
| service | Service this node is associated with, added as a dimension. | |
| system_only | This optional parameter if set true will cause only the basic system checks to be configured all other detection will be skipped. Basic system checks include cpu, disk, load, memory, network. | |
| detection_plugins | Skip base config and service setup and only configure provided space separated list of plugins. This assumes the base config has already run.| kafka ntp|
| skip_detection_plugins | Skip provided space separated list of detection plugins. | system |
| overwrite | This is an optional parameter to overwrite the plugin configuration.  Use this if you don't want to keep the original configuration.  If this parameter is not specified, the configuration will be appended to the existing configuration, possibly creating duplicate checks.  **NOTE:** The agent config file, agent.yaml, will always be overwritten, even if this parameter is not specified. | |
| detection_args | Some detection plugins can be passed arguments. This is a string that will be passed to the detection plugins. | "hostname=ping.me" |
| detection_args_json | A JSON string can be passed to the detection plugin. | '{"process_config":{"process_names":["monasca-api","monasca-notification"],"dimensions":{"service":"monitoring"}}}' |
| max_measurement_buffer_size | Integer value for the maximum number of measurements to buffer locally while unable to connect to the monasca-api. If the queue exceeds this value, measurements will be dropped in batches. A value of '-1' indicates no limit | 100000 |
| backlog_send_rate | Integer value of how many batches of buffered measurements to send each time the forwarder flushes data | 1000 |
| monasca_statsd_port | Integer value for statsd daemon port number | 8125 |

#### A note around using monasca-agent with different versions of Keystone

Keystone comes in two version: **v2.0** and **v3**. These versions differ between each
other when it comes to the set of acceptable parameters that client library can send to Keystone API.

monasca-agent can work with either of versions mentioned above.
However there are certain limitations. Examine a list below to see what
parameters should be provided via monasca-setup (or manually in agent.yaml) to
successfully configure connectivity with Keystone.

For **v2_0** arguments are:
* ```username```
* ```password```
* ```project_id``` (internally mapped to **tenant_id**)
* ```project_name``` (internally mapped to **tenant_name**)

For **v3** arguments are:
* ```username```
* ```password```
* ```project_id```
* ```project_name```
* ```project_domain_id```
* ```project_domain_name```
* ```user_domain_id```
* ```user_domain_name```

### Providing Arguments to Detection plugins
When running individual detection plugins you can specify arguments that augment the configuration created. In some instances the arguments just provide additional
information for the detection plugin, for example `monasca-setup -d nova -a disable_http_check=true.` In others detection is skipped entirely and the arguments provide
the configuration details. For the argument based plugins monasca-setup is used not for detection but as a tool to merge various configurations details without having to parse the configuration.
For example, `monasca-setup -d httpcheck -a 'url=http://ip:port/ dimensions=service:my_service'`. Both the httpcheck and hostalive check are argument based plugins.

## Manual Configuration of the Agent

This is not the recommended way to configure the agent but if you are having trouble running the monasca-setup program, you can manually configure the agent using the steps below:

Start by creating an agent.yaml file.  An example configuration file can be found in <install_dir>/share/monasca/agent/.

    $ sudo mkdir -p /etc/monasca/agent
    $ sudo cp /usr/local/share/monasca/agent/agent.yaml.template /etc/monasca/agent/agent.yaml

and then edit the file with your favorite text editor (vi, nano, emacs, etc.)

    $ sudo nano /etc/monasca/agent/agent.yaml

In particular, replace any values that have curly braces.
Example:
Change

    username: {args.username}

        to

    username: myuser

You must replace all of the curly brace values and you can also optionally tweak any of the other configuration items as well like a port number in the case of a port conflict.  The config file options are documented in the agent.yaml.template file.  You may also specify zero or more dimensions that would be included in every metric generated on that node, using the dimensions: value. Example: (include no extra dimensions on every metric)

    dimensions: (No dimensions example)
        OR
    dimensions: (Single dimension example)
        service: nova
        OR
    dimensions: (3 dimensions example)
        service: nova
        group: group_a
        zone: 2

Once the configuration file has been updated and saved, monasca-agent must be restarted.

    $ sudo service monasca-agent restart

## Dimension Precedence
If a dimension is specified in /etc/monasca/agent/agent.yaml with the same name (e.g. service)
```
Main:
  check_freq: 15
  dimensions:
    service: monitoring
  hostname: mini-mon
```

The default internal dimension for a specific plugin will be overwritten (e.g. mysql.py) by the agent configuration

```
dimensions = self._set_dimensions({'component': 'mysql', 'service': 'mysql'}, instance)
```
Your final dimension value from agent.yaml would prevail

```
service: monitoring
```

## Manual Configuration of Plugins
If you did not run monasca-setup and/or there are additional plugins you would like to activate there are two options.

If a detection plugin exists for monasca-setup you can run monasca-setup with the --detection_plugins flage, ie `monasca-setup --detection-plugins kafka`.

To manually configure a plugin follow the steps below:

Agent plugins are activated by placing a valid configuration file in the /etc/monasca/agent/conf.d/ directory. Configuration files are in YAML format, with the file extension .yaml. You may find example configuration files in /usr/local/share/monasca/agent/conf.d/

For example, to activate the http_check plugin:

    $ sudo mkdir -p /etc/monasca/agent/conf.d
    $ sudo cp /usr/local/share/monasca/agent/conf.d/http_check.yaml.example \
      /etc/monasca/agent/conf.d/http_check.yaml

and then edit the file as needed for your configuration.

    $ sudo nano /etc/monasca/agent/conf.d/http_check.yaml

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
        - host: localhost
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

monasca-collector service can receive a `--config-file` argument, which represents an alternate agent configuration file, instead of the default /etc/monasca/agent.yaml.

example:

```
monasca-collector --config-file="/path/to/monasca_agent.yaml"
```

# Running
The monasca-setup command will create an appropriate startup script for the agent and so the agent can be run by using the standard daemon control tool for your operating system. If you have configured manually the startup script templates can be found in the code under the packaging directory.

# Running the collector with multiple threads
The number of threads to use for running the plugins is via num_collector_threads. Setting this value to greater than 1 can be very useful when some plugins take a relatively long time to run. With num_collector_threads set to 1, the plugins are run serially. If the sum of the collection times for each plugin is greater than the check_frequency, then the metrics will not be collected as often as they should be. With more threads, the collection time is closer to the longest plugin collection time.

The collector is optimized for collecting as many metrics on schedule as possible. The plugins are run in reverse order of their collection time, i.e., the fastest plugin first. Also, if a plugin does not complete within the collection frequency, that plugin will be skipped in the next collection cycle. These two optimizations together ensure that plugins that complete with collection frequency seconds will get run on every collection cycle.

If there is some problem with multiple plugins that end up blocking the entire thread pool, the collector will exit so that it can be restarted by the supervisord. The parameter pool_full_max_retries controls when this happens. If pool_full_max_retries consecutive collection cycles have ended with the Thread Pool completely full, the collector will exit.

Some of the plugins have their own thread pools to handle asynchronous checks. The collector thread pool is separate and has no special interaction with those thread pools.
# License
(C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
