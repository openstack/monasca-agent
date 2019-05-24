===============================
Docker images for Monasca Agent
===============================
There are two separate images for monasca-agent services: collector
and forwarder. Collector is working best with services that allow remote access
to them and to gather host level metrics collector will need to work together
with cAdvisor service.


Building monasca-base image
===========================
See https://opendev.org/openstack/monasca-common/src/branch/master/docker/README.rst


Building Monasca Agent images
=============================

``build_image.sh`` script in top level folder (``docker/build_image.sh``) is
dummy script that will build both collector and forwarder images at once.

Example:
  $ ./build_image.sh <repository_version> <upper_constrains_branch> <common_version>

Everything after ``./build_image.sh`` is optional and by default configured
to get versions from ``Dockerfile``. ``./build_image.sh`` also contain more
detailed build description.


Environment variables
~~~~~~~~~~~~~~~~~~~~~
============================== =========================== ====================================================
Variable                       Default                     Description
============================== =========================== ====================================================
LOG_LEVEL                      WARN                        Python logging level
MONASCA_URL                    http://monasca:8070/v2.0    Versioned Monasca API URL
FORWARDER_URL                  http://localhost:17123      Monasca Agent Collector URL
KEYSTONE_DEFAULTS_ENABLED      true                        Use all OS defaults
OS_AUTH_URL                    http://keystone:35357/v3/   Versioned Keystone URL
OS_USERNAME                    monasca-agent               Agent Keystone username
OS_PASSWORD                    password                    Agent Keystone password
OS_USER_DOMAIN_NAME            Default                     Agent Keystone user domain
OS_PROJECT_NAME                mini-mon                    Agent Keystone project name
OS_PROJECT_DOMAIN_NAME         Default                     Agent Keystone project domain
HOSTNAME_FROM_KUBERNETES       false                       Determine node hostname from Kubernetes
AUTORESTART                    false                       Auto Restart Monasca Agent Collector
COLLECTOR_RESTART_INTERVAL     24                          Interval in hours to restart Monasca Agent Collector
STAY_ALIVE_ON_FAILURE          false                       If true, container runs 2 hours after tests fail
============================== =========================== ====================================================

Note that additional variables can be specified as well, see the
``agent.yaml.j2`` for a definitive list in every image folder.

Note that the auto restart feature can be enabled if the agent collector
has unchecked memory growth. The proper restart behavior must be enabled
in Docker or Kubernetes if this feature is turned on.

Environment variables for self monitoring
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provide them to monasca agent collector container.

============================== =========== =====================================
Variable                       Default     Description
============================== =========== =====================================
DOCKER                         false       Monitor Docker
CADVISOR                       false       Monitor Cadvisor
KUBERNETES                     false       Monitor Kubernetes
KUBERNETES_API                 false       Monitor Kubernetes API
PROMETHEUS                     false       Monitor Prometheus
MONASCA_MONITORING             false       Monitor services for metrics pipeline
MONASCA_LOG_MONITORING         false       Monitor services for logs pipeline
============================== =========== =====================================

Scripts
~~~~~~~
start.sh
  In this starting script provide all steps that lead to the proper service
  start. Including usage of wait scripts and templating of configuration
  files. You also could provide the ability to allow running container after
  service died for easier debugging.

health_check.py
  This file will be used for checking the status of the application.


Docker Plugin
-------------

This plugin is enabled when ``DOCKER=true``. It has the following options:

 * ``DOCKER_ROOT``: The mounted host rootfs volume. Default: ``/host``
 * ``DOCKER_SOCKET``: The mounted Docker socket. Default: ``/var/run/docker.sock``

This plugin monitors Docker containers directly. It should only be used in a
bare Docker environment (i.e. not Kubernetes), and requires two mounted volumes
from the host:

 * Host ``/`` mounted to ``/host`` (path configurable with ``DOCKER_ROOT``)
 * Host ``/var/run/docker.sock`` mounted to ``/var/run/docker.sock`` (path
   configurable with ``DOCKER_SOCKET``)

