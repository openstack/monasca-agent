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

import monasca_setup.detection


class Swift(monasca_setup.detection.ServicePlugin):

    """Detect Swift daemons and setup configuration to monitor them.

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'object-storage',
            'process_names': ['swift-container-updater', 'swift-account-auditor',
                              'swift-object-replicator', 'swift-container-replicator',
                              'swift-object-auditor', 'swift-container-auditor',
                              'swift-account-reaper', 'swift-container-sync',
                              'swift-account-replicator', 'swift-object-updater',
                              'swift-object-server', 'swift-account-server',
                              'swift-container-server', 'swift-proxy-server'],
            'service_api_url': 'http://localhost:8080/healthcheck',
            'search_pattern': '.*OK.*'
        }

        super(Swift, self).__init__(service_params)
