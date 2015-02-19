# Enabled plugins

from apache import Apache
from ceilometer import Ceilometer
from cinder import Cinder
from glance import Glance
from kafka_consumer import Kafka
from keystone import Keystone
from libvirt import Libvirt
from mon import MonAPI, MonPersister, MonThresh
from mysql import MySQL
from neutron import Neutron
from nova import Nova
from ntp import Ntp
from postfix import Postfix
from rabbitmq import RabbitMQ
from swift import Swift
from system import System
from zookeeper import Zookeeper

DETECTION_PLUGINS = [Apache,
                     Ceilometer,
                     Cinder,
                     Glance,
                     Kafka,
                     Keystone,
                     Libvirt,
                     MonAPI,
                     MonPersister,
                     MonThresh,
                     MySQL,
                     Neutron,
                     Nova,
                     Ntp,
                     Postfix,
                     RabbitMQ,
                     Swift,
                     System,
                     Zookeeper]
