# b-solution

#############################################################################

## Solution's Assumptions

Before explaining the solution's architecture I will first explain the configuration aspects that fall out of the solution's scope and that must be manually configured by its users in order for it to function properly.

1 - The solution expects to be able to manage a fully configured Kubernetes cluster which should be accessible through a valid kubeconfig file. The kubeconfig's path must be declared in the corresponding ansible's default value or the solution config file, and the path itself must also be valid;

2 - The solution also expects to be able to create a LoabBalancer on the Kubernetes cluster and this LoadBalancer should automatically be externally reachable;

3 - How you configure the ansible to run is out of the scope of the solution. As such, some adaptations may need to be made to your ansible installation for it to  i.e run on a remote server.

Personally, I have designed and tested the solution using AWS's EKS and LB services which minimized (specially in the LoabBalancer part) the manual configuration steps. For those trying evaluate the solution, if possible, try to test the solution in a similar environment!

Now to the solution.


## Architecture  

This solution was designed using Ansible and Python3.
```
    - Ansible was used to automate the solution's installation on a bare (only tested on a Ubuntu) image.
        - The ansible installs all the programs dependancies (pull the solution's code from my github) and also installs a kubectl client on the machine that will be helpfull when trying to evaluate the solution;
        - The ansible also allows its users to overide the solution's default configuration values, by replacing the solution's default value with those defined in the ansible defaults.

    - The python3 application (from now on refered to as PYAPP) has two main goals:
        - It manages blip's LB application lifecycle operations (creation, deletion, update, etc) through api calls to a Kubernetes cluster;
            - These interactions are done through a "kubernetes connector" that implements a kubernetes-client by calling the methods defined in the lib found in https://github.com/kubernetes-client/python.
        - It also handles blip's LB application configuration licecycle operations;
            - These interactions are also done in a similar fashion, through a "LB connector" that implements the API defined the the LB's documentation.
```
The PYAPP is stateless and when performing any operations it always queries the Kubernetes cluster for the "latest information".

## Application State Management
As previously mentioned, Kubernetes was used the container orchestration engine through which we manage blip's LB app state. 
```
When designing the solution, one of the biggest challenges was finding a way to manage the LB's application state since one of the constraints was that the app should be called in the <program> <new_ip_1> <new_ip_2> <new_ip_3> format, a syntax that is a little... constraining :) .
    - As such, the solution found controls the LB application's state in a terraform-like fashion: we have a lb-deployment.yaml (that tells us how we want the application to look like after we run the PYAPP) and a lb-deployment-active.yaml (that tells us how the application is currently looking like in the Kubernetes cluster).
    - Each time the PYAPP is run it compares the two files
        - If the lb-deployment-active.yaml does not exist it is a creation operation.
        - If both files exist but they are the same nothing is done (at least deployment state wise, it may need to perform configurations on the LB)
        - If both files exist but they are differsis lb-deploment-active.yaml but when it queries the cluster it is not detected a lb-deploment, it ignores what would be considered an updated and treats the operation as a create rather than an update one.
```
## Application Configuration Management 
The LB's configuration is managed through a configuration file under the <PYAPP_PATH>/config/config.yaml. There the user is able to configure the LB's config values requested in the challenge.

While these values are always loaded on each call of the PYAPP, the PYAPP does not evaluate if the current configuration matches the desired one i.e If a monitor has been created on a previous PYAPP call and the user changed i.e the monitor_path variable on the config file only new monitors will be created with the new monitor_path (there was not time for everything...)
```
The values passed as arguments to the PYAPP (from what I undertood) refer to the other service endpoints' the LB is supposed to balance traffic to.
    - As previously said the PYAPP is stateless. As such, on each run, the PYAPP queries the LB to find which services (identified by their ips) are currently "running" and compares them to the endpoints provided in argument.
    - The first the PYAPP is run the behavior is simple: it creates the three services (and their associated lifecycle creation tasks).
        - When "creating a service" the PYAPP creates a service and its monitor, bind them together and them bind the service to the lb
    - On subsequent runs the PYAPP analyses which services are running and which are supposed to be running on the new run and updates de LB state:
        - When there are inconsistencies, the PYAPP deletes the service that should no longer be running and creates new ones with the correct endpoints
            - When "deleting a service" the PYAPP unbinds the monitor from the service and the service from the lb and them deletes both the service and the monitor.
```
## Usage 
The software can be installed on a remote machine through the usage of the ansible provided in the folder "ansible". If you wish to change any config values, do so under the <ansible>/roles/lb-manager/defaults/main.yml
```
As defined in the requirements, after the ansible finished the PYAPP's intallation (it can  also be run locally on your machine), the PYAPP can be called in two ways:
    - It can be called with the required three input arguments (as required in the challeenge's constraints) to perform create or update operations  i.e "python3 main.py 10.0.0.1 10.0.0.2 10.0.0.3" 
    - It can be called without input arguments to delete de LB app and its corresponding cluster from the Kubernetes cluster i.e "python main.py"
The PYAPP also comer with his own venv under <PYAPP_PATH>/venv that contains the PYAPP dependencies. This venv should be loaded before running the PYAPP.
```

## Surprise features (AKA Bugs)
While it should possible to upload a kubernetes service file describing the LB configuration in the same fashion it was done for the deployments, at test time, the LB created through this method did not work as expected an kept answering with "connection reset" to any attempt to connect to it.
    - For this reason it was implemented a messier but working solution (through a bash kubectl expose command in the PYAPP source code) .
    - This approach, however, brought un undesired bug: the expose command directly exposes blip's LB application port and thus, while it possible to alter both ports, they must be an exact match i.e in the config file the "lb_port" must be the same as "service_port" otherwise connectivity through the Kubernetes' LB will be lost.

While the lb-deployment-name and lb-service-name appear as a variable in the config file they must match the value name present in the lb-deploment.yaml file and as a simplification, the queries to the kubernetes services ended up being hardcoded to look for those names
	- Please do not change these values

When we perform a rolling updated increasing the deployment size to a number larget than 1 replica, the PYAPP breaks due to a lack of synchronism between the two LB application's instances! i.e if we create a service at a given point when we have two replicas, due to the balance of traffic among the instances, we may end up trying to do a bind operation on the instance in which the service was not created which will break the PYAPP.
    - While this bug does not come from the PYAPP itself, its an interesting scenario to take note!


## Constraints
There is no input verification nor (much) error handling.
In general the wait funtions are a little... rudimentar to say the least :D
From my perpective I had to make a choice: do something really simple and robust or something more complex but cut some corners. I chose the latter.







