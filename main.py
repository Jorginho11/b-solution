import sys
from core import core

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    if (len(sys.argv) == 4):
        ip_list = list()
        for arg in sys.argv[1:]:
            ip_list.append(arg)
        r = core.process_request(ip_list)
        #r = core.teste()
        print(r)
    elif (len(sys.argv) == 1):
        print("About to destroy all")
        r = core.destroy_all()
        print(r)
    else:
        print("Incorrect number of parameters")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
