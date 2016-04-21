import sys
import inspect
import os
import signal

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.common.util import Paths


def kill_subprocess(process_obj):
    try:
        process_obj.terminate()
    except AttributeError:
        os.kill(process_obj.pid, signal.SIGKILL)


def get_check(name, config_str):
    checksd_path = Paths().get_checksd_path()
    if checksd_path not in sys.path:
        sys.path.append(checksd_path)
    check_module = __import__(name)
    check_class = None
    classes = inspect.getmembers(check_module, inspect.isclass)
    for name, clsmember in classes:
        if AgentCheck in clsmember.__bases__:
            check_class = clsmember
            break
    if check_class is None:
        raise Exception(
            "Unable to import check %s. Missing a class that inherits AgentCheck" % name)

    return check_class.from_yaml(yaml_text=config_str, check_name=name)
