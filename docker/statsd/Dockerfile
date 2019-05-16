ARG DOCKER_IMAGE=monasca/statsd
ARG APP_REPO=https://opendev.org/openstack/monasca-agent

# Branch, tag or git hash to build from.
ARG REPO_VERSION=master
ARG CONSTRAINTS_BRANCH=master

# Extra Python3 dependencies.
#ARG EXTRA_DEPS=""

# Always start from `monasca-base` image and use specific tag of it.
ARG BASE_TAG=master
FROM monasca/base:$BASE_TAG

# Environment variables used for our service or wait scripts.
ENV \
    KEYSTONE_DEFAULTS_ENABLED=true \
    MONASCA_URL=http://monasca:8070/v2.0 \
    LOG_LEVEL=WARN \
    HOSTNAME_FROM_KUBERNETES=false \
    STAY_ALIVE_ON_FAILURE="false"

# Copy all neccessary files to proper locations.
COPY agent.yaml.j2 /etc/monasca/agent/agent.yaml.j2
COPY start.sh health_check.py /

# Run here all additionals steps your service need post installation.
# Stay with only one `RUN` and use `&& \` for next steps to don't create
# unnecessary image layers. Clean at the end to conserve space.
#RUN

# Implement start script in `start.sh` file.
CMD ["/start.sh"]