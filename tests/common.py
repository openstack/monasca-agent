import os
import sys
import inspect

import monasca_agent.common.config as configuration
from monasca_agent.common.util import Paths

# Base config must be loaded before AgentCheck or it will try to load with no config file
base_config = configuration.Config(os.path.join(os.path.dirname(__file__), 'test-agent.yaml'))

from monasca_agent.collector.checks import AgentCheck

def load_check(name, config):
    checksd_path = Paths().get_checksd_path()
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)

    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for name, clsmember in classes:
        if clsmember == AgentCheck:
            continue
        if issubclass(clsmember, AgentCheck):
            check_class = clsmember
            if AgentCheck in clsmember.__bases__:
                continue
            else:
                break
    if check_class is None:
        raise Exception(
            "Unable to import check %s. Missing a class that inherits AgentCheck" % name)

    init_config = config.get('init_config', None)
    instances = config.get('instances')

    agent_config = base_config.get_config(sections='Main')
    # init the check class
    try:
        return check_class(
            name, init_config=init_config, agent_config=agent_config, instances=instances)
    except:
        # Backwards compatitiblity for old checks that don't support the
        # instances argument.
        c = check_class(name, init_config=init_config, agent_config=agent_config)
        c.instances = instances
        return c

