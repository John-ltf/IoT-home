import argparse
import logging
import json
import importlib
import time
from mqtt.mqttHandler import mqttProducer 
import asyncio
import sys
sys.path.insert(2, './IoTsdk')
from IoTsdk import IoTHub, IoTdevice

def collect(interval: int, collectorClass: str, deviceName: str,  mac: str, userId: str, mqttEnabled: bool, mqttHost: str, mqttPort: int, IoTHubEnabled: bool, iotHubName: str, connectionString: str):
    logging.info(f'Importing collectors.{collectorClass} module')
    collector_module = importlib.import_module(f'collectors.{collectorClass}')

    logging.info(f'Instantiating class {collectorClass} with args: mac ({mac})')
    class_ = getattr(collector_module, collectorClass)
    instance = class_(mac)

    if mqttEnabled:
        mqttTopic = deviceName
        logging.info('Connecting to MQTT')
        mqttc = mqttProducer(ID=instance.getID(), mqttHost=mqttHost, mqttPort=mqttPort)

    if IoTHubEnabled: 
        props = [{"TelemetryData": "True"}, {"Controller": "False"}]
        tags = {"User": userId, "NickName": ""}
        logging.info('Connecting to IoT Hub')
        iot = IoTHub(iotHubName = iotHubName, deviceName=deviceName, deviceMac=mac, tags=tags, props=props, connectionString=connectionString)
        logging.info('Register/Retrieve device')
        registered = iot.registerDevice()
        logging.info('Connect to device')
        device = IoTdevice(iot.getDeviceConnectionString(), instance)
        asyncio.run(device.connect())

        if registered:
            logging.info('Setting initial properties')
            device.sendReportedProperties([{ "AutoRegistered": "True"}])
 
    while(True):
        logging.debug(f'Collecting Data')
        instance.collectData()
        if instance.dataCollected():
          logging.info(instance.getData())
          if mqttEnabled:
              mqttc.send(mqttTopic, instance.getData())

          if IoTHubEnabled:
              instance.set_ttl(device.getRetentionPolicyData())
              asyncio.run(device.sendMessage(instance.getPureData()))
              device.sendReportedProperties(instance.getPropertyData())
        
        #if Iot enabled, check for interval update
        if IoTHubEnabled:
            intervalPatch = device.getInterval()
            if intervalPatch != -1 and intervalPatch != interval:
                interval = intervalPatch
        
        time.sleep(interval)

if __name__ == "__main__":
    DeviceClassMap = {}
    with open('classDeviceMap.json') as f:
        DeviceClassMap = data = json.load(f)

    parser = argparse.ArgumentParser(description='Data collector')
    parser.add_argument('-d', '--debug',
                        help="Print debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=logging.INFO,
    )
    parser.add_argument('-v', '--verbose',
                        help="Be verbose",
                        action="store_const", dest="loglevel", const=logging.INFO,
    )
    parser.add_argument('--device', 
                        type=str,
                        choices=list(DeviceClassMap.keys()),
                        help='Available Devices',
                        required=True)
    parser.add_argument('--deviceName',
                        type=str,
                        help='Your Device Name',
                        required=True)
    parser.add_argument('--mac', 
                        type=str,
                        help='Mac Address of Device',
                        required=True)
    parser.add_argument('--userId',
                        type=str,
                        help='The user Name/Id (Azure AD) ',
                        required=False)
    parser.add_argument('--interval', 
                        type=int,
                        nargs='?',
                        default=60,
                        help='Interval of collecting data (seconds)')
    parser.add_argument('--mqttHost',
                        type=str,
                        nargs='?',
                        help='MQTT host')
    parser.add_argument('--mqttPort',
                        type=int,
                        default=1883,
                        nargs='?',
                        help='MQTT port')
    parser.add_argument('--iot',
                        type=str,
                        nargs='?',
                        help='Azure IoT Hub Name (if telemetry is streamed directly tou cloud)')
    parser.add_argument('--connectionString',
                        type=str,
                        nargs='?',
                        help='Azure IoT Hub Connection String')
    args =  parser.parse_args()
    logging.basicConfig(format="%(asctime)s: %(levelname)s - %(message)s", level=args.loglevel)
    
    collect(args.interval,
            DeviceClassMap[args.device],
            args.deviceName,
            args.mac,
            args.userId,
            (args.mqttHost is not None),
            args.mqttHost,
            args.mqttPort,
            (args.iot is not None),
            args.iot,
            args.connectionString)
