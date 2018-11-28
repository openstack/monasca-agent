# (C) Copyright 2017 Hewlett Packard Enterprise Development LP
# coding=utf-8

from monasca_agent.collector.checks import utils

kubernetes_connector = utils.KubernetesConnector(3)
print(kubernetes_connector.get_agent_pod_host(return_host_name=True))
