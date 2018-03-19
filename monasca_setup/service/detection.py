# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP
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

import logging
import platform
import sys

from monasca_setup.service import linux


LOG = logging.getLogger(__name__)


def detect_init(*args, **kwargs):
    """Create a service object if possible.

    Detect if systemd is present on the system and if so return the service
    object.

    :return: a systemd service object for this system.
    """
    detected_os = platform.system()
    if has_systemd():
        return linux.Systemd(*args, **kwargs)
    LOG.error("{0} is not currently supported by the Monasca Agent"
              .format(detected_os))
    sys.exit(1)


def has_systemd():
    """Detect if Linux init is systemd."""
    with open('/proc/1/comm', 'r') as init_proc:
        init = init_proc.readline().strip()
        return init == 'systemd'
