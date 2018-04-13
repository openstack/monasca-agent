# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os
import sys
import inspect

import monasca_agent.collector.checks as checks
import monasca_agent.common.config as configuration
from monasca_agent.common.util import Paths


base_config = configuration.Config(os.path.join(os.path.dirname(__file__),
                                                'test-agent.yaml'))


def load_check(name, config):
    checksd_path = Paths().get_checksd_path()
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for name, clsmember in classes:
        if clsmember == checks.AgentCheck:
            continue
        if issubclass(clsmember, checks.AgentCheck):
            check_class = clsmember
            if checks.AgentCheck in clsmember.__bases__:
                continue
            else:
                break
    if check_class is None:
        raise Exception(
            "Unable to import check %s. Missing a class that inherits "
            "AgentCheck" % name)

    init_config = config.get('init_config', None)
    instances = config.get('instances')

    agent_config = base_config.get_config(sections='Main')
    # init the check class
    try:
        return check_class(
            name, init_config=init_config, agent_config=agent_config,
            instances=instances)
    except Exception:
        # Backwards compatitiblity for old checks that don't support the
        # instances argument.
        c = check_class(name, init_config=init_config,
                        agent_config=agent_config)
        c.instances = instances
        return c
