from .collectorInterface import collectorI
from lywsd03mmc import Lywsd03mmcClient
import json
from datetime import datetime, date
import logging
import time
from collections import defaultdict
from bluepy.btle import Scanner, Peripheral, DefaultDelegate, ADDR_TYPE_RANDOM, BTLEException
from bluetoothExclusiveAccess import bluetoothExclusiveAccess
from typing import List, Dict
from enum import Enum

import os
import sys
import xiaomi_mi_scale
sys.path.insert(2, os.path.dirname(xiaomi_mi_scale.__file__))
import body_metrics

class measurementStatus(Enum):
    NO_STATUS = 1
    PUBLISHABLE_DATA = 2
    SAME_DATA = 3
    NEW_MEASUREMENT = 4

class collectorMIBFS_delegator(DefaultDelegate):
    metricsStatusList = ["PUBLISH", "SKIP_PUBLISH", "NEW_MEASUREMENT"]
    def __init__(self, mac: str):
        self._mac = mac
        self._data = { "impedance": "", "unitCode": "", "weight": "", "impedanceValue": "", "unit_weight": "" }
        self._publishData = self._data.copy()
        self._collectSuccess = False
        self.lastPublish = ""
        self.metricsStatus = measurementStatus.NO_STATUS
        self.ttl = -1

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
            self._data['unit_weight'] = "jin"
        elif (self._data['unitCode'] & (1<<2)) != 0:
            self._data['unit_weight'] = "lbs"
        elif (self._data['unitCode'] & (1<<1)) != 0:
            self._data['unit_weight'] = "kg"
        else:
            self._data['unit_weight'] = "unknown"

        self._data['weight'] = int.from_bytes(data[13:15], byteorder='little') / 100
        if self._data['unit_weight'] == "kg":
            self._data['weight'] /= 2

        logging.info(f"{self._data['stabilized']} {self._data['impedance']} {self._data['unitCode']} {self._data['weight']} {self._data['impedanceValue']} {self._data['unit_weight']}")
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

  
    def calcAge(self, userProfile):
        today = date.today()
        return today.year - userProfile["year"] - ((today.month, today.day) < (userProfile["month"], userProfile["day"]))
	
    def getDerivedValues(self, userProfile):
        data = {}
        if userProfile["ready"] == True:
            bm = body_metrics.bodyMetrics(float(self._publishData['weight']), userProfile["height"], self.calcAge(userProfile), userProfile["gender"], int(self._publishData['impedanceValue']))
            data["bodyFat"]			= bm.getFatPercentage()
            data["water"]			= bm.getWaterPercentage()
            data["protein"]			= bm.getProteinPercentage()
            data["bodyAge"]			= bm.getMetabolicAge()
            data["boneMass"]		        = bm.getBoneMass()
            data["muscle"]			= bm.getMuscleMass()
            data["visceralFat"]	        	= bm.getVisceralFat()
            data["bmi"]				= bm.getBMI()
            data["basalMetabolism"]	        = bm.getBMR()
            data["leanBodyMass"]        	= bm.getLBMCoefficient()
        return data
	
    def getData(self, userProfile) -> str:
        data = {
                "DeviceType": "MIBFS",
                "MAC": self._mac,
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "impedance" : str(self._publishData['impedance']),
                "unitCode" : str(self._publishData['unitCode']),
                "weight" : str(self._publishData['weight']),
                "impedanceValue" : str(self._publishData['impedanceValue']),
                "unit_weight" : str(self._publishData['unit_weight']),
                "ttl": str(self.ttl)
                }
        if self._publishData['impedance']:
            data.update(self.getDerivedValues(userProfile))
            data["unit_bodyFat"]		= "percentage"
            data["unit_water"]			="percentage"
            data["unit_protein"]		="percentage"
            data["unit_bodyAge"]		="years"
            data["unit_boneMass"]		="kg"
            data["unit_muscle"]			="kg"
            data["unit_visceralFat"]    	="unknown"
            data["unit_bmi"]			="bmi"
            data["unit_basalMetabolism"]        ="kcal"
            data["leanBodyMass"]		="kg"
        return json.dumps(data)

    def getPureData(self, userProfile) -> str:
        data = {
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "weight" : str(self._publishData['weight']),
                "impedanceValue" : str(self._publishData['impedanceValue']),
                "ttl": str(self.ttl)
                }
        if self._publishData['impedance']:
            data.update(self.getDerivedValues(userProfile))
        return json.dumps(data)

    def set_ttl(self, ttl : str):
        self.ttl = ttl;

    def getPropertyData(self) -> List[Dict]:
        data = list()
        data.append({ "DeviceType": "MIBFS" })
        data.append({ "MAC": self._mac })
        data.append({ "impedance" : str(self._publishData['impedance']) })
        data.append({ "unitCode" : str(self._publishData['unitCode']) })
        data.append({ "unit_weight" : str(self._publishData['unit_weight']) })
        if self._publishData['impedance']:
            data.append({ "unit_bodyFat" : "percentage" })
            data.append({ "unit_water" : "percentage" })
            data.append({ "unit_protein" : "percentage" })
            data.append({ "unit_bodyAge" : "years" })
            data.append({ "unit_boneMass" : "kg" })
            data.append({ "unit_muscle" : "kg" })
            data.append({ "unit_visceralFat" : "unknown" })
            data.append({ "unit_bmi" : "bmi" })
            data.append({ "unit_basalMetabolism" : "kcal" })
            data.append({ "leanBodyMass" : "kg" })
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
        self.ttl = -1
        self.userProfile = { "gender": "", "height": "", "year": "", "month": "", "day" : "", "ready" : False }

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
            return self.collectorObject.getData(self.userProfile)

    def getPureData(self) -> str:
        if self.dataCollected():
            return self.collectorObject.getPureData(self.userProfile)
        return json.dumps(data)

    def setRetentionPolicy(self, ttl : str):
        self.ttl = ttl;
        self.collectorObject.set_ttl(self.ttl)
		
    def getPropertyData(self) -> List[Dict]:
        if self.dataCollected():
            data = self.collectorObject.getPropertyData()

            newPropertyData = ','.join(json.dumps(d) for d in data)
            if newPropertyData != self.lastPropertyData:
                self.lastPropertyData = newPropertyData
                return data
        return list()

    def handleDesiredProperties(self, twinPatch: Dict):
        props = 0
        if "Gender" in twinPatch:
            self.userProfile["gender"] = twinPatch["Gender"]
            props +=1
        if "Height" in twinPatch:
            try:
                self.userProfile["height"] = int(twinPatch["Height"])
                props +=1
            except ValueError:
                logging.error('height is not an integer')
        if "Year" in twinPatch:
            try:
                self.userProfile["year"] = int(twinPatch["Year"])
                props +=1
            except ValueError:
                logging.error('year is not an integer')
        if "Month" in twinPatch:
            try:
                self.userProfile["month"] = int(twinPatch["Month"])
                props +=1
            except ValueError:
                 logging.error('month is not an integer')
        if "Day" in twinPatch:
            try:
                self.userProfile["day"] = int(twinPatch["Day"])
                props +=1
            except ValueError:
                 logging.error('month is not an integer')
        if props == 5:
            self.userProfile["ready"] = True
