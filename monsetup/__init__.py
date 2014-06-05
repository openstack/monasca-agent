#!/usr/bin/env python
""" Detect running daemons then configure and start the agent.
"""

import argparse
import sys

import detection
import service


DETECTION_CLASSES = [detection.Core]
OS_SERVICE_MAP = {'linux': service.sysv.SysV}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Detect running daemons then configure and start the agent.')
#    parser.add_argument('--foo')
#   - It will need to be invoked with keystone credentials. Other options you can invoke with include:
#    - non-interactive
#    - force overwrite of existing config
#    - alternative config output directory
#    - Optional active check config to include -
    args = parser.parse_args()

    # todo these are currently hardcoded
    config_dir = '/etc/mon-agent'
    overwrite = True
    # todo add the ability to build the config in a temp dir then diff


    # Detect os
    detected_os = 'linux'  # todo add detection

    # Run through detection and config building
    for detect_class in DETECTION_CLASSES:
        detect = detect_class(config_dir, overwrite)
        detect.build_config()

    # Service enable/start
    agent_service = OS_SERVICE_MAP[detected_os]
    # Todo add logic for situations where either enable or start is not needed or if not running as root isn't possible
    agent_service.enable()
    agent_service.start(restart=True)


if __name__ == "__main__":
    sys.exit(main())