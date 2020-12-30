import sys
from core import core

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    #get arguments input
    input = str(sys.argv)



    #c = core.create_service("lb", {"10.0.1.1", "10.0.1.2", "10.0.1.3"})
    #c = core.status_deployment("lb")
    #c = core.delete_deployment("lb-deployment")
    #c = core.list_pods()
    #c = core.list_deployments()
    #c = core.process_request("10.0.1.1", "10.0.1.2", "10.0.1.3")


    r = core.process_request("10.0.1.1", "10.0.1.2", "10.0.1.5")
    #r = core.teste()
    print (r)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
