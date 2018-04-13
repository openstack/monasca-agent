# Copyright 2018 SUSE LLC
#
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


class Cassandra(monasca_setup.detection.ServicePlugin):

    """Detect Cassandra daemons and setup configuration to monitor them.
        Cassandra directories can be checked by passing in a directory_names
        list. example: 'directory_names': [('/var/cassasndra/data',
        '/var/cassasndra/commitlog', '/var/log/cassandra')]
        Cassandra process user name can be overwritten by passing in
        process_username.
        See ServicePlugin for details.
    """

    def __init__(self, template_dir, overwrite=True, args=None):
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'cassandra',
            'component_name': 'cassandra',
            'process_username': 'cassandra',
            'service_api_url': '',
            'search_pattern': ''
        }

        super(Cassandra, self).__init__(service_params)
