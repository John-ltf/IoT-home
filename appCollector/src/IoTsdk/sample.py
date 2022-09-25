import argparse
import logging
import sys
import time
import asyncio
from IoTsdk import IoTHub, IoTdevice

async def sendToDevice(deviceConnectionString):
    device = IoTdevice(deviceConnectionString)
    await device.connect()
    await device.sendMessage("ping")
    await device.disconnect()

async def patchDevice(deviceConnectionString):
    device = IoTdevice(deviceConnectionString)
    await device.connect()
    reported_patch = {"connectivity": "cellular"}
    await device.sendReportedProperty(reported_patch)
    await device.disconnect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MQTT Producer')
    parser.add_argument('-d', '--debug',
                        help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=logging.INFO,
    )
    parser.add_argument('-v', '--verbose',
                        help="Be verbose",
                        action="store_const", dest="loglevel", const=logging.INFO,
    )
    parser.add_argument('--iot',
                        type=str,
                        nargs='?',
                        help='IoT Hub Name',
                        required=True)
    parser.add_argument('--device', 
                        type=str,
                        nargs='?',
                        help='Device Name',
                        required=True)
    parser.add_argument('--mac',
                        type=str,
                        nargs='?',
                        help='Device MAC address',
                        required=True)
    parser.add_argument('--connectionString', 
                        type=str,
                        nargs='?',
                        help='Azure IoT Hub connection String',
                        required=True)
    args =  parser.parse_args()

    logging.basicConfig(format="%(asctime)s: %(levelname)s - %(message)s", level=args.loglevel)
    
    iot = IoTHub(iotHubName = args.iot, deviceName=args.device, deviceMac=args.mac, connectionString=args.connectionString)
    iot.registerDevice()

    #sas = iot.generateSaSToken()
    #logging.info(sas)
    deviceConnectionString = iot.getDeviceConnectionString()
    #logging.info(deviceConnectionString)
    
    #asyncio.run(sendToDevice(deviceConnectionString))

    device = asyncio.run(patchDevice(deviceConnectionString))


    sys.exit(0)
