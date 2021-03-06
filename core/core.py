import logging
import os
import yaml
import shutil
import filecmp
import numpy
import time
import subprocess

import connectors.kubernetes_connector as kc
import connectors.lb_connector as lbc

#Preciso para se poder usar nas funcoes de config mais em baixo


#Load vars from config file
with open(os.path.abspath("./config/config.yaml")) as file:
    init_params = yaml.load(file, Loader=yaml.FullLoader)

#Initialize the kubectl connector with the cluster's credentials
kube_conn = kc.kubernetes_connector(init_params["kubernetes"]["kubectl_location"])
#lb_conn = None

lb_deployment_name = init_params["kubernetes"]["lb_deployment_name"]
lb_service_name = init_params["kubernetes"]["lb_service_name"]
deployments_path = init_params["kubernetes"]["templates_location"] + "/deployments"
services_path = init_params["kubernetes"]["templates_location"] + "/services"
lb_config = init_params["lb-config"]


#Functions that assesses if there is necessity to create LB deployment or it only needs to update it
def process_request(ip_list):

    need_to_create = True
    #check if LB deployment exists
    deployments = list_deployments()
    for item in deployments.items:
        if item.metadata.name == lb_deployment_name:
            need_to_create = False

    print("Do I need to create?")
    print(need_to_create)

    if need_to_create:
        #creation of the deployment
        stat = create_deployment()

        #create a lb deployment-active.yaml that mirrors the current state of the deployment
        shutil.copyfile(deployments_path + "/" + lb_deployment_name + ".yaml", deployments_path + "/" + lb_deployment_name + "-active.yaml")

        #create lb-service to expose the deployment
        stat2 = create_service()

        #wait until the aws lb endpoint is working
        print("Waiting for Kubernetes LB to be ready")
        wait_aws_lb_ready()

        # fetch the lb service's endpoint
        aws_lb_endpoint = find_aws_lb_endpoint()
        print("aws-endpoint found: {}".format(aws_lb_endpoint))

        #create lb_connector instance to configure the lb application
        lb_conn = lbc.lb_connector(aws_lb_endpoint + ":" + str(lb_config["lb_port"]))

        #configure the lb_app
        create_and_configure_lb(lb_conn, lb_config, ip_list)

        return ("Success!")

    if not need_to_create:
        #check if there is a lb-deployment active
        try:
            with open(os.path.abspath(deployments_path+ "/" + lb_deployment_name + "-active.yaml")) as f:
                service = yaml.safe_load(f)

            #create lb_connector
            aws_lb_endpoint = find_aws_lb_endpoint()
            print("aws-endpoint found: {}".format(aws_lb_endpoint))
            lb_conn = lbc.lb_connector(aws_lb_endpoint + ":" + str(lb_config["lb_port"]))

            #if there is an active deployment file check if there is any difference with the newer version
            if filecmp.cmp(os.path.abspath(deployments_path + "/" + lb_deployment_name + ".yaml"), os.path.abspath(deployments_path + "/" + lb_deployment_name + "-active.yaml")):

                print("There are no changes in the deployment")
                #If there are no updates check if the ips provided match those already in place
                services_info = lb_conn.list_all_services()
                current_ips = list()
                for key in services_info.keys():
                    current_ips.append(services_info[key]["ip"])

                print("Current Service IPS are: {}".format(current_ips))

                #check if there are any differences
                print(set(ip_list) == set(current_ips))

                #if they match to the ones provided as arguments do nothing
                if set(ip_list) == set(current_ips):
                    return ("No changes detected")

                #if the IPs are different delete the current ones and replace them with the new ones
                else:
                    print("Fuck, there are changes")
                    replace_lb_services(lb_conn, lb_config, current_ips, ip_list)
                    return ("Services have been updated")

            #If the files are not the same we need to perform a rolling update of the service!
            else:
                print("Fuck, the deployment needs a rolling update!")
                update_deployment()

                #wait for the update to complete
                time.sleep(10)
                print("The deployment has been updated!")

                #check if there are changes in the services
                services_info = lb_conn.list_all_services()
                current_ips = list()
                for key in services_info.keys():
                    current_ips.append(services_info[key]["ip"])

                print("Current Service IPS are: {}".format(current_ips))

                # check if there are any differences
                print(set(ip_list) == set(current_ips))

                # if they match to the ones provided as arguments do nothing
                if set(ip_list) == set(current_ips):
                    return ("No changes detected")

                # if the IPs are different delete the current ones and replace them with the new ones
                else:
                    print("Fuck, there are changes")
                    replace_lb_services(lb_conn, lb_config, current_ips, ip_list)
                    return ("Services have been updated")

        except FileNotFoundError as e:
            print("We found a service already running but found no deployment-active file!")
            print("Destroying zombie LB app")
            #if there is a  service already up but no record of active template file delete the existing service and recreate
            r = kube_conn.delete_service(lb_service_name)
            r = kube_conn.delete_deployment(lb_deployment_name)
            print("Destroyed the zombie LB deployment successfully")
            print("Destroyed the zombie LB service successfully")

            #Create the serbvice again
            # creation of the deployment
            stat = create_deployment()

            # create a lb deployment-active.yaml that mirrors the current state of the deployment
            shutil.copyfile(deployments_path + "/" + lb_deployment_name + ".yaml",
                            deployments_path + "/" + lb_deployment_name + "-active.yaml")

            # create lb-service to expose the deployment
            stat2 = create_service()

            # wait until the aws lb endpoint is working
            print("Waiting for Kubernetes LB to be ready")
            wait_aws_lb_ready()

            # fetch the lb service's endpoint
            aws_lb_endpoint = find_aws_lb_endpoint()
            print("aws-endpoint found: {}".format(aws_lb_endpoint))

            # create lb_connector instance to configure the lb application
            lb_conn = lbc.lb_connector(aws_lb_endpoint + ":" + str(lb_config["lb_port"]))

            # configure the lb_app
            create_and_configure_lb(lb_conn, lb_config, ip_list)

            return ("Success!")


    return 0

