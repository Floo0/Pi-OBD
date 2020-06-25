import time
import json
import logging
import os,sys

sys.path.insert(1, os.path.join(sys.path[0], '..'))
import client
import _uds_helper


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SERVICE = "uds/disp"
UDS = [
        ["DiagnosticSessionControl", "Default"],
        ["DiagnosticSessionControl", "Programming"],
        ["DiagnosticSessionControl", "Extended"],
        ["TesterPresent", "Request"],
        ["ReadDataByIdentifier", "ReadOdometerValueFromBus"],
        ["ReadDataByIdentifier", "ActiveDiagnosticInformation"],
        ["ReadDataByIdentifier", "ElectroniControlUnitSerialNumber"],
        ["AsynchronousRoutine", "StartDisplayPatternBlack"],
        ["AsynchronousRoutine", "StartDisplayPatternWhite"],
        ["AsynchronousRoutine", "StartDisplayPatternRed"],
        ["AsynchronousRoutine", "StartDisplayPatternGreen"],
        ["AsynchronousRoutine", "StartDisplayPatternBlue"],
        ["AsynchronousRoutine", "StopDisplayPattern"],
        ["AsynchronousRoutine", "RequestResults"],
        ["InputOutputControlByIdentifier", "SetDisplayIntensity"],
        ["InputOutputControlByIdentifier", "ResetDisplayIntensity"],
        ]


def on_request(client, msg):
    logger.debug("Callback: Got message: {} on topic: {}".format(msg.payload, msg.topic))
    topics = msg.topic.split("/")
    message = json.loads(msg.payload.decode('utf-8'))
    response = message['response']

    uds_helper = _uds_helper.UDSHelper(client, response)
    service = topics[-2]
    parameter = topics[-1]
    TxID = "063B"
    RxID = "05BB"

    uds_helper.connectISOTP(TxID, RxID)
    result = uds_helper.executeUDS(service, parameter, message)
    json_result = json.dumps(result)
    client.publish(response, json_result, 1)


def main():
    cl = client.Client(SERVICE)
    cl.run()
    time.sleep(0.1) # wait to get connected
    cl.subscribe(SERVICE + "/#", on_request, 1)
    uds_dict = _uds_helper.UDSHelper().uds_dict

    while True:
        for element in UDS:
            # print("element", element)
            # print("uds_dict[element[0]][element[1]]", uds_dict[element[0]][element[1]])
            description = "No description available."
            if "description" in uds_dict[element[0]][element[1]]:
                description = uds_dict[element[0]][element[1]]["description"]
            message = {
                "request": SERVICE + "/" + element[0] + "/" + element[1],
                "description": description,
                "parameters": {
                    "response": {
                        "default": "tester1/disp",
                        "description": "Topic to publish response to.",
                        "type": "string"}}}
            if "parameters" in uds_dict[element[0]][element[1]]:
                for parameter in uds_dict[element[0]][element[1]]["parameters"]:
                    message["parameters"][parameter] = uds_dict[element[0]][element[1]]["parameters"][parameter]
            cl.publishService(message)
            time.sleep(0.1)
        time.sleep(5)


if __name__ == "__main__":
    # main()
    while True:
        try:
            main()
        except Exception as e:
            print("main error: " + str(e))
        time.sleep(3)
