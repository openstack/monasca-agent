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

from common import get_check
from random import shuffle, sample

import unittest
import os
import binascii
import re
import shutil
from nose.plugins.skip import SkipTest
from six.moves import range

class TestPostfix(unittest.TestCase):
    #
    # you can execute this dd-agent unit test via python's nose tool
    #
    # example:
    #
    #     nosetests --nocapture --tests=dd-agent/tests/test_postfix.py
    #

    def setUp(self):
        self.queue_root = '/tmp/dd-postfix-test/var/spool/postfix'

        self.queues = [
            'active',
            'maildrop',
            'bounce',
            'incoming',
            'deferred'
        ]

        self.in_count = {}

        # create test queues
        for queue in self.queues:
            try:
                os.makedirs(os.path.join(self.queue_root, queue))
                self.in_count[queue] = [0, 0]
            except Exception:
                pass

    def tearDown(self):
        # clean up test queues
        shutil.rmtree('/tmp/dd-postfix-test')

    def stripHeredoc(self, text):
        indent = len(min(re.findall('\n[ \t]*(?=\S)', text) or ['']))
        pattern = r'\n[ \t]{%d}' % (indent - 1)
        return re.sub(pattern, '\n', text)

    def test_checks(self):
        raise SkipTest('Requires root access to postfix')
        self.config = self.stripHeredoc("""init_config:

        instances:
            - directory: %s
              queues:
                  - bounce
                  - maildrop
                  - incoming
                  - active
                  - deferred
        """ % (self.queue_root))

        # stuff 10K msgs in random queues
        for _ in range(1, 10000):
            shuffle(self.queues)
            rand_queue = sample(self.queues, 1)[0]
            queue_file = binascii.b2a_hex(os.urandom(7))

            open(os.path.join(self.queue_root, rand_queue, queue_file), 'w')

            # keep track of what we put in
            self.in_count[rand_queue][0] += 1

        check, instances = get_check('postfix', self.config)

        check.check(instances[0])
        out_count = check.get_metrics()

        # output what went in... per queue
        print()
        for queue, count in self.in_count.items():
            print('Test messages put into', queue, '= ', self.in_count[queue][0])

        # output postfix.py dd-agent plugin counts... per queue
        print()
        for tuple in out_count:
            queue = tuple[3]['dimensions'][0].split(':')[1]
            self.assertEqual(int(tuple[2]), int(self.in_count[queue][0]))
            print('Test messages counted by dd-agent for', queue, '= ', tuple[2])

        #
        # uncomment this to see the raw dd-agent metric output
        #
        # print out_count

if __name__ == '__main__':
    unittest.main()