def destroy_all():
    #evaluate if anything has been created
    try:
        with open(os.path.abspath(deployments_path + "/" + lb_deployment_name + "-active.yaml")) as f:
            service = yaml.safe_load(f)

        #destroy the service and the deployment
        r = kube_conn.delete_service(lb_service_name)
        r = kube_conn.delete_deployment(lb_deployment_name)
        #delete the deployment-active file
        os.remove(os.path.abspath(deployments_path + "/" + lb_deployment_name + "-active.yaml"))
        return ("Destruction was successful")

    except FileNotFoundError as e:
        return ("No active deployment and therefore nothing to destroy")


#DEPLOYMENT FUNCTIONS
def create_deployment():
    res = kube_conn.create_deployment(deployments_path, lb_deployment_name)
    res_2 = kube_conn._wait_for_deployment_to_complete(lb_deployment_name)
    print("Deployment Created")
    return ("Deployment Created")

def delete_deployment():
    #check if deployment exists
    res = kube_conn.delete_deployment(lb_deployment_name)
    return ("Deployment Deleted")

def update_deployment():
    #dar update no kubernetes
    res = kube_conn.update_deployment(os.path.abspath(deployments_path), lb_deployment_name)
    #copy to deployment-active
    shutil.copyfile(deployments_path + "/" + lb_deployment_name + ".yaml",
                    deployments_path + "/" + lb_deployment_name + "-active.yaml")
    return ("Deployment Updated")

def status_deployment(deployment_name):
    deployment_status = kube_conn.status_deployment(deployment_name + "-deployment")
    return deployment_status

def list_deployments():
    deps = kube_conn.list_deployments("default")
    return deps


#SERVICE FUNCTIONS
def create_service():
    #unfortunatly this does not work
    #res = kube_conn.create_service(services_path, lb_service_name)

    #this workaround is messy but al least it works
    bash_command = "kubectl expose deployment " + lb_deployment_name + " --type=LoadBalancer --name="  + lb_service_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    print (output)
    print("Service created")
    return ("Service created")

def delete_service():
    #same as above
    #res = kube_conn.delete_service(lb_service_name)
    bash_command = "kubectl delete service " + lb_service_name
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    print(output)
    return ("Service deleted ")

def find_aws_lb_endpoint():
    r = kube_conn.list_services()
    for item in r.items:
        if item.metadata.name == "lb-service":
            return item.status.load_balancer.ingress[0].hostname
        else:
            continue
    return ("lb-service not found")


def wait_aws_lb_ready():
    time.sleep(180)
    return ("ok")

#POD FUNCTIONS
def list_pods():
    res = kube_conn.list_pods("default")
    print (res)


#LB FUNCTIONS - Performs operations on the LB through its associated connector

