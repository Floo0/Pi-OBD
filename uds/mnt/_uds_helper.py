import time
# import can
import isotp
import json
# import udsoncan
# from udsoncan.connections import PythonIsoTpConnection
import logging


logger = logging.getLogger(__name__)

# standard values
RXID = 0x7DF
TXID = 0x7E8


def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


class UDSHelper(object):
    def __init__(self, client=None, response=None):
        self.mqtt_client = client
        self.response_topic = response
        self.uds_dict = {
            "DiagnosticSessionControl": {
                "ID": "10",
                "Default": {
                    "ID": "01",
                    "description": "Change to Default Session, standard session if no other session is running.",
                },
                "Programming": {
                    "ID": "02",
                    "description": "Change to Programming Session specific functionality required for ECU flashing.",
                },
                "Extended": {
                    "ID": "03",
                    "description": "Change to Extended Session to get access to all supported diagnostic services.",
                },
            },
            "ReadDataByIdentifier": {
                "ID": "22",
                "ReadOdometerValueFromBus": {
                    "ID": "010C",
                    "description": "Represents the current ODO-Information of the vehicle bus.",
                },
                "ReadAnalogDigitalConverterRawValues": {
                    "ID": "0301",
                    "description": "Read the current raw values of the CT ADC.",
                },
                "InputOutputStates": {
                    "ID": "0310",
                    "description": "With this service, the current values of the signals present at the ECU inputs and outputs as well as internal states can be queried.",
                },
                "ActiveDiagnosticInformation": {
                    "ID": "F100",
                    "description": "This Data Identifier provides the diagnostic information used by the tester to uniquely identify the respective diagnostic data set assigned to a specific ECU version.",
                },
                "ElectroniControlUnitSerialNumber": {
                    "ID": "F18C",
                    "description": "This record shall be used to uniquely identify a specific ECU hardware to be able to identify ECUs of a specific batch.",
                },
                "VehicleIdentificationNumberOriginal": {
                    "ID": "F190",
                    "description": "This data record reflects the Vehicle Identification Number of the vehicle an ECU was originally installed.",
                },
                "VehicleIdentificationNumberCurrent": {
                    "ID": "F1A0",
                    "description": "This data record reflects the Vehicle Identification Number of the vehicle an ECU is currently installed.",
                },
            },
            
            "InputOutputControlByIdentifier": {
                "ID": "2F",
                "OpenTrunk": {
                    "ID": "D0010302",
                    "description": "Starts the trunk motor to open the trunk lid.",
                },
                "BrakeTrunk": {
                    "ID": "D0010304",
                    "description": "Brakes the trunk motor.",
                },
                "SetDisplayIntensity": {
                    "ID": "D01303",
                    "description": "Sets the display intensity.",
                    "parameters": {
                        "intensity": {
                            "default": "50",
                            "description": "Percentage of maximum intensity possible.",
                            "type": "integer",
                            "interpretation": "x = format(int(x), 'x')",
                            "bit": "20", # parameter position in hex
                        }
                    },
                },
                "ResetDisplayIntensity": {
                    "ID": "D01301",
                    "description": "Resets the display intensity to the default value.",
                },
            },

            "AsynchronousRoutine": {
                "ID": "31",
                "StartDisplayPatternBlack": {
                    "ID": "0103B104",
                },
                "StartDisplayPatternWhite": {
                    "ID": "0103B105",
                },
                "StartDisplayPatternRed": {
                    "ID": "0103B106",
                },
                "StartDisplayPatternGreen": {
                    "ID": "0103B107",
                },
                "StartDisplayPatternBlue": {
                    "ID": "0103B108",
                },
                "StopDisplayPattern": {
                    "ID": "0203B1",
                },
                "RequestResults": {
                    "ID": "0303B1",
                },
            },

            "TesterPresent": {
                "ID": "3E",
                "Request": {
                    "ID": "00",
                    "description": "Check if ECU is reachable (keep ECU awake/connection alive).",
                },
            },

            "Diagnostic Session Control Positive Response": {
                "ID": "50",
                "Default Session Response": {
                    "ID": "01",
                    "interpretation": "x = str(int(x[0:4], 16) * 1) + 'ms, ' + str(int(x[4:8], 16) * 10) + 'ms'",
                    "description": "Changed to Default Session with Timing Parameters \"P2_CAN_ECU_max\" and \"P2s_CAN_ECU_max\"",
                },"Programming Session Response": {
                    "ID": "02",
                    "interpretation": "x = str(int(x[0:4], 16) * 1) + 'ms, ' + str(int(x[4:8], 16) * 10) + 'ms'",
                    "description": "Changed to Programmingim gegensatz zu Session with Timing Parameters \"P2_CAN_ECU_max\" and \"P2s_CAN_ECU_max\"",
                },
                "Extended Session Response": {
                    "ID": "03",
                    "interpretation": "x = str(int(x[0:4], 16) * 1) + 'ms, ' + str(int(x[4:8], 16) * 10) + 'ms'",
                    "description": "Changed to Extended Session with Timing Parameters \"P2_CAN_ECU_max\" and \"P2s_CAN_ECU_max\"",
                },
            },

            "Read Data By Identifier Positive Response": {
                "ID": "62",
                "Read Odometer Response": {
                    "ID": "010C",
                    "interpretation": "x = str(int(x, 16) * 0.1)",
                    "unit": "km",
                },
                "Read Analog Digital Converter Raw Values Response": {
                    "ID": "0301",
                    "interpretation": "x = x",
                },
                "Input Output States Response": {
                    "ID": "0310",
                    "interpretation": "x = x"
                },
                "Active Diagnostic Information Response": {
                    "ID": "F100",
                    "interpretation": """
if x=="00080201": x="Default Session"
elif x=="00080202": x="Programming Session"
elif x=="00080203": x="Extended Session" """,
                },
                "Electronic Control Unit Serial Number Response": {
                    "ID": "F18C",
                    "interpretation": "x = x",
                },
                "Vehicle Identification Number Original Response": {
                    "ID": "F190",
                    "interpretation": "x = bytes.fromhex(x).decode('utf-8')",
                },
                "Vehicle Identification Number Current Response": {
                    "ID": "F1A0",
                    "interpretation": "x = bytes.fromhex(x).decode('utf-8')",
                },
            },

            "Input Output Control By Identifier Positive Response": {
                "ID": "6F",
                "Open Trunk Response": {
                    "ID": "D0010302",
                },
                "Brake Trunk Response": {
                    "ID": "D0010304",
                },
                "Display Control Reset Intensity Response": {
                    "ID": "D01301",
                    "description": "Display intensity reset to default (returns last set intensity, not the default value).",
                    "interpretation": "x = str(int(x, 16))",
                    "unit": "%",
                },
                "Display Control Set Intensity Response": {
                    "ID": "D01303",
                    "description": "New intesity set.",
                    "interpretation": "x = str(int(x, 16))",
                    "unit": "%",
                },
            },

            "Asynchronous Routine Positive Response": {
                "ID": "71",
                "Start Display Pattern Response": {
                    "ID": "0103B101",
                },
                "Stop Display Pattern Response": {
                    "ID": "0203B100",
                },
                "Routine successfully completed": {
                    "ID": "0303B100",
                },
                "Routine in progress": {
                    "ID": "0303B101",
                },
                "Routine stopped without results": {
                    "ID": "0303B100",
                },
            },

            "Tester Present Response": {
                "ID": "7E",
                "Positive Response": {
                    "ID": "00",
                },
            },

            "Negative Response": {
                "ID": "7F",
                "Incorrect message length or invalid format (by ReadDataByIdentifier)": {
                    "ID": "2213",
                },
                "Conditions not correct (by ReadDataByIdentifier)": {
                    "ID": "2222",
                },
                "Request out of range (by ReadDataByIdentifier)": {
                    "ID": "2231",
                },
                # "Request correctly received - response pending": {
                #     "ID": "3178",
                # },
                "Incorrect message length or invalid format (by InputOutputControlByIdentifier)": {
                    "ID": "2F13",
                },
                "Service not supported in (currently) active session (by AsynchronousRoutine)": {
                    "ID": "317F",
                },
            }
        }
        
        self.isotp_socket = isotp.socket()

    def getSIDbyName(self, name):
        """ needs a SID name, returns SID as hex string """

        for service in self.uds_dict:
            if service == name:
                return self.uds_dict[service]["ID"]
        logger.info("Could not find SID by Name (SID not implemented yet)")
        return False

    def getPIDbyName(self, SID, name):
        """ needs a SID as hex string and a PID name, returns SID as hex string """
        # logger.debug("getPIDbyName {} {}".format(SID, name))

        for parameter in self.uds_dict[SID]:
            if parameter == name:
                return self.uds_dict[SID][parameter]["ID"]
        logger.info("Could not find SID or PID by Name (SID or PID not implemented yet)")
        return False

    def getRxIDbyName(self, SID, name):
        """ same as getPIDbyName, but returns RxID """
        for key in self.uds_dict[SID]:
            if isinstance(self.uds_dict[SID][key], dict) and self.uds_dict[SID][key]["name"] == name:
                if "rxid" in self.uds_dict[SID][key]:
                    return self.uds_dict[SID][key]["rxid"]
                else:
                    return RXID
        logger.info("Could not find SID by Name (SID not implemented yet)")
        return False

    def getTxIDbyName(self, SID, name):
        """ same as getPIDbyName, but returns TxID """
        for key in self.uds_dict[SID]:
            if isinstance(self.uds_dict[SID][key], dict) and self.uds_dict[SID][key]["name"] == name:
                if "txid" in self.uds_dict[SID][key]:
                    return self.uds_dict[SID][key]["txid"]
                else:
                    return TXID
        logger.info("Could not find SID by Name (SID not implemented yet)")
        return False

    def connectISOTP(self, txid="07DF", rxid="07E8"):
        self.isotp_socket.set_opts(txpad=0x55, rxpad=0xAA)
        self.isotp_socket.set_fc_opts(stmin=0, bs=8) # configure stmin and blocksize for flow control options (0, 8)
        self.isotp_socket.bind('can0', isotp.Address(rxid=int(rxid,16), txid=int(txid,16))) # use vcan for virtual can or can0 for PiCAN2

    def _transmitISOTP(self, SID, PID):
        # build request (hex values), fill remaining bytes to fit 8 byte can message
        payload = SID + PID
        # logger.debug("uds payload raw: {}".format(payload))
        # print("uds transmit payload raw: {}".format(payload))
        payload = bytearray.fromhex(payload)
        # logger.debug("uds payload: {}".format(payload))
        # send message
        self.isotp_socket.send(payload)
        # while self.isotp_socket.transmitting():
        #     self.isotp_socket.process()
        #     time.sleep(self.isotp_socket.sleep_time())

    def _interpretParameter(self, parameter):
        # print("_interpretParameter", response)
        # if "length" in self.uds_dict[response["SID"]][response["PID"]]:
        #     response["Data"] = response["Data"][:self.uds_dict[response["SID"]][response["PID"]]["length"]]
        # if "encoding" in self.uds_dict[response["SID"]][response["PID"]]:
        #     response["Datastr"] = response["Data"].decode(self.uds_dict[response["SID"]][response["PID"]]["encoding"])
        # response["Data"] = int.from_bytes(response["Data"], byteorder='big')
        if "interpretation" in parameter and parameter["interpretation"]:
            local = {"x": parameter["data"]}
            exec(parameter["interpretation"], {}, local)
            parameter["interpretation"] = local["x"]
        return parameter

    def _getUDSInformation(self, payload, response):
        # check if response SID is known -> get name
        for service in self.uds_dict:
            # print("compare service", self.uds_dict[service]["ID"].lower(), format(response["SID"], "x"), service)
            if self.uds_dict[service]["ID"].lower() == response["SID"]:
                response["service"] = service
                break
        
        # check if response PID is known -> get name
        pid_length = 2
        found = False
        while not found and response["service"] != "unknown UDS service":
            pid_length += 2
            if pid_length > 15:
                response["PID"] = payload[2:]
                break
            response["PID"] = payload[2:pid_length]
            # print("PID raw", response["PID"])
            # print("PID", hex(response["PID"]))

            for parameter in self.uds_dict[service]:
                if parameter in ["ID", ""]:
                    continue
                # print("compare parameter", self.uds_dict[service][parameter]["ID"].lower(), response["PID"], parameter)
                if self.uds_dict[service][parameter]["ID"].lower() == response["PID"]:
                    found = True
                    response["parameter"] = parameter
                    if "description" in self.uds_dict[service][parameter]:
                        response["description"] = self.uds_dict[service][parameter]["description"]
                    if "interpretation" in self.uds_dict[service][parameter]:
                        response["interpretation"] = self.uds_dict[service][parameter]["interpretation"]
                        if "unit" in self.uds_dict[service][parameter]:
                            response["unit"] = self.uds_dict[service][parameter]["unit"]
                    break
        
            response["data"] = payload[pid_length:]

        return self._interpretParameter(response)

    def _receiveISOTP(self, SID, PID):
        # print("_receiveISOTP", SID, PID)
        # wait for response
        payload = None
        t1 = time.time()
        delta = 7
        # check for delta seconds
        while time.time() - t1 < delta and not payload:
            # if self.isotp_socket.available():
            payload = self.isotp_socket.recv().hex()
            if payload == "7F2F78".lower() or payload == "7F3178".lower():
                # print("Request correctly received - response pending")
                pending = json.dumps({"type": "info",
                            "SID": "7f",
                            "service": "Negative Response",
                            "PID": payload[2:],
                            "parameter": "Request correctly received - response pending",
                            "data": None,
                            "description": None,
                            "interpretation": None,
                            "unit": None})
                self.mqtt_client.publish(self.response_topic, pending, 1)
                payload = None
            # logger.info("Received payload: {}".format(payload))
            time.sleep(0.05)
        if not payload:
            logger.info("no message received for SID {} and PID/LEV {}".format(SID, hex(PID)))
            return False
        # print("received payload", payload)
        # print("received payload hex", payload.hex()[0])

        response = {
            "type": "uds",
            "SID": None,
            "service": "unknown UDS service",
            "PID": None,
            "parameter": "unknown UDS parameter/level",
            "data": None,
            "description": None,
            "interpretation": None,
            "unit": None,
        }
        response["SID"] = payload[:2]
        # print("SID", response["SID"], format(int(SID, 16) + 4*16, "x"))

        # check if UDS execution was successfull
        if response["SID"] == format(int(SID, 16) + 4*16, "x"):# and response["PID"] == PID:
            logger.info("successfully received uds message: {}".format(payload))
            response = self._getUDSInformation(payload, response)
            
        else:
            logger.info("received error message: {}".format(payload))
            response = self._getUDSInformation(payload, response)
        # print("final response", response)
        return response

    def executeUDS(self, service, parameter, message={}):
        #print("sendRequest " + format(SID, 'x').upper()+ " " + format(PID, 'x').upper())
        print("executeUDS ", service, parameter, self.uds_dict[service][parameter])

        SID = ""
        if service in self.uds_dict:
            SID = self.uds_dict[service]["ID"]
        else:
            info = "Could not find SID by Name (SID not implemented yet)."
            logger.info(info)
            return {"type": "error", "error": info}

        PID = ""
        if parameter in self.uds_dict[service]:
            PID = self.uds_dict[service][parameter]["ID"]
            if "parameters" in self.uds_dict[service][parameter]:
                dict_parameters = self.uds_dict[service][parameter]["parameters"]
                for dict_parameter in dict_parameters:
                    # print("parameter, para", parameter, dict_parameter)
                    dict_parameters[dict_parameter]["data"] = message[dict_parameter]
                    # print("dict_parameters", dict_parameters)
                    dict_parameters[dict_parameter] = self._interpretParameter(dict_parameters[dict_parameter])
                    # print("PID interpretation: {}".format(interpretation))
                    shift = int(dict_parameters[dict_parameter]["bit"], 16) - len(PID)*4
                    print("PID before", PID, dict_parameters[dict_parameter]["bit"], dict_parameters[dict_parameter]["interpretation"])
                    PID = format((int(PID, 16) << shift) + int(dict_parameters[dict_parameter]["interpretation"], 16), 'x')
                    print("PID after", PID)

        else:
            info = "Could not find PID by Name (PID not implemented yet)."
            logger.info(info)
            return {"type": "error", "error": info}

        logger.info("transmit (execute) SID, PID: {}, {}".format(SID, PID))
        self._transmitISOTP(SID, PID)
        response = self._receiveISOTP(SID, PID)
        logger.info("response: {}".format(response))
        return response

    def rawUDS(self, RxID, TxID, SID, PID):
        if isinstance(RxID, str):
            if RxID.startswith("0x"):
                RxID = int(RxID, 0)
            else:
                RxID = int(RxID, 16)
        if isinstance(TxID, str):
            if TxID.startswith("0x"):
                TxID = int(TxID, 0)
            else:
                TxID = int(TxID, 16)

        self.isotp_socket.bind('can0', rxid=RxID, txid=TxID)
        response = self.executeUDS(SID, PID)
        if response:
            logger.info("response: {}".format(response))

    # def getECUIDs(self):
    #     SID = self.getSIDbyName("VehicleInformation")
    #     # print("SID", SID)
    #     PID = self.getPIDbyName(SID, "ECUName")

    #     for id in reversed(range(0x000, 0x7F8)):
    #     # for id in range(0x7E0, 0x7F8):
    #         logger.info("send ECU-Name request on {}".format(id))
    #         self.isotp_socket.bind('can0', rxid=id+8, txid=id)
    #         response = self.executeUDS(SID, PID)
    #         if response:
    #             logger.info("response: {}".format(response))
