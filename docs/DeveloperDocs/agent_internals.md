<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [Modify_Config](#modify_config)
  - [Examples](#examples)
      - [Adding a new instance](#adding-a-new-instance)
      - [Changing the current instance](#changing-the-current-instance)
- [Connector](#connector)
  - [Kubernetes Connector](#kubernetes-connector)
- [License](#license)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Modify_Config
`modify_config` is a function in [monasca_setup/main.py](monasca_setup/main.py).
It compares existing and detected configurations for each check plugin and
writes out the plugin configurations if there are changes.

## Examples
There are two examples shown here using http_check to:
* add a new instance
* detect endpoint change on an existing http_check instance

#### Adding a new instance
old_config:

```
{'init_config': None,
 'instances': [{'built_by': 'HttpCheck',
                'name': 'logging',
                'url': 'http://127.0.0.1:9200',
                'use_keystone': False,
                'match_pattern': '.*VERSION.*',
                'collect_response_time': True,
                'timeout': '10',
                'dimensions': {'service': 'logging'}}]
}
```

monasca-setup arguments:

    $ monasca-setup -d 'HttpCheck' -a 'url=http://192.168.10.6:8070
      match_pattern=.*OK.* name=monasca dimensions=service:monitoring'

input_config generated from monasca-setup:

```
{'http_check':
    {'instances': [{'built_by': 'HttpCheck',
                    'name': 'monasca',
                    'url': 'http://192.168.10.6:8070',
                    'use_keystone': False,
                    'match_pattern': '.*OK.*',
                    'collect_response_time': True,
                    'timeout': '10',
                    'dimensions': {'service': 'monitoring'}
                    }]
    'init_config': None
    }
}
```

output_config from modify_config:

```
{'init_config': None,
 'instances': [{'built_by': 'HttpCheck',
                'name': 'logging',
                'url': 'http://127.0.0.1:9200',
                'use_keystone': False,
                'match_pattern': '.*VERSION.*',
                'collect_response_time': True,
                'timeout': '10',
                'dimensions': {'service': 'logging'}},
               {'built_by': 'HttpCheck',
                'name': 'monasca',
                'url': 'http://192.168.10.6:8070',
                'use_keystone': False,
                'match_pattern': '.*OK.*',
                'collect_response_time': True,
                'timeout': '10',
                'dimensions': {'service': 'monitoring'}}]
}
```

#### Changing the current instance
old_config:

```
{'init_config': None,
 'instances': [{'built_by': 'HttpCheck',
                'name': 'logging',
                'url': 'http://192.168.10.6:8070',
                'use_keystone': False,
                'match_pattern': '.*VERSION.*',
                'collect_response_time': True,
                'timeout': '10',
                'dimensions': {'service': 'logging'}}]
}
```

monasca-setup arguments:

    $ monasca-setup -d 'HttpCheck' -a 'url=https://192.168.10.6:8070
      match_pattern=.*VERSION.* dimensions=service:logging'

input_config generated from monasca-setup:

```
{'http_check':
   {'instances': [{'built_by': 'HttpCheck',
                    'name': 'https://192.168.10.6:8070',
                    'url': 'https://192.168.10.6:8070',
                    'use_keystone': False,
                    'match_pattern': '.*VERSION.*',
                    'collect_response_time': True,
                    'dimensions': {'service': 'logging'}
                    }]
    'init_config': None
   }
}
```

output_config from modify_config:

```
{'init_config': None,
 'instances': [{'built_by': 'HttpCheck',
                'name': 'https://192.168.10.6:8070',
                'url': 'https://192.168.10.6:8070',
                'use_keystone': False,
                'match_pattern': '.*VERSION.*',
                'collect_response_time': True,
                'dimensions': {'service': 'logging'}
                }]
}
```

# Remove Config

There are two methods for removing configurations.

The first is `remove_config` which will remove a configuration exactly matching the parameters.

The second is `remove_config_for_matching_args` which will search for any configuration that matches the given
arguments but allows for some variation. This is useful in the use case where a compute node has been removed
and all configuration related to that host should be removed, but all the parameters in configuration used may
not be known (like target_hostname for host_alive checks).

WARNING: JSON support for detection arguments has not been added to `--remove_matching_args`.

Example call to monasca-setup, to remove ping checks of a compute host in host_alive.yaml:
```bash
monasca-setup --user monasca-agent \
--agent_service_name openstack-monasca-agent --remove-matching-args \
-d HostAlive --detection_args "hostname=deletehost-localcloud-mgmt type=ping dimensions=service:compute"
```
REMINDER: Multiple dimensions can be in the form `dimensions=service:compute,tag:east`

# Connector
## Kubernetes Connector
Kubernetes Connector is a class within [monasca-collector utils](monasca_agent/collector/checks/utils.py)
that is used for connecting to the Kubernetes API from within a container that is running in a k8 cluster.

When a container is brought up in Kubernetes by default there are environmental variables passed in that include needed
configurations to connect to the API. Also, the cacert and token that is tied to the service account the container is
under is mounted to the container file system. This class processes both and allows requests to the Kubernetes API.

# License
(C) Copyright 2016,2017 Hewlett Packard Enterprise Development LP
(C) Copyright 2019,2020 SUSE LLC