def create_and_configure_lb(lb_conn, lb_config, ip_list):
    #create lb
    resp = lb_conn.create_lb(lb_config["lb_name"], lb_config["lb_vip"], lb_config["ttl"],
                             lb_config["fqdn"], lb_config["lb_port"])
    print("Load Balancer {} created".format(resp["name"]))

    #create a service and its monitor for each ip provided
    for item in ip_list:
        resp = lb_conn.create_service(lb_config["service_name"] + "-" + item, item, lb_config["service_port"])
        print(resp)
        print("Service {} created".format(resp["name"]))
        resp_2 = lb_conn.create_monitor(lb_config["service_name"] + "-" + item + "-monitor", lb_config["ok_msg"],
                                            lb_config["hc_interval"], lb_config["monitor_path"])
        print(resp_2)
        print("Monitor {} created".format(resp_2["name"]))
        resp_3 = lb_conn.bind_monitor_to_service(lb_config["service_name"] + "-" + item, lb_config["service_name"] + "-" + item + "-monitor")
        print("Monitor {} bound to Service {}".format(resp["name"], resp_2["name"]))

    #bind each service to the lb
    for item in ip_list:
        resp = lb_conn.bind_lb_to_service(lb_config["lb_name"], lb_config["service_name"] + "-" + item)
        print("Service {} bound to Load Balancer {}".format(lb_config["service_name"], lb_config["lb_name"]))

    return ("Sucess!")

def replace_lb_services(lb_conn, lb_config, current_ips, ip_list):

    services = lb_conn.list_all_services()
    for key in services.keys():
        #if the service ip not in current ips then it need to be deleted along with its monitors and removed from the lb
        if services[key]["ip"] not in ip_list:
            lb_conn.unbind_monitor_from_service(services[key]["name"], services[key]["name"] + "-monitor")
            lb_conn.unbind_service_from_lb(lb_config["lb_name"], services[key]["name"])
            lb_conn.delete_monitor(services[key]["name"] + "-monitor")
            lb_conn.delete_service(services[key]["name"])
            print("Deleted service {} and its corresponding monitor".format(services[key]["name"]))

    # list with ips that need to be created
    to_create = numpy.setdiff1d(ip_list, current_ips)
    print("IP that need creation: {}".format(to_create))

    for item in to_create:
        resp = lb_conn.create_service(lb_config["service_name"] + "-" + item, item, lb_config["service_port"])
        print("Service {} created".format(resp["name"]))
        resp_2 = lb_conn.create_monitor(lb_config["service_name"] + "-" + item + "-monitor", lb_config["ok_msg"],
                                        lb_config["hc_interval"], lb_config["monitor_path"])
        print("Monitor {} created".format(resp_2["name"]))
        resp_3 = lb_conn.bind_monitor_to_service(lb_config["service_name"] + "-" + item,
                                                 lb_config["service_name"] + "-" + item + "-monitor")
        print("Monitor {} bound to Service {}".format(resp["name"], resp_2["name"]))

        # bind each service to the lb
    for item in to_create:
        resp = lb_conn.bind_lb_to_service(lb_config["lb_name"], lb_config["service_name"] + "-" + item)
        print("Service {} bound to Load Balancer {}".format(lb_config["service_name"], lb_config["lb_name"]))

    return ("Success!")



#Not needed, when one is destroying stuff one destroys the whole deployment at once
def destroy_lb(lb_conn):

    #Retrieve all monitors

    #Retrieve all services

    #Retrieve all lbs

    #Unbind monitors from the services

    #Unbind services from the lb

    #Delete monitors

    #Delete services

    #Delete lb

    return ("Success!")


#TESTE
def teste():

    lb_conn = lbc.lb_connector("ac47d2e917a6d49ae9ba4d65c4a7d3f0-131937175.eu-west-1.elb.amazonaws.com:" + str(lb_config["lb_port"]))
    #create_and_configure_lb(lb_conn, lb_config, ["10.0.1.1", "10.0.1.2", "10.0.1.3"])

    resp7 = lb_conn.list_all_monitors()
    print(resp7)
    resp8 = lb_conn.list_all_services()
    print(resp8)
    #resp9 = lb_conn.list_all_lbs()
    #print(resp9)

    #lb
    #resp = lb_conn.create_lb(lb_config["lb_name"], lb_config["lb_vip"], lb_config["ttl"], lb_config["fqdn"], lb_config["lb_port"])
    #resp = lb_conn.list_all_lbs()

    #service
    #resp = lb_conn.create_service(lb_config["service_name"], "10.0.1.10", lb_config["service_port"])
    #print(resp)
    #resp2 = lb_conn.list_all_services()
    #print (resp2)


    #monitors
    #resp = lb_conn.create_monitor(lb_config["service_name"] + "-monitor", lb_config["ok_msg"], lb_config["hc_interval"], lb_config["monitor_path"])
    #print (resp)
    #resp2 = lb_conn.list_all_monitors()
    #print (resp2)

    #monitor/service  association
    #resp = lb_conn.bind_monitor_to_service(lb_config["service_name"], lb_config["service_name"] + "-monitor")
    #print (resp)

    #service/lb association
    #resp = lb_conn.bind_lb_to_service(lb_config["lb_name"], lb_config["service_name"])
    #print (resp)



    return ("ok")

