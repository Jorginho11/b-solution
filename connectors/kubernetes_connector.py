import yaml
import os
import time
import json

from connectors import base_connector
from kubernetes import client, config, watch

class kubernetes_connector(base_connector.base_connector):

    def __init__(self, kubectl_path):
        #create kubectl stufff
        print(kubectl_path)
        self.config = config.load_kube_config(kubectl_path)
        self.kube_client = client.CoreV1Api()
        self.apps = client.AppsV1Api()
        self.api = client.ExtensionsV1beta1Api()

        #create db to store deployment instance info
        self.db = dict()

#DEPLOYMENT METHODS
    def create_deployment(self, deployment_path, deployment_name, namespace="default"):

        with open(os.path.abspath(deployment_path+"/" + deployment_name + ".yaml")) as f:
            deployment = yaml.safe_load(f)
        resp = self.apps.create_namespaced_deployment(body=deployment, namespace=namespace)
        print("Deployment created. status='%s'" % str(resp.status))
        return resp

    def delete_deployment(self, deployment_name, namespace="default"):
        resp = self.apps.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
        #body=client.V1DeleteOptions(propagation_policy="Foreground", grace_period_seconds=5)
        return resp

    def update_deployment(self, deployment_path, deployment_name, namespace="default"):
        #load the updated information
        with open(os.path.abspath(deployment_path + "/" + deployment_name + ".yaml")) as f:
            deployment = yaml.safe_load(f)
        resp = self.apps.replace_namespaced_deployment(name=deployment_name, namespace=namespace, body=deployment)
        return resp

    def status_deployment(self, deployment_name, namespace="default"):
        resp = self.api.read_namespaced_deployment_status(deployment_name, namespace)
        return resp

    def list_deployments(self, namespace="default"):
        resp = self.apps.list_namespaced_deployment(namespace)
        return resp

    def _wait_for_deployment_to_complete(self, deployment_name, namespace="default", timeout=60):
        time.sleep(10)
        return ("ok")

    def wait_for_deployment_to_complete(self, deployment_name, namespace="default", timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            response = self.api.read_namespaced_deployment_status(deployment_name, namespace)
            s = response.status
            if (s.updated_replicas == response.spec.replicas and
                    s.replicas == response.spec.replicas and
                    s.available_replicas == response.spec.replicas and
                    s.observed_generation >= response.metadata.generation):
                return True
            else:
                print(f'[updated_replicas:{s.updated_replicas},replicas:{s.replicas}'
                      ',available_replicas:{s.available_replicas},observed_generation:{s.observed_generation}] waiting...')

        return ("Deployment not created")

#SERVICE_METHODS

    def create_service(self, service_path, service_name, namespace= "default"):
        with open(os.path.abspath(service_path+"/" + service_name + ".yaml")) as f:
            service = yaml.safe_load(f)
        resp = self.kube_client.create_namespaced_service(body=service, namespace=namespace)
        print("Service created. status='%s'" % str(resp.status))
        return resp

    def delete_service(self, service_name, namespace= "default"):
        resp = self.kube_client.delete_namespaced_service(service_name, namespace)
        return resp

    def list_services(self, namespace="default"):
        resp = self.kube_client.list_namespaced_service(namespace)
        return resp

#POD METHODS

    def list_pods(self, namespace="default"):
        res = self.kube_client.list_namespaced_pod(namespace)
        return res
