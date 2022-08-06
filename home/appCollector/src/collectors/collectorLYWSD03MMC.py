from .collectorInterface import collectorI
from lywsd03mmc import Lywsd03mmcClient
import json
from datetime import datetime
import logging
import subprocess
from typing import List, Dict
from bluetoothExclusiveAccess import bluetoothExclusiveAccess

global timeout
timeout = 30

class collectorLYWSD03MMC(collectorI):
    def __init__(self, mac: str):
        self._mac = mac
        self._data = { "temperature": "", "humidity": "", "battery": "", "units": "" }
        self._id = f"LYWSD03MMC_{mac.replace(':','_')}"
        self.lastPropertyData = ""
        self.exclusive = bluetoothExclusiveAccess(appId = self.getID())

    def dataCollected(self):
        return self._collectSuccess

    def getID(self):
        return self._id

    def getOutput(self, output):
        count = 0
        for line in output.decode("utf-8").split("\n"):
            if line:
                logging.debug("Subproccess:" + line)
            if "failed" in line or "Failed" in line:
                self._collectSuccess = False
                return
            else:
                if "Temperature" in line:
                    self._data['temperature'] = line.split(":")[1][0:-2]
                    self._data['units'] = line.split(":")[1][-1:]
                    count += 1
                elif "Humidity" in line:
                    self._data['humidity'] = line.split(":")[1][0:-1]
                    count += 1
                elif "Battery" in line:
                    self._data['battery'] = line.split(":")[1][0:-1]
                    count += 1
        if count == 3:            
            self._collectSuccess = True

    def collectData(self) -> None:
        self.exclusive.acquire()
        self._collectData()
        self.exclusive.release()

    def retrieveData(self,*argv) -> tuple:
        lockObject = bluetoothExclusiveAccess(appId = f"{self.getID()} - retrieve method")
        lockObject.acquire()
        self._collectData()
        lockObject.release()

        if self.dataCollected():
            return True, self.getPureData()
        return False, None

    def _collectData(self):
        self._collectSuccess = False
        try:
            output = subprocess.check_output(f"lywsd03mmc {self._mac}", stderr=subprocess.STDOUT, shell=True, timeout=timeout)
            self.getOutput(output)
        except subprocess.CalledProcessError as e:
            logging.error(f"command '{e.cmd}' return with error (code {e.returncode}): {e.output}")
            self._collectSuccess = False
        except subprocess.TimeoutExpired: 
            logging.error("Retrieving data gets to long.. Killing subprocess...")
            subprocess.run(["pkill", "lywsd03mmc"])
            self._collectSuccess = False
  
    def getData(self) -> str:
        data = {
                "device": "LYWSD03MMC",
                "MAC": self._mac,
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "temperature" : str(self._data['temperature']),
                "humidity" : str(self._data['humidity']),
                "battery" : str(self._data['battery']),
                "units" : str(self._data['units'])
                }
        return json.dumps(data)

    def getPureData(self) -> str:
        data = {
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "temperature" : str(self._data['temperature']),
                "humidity" : str(self._data['humidity'])
                }
        return json.dumps(data)

    def getPropertyData(self) -> List[Dict]:
        data = list()
        data.append({ "device": "LYWSD03MMC" })
        data.append({ "MAC": self._mac })
        data.append({ "battery" : str(self._data['battery']) })
        data.append({ "units" : str(self._data['units']) })

        newPropertyData = ','.join(json.dumps(d) for d in data)
        if newPropertyData != self.lastPropertyData:
            self.lastPropertyData = newPropertyData
            return data
        return list()

    def handleDesiredProperties(self, twinPatch: Dict):
        pass
