Team and repository tags
========================

|Team and repository tags|

Introduction
============

The Monasca Agent is a modern Python monitoring agent for gathering
metrics and sending them to the Monasca API. The Agent supports
collecting metrics from a variety of sources as follows:

-  System metrics such as cpu and memory utilization.
-  Nagios plugins. The Monasca Agent can run Nagios plugins and send the
   status code returned by the plugin as a metric to the Monasca API.
-  Statsd. The Monasca Agent supports an integrated Statsd daemon which
   can be used by applications via a statsd client library.
-  Host alive. The Monasca Agent can perform active checks on a host to
   determine if it is alive using ping (ICMP) or SSH.
-  Process checks. The Monasca Agent can check a process and return
   several metrics on the process such as a number of instances, memory,
   io and threads.
-  Http Endpoint checks. The Monasca Agent can perform active checks on
   http endpoints by sending an HTTP request to an API.
-  Service checks. The Agent can check services such as MySQL, RabbitMQ,
   and many more.
-  OpenStack metrics. The agent can perform checks on OpenStack
   processes.
-  The Agent can automatically detect and setup checks on certain
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
`github.com/openstack/monasca-agent/blob/master/docs/Agent.md <https://github.com/openstack/monasca-agent/blob/master/docs/Agent.md>`__

Agent Customizations
`github.com/openstack/monasca-agent/docs/Customizations.md <https://github.com/openstack/monasca-agent/blob/master/docs/Customizations.md>`__

Monasca Metrics
`github.com/openstack/monasca-agent/docs/MonascaMetrics.md <https://github.com/openstack/monasca-agent/blob/master/docs/MonascaMetrics.md>`__

Agent Plugin details
`github.com/openstack/monasca-agent/docs/Plugins.md <https://github.com/openstack/monasca-agent/blob/master/docs/Plugins.md>`__

* License: Simplified BSD License
* Source: http://git.openstack.org/cgit/openstack/monasca-agent
* Bugs: https://storyboard.openstack.org/#!/project/861 (please use `bug` tag)

.. |Team and repository tags| image:: https://governance.openstack.org/tc/badges/monasca-agent.svg
   :target: https://governance.openstack.org/tc/reference/tags/index.html
