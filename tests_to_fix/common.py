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
