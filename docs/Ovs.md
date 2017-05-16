<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Open vSwitch Neutron Router Monitoring](#open-vswitch-neutron-router-monitoring)
  - [Overview](#overview)
  - [Configuration](#configuration)
  - [Per-Router Rate Metrics](#per-router-rate-metrics)
  - [Per-Router Metrics](#per-router-metrics)
  - [Per-DHCP port Metrics](#per-dhcp-port-metrics)
  - [Per-DHCP Rate Metrics](#per-dhcp-rate-metrics)
  - [Per-Host Metrics](#per-host-metrics)
  - [Mapping Metrics to Configuration Parameters](#mapping-metrics-to-configuration-parameters)
  - [Router Metric Dimensions](#router-metric-dimensions)
  - [OVS Port Metric Dimensions](#ovs-port-metric-dimensions)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Open vSwitch Neutron Router Monitoring

## Overview
This plugin provides metrics for neutron virtual routers implemented with Open vSwitch.  Much like the libvirt plugin,
this plugin will publish metrics both to the project associated with the virtual router, as well as the infrastructure
project.  Also similar to the libvirt plugin, metric names that are cross-posted to the infrastructure project will
have the `ovs.` prefix.

NOTE: The `/usr/bin/ovs-vsctl` command requires sudo to run.  See notes in `ovs_cmd` section below for how to customize this plugin to work around this requirement if sudo is not allowed in certain installations.

## Configuration
This plugin is not currently automatically configured using the monasca-setup program -- it must be explicitly
configured using the configuration file example below.

`password` password for the neutron user.

`project_name` is the project/tenant to POST metrics with the `ovs.` prefix.

`username` is the username capable of making administrative neutron calls.

`neutron_refresh` is the number of seconds to wait before updating the neutron router cache file.  This requires two neutron calls to get port and router info, so we intentionally overload neutron by making these calls each time the agent wakes up.

`auth_url` is the keystone endpoint for auth.

`endpoint_type` is the endpoint type for making neutron calls.

`region_name` is used to add the region dimension to metrics.

`cache_dir` will be used to cache metric counters and neutron router/port info to not overwhelm neutron each time metrics are calculated/POSTed.

`network_use_bits` will submit network metrics in bits rather than bytes.  This will stop submitting the metrics `router.in_bytes_sec` and `router.out_bytes_sec`, and instead submit `router.in_bits_sec` and `router.out_bits_sec`.

`check_router_ha` will check router HA status if set to true.  This should be set to false if not configuring routers for HA, as setting this to true will cause the plugin to make additional neutron calls.

`metadata` specifies the list of router metadata keys to be included as dimensions with the cross-tenant metrics for the operations project. This is helpful to give more information about an router. Tenant name (in addition to default ID) can be provided as dimensions if `tenant_name` is provided in the list of metadata keys.

`ovs_cmd` is the location of the open vswitch command.  Installations that allow sudo should set this to `sudo /usr/bin/ovs-vsctl` and add `mon-agent ALL=(ALL) NOPASSWD:/usr/bin/ovs-vsctl` to the `/etc/sudoers` file.  Installations that don't allow usage of sudo should copy the `ovs-vsctl` command to another location and use the `setcap` command to allow the monasca-agent to run that command.  The new location of the `ovs-vsctl` command should be what is set in the config file for `ovs_cmd`.

`instances` are not used and should be empty in `ovs.yaml` because like the ovs plugin it runs against all routers hosted on the node at once.

`included_interface_re` will include network interfaces for collecting the ovs statistics matching the given regex. By default qg, vhu(dpdk) and sg interfaces will be enabled by detection plugin.

`use_absolute_metrics` will submit the raw counters from ovs-vsctl command output for the given network interface. If this flag is disabled then default rate metrics will get collected for the enabled network interfaces (Default True). Please see "Mapping Metrics to Configuration Parameters" section below for what metrics are controlled by this flag.

`use_rate_metrics`  will submit the rate metrics derived from ovs-vsctl command output for the given network interface (Default False). Please see "Mapping Metrics to Configuration Parameters" section below for what metrics are controlled by this flag.

`use_health_metrics`  will submit the health related metrics from ovs-vsctl command output for the given network interface. Example metric names are in_dropped, out_dropped, out_error and in_errors (Default False). Please see "Mapping Metrics to Configuration Parameters" section below for what metrics are controlled by this flag.

Example config (`ovs.yaml`):
```
---
init_config:
  password: password
  project_name: services
  username: neutron
  neutron_refresh: 14400
  auth_url: 'http://192.168.10.5/identity'
  endpoint_type: 'publicURL'
  region_name: 'region1'
  cache_dir: /dev/shm
  network_use_bits: true
  use_absolute_metrics: true
  ovs_cmd: 'sudo /usr/bin/ovs-vsctl' 
  included_interface_re: qg.*|vhu.*|sg.*
  use_rate_metrics: true
  use_health_metrics: true

instances:
 - {}
```

## Per-Router Rate Metrics

| Name                        | Description                                                                |
| --------------------------- | -------------------------------------------------------------------------- |
| vrouter.in_bytes_sec         | Inbound bytes per second for the router (if `network_use_bits` is false)   |
| vrouter.out_bytes_sec        | Outgoing bytes per second for the router  (if `network_use_bits` is false) |
| vrouter.in_bits_sec          | Inbound bits per second for the router  (if `network_use_bits` is true)    |
| vrouter.out_bits_sec         | Outgoing bits per second for the router  (if `network_use_bits` is true)   |
| vrouter.in_packets_sec       | Incoming packets per second for the router                                 |
| vrouter.out_packets_sec      | Outgoing packets per second for the router                                 |
| vrouter.in_dropped_sec       | Incoming dropped packets per second for the router                         |
| vrouter.out_dropped_sec      | Outgoing dropped packets per second for the router                         |
| vrouter.in_errors_sec        | Number of incoming errors per second for the router                        |
| vrouter.out_errors_sec       | Number of outgoing errors per second for the router                        |

## Per-Router Metrics

| Name                     | Description                                                                                                              |
| -------------------------|--------------------------------------------------------------------------------------------------------------------------|
| vrouter.in_bytes         | Inbound bytes for the router (if `network_use_bits` is false)                                                            |
| vrouter.out_bytes        | Outgoing bytes for the router  (if `network_use_bits` is false)                                                          |
| vrouter.in_bits          | Inbound bits for the router  (if `network_use_bits` is true)                                                             |
| vrouter.out_bits         | Outgoing bits for the router  (if `network_use_bits` is true)                                                            |
| vrouter.in_packets       | Incoming packets for the router                                                                                          |
| vrouter.out_packets      | Outgoing packets for the router                                                                                          |
| vrouter.in_dropped       | Incoming dropped packets for the router                                                                                  |
| vrouter.out_dropped      | Outgoing dropped packets for the router                                                                                  |
| vrouter.in_errors        | Number of incoming errors for the router                                                                                 |
| vrouter.out_errors       | Number of outgoing errors for the router                                                                                 |
| vrouter.max_bw_kb        | Maximum bandwidth possible for the router based on the instances using the router (if `publish_router_capacity` is true) |

## Per-DHCP port Metrics

| Name                     | Description
| -------------------------|---------------------------------------------------------------------|
| vswitch.in_bytes         |Inbound bytes for the DHCP port (if `network_use_bits` is false)     |
| vswitch.out_bytes        | Outgoing bytes for the DHCP port  (if `network_use_bits` is false)  |
| vswitch.in_bits          | Inbound bits for the DHCP port  (if `network_use_bits` is true)     |
| vswitch.out_bits         | Outgoing bits for the DHCP port  (if `network_use_bits` is true)    |
| vswitch.out_packets      | Outgoing packets for the  DHCP port                                 |
| vswitch.in_packets       | Incoming packets for the DHCP port                                  |
| vswitch.out_dropped      | Incoming dropped packets for the DHCP port                          |
| vswitch.in_dropped       | Outgoing dropped packets for the DHCP port                          |
| vswitch.out_error        | Errors transmitted for the DHCP port                                |
| vswitch.in_error         | Errors received for the DHCP port                                   |

## Per-DHCP Rate Metrics

| Name                       | Description
| ---------------------------|---------------------------------------------------------------------------|
| vswitch.out_bytes_sec      | Outgoing Bytes per second on DHCP port(if `network_use_bits` is false)    |
| vswitch.in_bytes_sec       | Incoming Bytes per second on DHCP port(if `network_use_bits` is false)    |
| vswitch.out_bits_sec       | Outgoing Bits per second on DHCP port(if `network_use_bits` is true)      |
| vswitch.in_bits_sec        | Incoming Bits per second on DHCP port(if `network_use_bits` is true)      |
| vswitch.out_packets_sec    | Outgoing packets per second for the  DHCP port                            |
| vswitch.in_packets_sec     | Incoming packets per second for the DHCP port                             |
| vswitch.out_dropped_sec    | Outgoing dropped packets per second for the DHCP port                     |
| vswitch.in_dropped_sec     | Incoming dropped per second for the DHCP port                             |
| vswitch.out_error_sec      | Outgoing errors per second for the DHCP port                              |
| vswitch.in_error_sec       | Incoming errors per second for the DHCP port                              |

## Per-Host Metrics

| Name                       | Description                                                                                                                                                                         |
| ---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ovs.vrouter.host_max_bw_kb | Maximum bandwidth possible for routers on the the host based on the instances using those routers (if `publish_router_capacity` is true).  Only published to the operations tenant. |
| ovs.vrouter.active_routers | Count of active routers on this host (only published to the operations tenant)                                                                                                      |

## Mapping Metrics to Configuration Parameters
Configuration parameters can be used to control which metrics are reported by ovs plugin. There are 4 parameters currently in ovs config file: use_rate_metrics, use_absolute_metrics, use_health_metrics and publish_router_capacity.


| Tuning Knob | Admin Metric Name | Tenant Metric Name |
| ----------- | ----------------- | ------------------ |
| use_rate_metrics (default: False) | ovs.vrouter.in_bytes_sec | vrouter.in_bytes_sec |
| | ovs.vrouter.in_packets_sec | vrouter.in_packets_sec |
| | ovs.vrouter.out_bytes_sec | vrouter.out_bytes_sec |
| | ovs.vrouter.out_packets_sec | vrouter.out_packets_sec |
| use_absolute_metrics (default: True) | ovs.vrouter.in_bytes | vrouter.in_bytes |
| | ovs.vrouter.in_packets | vrouter.in_packets |
| | ovs.vrouter.out_bytes | vrouter.out_bytes |
| | ovs.vrouter.out_packets | vrouter.out_packets |
| use_health_metrics (default: False) and use_rate_metrics (default: False) | ovs.vrouter.in_dropped_sec | vrouter.in_dropped_sec |
| | ovs.vrouter.in_errors_sec | vrouter.in_errors_sec |
| | ovs.vrouter.out_dropped_sec | vrouter.out_dropped_sec |
| | ovs.vrouter.out_errors_sec | vrouter.out_errors_sec |
| use_health_metrics(default: False) and use_absolute_metrics (default: True)| ovs.vrouter.in_dropped | vrouter.in_dropped |
| | ovs.vrouter.in_errors | vrouter.in_errors |
| | ovs.vrouter.out_dropped | vrouter.out_dropped |
| | ovs.vrouter.out_errors | vrouter.out_errors |
| publish_router_capacity (default: False) | ovs.vrouter.max_bw_kb | vrouter.max_bw_kb |
| | ovs.vrouter.host_max_bw_kb | N/A |


NOTE:
&nbsp;&nbsp;1) per router metrics start with vrouter.* or ovs.vrouter.*
&nbsp;&nbsp;2) per DHCP metrics start with vswitch.* or ovs.vswitch.*
&nbsp;&nbsp;3) Default use_absolute_metrics=true, use_rate_metrics=false, use_health_metrics=false

## Router Metric Dimensions

| Dimension Name | Customer Value             | Operations Value                                                   |
| -------------- | -------------------------- | ------------------------------------------------------------------ |
| hostname       | (N/A)                      | hostname hosting the router                                        |
| resource_id    | resource ID of router      | resource ID of router                                              |
| service        | "networking"               | "networking"                                                       |
| component      | "ovs"                      | "ovs"                                                              |
| router_name    | name of the virtual router | name of the virtual router                                         |
| tenant_id      | (N/A)                      | id of the project owner of the router                              |
| tenant_name    | (N/A)                      | name of the project owner of the router (if configured to publish) |
| port_id        | port ID of the router      | port ID of the router                                              |

## OVS Port Metric Dimensions
| Dimension Name | Customer Value             | Operations Value                                                   |
| -------------- | -------------------------- | ------------------------------------------------------------------ |
| hostname       | (N/A)                      | hostname hosting the ports                                         |
| resource_id    | resource ID of port        | resource id of the port                                            |
| service        | "networking"               | "networking"                                                       |
| component      | "ovs"                      | "ovs"                                                              |
| tenant_id      | (N/A)                      | project owner of the port                                          |
| tenant_name    | (N/A)                      | name of the project owner of the router (if configured to publish) |
| port_id        | port ID of VM              | port ID of VM                                                      |

# License
(C) Copyright 2015-2016 Hewlett Packard Enterprise Development LP
