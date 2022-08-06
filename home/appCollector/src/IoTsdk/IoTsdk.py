import sys
from msrest.exceptions import HttpOperationError
from azure.iot.hub import IoTHubRegistryManager
from base64 import b64encode, b64decode
from hashlib import sha256
import time 
from urllib import parse
from hmac import HMAC
import logging
import os
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import MethodResponse
from typing import List, Dict

class IoTHub:
    def __init__(self, iotHubName: str, connectionString: str, deviceName: str):
        self.iotHubName = iotHubName
        self.connectionString = connectionString
        self.deviceName = deviceName
        self.sharedKey = self._getSharedKey()
        self.uri = f"{self.iotHubName}.azure-devices.net/devices/{self.deviceName}"

    def registerDevice(self):
        try:
            #RegistryManager
            iothub_registry_manager = IoTHubRegistryManager(self.connectionString)

            try:
                # CreateDevice - let IoT Hub assign keys
                logging.info(f"Registering device {self.deviceName}")
                self.device = iothub_registry_manager.create_device_with_sas(self.deviceName, "", "", "enabled")
            except HttpOperationError as ex:
                if ex.response.status_code == 409:
                    # 409 indicates a conflict. This happens because the device already exists.
                    logging.info:(f"Device {self.deviceName} allready registered")
                    self.device = iothub_registry_manager.get_device(self.deviceName)
                else:
                    logging.error(f"Cannot create device {self.deviceName}")
                    raise Exception(f"Cannot create device {self.deviceName}")
        except Exception as ex:
            print("Unexpected error {0}".format(ex))
        except KeyboardInterrupt:
            print("IoTHubRegistryManager sample stopped")


    def getDeviceConnectionString(self):
        return f"HostName={self.iotHubName}.azure-devices.net;DeviceId={self.deviceName};SharedAccessKey={self.device.authentication.symmetric_key.primary_key}"

    def _getSharedKey(self):
        tokens = self.connectionString.split(";")
        for token in tokens:
            subTokens = token.split("=", 1)
            if len(subTokens) == 2 and subTokens[0] == "SharedAccessKey":
                return subTokens[1]


    def generateSaSToken(self, policyName = "PythonServiceSDK", expiry = 3600):
         ttl = time() + expiry
         signKey = "%s\n%d" % ((parse.quote_plus(self.uri)), int(ttl))
         signature = b64encode(HMAC(b64decode(self.sharedKey), signKey.encode('utf-8'), sha256).digest())

         rawtoken = {
            'sr' : self.uri,
            'sig': signature,
            'se' : str(int(ttl))
         }

         if policyName is not None:
            rawtoken['skn'] = policyName

         return 'SharedAccessSignature ' + parse.urlencode(rawtoken)

class IoTdevice:
    @staticmethod
    def twinPatchHandler(objects: object, twinPatch: Dict):
        for obj in objects:
            handlerFunc = getattr(obj, "handleDesiredProperties", None)
            if callable(handlerFunc):
                obj.handleDesiredProperties(twinPatch)

    @staticmethod
    def checkMethodExistance(objects: object, objName: str, directMethodName: str):
        if objName in objects and \
         objects[objName] is not None and \
         getattr(objects[objName], directMethodName, None) and \
         callable(getattr(objects[objName], directMethodName, None)):
            return True
        return False

    @staticmethod
    def directMethodHandler(objects: object, methodRequest: object):
        logging.info(f"Invoking Direct Method Handler")
        if IoTdevice.checkMethodExistance(objects, "collectorObj", methodRequest.name):
            logging.info(f"Invoking Collector method {methodRequest.name} with payload {methodRequest.payload}")
            res, payload = getattr(objects["collectorObj"], methodRequest.name)(methodRequest.payload)
            status = 200 if res else 400
        elif IoTdevice.checkMethodExistance(objects, "iotObj", methodRequest.name):
            logging.info(f"Invoking IoT device method {methodRequest.name} with payload {methodRequest.payload}")
            res, payload = getattr(objects["iotObj"], methodRequest.name)(methodRequest.payload)
        else:
            logging.error(f"Unknown direct method {methodRequest.name}")
            payload = {"result": False, "data": "unknown method"}
            status = 400
        if "iotObj" in objects:
            methodResponse = MethodResponse.create_from_method_request(methodRequest, status, payload)
            asyncio.run(objects["iotObj"].sendDirectMethodResponce(methodResponse))

    def __init__(self, deviceConnectionString: str, collectorObj: object = None):
        self.deviceConnectionString = deviceConnectionString
        self.deviceClient = IoTHubDeviceClient.create_from_connection_string(self.deviceConnectionString)
        #set Twin Desired Properties Handling
        self._desiredProperties = {}
        self.deviceClient.on_twin_desired_properties_patch_received = lambda twinPatch: IoTdevice.twinPatchHandler([self, collectorObj], twinPatch)
        #set Direct Methods Handling
        self.deviceClient.on_method_request_received = lambda methodRequest: IoTdevice.directMethodHandler({ 'iotObj': self, 'collectorObj': collectorObj}, methodRequest)

    async def connect(self):
        await self.deviceClient.connect()

    async def disconnect(self):
        await self.deviceClient.shutdown()

    async def sendMessage(self, msg: str):
        await self.deviceClient.send_message(msg)

    def handleDesiredProperties(self, twinPatch: Dict):
        self._desiredProperties = dict(twinPatch)

    def getTwinPatchValue(self, key):
        if key in self._desiredProperties:
            return self._desiredProperties[key] 
        return None

    def sendReportedProperties(self, reportedProperties: List[Dict]):
        for reportedProperty in reportedProperties:
            asyncio.run(self.sendReportedProperty(reportedProperty))

    async def sendReportedProperty(self, reportedProperty: Dict):
        try:
            await self.deviceClient.patch_twin_reported_properties(reportedProperty)
        except KeyboardInterrupt:
            logging.error("IoT Hub Device Twin device sample stopped")
        finally:
            logging.error("Shutting down IoT Hub Client")
            self.disconnect


    async def sendDirectMethodResponce(self, methodResponse: object):
        await self.deviceClient.send_method_response(methodResponse)
