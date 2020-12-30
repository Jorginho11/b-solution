from flask import Flask, escape, request
#from app_core import core
import logging

app = Flask(__name__)
app.config["DEBUG"] = True

@app.route('/create_service' , methods=['POST'])
def test():
    http_content = request.json
    response = core.test(http_content["dict"])
    return response


def run():
    #todo: configure better logging tools
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename='/Users/cptrekstor/PycharmProjects/call_bob/logs/api_logging',
                        filemode='w')
    app.run()