<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Customizing the Monasca Agent](#customizing-the-monasca-agent)
  - [Overview](#overview)
  - [Managing Built-In and Custom Plugins](#managing-built-in-and-custom-plugins)
    - [Configuring Built-In Check Plugins](#configuring-built-in-check-plugins)
    - [Adding Custom Check Plugins](#adding-custom-check-plugins)
    - [Adding Custom Detection Plugins](#adding-custom-detection-plugins)
    - [Disabling Built-In Check Plugins](#disabling-built-in-check-plugins)
  - [Customization Best Practices](#customization-best-practices)
    - [Metric Specification Best Practices](#metric-specification-best-practices)
      - [Appropriate Use of Metrics](#appropriate-use-of-metrics)
    - [Custom Plugin Best Practices](#custom-plugin-best-practices)
  - [Creating Custom Plugins](#creating-custom-plugins)
    - [Creating a Custom Check Plugin](#creating-a-custom-check-plugin)
      - [AgentCheck Interface](#agentcheck-interface)
      - [ServicesCheck interface](#servicescheck-interface)
      - [Submitting Metrics](#submitting-metrics)
      - [Example Check Plugin](#example-check-plugin)
      - [Check Plugin Configuration](#check-plugin-configuration)
        - [init_config](#init_config)
        - [instances](#instances)
        - [Plugin Documentation](#plugin-documentation)
    - [Creating a Custom Detection Plugin](#creating-a-custom-detection-plugin)
      - [Plugins Object](#plugins-object)
      - [Plugin Interface](#plugin-interface)
      - [Plugin Utilities](#plugin-utilities)
      - [Example Detection Plugin](#example-detection-plugin)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

This README describes how to customize the Monasca agent.

# Customizing the Monasca Agent

## Overview

The Collector component of the Agent runs at a configurable interval, generating a standard set of Monasca metrics. The Collector also executes a configurable set of Python check plugins. In addition to the plugins shipped with the agent, additional custom check plugins can be added.

Although check plugins can be configured manually, the `monasca-setup` tool is provided to help with this. When run, `monasca-setup` configures the check plugins based on auto-detection of the configuration and status of components and subsystems present on the local system. To accomplish this, the setup script runs a configurable set of Python detection plugins, each of which performs a subset of this auto-detection. Custom detection plugins can be added to do detection and configuration for custom check plugins.

The following sections describe how one customizes the Monasca Agent by:
- Configuring built-in check plugins
- Adding custom check plugins
- Adding custom detection plugins
- Disabling built-in check plugins
- Providing custom configurations for built-in check plugins

## Managing Built-In and Custom Plugins

### Configuring Built-In Check Plugins

The built-in Python check plugin scripts are installed as part of the monasca-agent package, and are available in `[installed base dir]/monasca_agent/collector/checks_d`. A sample `yaml` configuration file for each of these plugins is available in `[installed prefix dir]/share/monasca/agent/conf.d`, where the stem name of the `yaml` file matches the stem name of the corresponding Python check script.

Config files for the plugin scripts can be added directly to the standard plugin configuration directory, `/etc/monasca/agent/conf.d` or added by a `monasca-setup` plugin script that auto-detects that the checks are required and then generates and adds the appropriate config file to enable them.

See [Plugin Checks](#https://github.com/openstack/monasca-agent/blob/master/docs/Plugins.md#standard-plugins) for a description of the configuration and output of the built-in check plugins.

### Adding Custom Check Plugins

Adding custom check plugins to the Agent is easy:

- Ensure that directory `/usr/lib/monasca/agent/custom_checks.d` is present (e.g. with `mkdir -p` on a linux system)
- Add your custom Python check plugin scripts to that directory. Make sure they are readable by the agent user.

That's it! Each plugin is now available to the Collector once they are enabled. To enable a custom plugin, an appropriate `yaml` configuration file with the same stem name as the plugin must be added to `/usr/lib/monasca/agent/conf.d`. This can be done manually or via `monasca-setup` using a 
[custom detection plugin](#creating-a-custom-detection-plugin).

Developers of custom plugins are encouraged to upstream them if they would be useful to the larger Monasca community.

See [Creating a Custom Check Plugin](#creating-a-custom-check-plugin) for instructions on how to create a Monasca custom check plugin script.

### Adding Custom Detection Plugins

Adding custom detection plugins to the Agent is easy:

- Ensure that directory `/usr/lib/monasca/agent/custom_detect.d` is present (e.g. with `mkdir -p` on a linux system)
- Add your custom Python detection plugin scripts to that directory.

That's it! When it runs, the `monasca-setup` script runs the standard list of detection plugins (as modified by any excludes as explained in the next section), each of which generates any appropriate check plugin config. Then the setup script runs the custom detection plugins found in the `custom_detect.d` directory, each of which will generate any appropriate check plugin config.

See [Creating a Custom Detection Plugin](#creating-a-custom-detection-plugin) for instructions on how to create a detection plugin.

### Disabling Built-In Check Plugins

`monasca-setup` is run to detect local or remote manageable entities and generate `yaml` configuration files to enable the required check plugins. The setup script runs Python detection plugins to accomplish this. By default it will run all of the available detection plugins. To avoid running detection plugins first create the primary configuration by running monasca-setup with the '--system_only' argument. You can then run with the `--detection_plugins` argument followed by a space separated list of plugins you would like to run.

## Customization Best Practices

Be aware of these best practices before defining new metrics and adding custom plugins to Monasca.

### Metric Specification Best Practices

#### Appropriate Use of Metrics

Here are some best practices concerning appropriate use of metrics:

- Be aware of [naming conventions](#https://github.com/openstack/monasca-agent/blob/master/docs/MonascaMetrics.md) with metrics.
- Considerations affecting system performance
  - Before installing and configuring a custom check plugin, be certain that you have identified consumers who will actually make use of the metric.
  - Before defining a new metric, make sure that a metric that is essentially the same hasn't already been defined. If it has, use that definition. Re-use is good!
  - Only include metric dimensions that are required by the consumers of the metric. Don't include extra dimensions simply because someone may someday be interested in them.
  - Follow the common and openstack naming conventions, as appropriate, when defining metrics.
  - Include value_meta data only when necessary, e.g. when the metric value returned with a measurement can only be understood in the context of the text included in the value_meta. In your plugins, be as economical as possible with the text returned as value_meta. Like other measurement data, value_meta is stored in the database "forever".

### Custom Plugin Best Practices

- Before creating a custom plugin, see if your needs can be met by an existing plugin (See [Plugin Checks](#https://github.com/openstack/monasca-agent/blob/master/docs/Plugins.md#standard-plugins) for a list of them.)
- If you identify a bug or other problem with an existing plugin, report the defect so everyone can benefit from your discovery.
- If you do create custom plugins, consider upstreaming them if you think others would benefit from using them.
- When writing your plugins, strive for efficiency and economy. Have the plugin perform the necessary checks in the most efficient way. Remember that cycles spent monitoring the system are cycles that cannot be used by the "application" components running on the system.
- If you create a custom plugin, make sure you do not give it the same name as an existing standard check plugin

## Creating Custom Plugins

The references in these sections to classes, utilities, etc. are to locations in the monasca-agent git repo, `https://git.openstack.org/openstack/monasca-agent`.

### Creating a Custom Check Plugin

Developers can extend the functionality of the Agent by creating a custom Python check plugin script. This Section provides instructions on how to create a custom check plugin script.

Plugins are written in Python according to the conventions described below. Scripts should be pep8 compliant for ease in upstreaming custom scripts that are of larger community interest.

#### AgentCheck Interface
Most monasca-agent plugin code uses the AgentCheck interface. All custom checks inherit from the AgentCheck class found in `monasca_agent/collector/checks/check.py` and require a check() method that takes one argument, instance, which is a dict specifying the configuration of the instance on behalf of the plugin being executed. The check() method is run once per instance defined in the check's configuration (discussed later).

#### ServicesCheck interface
Some monasca-agent plugins use the ServicesCheck class found in `monasca_agent/collector/services_checks.py`. These require a `_check()` method that is similar to AgentCheck's check(), but instead of being called once per iteration in a linear fashion, it is run against a threadpool to allow concurrent instances to be checked. Also, `_check()` must return a tuple consisting of either Status.UP or Status.DOWN, plus a text description.

The size of the threadpool is either 6 or the total number of instances, whichever is lower. This may be adjusted with the threads_count parameter in the plugin's init_config (see Plugin Configuration below).

#### Submitting Metrics
Submitting metrics in a check is easy, and is very similar to submitting metrics using a statsd client. The following methods are available:

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
* dimensions: (optional) A dictionary of dimensions (name:value pairs) to associate with this metric
* delegated_tenant: (optional) Submit the metrics on behalf of this tenant ID
* hostname: (optional) A hostname to associate with this metric. This defaults to the local host name
* device_name: (optional) A device name to associate with this metric
* value_meta: (optional) A dictionary of additional textual metadata (name:value pairs) associated with this value

In addition, self.gauge also takes as an optional parameter the timestamp for the metric value.

These methods may be called from anywhere within your check logic. At the end of your check function, all metrics that were submitted will be collected and flushed out with the other Agent metrics.

As part of the parent class, you're given a logger at self.log. The log handler will be checks.{name} where {name} is the stem filename of your plugin.

Of course, when writing your plugin you should ensure that your code raises meaningful exceptions when unanticipated errors occur.

#### Example Check Plugin
/usr/lib/monasca/agent/custom_checks.d/example.py

```
import time
import monasca_agent.collector.checks as checks


class Example(checks.AgentCheck):

    def check(self, instance):
        """Example stats """
        dimensions = self._set_dimensions(None, instance)
        self.gauge('example.time', time.time(), dimensions)
```

#### Check Plugin Configuration
Each plugin has a corresponding `yaml` configuration file with the same stem name as the plugin script file.

The configuration file has the following structure:

```
init_config:
    key1: value1
    key2: value2

instances:
    - name: john_smith
      username: john_smith
      password: 123456
    - name: jane_smith
      username: jane_smith
      password: 789012
```

##### init_config
In the init_config section you can specify an arbitrary number of global name:value pairs that will be available on every run of the check in self.init_config.

##### instances
The instances section is a list of instances that this check will be run against. Your actual check() method is run once per instance. The name:value pairs for each instance specify details about the instance that are necessary for the check.

It is vitally important to have a `name` attribute with a unique value for each
instance as the `monasca-setup` program uses this to avoid duplicating
instances. If any of the instances does not have a `name` attribute,
`monasca-setup` will duplicate it every time it runs, causing not only a
cluttered configuration file but also a multiplication of metrics sent by the
plugin. See https://storyboard.openstack.org/#!/story/2001311 for an example of
the plugin where this problem occurred.

#### DynamicCheckHelper class

The `DynamicCheckHelper` can be used by check plugins to map data from existing monitoring endpoints to Monasca metrics.

Features
* Adjust metric names to Monasca naming conventions
* Map metric names and dimension keys
* Provide metric type information
* Map metadata to dimensions
* Transform names and values using regular expressions
* Filter values using regular expressions on attributes

To support all these capabilities, an element 'mapping' needs to be added to the instance configuration. A default mapping can be supplied for convenience.

Filtering and renaming of input measurements is performed through regular expressions that can be provided for metric-names and dimension values.

##### Selecting and Renaming Metrics

Metrics are specified by providing a list of names or regular expressions. For every metric type (gauge, rate, counter) a separate list is provided. If an incoming measurement does not match any of the listed names/regular expressions, it will be silently filtered out. 

If match-groups are specified, the group-values are concatenated with '_' (underscore). If no match-group is specified, the name is taken as is. The resulting name is normalized according to Monasca naming standards for metrics. This implies that dots are replaced by underscores and *CamelCase* is transformed into *lower_case*. Special characters are eliminated, too.

Example:

```
a) Simple mapping:

   rates: [ 'FilesystemUsage' ]             # map rate metric 'FileystemUsage' to 'filesystem_usage'

b) Mapping with simple regular expression

   rates: [ '.*Usage' ]                     # map metrics ending with 'Usage' to '..._usage'

b) Mapping with regular expression and match-groups

   counters: [ '(.*Usage)\.stats\.(total)' ]   # map metrics ending with 'Usage.stats.total' to '..._usage_total'
```

##### Mapping Metadata to Dimensions
 
The filtering and mapping Mapping of metadata attributes to dimensions is a little more complex. For each dimension, an entry of the following format is required:

```
component: app
```

This will map attribute `app` to dimension `component`.

Complex mapping statements use regular expressions to filter and/or transform metadata attributes into dimensions.
 
The following configuration attributes control the process:
* *source\_key*: name of the incoming metadata attribute. Default: target dimension.
* *regex*: Regular expression to match the incoming metadata attribute _value_ with. This is used for both filtering and transformation using match-groups. Default: `(.*)` (match any and copy value as is).
* *separator*: This string will be used to concatenate the match-groups. Default is `-`(dash).

Example:

```
service:
   source_key: kubernetes.namespace
   regex: prod-(.*)
```

The regular expression is applied to the dimension value. If the regular expression does not match, then the measurement is ignored. If match-groups are part of the regular expression then the regular expression is used for value transformation: The resulting dimension value is created by concatenating all match-groups (in braces) using the specified separator. If no match-group is specified, then the value is acting as a filter and just normalized. If the regex is a string constant (no wildcards), then it will not be mapped to a dimension at all.

##### Metric Groups

Both metrics and dimension can be defined globally or as part of a group.

When a metric is specified in a group, then the group name is used as a prefix to the metric and the group-specific dimension mappings take precedence over the global ones. When several groups or the global mapping refer to the same input metric, then the Check plugin using the `DynCheckHelper` class needs to specify explicitly which group to select for mapping.

Example:
```
instances:
- name: kubernetes
  mapping
    dimensions:
        pod_name: io.kubernetes.pod.name    # simple mapping
        pod_basename:
            source_key: label_name
            regex: 'k8s_.*_.*\._(.*)_[0-9a-z\-]*'
    rates:
    - io.*
    groups:
      postgres:
        gauges: [ 'pg_(database_size_gauge_average)', 'pg_(database_size)' ]
        dimensions:
          service: kubernetes_namespace
          database: datname
```

##### Plugin Documentation
Your plugin should include an example `yaml` configuration file to be placed in `/etc/monasca/agent/conf.d` which has the name of the plugin YAML file plus the extension '.example', so the example configuration file for the process plugin would be at `/etc/monasca/agent/conf.d/process.yaml.example. This file should include a set of example init_config and instances clauses that demonstrate how the plugin can be configured.

### Creating a Custom Detection Plugin

Developers can add custom Python detection plugins to extend the auto-discovery and configuration capabilities of monasca-setup.
This section provides instructions on how to create a Python detection plugin script that can be run by `monasca-setup` to do custom discovery and configuration of the Monasca Agent.

Plugins are written in Python according to the conventions described below. Scripts should be pep8 compliant for ease in upstreaming custom scripts that are of larger community interest.

#### Plugins Object

A detection plugin provides configuration information to monasca-setup as a Plugins object. The Plugins class is defined in `monasca_setup/agent_config.py`. As it runs each plugin, monasca-setup merges its config object with other plugin config returned. After all plugins have been run, it writes the appropriate `yaml` files containing the config information.

#### Plugin Interface

All detection plugins inherit either from the Plugin class found in `monasca_setup/detection/plugin.py` or the ServicePlugin class found in `monasca_setup/detection/service_plugin.py`. The ServicePlugin itself inherits from the Plugin class but provides some additional functionality to automatically add process watching and an http check against an API. This class has been useful for monitoring of OpenStack services.

#### Plugin Utilities

Useful detection plugin utilities can be found in `monasca_setup/detection/utils.py`. Utilities include functions to find local processes by commandline or name, or who's listening on a particular port, or functions to watch processes or service APIs.

#### Example Detection Plugin
/usr/lib/monasca/agent/custom_detect.d/example.py
```
import monasca_setup.agent_config
import monasca_setup.detection


class Example(monasca_setup.detection.Plugin):
    """Configures example detection plugin."""
    def _detect(self):
        """Run detection, set self.available True if the service is detected."""
        self.available = True

    def build_config(self):
        """Build the config as a Plugins object and return.  """
        config = monasca_setup.agent_config.Plugins()
        config['example'] = {'init_config': None,
                             'instances': [{'name': 'example', 'dimensions':{'example_key':'example_value'}}]}
        return config

    def dependencies_installed(self):
        return True
```
