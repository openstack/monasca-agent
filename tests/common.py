import sys
import inspect
import os
import signal

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.common.util import load_check_directory
from monasca_agent.common.util import get_os


def load_check(name, config, agent_config):
    checksd_path = load_check_directory()
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


def kill_subprocess(process_obj):
    try:
        process_obj.terminate()
    except AttributeError:
        # py < 2.6 doesn't support process.terminate()
        if get_os() == 'windows':
            import ctypes
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False,
                                                        process_obj.pid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)
        else:
            os.kill(process_obj.pid, signal.SIGKILL)


def get_check(name, config_str):
    checksd_path = load_check_directory()
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
