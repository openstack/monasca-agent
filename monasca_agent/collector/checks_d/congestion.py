#!/bin/env python

# Copyright 2017 OrangeLabs

from copy import deepcopy
import json
import logging
import math
import os
import stat
import subprocess
import time

from monasca_agent.collector.checks import AgentCheck
from monasca_agent.common import keystone
from novaclient import client as nova_client

log = logging.getLogger(__name__)
prerouting_chain = "PREROUTING"
congestion_chain = "congestion"
forward_chain = "FORWARD"

"""Monasca Agent interface for congestion metrics"""


class Congestion(AgentCheck):

    """This Agent provides congestion metrics necessary to monitor network
    performance. It uses ECN marking mechanism to discover the congestion
    in the network. The iptables chains and rules are used to collect ECN
    packets/bytes. Also, the agent provides congestion threshold computed
    from the collected ECN bytes.
    """

    def __init__(self, name, init_config, agent_config, instances=None):
        AgentCheck.__init__(self, name, init_config,
                            agent_config, instances=[{}])
        cache_dir = self.init_config.get('cache_dir')
        self.enable_vm = self.init_config.get('enable_vm')
        self.enable_ecn = self.init_config.get('enable_ecn')
        self.s_factor = self.init_config.get('s_factor')
        self.collect_period = self.init_config.get('collect_period')
        self.cong_cache_file = os.path.join(cache_dir,
                                            'congestion_status.json')
        self.session = keystone.get_session(**self.init_config)
        self.chain_exist = False
        self.rule_exist = False
        self._check_chain()
        self.checked = []
        if self.enable_ecn:
            self._activate_ecn()

    def check(self, instance):
        """Extend check method to collect and update congestion metrics.
        """
        dimensions = self._set_dimensions({'service': 'networking',
                                           'component': 'neutron'}, instance)
        self.sample_time = float("{:9f}".format(time.time()))
        """Check iptables information and verify/install the ECN rule for
        specific hypervisor"""
        ip_list = self._get_hypervisors()
        """update congestion metrics for each remote hypervisor"""
        for name, ip in ip_list.items():
            if name != self.hostname and name not in self.checked:
                self.checked.append(name)
                dimensions.update({'hostname': name})
                self._update_metrics(name, ip, dimensions)
                """update congestion metrics for vms if this option
                was enabled"""
                if self.enable_vm:
                    ip_vm_list = self._get_vms(name)
                    if ip_vm_list:
                        for name_vm, ip_vm in ip_vm_list.items():
                            if name_vm not in self.checked:
                                self.checked.append(name_vm)
                                dimensions.update({'device': name_vm})
                                self._update_metrics(name_vm, ip_vm,
                                                     dimensions)

    def _update_metrics(self, name, ip, dimensions):
        """This method updates congestion metrics and cache and sends
        them to monasca API for further treatment or evaluation.
        """
        cong_cache = self._load_cong_cache()
        rule_data = self._get_counters(ip, congestion_chain)
        if not rule_data:
            match = "tos --tos 0x03"
            action = "MARK --set-mark 3"
            self._add_rule(congestion_chain, ip, match, action)
            rule_data = self._get_counters(ip, congestion_chain)
        if name not in cong_cache:
            cong_cache[name] = {}
            """initalize cache values"""
            cong_cache[name]['ecn.cong.rate'] = {'value': 0}
            cong_cache[name]['ecn.bytes'] = {'value': 0}
            cong_cache[name]['ecn_bytes_sum'] = {'value': 0}
            cong_cache[name]['ecn.packets'] = {'value': 0}
            cong_cache[name]['ecn.packets_sum'] = {'value': 0}
        ecn_packets = int(rule_data[0]) - \
            cong_cache[name]['ecn.packets_sum']['value']
        cong_cache[name]['ecn.packets_sum']['value'] = int(rule_data[0])
        ecn_bytes = int(rule_data[1]) - \
            cong_cache[name]['ecn_bytes_sum']['value']
        cong_cache[name]['ecn_bytes_sum']['value'] = int(rule_data[1])
        """ecn congestion average equation"""
        ecn_cong_avg = self.s_factor * \
            (ecn_bytes * 8 / 1000 / self.collect_period)
        ecn_cong_rate_prev = cong_cache[name]['ecn.cong.rate']['value']
        """Actual ecn congestion rate takes into consideration the previous
        value with a certain percentage. The result is expressed in kbps"""
        ecn_cong_rate = ecn_cong_avg + (1 - self.s_factor) * ecn_cong_rate_prev
        """Update the cache file with new metric values"""
        cong_cache[name]['ecn.packets'] = {'timestamp': self.sample_time,
                                           'value': ecn_packets}
        cong_cache[name]['ecn.bytes'] = {'timestamp': self.sample_time,
                                         'value': ecn_bytes}
        cong_cache[name]['ecn.cong.rate'] = {'timestamp': self.sample_time,
                                             'value': ecn_cong_rate}
        self.log.info("metric updated for %s.", name)
        self.gauge('ecn.packets', ecn_packets, dimensions)
        self.gauge('ecn.bytes', ecn_bytes, dimensions)
        self.gauge('ecn.cong.rate', ecn_cong_rate, dimensions)
        self._update_cong_cache(cong_cache)

    def _check_chain(self):
        """Verify if the necessary iptables' chains are in place
        """
        for chain in [congestion_chain, prerouting_chain]:
            self._get_rule(chain)
        """Add new congestion chain if it's not in the table"""
        if not self.chain_exist:
            self._add_chain(congestion_chain)
        """Redirect any packet received by Prerouting chain to congestion
        chain"""
        if not self.rule_exist:
            self._add_rule(prerouting_chain, None, None, congestion_chain)

    def _activate_ecn(self):
        """Ensures that the ECN marking is enable on each tap interface
        """
        tos_rule = "TOS --set-tos 0x02/0xff"
        taps = None
        """Collect tap intefaces attached to linux bridge"""
        try:
            taps = subprocess.check_output(
                "brctl show | awk '{print $1}' | grep tap",
                shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.log.error(e.output)
        if taps:
            taps = filter(None, taps.split('\n'))
            """Collect installed rules in Forward chain"""
            forw_rules = self._get_rule(forward_chain)
            for tap in taps:
                tap = tap + " --physdev-is-bridged"
                if not self._find_tap(tap, forw_rules, tos_rule):
                    """Enable ECN"""
                    match = "physdev --physdev-in " + tap
                    self._add_rule(forward_chain, None, match, tos_rule)
                    self.log.info("ECN is enabled for %s interface.", tap)

    def _find_tap(self, tap, chain, tos_rule):
        for rule in chain:
            """Check if the rule was applied to tap interface"""
            if (tap + " -j " + tos_rule) in rule:
                return True
        return False

    def _add_chain(self, chain):
        """This method adds 'chain' into iptables.
        """
        command = "sudo iptables -t mangle -N " + chain + " -w"
        try:
            subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Command {} return with error (code {}): {}"
                    .format(e.cmd, e.returncode, e.output))
        self.log.info("New %s chain was added to mangle table.", chain)

    def _add_rule(self, chain, ip, match, action):
        """Add new iptables rule based on the given arguments.
        """
        basic_rule = "sudo iptables -t mangle -A "
        if chain == prerouting_chain:
            command = basic_rule + chain + " -j " + action + " -w "
        if chain == congestion_chain:
            command = basic_rule + chain + " -s " + ip + " -m " + match + \
                " -j " + action + " -w"
        if chain == forward_chain:
            command = basic_rule + chain + " -m " + match + \
                " -j " + action + " -w"
        try:
            subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Command {} return with error (code {}): {}"
                    .format(e.cmd, e.returncode, e.output))
        self.log.info("New rule was added to %s ", chain)

    def _get_rule(self, chain):
        """Search in the iptables chains if 'chain' exist.
        """
        command = "sudo iptables -S -t mangle -w"
        forw_rules = []
        try:
            output = subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT,
                universal_newlines=True)
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Command {} return with error (code {}): {}"
                    .format(e.cmd, e.returncode, e.output))
        output = filter(None, output.split('\n'))
        if chain == congestion_chain:
            for rule in output:
                if '-N congestion' in rule:
                    self.chain_exist = True
                    break
        if chain == prerouting_chain:
            for rule in output:
                if '-A PREROUTING -j congestion' in rule:
                    self.rule_exist = True
                    break
        if chain == forward_chain:
            for rule in output:
                if '-A FORWARD' in rule:
                    forw_rules.append(rule)
            return forw_rules
        return 0

    def _get_hypervisors(self):
        """Connect to nova client and get the name/ip of all remote compute
        (hypervisor).
        """
        hyp_list = {}
        n_client = self._get_nova_client()
        hypervisors = n_client.hypervisors.list()
        for hypervisor in hypervisors:
            name = hypervisor.__dict__['hypervisor_hostname']
            ip = hypervisor.__dict__['host_ip']
            if name not in hyp_list:
                hyp_list[name] = ip
        return hyp_list

    def _get_vms(self, compute_name):
        """Connect to nova client and collect the name and the ip of all VMs
        deployed in a specific compute_name.
        """
        vm_list = {}
        n_client = self._get_nova_client()
        try:
            instances = n_client.servers.list(
                search_opts={'all_tenants': 1, 'host': compute_name})
        except Exception as e:
            self.log.error(
                "%s : No instances hosted in %s compute. ", e, compute_name)
            vm_list = {}
        if instances:
            for instance in instances:
                inst_name = instance.__getattr__('name')
                for net in instance.addresses:
                    for ip in instance.addresses[net]:
                        if (ip['OS-EXT-IPS:type'] == 'fixed' and
                           ip['version'] == 4):
                            vm_list[inst_name] = ip['addr']
        return vm_list

    def _get_counters(self, ip, chain):
        """Collect packets and bytes of each source 'ip' existing in 'chain'.
        """
        counters = ()
        command = "sudo iptables -L " + chain + " -v -t mangle -w"
        try:
            output = subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT,
                universal_newlines=True)
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Command {} return with error (code {}): {}"
                    .format(e.cmd, e.returncode, e.output))
        output = filter(None, output.split('\n'))
        for line in output:
            if 'tos match0x03' in line:
                line = filter(None, line.split(' '))
                if str(ip) == line[7]:
                    packet = self._convert_data(line[0])
                    bytes = self._convert_data(line[1])
                    counters = (packet, bytes)
        return counters

    def _convert_data(self, data):
        """Convert any string that contains a K or M letter to an integer.
        """
        if 'K' in str(data):
            data = int(data.replace('K', '')) * 1000
        if 'M' in str(data):
            data = int(data.replace('M', '')) * 1000000
        return data

    def _load_cong_cache(self):
        """Load congestion metrics from the previous measurement stored as
        cache file in the hard disk.
        """
        load_cong_cache = {}
        try:
            with open(self.cong_cache_file, 'r') as cache_json:
                load_cong_cache = json.load(cache_json)
        except (IOError, TypeError, ValueError):
            self.log.warning(
                "Congestion cache missing or corrupt, rebuilding.")
            load_cong_cache = {}
        return load_cong_cache

    def _update_cong_cache(self, cong_cache):
        """update cache file."""
        write_cong_cache = deepcopy(cong_cache)
        try:
            with open(self.cong_cache_file, 'w') as cache_json:
                json.dump(write_cong_cache, cache_json)
            if stat.S_IMODE(os.stat(self.cong_cache_file).st_mode) != 0o600:
                os.chmod(self.cong_cache_file, 0o600)
            self.log.warning("Your cache file is updated : %s ", time.time())
        except IOError as e:
            self.log.error("Cannot write to {0}: {1}".
                           format(self.cong_cache_file, e))

    def _get_nova_client(self):
        """Get nova client object based on configured parameters.
        """
        region_name = self.init_config.get('region_name')
        endpoint_type = self.init_config.get("endpoint_type", "publicURL")
        nc = nova_client.Client(2, session=self.session,
                                endpoint_type=endpoint_type,
                                service_type="compute",
                                region_name=region_name)

        return nc
