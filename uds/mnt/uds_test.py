import json
import logging
import time
import os,sys

import _uds_helper


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

uds_helper = _uds_helper.UDSHelper()

# SIDstr = "PowertrainDiagnosticData"
#SIDstr = "VehicleInformation"
SIDstr = "ReadDataByIdentifier"
# PIDstr = "EngineRPM"
#PIDstr = "ECUName"
PIDstr = "ReadOdometerValueFromBus"

SID = uds_helper.getSIDbyName(SIDstr)
# print("SID", SID)
PID = uds_helper.getPIDbyName(SID, PIDstr)
# print("PID", PID)
RxID = uds_helper.getRxIDbyName(SID, PIDstr)
TxID = uds_helper.getTxIDbyName(SID, PIDstr)

uds_helper.connectISOTP(RxID, TxID)
uds_helper.executeUDS(SID, PID)
#uds_helper.getECUIDs()