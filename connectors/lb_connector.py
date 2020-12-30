import requests
import json

from connectors import base_connector

class lb_connector(base_connector.base_connector):

    def __init__(self, lb_url):
        self.lb_url = "http://" + lb_url

#LB
    def create_lb(self, name, vip, ttl, cname, port):
        path = "/lb"
        data = {
            "name": name,
            "vip": vip,
            "dns": {
                "ttl": ttl,
                "cname": cname
            },
            "port": port
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.post(self.lb_url+path, data=json.dumps(data), headers=headers)
        return r.json()

    def delete_lb(self, lb_name):
        path = "/lb/" + lb_name
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.delete(self.lb_url + path,  header=headers)
        return r.json()


    def bind_lb_to_service(self, lb_name, service_name):
        path = "/lb/" + lb_name + "/bind/" + service_name
        data = {
            "name": lb_name,
            "service_name": service_name
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.put(self.lb_url+path, data=json.dumps(data), headers=headers)
        return r.json()

    def unbind_service_from_lb(self, lb_name, service_name):
        path =  "/lb/" + lb_name + "/unbind/" + service_name
        data = {
            "name": lb_name,
            "monitor_name": service_name
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.put(self.lb_url + path, data=json.dumps(data), headers=headers)
        return r.json()

    def list_all_lbs(self):
        path = "/lb"
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.get(self.lb_url + path, headers=headers)
        return r.json()



#MONITOR
    def create_monitor(self, monitor_name, response, interval, monitor_path):
        path = "/monitor"
        data = {
            "name": monitor_name,
            "response": response,
            "interval": interval,
            "monitor_path": monitor_path
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.post(self.lb_url + path, data=json.dumps(data), headers=headers)
        return r.json()

    def delete_monitor(self, monitor_name):
        path = "/monitor/" + monitor_name
        data = {
            "name": monitor_name
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.delete(self.lb_url + path, data=json.dumps(data), headers=headers)
        return r.json()

    def list_all_monitors(self):
        path = "/monitor/"
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.get(self.lb_url + path, headers=headers)
        return r.json()

#SERVICE
    def create_service(self, name, ip, port):
        path = "/service"
        data = {
            "name": name,
            "ip": ip,
            "port": port,
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.post(self.lb_url+path, data=json.dumps(data), headers=headers)
        return r.json()

    def delete_service(self, service_name):
        path = "/service/" + service_name
        data = {
            "name": service_name
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.delete(self.lb_url + path, data=json.dumps(data), headers=headers)
        return r.json()

    def list_all_services(self):
        path = "/service/"
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.get(self.lb_url + path, headers=headers)
        return r.json()

    def bind_monitor_to_service(self, service_name, monitor_name):
        path = "/service/" + service_name + "/bind/" + monitor_name
        data = {
            "name": service_name,
            "monitor_name": monitor_name
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.put(self.lb_url + path, data=json.dumps(data), headers=headers)
        return r.json()

    def unbind_monitor_from_service(self, service_name, monitor_name):
        path =  "/service/" + service_name + "/unbind/" + monitor_name
        data = {
            "name": service_name,
            "monitor_name": monitor_name
        }
        headers = {"Content-Type": 'application/json', "Accept": 'application/json'}
        r = requests.put(self.lb_url + path, data=json.dumps(data), headers=headers)
        return r.json()


