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
import socket
import unittest


from monasca_agent.common.keystone import Keystone

port_used = 0


class TestKeystone(unittest.TestCase):

    def setUp(self):
        global port_used
        # Create a server socket so the htto check config gets created
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.bind(('', 0))
            self.s.listen(1)
        except socket.error as msg:
            raise Exception('Bind failed. Message ' + msg[1])
        (host, port_used) = self.s.getsockname()
        
    def tearDown(self):
        self.s.close()

    def test_no_override_(self):
        """ Test setting values with no overrides works as expected
        """
        args = None
        test_plugin = TestPlugin('.', args=args)
        test_plugin._detect()
        config = test_plugin.build_config()
        http_instance = config['http_check']['instances'][0]
        url = 'http://localhost:{0}/healthcheck'.format(port_used)
        self.assertEqual(http_instance['url'], url)
        self.assertEqual(http_instance['match_pattern'], '.*OK.*')

        processes = config['process']['instances']
        self.assertEqual(processes[0]['search_string'], ['testr'])

    def test_override_values(self):
        """ Test overriding values using args works
        """
        url = 'http://localhost:{0}/othercheck'.format(port_used)
        pattern = 'CHECK.*'
        args = 'process_names=tox,testr service_api_url='
        args += ' service_api_url=' + url
        args += ' search_pattern=' + pattern
        test_plugin = TestPlugin('.', args=args)
        test_plugin._detect()
        config = test_plugin.build_config()

        http_instance = config['http_check']['instances'][0]
        self.assertEqual(http_instance['url'], url)
        self.assertEqual(http_instance['match_pattern'], pattern)

        processes = config['process']['instances']
        self.assertEqual(processes[0]['search_string'], ['tox'])
        self.assertEqual(processes[1]['search_string'], ['testr'])


class TestPlugin(monasca_setup.detection.ServicePlugin):

    """Test Plugin

    """

    def __init__(self, template_dir, overwrite=True, args=None):
        url = 'http://localhost:{0}/healthcheck'.format(port_used)
        service_params = {
            'args': args,
            'template_dir': template_dir,
            'overwrite': overwrite,
            'service_name': 'os-testr',
            'process_names': ['testr'],
            'service_api_url': url,
            'search_pattern': '.*OK.*'
        }

        super(TestPlugin, self).__init__(service_params)
