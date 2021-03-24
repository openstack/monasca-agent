#!/bin/sh

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

# Starting script.
# All checks and configuration templating you need to do before service
# could be safely started should be added in this file.

set -eo pipefail # Exit the script if any statement returns error.

PLUGIN_TEMPLATES="/templates"
USER_PLUGINS="/plugins.d"

AGENT_CONF="/etc/monasca/agent"
AGENT_PLUGINS="$AGENT_CONF/conf.d"

if [ "$KEYSTONE_DEFAULTS_ENABLED" = "true" ]; then
  export OS_AUTH_URL=${OS_AUTH_URL:-"http://keystone:35357/v3/"}
  export OS_USERNAME=${OS_USERNAME:-"monasca-agent"}
  export OS_PASSWORD=${OS_PASSWORD:-"password"}
  export OS_USER_DOMAIN_NAME=${OS_USER_DOMAIN_NAME:-"Default"}
  export OS_PROJECT_NAME=${OS_PROJECT_NAME:-"mini-mon"}
  export OS_PROJECT_DOMAIN_NAME=${OS_PROJECT_DOMAIN_NAME:-"Default"}
fi

mkdir -p "$AGENT_PLUGINS"

# Test services we need before starting our service.
#echo "Start script: waiting for needed services"

# Template all config files before start, it will use env variables.
# Read usage examples: https://pypi.org/project/Templer/
echo "Start script: creating config files from templates"

alias template="templer --ignore-undefined-variables --force --verbose"

if [ "$HOSTNAME_FROM_KUBERNETES" = "true" ]; then
  if ! AGENT_HOSTNAME=$(python /kubernetes_get_host.py); then
    echo "Error getting hostname from Kubernetes"
    return 1
  fi
  export AGENT_HOSTNAME
fi

if [ "$DOCKER" = "true" ]; then
  template $PLUGIN_TEMPLATES/docker.yaml.j2 $AGENT_PLUGINS/docker.yaml
fi

# Cadvisor.
if [ "$CADVISOR" = "true" ]; then
  template $PLUGIN_TEMPLATES/cadvisor_host.yaml.j2 $AGENT_PLUGINS/cadvisor_host.yaml
fi

# Kubernetes.
if [ "$KUBERNETES" = "true" ]; then
  template $PLUGIN_TEMPLATES/kubernetes.yaml.j2 $AGENT_PLUGINS/kubernetes.yaml
fi

# Kubernetes_api.
if [ "$KUBERNETES_API" = "true" ]; then
  template $PLUGIN_TEMPLATES/kubernetes_api.yaml.j2 $AGENT_PLUGINS/kubernetes_api.yaml
fi

# Prometheus scraping.
if [ "$PROMETHEUS" = "true" ]; then
  template $PLUGIN_TEMPLATES/prometheus.yaml.j2 $AGENT_PLUGINS/prometheus.yaml
fi

# Monasca monitoring.
if [ "$MONASCA_MONITORING" = "true" ]; then
  template $PLUGIN_TEMPLATES/zk.yaml.j2 $AGENT_PLUGINS/zk.yaml
  template $PLUGIN_TEMPLATES/kafka_consumer.yaml.j2 $AGENT_PLUGINS/kafka_consumer.yaml
  template $PLUGIN_TEMPLATES/mysql.yaml.j2 $AGENT_PLUGINS/mysql.yaml
fi

# Monasca-log-monitoring.
if [ "$MONASCA_LOG_MONITORING" = "true" ]; then
  template $PLUGIN_TEMPLATES/elastic.yaml.j2 $AGENT_PLUGINS/elastic.yaml
fi

# Common for monasca-monitoring and monasca-log-monitoring.
if [ "$MONASCA_MONITORING" = "true" ] || [ "$MONASCA_LOG_MONITORING" = "true" ]; then
  template $PLUGIN_TEMPLATES/http_check.yaml.j2 $AGENT_PLUGINS/http_check.yaml
  template $PLUGIN_TEMPLATES/process.yaml.j2 $AGENT_PLUGINS/process.yaml
fi

# Apply user templates.
for f in $USER_PLUGINS/*.yaml.j2; do
  if [ -e "$f" ]; then
    template "$f" "$AGENT_PLUGINS/$(basename "$f" .j2)"
  fi
done

# Copy plain user plugins.
for f in $USER_PLUGINS/*.yaml; do
  if [ -e "$f" ]; then
    cp "$f" "$AGENT_PLUGINS/$(basename "$f")"
  fi
done

template $AGENT_CONF/agent.yaml.j2 $AGENT_CONF/agent.yaml

# Start our service.
echo "Start script: starting container"
monasca-collector foreground

# Allow server to stay alive in case of failure for 2 hours for debugging.
RESULT=$?
if [ $RESULT != 0 ] && [ "$STAY_ALIVE_ON_FAILURE" = "true" ]; then
  echo "Service died, waiting 120 min before exiting"
  sleep 7200
fi
exit $RESULT
