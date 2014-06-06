#mon-agent

The Monitoring Agent is a system for gathering metrics and sending them to
the Monitoring API.  In its basic configuration, the Agent collects metrics
on various aspects of the host system, but may be extended with Python-based
plugins or statsd-compatible clients.  Many plugins are included, and some of
these may be used to gather metrics against remote systems and services as well.

For information on deploying and using the Monitoring Agent, please see the
[Wiki](https://github.com/hpcloud-mon/mon-agent/wiki)

# Simple Installation
- `pip install mon-agent`
- Run configuration `mon-setup -u me -p pass -s mini-mon --keystone_url https://keystone --mon_url https://mon-api`

Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
