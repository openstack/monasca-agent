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

set -eo pipefail  # Exit the script if any statement returns error.

AGENT_CONF="/etc/monasca/agent"

if [ "$KEYSTONE_DEFAULTS_ENABLED" = "true" ]; then
  export OS_AUTH_URL=${OS_AUTH_URL:-"http://keystone:35357/v3/"}
  export OS_USERNAME=${OS_USERNAME:-"monasca-agent"}
  export OS_PASSWORD=${OS_PASSWORD:-"password"}
  export OS_USER_DOMAIN_NAME=${OS_USER_DOMAIN_NAME:-"Default"}
  export OS_PROJECT_NAME=${OS_PROJECT_NAME:-"mini-mon"}
  export OS_PROJECT_DOMAIN_NAME=${OS_PROJECT_DOMAIN_NAME:-"Default"}
fi

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

template $AGENT_CONF/agent.yaml.j2 $AGENT_CONF/agent.yaml

# Start our service.
echo "Start script: starting container"
monasca-forwarder

# Allow server to stay alive in case of failure for 2 hours for debugging.
RESULT=$?
if [ $RESULT != 0 ] && [ "$STAY_ALIVE_ON_FAILURE" = "true" ]; then
  echo "Service died, waiting 120 min before exiting"
  sleep 7200
fi
exit $RESULT