Kubernetes Plugin
-----------------

This plugin is enabled when ``KUBERNETES=true``. It has the following options:

 * ``KUBERNETES_TIMEOUT``: The K8s API connection timeout. Default: ``3``
 * ``KUBERNETES_NAMESPACE_ANNOTATIONS``: If set, will grab annotations from
   namespaces to include as dimensions for metrics that are under that
   namespace. Should be passed in as 'annotation1,annotation2,annotation3'.
   Default: unset
 * ``KUBERNETES_MINIMUM_WHITELIST``: Sets whitelist on kubernetes plugin for
   the following metrics pod.cpu.total_time_sec, pod.mem.cache_bytes,
   pod.mem.swap_bytes, pod.mem.used_bytes, pod.mem.working_set_bytes. This
   will alleviate the amount of load on Monasca.
   Default: unset

The Kubernetes plugin is intended to be run as a DaemonSet on each Kubernetes
node. In order for API endpoints to be detected correctly, ``AGENT_POD_NAME`` and
``AGENT_POD_NAMESPACE`` must be set using the `Downward API`_ as described
above.

Kubernetes API Plugin
---------------------

This plugin is enabled when ``KUBERNETES_API=true``. It has the following options:

 * ``KUBERNETES_API_HOST``: If set, manually sets the location of the Kubernetes
   API host. Default: unset
 * ``KUBERNETES_API_PORT``: If set, manually sets the port for of the Kubernetes
   API host. Only used if ``KUBERNETES_API_HOST`` is also set. Default: 8080
 * ``KUBERNETES_API_CUSTOM_LABELS``: If set, provides a list of Kubernetes label
   keys to include as dimensions from gathered metrics. Labels should be comma
   separated strings, such as ``label1,label2,label3`. The ``app`` label is always
   included regardless of this value. Default: unset
 * ``KUBERNETES_NAMESPACE_ANNOTATIONS``: If set, will grab annotations from
   namespaces to include as dimensions for metrics that are under that
   namespace. Should be passed in as 'annotation1,annotation2,annotation3'.
   Default: unset
 * ``REPORT_PERSISTENT_STORAGE``: If set, will gather bound pvc per a storage
   class. Will be reported by namespace and cluster wide. Default: true
 * ``STORAGE_PARAMETERS_DIMENSIONS``: If set and report_persistent_storage is
   set, will grab storage class parameters as dimensions when reporting
   persistent storage. Should be passed in as 'parameter1,parameter2". Default:
   unset

The Kubernetes API plugin is intended to be run as a standalone deployment and
will collect cluster-level metrics.

Prometheus Plugin
-----------------

This plugin is enabled when ``PROMETHEUS=true``. It has the following options:

 * ``PROMETHEUS_TIMEOUT``: The connection timeout. Default: ``3``
 * ``PROMETHEUS_ENDPOINTS``: A list of endpoints to scrape. If unset,
   they will be determined automatically via the Kubernetes API. See below for
   syntax. Default: unset
 * ``PROMETHEUS_DETECT_METHOD``: When endpoints are determined automatically,
   this specifies the resource type to scan, one of: ``pod``, ``service``.
   Default: ``pod``
 * ``PROMETHEUS_KUBERNETES_LABELS``: When endpoints are determined automatically,
   this comma-separated list of labels will be included as dimensions (by name).
   Default: ``app``

If desired, a static list of Prometheus endpoints can be provided by setting
`PROMETHEUS_ENDPOINTS`. Entries in this list should be comma-separated.
Additionally, each entry can specify a set of dimensions like so:

    ``http://host-a/metrics,http://host-b/metrics|prop=value&prop2=value2,http://host-c``

Note that setting ``PROMETHEUS_ENDPOINTS`` disables auto-detection.

When autodetection is enabled, this plugin will automatically scrape all
annotated Prometheus endpoints on the node the agent is running on. Ideally, it
should be run alongside the Kubernetes plugin as a DaemonSet on each node.

cAdvisor_host Plugin
--------------------

This plugin is enabled when ``CADVISOR=true``. It has the following options:

 * ``CADVISOR_TIMEOUT``: The connection timeout for the cAdvisor API. Default: ``3``
 * ``CADVISOR_URL``: If set, sets the URL at which to access cAdvisor. If unset,
   (default) the cAdvisor host will be determined automatically via the
   Kubernetes API.
 * ``CADVISOR_MINIMUM_WHITELIST``: Sets whitelist on cadvisor host plugin for
   the following metrics cpu.total_time_sec, mem.cache_bytes,
   mem.swap_bytes, mem.used_bytes, mem.working_set_bytes. This
   will alleviate the amount of load on Monasca.
   Default: unset

This plugin collects host-level metrics from a running cAdvisor instance.
cAdvisor is included in ``kubelet`` when in Kubernetes environments and is
necessary to retrieve host-level metrics. As with the Kubernetes plugin,
``AGENT_POD_NAME`` and ``AGENT_POD_NAMESPACE`` must be set to determine the URL
automatically.

cAdvisor can be easily run in `standard Docker environments`_ or directly on
host systems. In these cases, the URL must be manually provided via
``CADVISOR_URL``.

Monasca-monitoring
------------------

Metrics pipeline
^^^^^^^^^^^^^^^^
The monasca-monitoring enables plugins for HTTP endpoint check and processes.
Additionally enables plugins for detailed metrics for the following components:
Kafka, MySQL, and Zookeeper. This is enabled when ``MONASCA_MONITORING=true``.
The components use the default configuration. A user can specify own settings
for them in docker-compose file. To customize those settings you can adjust the
configuration of the components by passing environment variables:

Kafka
+++++
 * ``KAFKA_CONNECT_STR``: The kafka connection string. Default: ``kafka:9092``

Zookeeper
+++++++++
 * ``ZOOKEEPER_HOST``: The zookeeper host name.  Default: ``zookeeper``
 * ``ZOOKEEPER_PORT``: The port to listen for client connections. Default: ``2181``

MySQL
+++++
 * ``MYSQL_SERVER``: The MySQL server name. Default: ``mysql``
 * ``MYSQL_USER``, ``MYSQL_PASSWORD``: These variables are used in conjunction to specify user and password for this user. Default: ``root`` and ``secretmysql``
 * ``MYSQL_PORT``: The port to listen for client connections. Default: ``3306``

Logs pipeline
^^^^^^^^^^^^^
For logs pipeline you can enable HTTP endpoint check, process and
``Elasticsearch`` plugins. This is enabled when ``MONASCA_LOG_MONITORING=true``.
You can adjust the configuration of the components by passing environment
variables:

Elasticsearch
+++++++++++++
  * ``ELASTIC_URL``: The Elasticsearch connection string. Default: ``http://elasticsearch:9200``

Monasca-statsd
^^^^^^^^^^^^^^
To monitor ``monasca-notifcation`` and ``monasca-log-api`` use ``statsd``. Enable the
statsd monitoring by setting up ``STATSD_HOST`` and ``STATSD_PORT`` environment
variables in those projects.

Custom plugins
~~~~~~~~~~~~~~
Custom plugin configuration files can be provided by mounting them to
``/plugins.d/*.yaml`` inside the container of monasca agent collector.

Plugins should have ``yaml`` extension when you don't need any templating.
When they have ``yaml.j2`` extension, they will be processed as Jinja2
templates with access to all environment variables.

Links
~~~~~
https://opendev.org/openstack/monasca-agent/src/branch/master/README.rst

.. _`Downward API`: https://kubernetes.io/docs/user-guide/downward-api/
.. _`standard Docker environments`: https://github.com/google/cadvisor#quick-start-running-cadvisor-in-a-docker-container
