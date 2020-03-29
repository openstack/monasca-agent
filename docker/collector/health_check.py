#!/usr/bin/env python
# coding=utf-8

# (C) Copyright 2018 FUJITSU LIMITED
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Health check will returns 0 when service is working properly."""


def main():
    """Health check for Monasca-agent collector."""
    # TODO(Dobroslaw Zybort) wait for health check endpoint ...
    return 0


if __name__ == '__main__':
    main()
