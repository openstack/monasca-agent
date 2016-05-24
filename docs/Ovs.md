<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**
- [Open vSwitch Neutron Router Monitoring](#open-vswitch-neutron-router-monitoring)
  - [Overview](#overview)
  - [Configuration](#configuration)
  - [Per-Router Metrics](#per-router-metrics)
  - [Router Metric Dimensions](#router-metric-dimensions)
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

`admin_password` password for the neutron user.

`admin_tenant_name` is the project/tenant to POST metrics with the `vm.` prefix.

`admin_user` is the username capable of making administrative neutron calls.

`neutron_refresh` is the number of seconds to wait before updating the neutron router cache file.  This requires two neutron calls to get port and router info, so we intentionally overload neutron by making these calls each time the agent wakes up.

`identity_url` is the keystone endpoint for auth.

`region_name` is used to add the region dimension to metrics.

`cache_dir` will be used to cache metric counters and neutron router/port info to not overwhelm neutron each time metrics are calculated/POSTed.

`network_use_bits` will submit network metrics in bits rather than bytes.  This will stop submitting the metrics `router.in_bytes_sec` and `router.out_bytes_sec`, and instead submit `router.in_bits_sec` and `router.out_bits_sec`.

`check_router_ha` will check router HA status if set to true.  This should be set to false if not configuring routers for HA, as setting this to true will cause the plugin to make additional neutron calls.

`ovs_cmd` is the location of the open vswitch command.  Installations that allow sudo should set this to `sudo /usr/bin/ovs-vsctl` and add `mon-agent ALL=(ALL) NOPASSWD:/usr/bin/ovs-vsctl` to the `/etc/sudoers` file.  Installations that don't allow usage of sudo should copy the `ovs-vsctl` command to another location and use the `setcap` command to allow the monasca-agent to run that command.  The new location of the `ovs-vsctl` command should be what is set in the config file for `ovs_cmd`.

`instances` are not used and should be empty in `ovs.yaml` because like the ovs plugin it runs against all routers hosted on the node at once.

Example config (`ovs.yaml`):
```
---
init_config:
  admin_password: password
  admin_tenant_name: services
  admin_user: neutron
  neutron_refresh: 14400
  identity_uri: 'http://192.168.10.5:35357/v2.0'
  region_name: 'region1'
  cache_dir: /dev/shm
  network_use_bits: true
  ovs_cmd: 'sudo /usr/bin/ovs-vsctl'

instances:
 - {}
```

## Per-Router Metrics

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

## Router Metric Dimensions

| Dimension Name | Customer Value             | Operations Value            |
| -------------- | -------------------------- | --------------------------- |
| hostname       | (N/A)                      | hostname hosting the router |
| resource_id    | resource ID of router      | resource ID of router       |
| service        | "networking"               | "networking"                |
| component      | "ovs"                      | "ovs"                       |
| router_name    | name of the virtual router | name of the virtual router  |
| tenant_id      | (N/A)                      | project owner of the router |


# License
(C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP
