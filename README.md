#monasca-agent

The Monasca Monitoring Agent is a system for gathering metrics and sending them to
the Monitoring API.  In its basic configuration, the Agent collects metrics
on various aspects of the host system, but may be extended with Python-based
plugins or statsd-compatible clients.  Many plugins are included, and some of
these may be used to gather metrics against remote systems and services as well.

For information on deploying and using the Monasca Monitoring Agent, please see the
[Wiki](https://github.com/hpcloud-mon/mon-agent/wiki)

# Simple Installation
- `pip install monasca-agent`
- Run configuration `monasca-setup -u me -p pass --project_name myproject -s mini-mon --keystone_url https://keystone --monasca_url https://mon-api`

Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
