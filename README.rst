Openstack Monasca Agent
========================

|Team and repository tags|

Introduction
============

The *Monasca Agent* is a modern Python monitoring agent for gathering
metrics and sending them to the Monasca API. The Agent supports
collecting metrics from a variety of sources as follows:

System metrics
    such as cpu and memory utilization.
Prometheus
    The *Monasca Agent* supports scraping metrics from endpoints provided by
    *Prometheus exporters* or *Prometheus* instrumented applications.
Statsd
    The *Monasca Agent* supports an integrated *StatsD* daemon which
    can be used by applications via a statsd client library.
OpenStack metrics
    The agent can perform checks on OpenStack processes.
Host alive
    The *Monasca Agent* can perform active checks on a host to
    determine if it is alive using ping (ICMP) or SSH.
Process checks
    The *Monasca Agent* can check a process and return
    several metrics on the process such as a number of instances, memory,
    io and threads.
Http Endpoint checks
    The *Monasca Agent* can perform active checks on
    http endpoints by sending an HTTP request to an API.
Service checks
    The *Monasca Agent* can check services such as MySQL, RabbitMQ,
    and many more.
Nagios plugins
    The *Monasca Agent* can run *Nagios* plugins and send the
    status code returned by the plugin as a metric to the Monasca API.

The Agent can automatically detect and setup checks on certain
processes and resources.

The Agent is extensible through the configuration of additional plugins,
written in Python.

Detailed Documentation
======================

For an introduction to the Monasca Agent, including a complete list of
the metrics that the Agent supports, see the "Agent" detailed
documentation.

The Agent is extensible through the configuration of additional check and
setup plugins, written in Python. See the "Agent Customizations"
detailed documentation.

Agent
    https://opendev.org/openstack/monasca-agent/src/branch/master/docs/Agent.md

Agent Customizations
    https://opendev.org/openstack/monasca-agent/src/branch/master/docs/Customizations.md

Monasca Metrics
    https://opendev.org/openstack/monasca-agent/src/branch/master/docs/MonascaMetrics.md

Agent Plugin details
    https://opendev.org/openstack/monasca-agent/src/branch/master/docs/Plugins.md

* License: Simplified BSD License
* Source: https://opendev.org/openstack/monasca-agent
* Bugs: https://storyboard.openstack.org/#!/project/861 (please use `bug` tag)

.. |Team and repository tags| image:: https://governance.openstack.org/tc/badges/monasca-agent.svg
   :target: https://governance.openstack.org/tc/reference/tags/index.html
