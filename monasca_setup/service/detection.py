# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP

import logging
import platform
import sys

import linux


log = logging.getLogger(__name__)


def detect_init(*args, **kwargs):
    """Detect the service manager running on this box
       args/kwargs match those of service.Service
    :return: The appropriate Service object for this system
    """
    detected_os = platform.system()
    if detected_os == 'Linux':
        supported_linux_flavors = [
            'ubuntu', 'debian',
            'centos linux', 'red hat enterprise linux server',
            'suse linux enterprise server'
        ]
        flavor = platform.linux_distribution()[0].strip()
        if flavor.lower() not in supported_linux_flavors:
            log.warn('{0} is not a supported Linux distribution'.format(flavor))
        return detect_linux_init(*args, **kwargs)
    else:
        print("{0} is not currently supported by the Monasca Agent".format(detected_os))
        sys.exit(1)

    # Service enable, includes setup of users/config directories so must be
    # done before configuration


def detect_linux_init(*args, **kwargs):
    """Detect which of the linux inits is running
    :return: Return a valid Linux service manager object
    """
    with open('/proc/1/comm', 'r') as init_proc:
        init = init_proc.readline().strip()
        if init == 'systemd':
            return linux.Systemd(*args, **kwargs)
        else:
            return linux.SysV(*args, **kwargs)
