#!/bin/ash
# shellcheck shell=dash
# (C) Copyright 2018 FUJITSU LIMITED

set -x

alias template="templer --ignore-undefined-variables --force --verbose"

AGENT_CONF="/etc/monasca/agent"

template $AGENT_CONF/agent.yaml.j2 $AGENT_CONF/agent.yaml
rm $AGENT_CONF/agent.yaml.j2
cat $AGENT_CONF/agent.yaml

# Start our service.
echo "Start script: starting container"
monasca-statsd