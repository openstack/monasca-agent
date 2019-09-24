===============================
Docker image for Monasca Statsd
===============================
The Monasca Statsd image is based on the monasca-base image.


Building monasca-base image
===========================
See https://github.com/openstack/monasca-common/tree/master/docker/README.rst


Building Monasca Statsd image
=============================

Example:
  $ ./build_image.sh <repository_version> <upper_constains_branch> <common_version>

Everything after ``./build_image.sh`` is optional and by default configured
to get versions from ``Dockerfile``. ``./build_image.sh`` also contain more
detailed build description.

Environment variables
~~~~~~~~~~~~~~~~~~~~~
============================== ========================= ====================================================
Variable                       Default                   Description
============================== ========================= ====================================================
STATSD_PORT                    8125                      The port for statsd
LOG_LEVEL                      WARN                      Log level for service
HOSTNAME_FROM_KUBERNETES       false                     Determine node hostname from Kubernetes
STAY_ALIVE_ON_FAILURE          false                     If true, container runs 2 hours after service fails
MONASCA_URL                    http://monasca:8070/v2.0  Versioned Monasca API URL
KEYSTONE_DEFAULTS_ENABLED      true                      Use all OS defaults
============================== ========================= ====================================================


Requirements from monasca-base image
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
health_check.py
  This file will be used for checking the status of the Monasca API
  application.


Scripts
~~~~~~~
start.sh
    In this starting script provide all steps that lead to the proper service
    start. Including usage of wait scripts and templating of configuration
    files. You also could provide the ability to allow running container after
    service died for easier debugging.

build_image.sh
    Please read detailed build description inside the script.


Docker Compose
~~~~~~~~~~~~~~
When you want to use docker-compose add it as a new service in your docker-compose.yml file
Example:

    * monasca-statsd:
        * image: monasca/statsd:master


Links
~~~~~
https://docs.openstack.org/designate/latest/contributor/metrics.html