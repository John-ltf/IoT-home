from .collectorInterface import collectorI
from lywsd03mmc import Lywsd03mmcClient
import json
from datetime import datetime
import logging
import time
from collections import defaultdict
from bluepy.btle import Scanner, Peripheral, DefaultDelegate, ADDR_TYPE_RANDOM, BTLEException
from bluetoothExclusiveAccess import bluetoothExclusiveAccess
from typing import List, Dict
from enum import Enum

class measurementStatus(Enum):
    NO_STATUS = 1
    PUBLISHABLE_DATA = 2
    SAME_DATA = 3
    NEW_MEASUREMENT = 4

class collectorMIBFS_delegator(DefaultDelegate):
    metricsStatusList = ["PUBLISH", "SKIP_PUBLISH", "NEW_MEASUREMENT"]
    def __init__(self, mac: str):
        self._mac = mac
        self._data = { "impedance": "", "unitCode": "", "weight": "", "impedanceValue": "", "unit": "" }
        self._publishData = self._data.copy()
        self._collectSuccess = False
        self.lastPublish = ""
        self.metricsStatus = measurementStatus.NO_STATUS

    def getMeasurementStatus(self):
        return self.metricsStatus

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if self._mac and isNewData:
            if dev.addr.upper() == self._mac:
                self.extractReceivedData(dev)
                self.extractScaleData()

    def extractReceivedData(self, dev):
        self.data = {}
        for (idn, descriptor, data) in dev.getScanData():
            self.data[idn] = { "descriptor": descriptor, "data": data}

    def extractDataXiaomiV2Scale(self):
        data = bytes.fromhex(self.data[22]['data'])
        self._data['stabilized'] = (data[3] & (1<<5))
        self._data['impedance']  = (data[3] & (1<<1))
        self._data['impedanceValue'] = 0
        if self._data['impedance']:
            self._data['impedanceValue'] = int.from_bytes(data[11:13], byteorder='little')

        self._data['unitCode'] = data[2]
        if (self._data['unitCode'] & (1<<4)) != 0:
            self._data['unit'] = "jin"
        elif (self._data['unitCode'] & (1<<2)) != 0:
            self._data['unit'] = "lbs"
        elif (self._data['unitCode'] & (1<<1)) != 0:
            self._data['unit'] = "kg"
        else:
            self._data['unit'] = "unknown"

        self._data['weight'] = int.from_bytes(data[13:15], byteorder='little') / 100
        if self._data['unit'] == "kg":
            self._data['weight'] /= 2

        logging.info(f"{self._data['stabilized']} {self._data['impedance']} {self._data['unitCode']} {self._data['weight']} {self._data['impedanceValue']} {self._data['unit']}")
        if (self._data['stabilized'] and self._data['impedance']):
            if self.lastPublish != f"{self._data['weight']}-{self._data['impedanceValue']}":
                self.lastPublish = f"{self._data['weight']}-{self._data['impedanceValue']}"
                logging.info("Publishable new metrics from MIBFS")
                self._publishData = self._data.copy()
                self._collectSuccess = True
                self.metricsStatus = measurementStatus.PUBLISHABLE_DATA
            else:
                logging.info("Same metrics from MIBFS, skip publishing message")
                self.metricsStatus = measurementStatus.SAME_DATA
        else:
            self.lastPublish = "" #new measurement, reset latest publish message
            self.metricsStatus = measurementStatus.NEW_MEASUREMENT


    def extractScaleData(self):
        if 22 in self.data and self.data[22]['data'].startswith('1b18'):
            logging.debug("Extract Xiaomi V2 Scale data")
            self.extractDataXiaomiV2Scale()
        else:
            logging.error(f"Unsupported device/data {self.data[22]['data']}")

  
    def getData(self) -> str:
        data = {
                "device": "MIBFS",
                "MAC": self._mac,
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "impedance" : str(self._publishData['impedance']),
                "unitCode" : str(self._publishData['unitCode']),
                "weight" : str(self._publishData['weight']),
                "impedanceValue" : str(self._publishData['impedanceValue']),
                "unit" : str(self._publishData['unit'])
                }
        return json.dumps(data)

    def getPureData(self) -> str:
        data = {
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "weight" : str(self._publishData['weight']),
                "impedanceValue" : str(self._publishData['impedanceValue']),
                }
        return json.dumps(data)

    def getPropertyData(self) -> List[Dict]:
        data = list()
        data.append({ "device": "MIBFS" })
        data.append({ "MAC": self._mac })
        data.append({ "impedance" : str(self._publishData['impedance']) })
        data.append({ "unitCode" : str(self._publishData['unitCode']) })
        data.append({ "unit" : str(self._publishData['unit']) })
        return data

    def dataCollected(self):
        return self._collectSuccess

    def resetDataCollected(self):
        self._collectSuccess = False


class collectorMIBFS(collectorI):
    def __init__(self, mac: str):
        self._mac = mac
        self._id = f"MIBFS_{mac.replace(':','_')}"
        self.collectorObject = collectorMIBFS_delegator(self._mac)
        self.lastPropertyData = ""
        self.exclusive = bluetoothExclusiveAccess(appId = self.getID())

    def dataCollected(self):
        return self._collectSuccess

    def getID(self):
        return self._id

    def collectData(self):
        self.exclusive.acquire()
        self._collectData()
        self.exclusive.release()

    def retrieveData(self,*argv) -> tuple:
        #Find call timeour or set default 
        timeout = 60
        if argv and type(argv[0]) is dict:
            if 'timeout' in argv[0]:
                timeout = int(argv[0]['timeout']) - 10

        ttl = time.time()+timeout
        lockObject = bluetoothExclusiveAccess(appId = f"{self.getID()} - retrieve method")
        #repeat till timeout of get data
        while ttl >= time.time():
            lockObject.acquire()
            self._collectData()
            lockObject.release()
            
            if self.dataCollected():
                return True, self.getPureData()
            time.sleep(1)

        if self.collectorObject.getMeasurementStatus() == measurementStatus.SAME_DATA:
            return True, { 'message': 'measurement allready has been published' }
        return False, { 'message': 'measurement cannot be retrieved' }

    def _collectData(self):
        self._collectSuccess = False
        self.collectorObject.resetDataCollected()
        scanner = Scanner().withDelegate(self.collectorObject)
        try:
            scanner.start()
            scanner.process(10)
            scanner.stop()
        except:
            logging.debug(f"Failed to connect/get metrics from Xiaomi Scale device")
        self._collectSuccess = self.collectorObject.dataCollected()

    def getData(self) -> str:
        if self.dataCollected():
            return self.collectorObject.getData()

    def getPureData(self) -> str:
        if self.dataCollected():
            return self.collectorObject.getPureData()
        return json.dumps(data)

    def getPropertyData(self) -> List[Dict]:
        if self.dataCollected():
            data = self.collectorObject.getPropertyData()

            newPropertyData = ','.join(json.dumps(d) for d in data)
            if newPropertyData != self.lastPropertyData:
                self.lastPropertyData = newPropertyData
                return data
        return list()

    def handleDesiredProperties(self, twinPatch: Dict):
        pass
