#!/usr/bin/python
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

import json
from monasca_agent.collector.checks import AgentCheck
import requests
import requests.adapters
from requests.adapters import HTTPAdapter
from requests.packages import urllib3
from requests.packages.urllib3.poolmanager import PoolManager
import ssl


class SSLHTTPAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=context)


class A10Session(object):

    def __init__(self, device, username, passwd, ssl):
        self.device = device
        self.username = username
        self.passwd = passwd

    def get_authorization_signature(self):
        url = "https://" + self.device + "/axapi/v3/auth"
        payload = {"credentials": {"username": self.username, "password": self.passwd}}
        try:
            get_request = requests.post(url=url, headers={"content-type": "application/json"},
                                        data=json.dumps(payload), verify=False)
        except urllib3.exceptions.SSLError as e:
            self.log.warning("Caught SSL exception {}".format(e))

        signature = json.loads(get_request.text)
        authorization_signature = str(signature["authresponse"]["signature"])
        return authorization_signature

    def log_out(self, auth_sig):
        url = "https://" + self.device + "/axapi/v3/logoff"
        requests.post(url=url, headers={"Content-type": "application/json",
                                        "Authorization": "A10 %s" % auth_sig}, verify=False)


class A10MemoryCheck(AgentCheck):

    def __init__(self, name, init_config, agent_config):
        super(A10MemoryCheck, self).__init__(name, init_config, agent_config)

    def check(self, instance):
        a10_device = instance.get("a10_device")
        username = instance.get('a10_username')
        password = instance.get('a10_password')
        dimensions = self._set_dimensions(
            {'service': 'networking', 'a10_device': a10_device}, instance)

        try:
            authed_session = A10Session(a10_device, username, password, SSLHTTPAdapter)
            self.auth_sig = authed_session.get_authorization_signature()

        # Raise exception and halt program execution
        except Exception as e:
            self.log.exception(e)
            raise

        memory_data = self.get_memory_stats(a10_device)
        for key, value in memory_data.items():
            self.gauge(key, value, dimensions)

        try:
            authed_session.log_out(self.auth_sig)
        # Log a debug exception and continue on
        except Exception as e:
            self.log.exception(e)

    def get_memory_stats(self, a10_device):
        memory_data = {}
        try:
            url = "https://" + a10_device + "/axapi/v3/system/memory/oper"
            try:
                request = requests.get(
                    url=url,
                    headers={
                        "Content-type": "application/json",
                        "Authorization": "A10 %s" %
                        self.auth_sig},
                    verify=False)
            except urllib3.exceptions.SSLError as e:
                self.log.warning("Caught SSL exception {}".format(e))

            data = request.json()

            mem_used = data['memory']['oper']['Usage']

            convert_kb_to_mb = 1024

            memory_data['a10.memory_total_mb'] = (
                data['memory']['oper']['Total']) / convert_kb_to_mb
            memory_data['a10.memory_used_mb'] = (data['memory']['oper']['Used']) / convert_kb_to_mb
            memory_data['a10.memory_free_mb'] = (data['memory']['oper']['Free']) / convert_kb_to_mb
            memory_data['a10.memory_used'] = int(mem_used[:2])

        except Exception as e:
            self.log.exception(e)

        return memory_data
