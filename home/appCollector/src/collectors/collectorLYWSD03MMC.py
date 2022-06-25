from .collectorInterface import collectorI
from lywsd03mmc import Lywsd03mmcClient
import json
import traceback
from datetime import datetime
import threading
import ctypes
import logging
import time
import subprocess

global WAITING_TIME
WAITING_TIME = 30

class collectorLYWSD03MMC(collectorI):
    def __init__(self, mac: str):
        self._mac = mac
        self.__init_Lywsd03mmcClient()
        self._data = ""
        self._id = f"LYWSD03MMC_{mac.replace(':','_')}"
        self._lock = threading.Lock()

    def __init_Lywsd03mmcClient(self):
        logging.info("Initializing Lywsd03mmcClient")
        self._client = Lywsd03mmcClient(self._mac)

    def __runCollectData(self):
        self._collectDataThreadID = threading.current_thread().ident
        logging.debug(f"Run collect Data thread ID is: {self._collectDataThreadID}")
        try:
          self._collectSuccess = True
          self._data = self._client.data
        except Exception:
          #logging.error(traceback.format_exc())
          logging.error("Cannot retrieve metrics from LYWSD03MMC")
          self._collectSuccess = False

    def collectData(self):
        with self._lock:
          thread = threading.Thread(target=self.__runCollectData)
          thread.start()
          thread.join(WAITING_TIME)
          if thread.is_alive():
            logging.info("Collecting data from LYWSD03MMC takes too long. Stopping the thread.")
            self.__raise_exception(thread)
            logging.debug("Calling join to finilize threaad")
            thread.join()
            logging.debug("Thread terminated")
            self.__init_Lywsd03mmcClient()
            self._collectSuccess = False
  
    def __raise_exception(self, thread):
        thread_id = self._collectDataThreadID
        logging.warning(f'Trying to kill thread {thread_id}')
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id),
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            logging.error('Exception raise failure')
        time.sleep(2)
        if thread.is_alive():
            logging.debug("Highlander thread!")
            logging.debug("Killing  bluepy-helper proccess")
            subprocess.run(["pkill", "bluepy-helper"])

    def getData(self) -> str:
        data = {
                "device": "LYWSD03MMC",
                "MAC": self._mac,
                "time": datetime.utcnow().strftime("%Y-%m-%d:%H:%M:%S"),
                "temperature" : str(self._data.temperature),
                "humidity" : str(self._data.humidity),
                "battery" : str(self._data.battery),
                "units" : str(self._client.units)
                }
        return json.dumps(data)

    def dataCollected(self):
        return self._collectSuccess

    def getID(self):
        return self._id
