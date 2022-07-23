import argparse
import logging
import json
import importlib
import time
from mqtt.mqttHandler import mqttProducer 

def collect(interval: int, collectorClass: str, mac: str, mqttHost: str, mqttPort: int, mqttTopic: str):
    logging.info(f'Importing collectors.{collectorClass} module')
    collector_module = importlib.import_module(f'collectors.{collectorClass}')

    logging.info(f'Instantiating class {collectorClass} with args: mac ({mac})')
    class_ = getattr(collector_module, collectorClass)
    instance = class_(mac)

    logging.info('Connecting to MQTT')
    mqttc = mqttProducer(ID=instance.getID(), mqttHost=mqttHost, mqttPort=mqttPort)

    while(True):
        logging.debug(f'Collecting Data')
        instance.collectData()
        if instance.dataCollected():
          logging.info(instance.getData())
          mqttc.send(mqttTopic, instance.getData())

        time.sleep(interval)

if __name__ == "__main__":
    DeviceClassMap = {}
    with open('classDeviceMap.json') as f:
        DeviceClassMap = data = json.load(f)

    parser = argparse.ArgumentParser(description='Data collector')
    parser.add_argument('-d', '--debug',
                        help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=logging.WARNING,
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
    parser.add_argument('--mac', 
                        type=str,
                        help='Mac Address of Device',
                        required=True)
    parser.add_argument('--interval', 
                        type=int,
                        nargs='?',
                        default=60,
                        help='Interval of collecting data (seconds)')
    parser.add_argument('--mqttHost',
                        type=str,
                        nargs='?',
                        default="127.0.0.1",
                        help='MQTT host')
    parser.add_argument('--mqttPort',
                        type=int,
                        nargs='?',
                        default=1883,
                        help='MQTT port')
    parser.add_argument('--topic',
                        type=str,
                        nargs='?',
                        default="telemetry",
                        help='Topic Name')
    args =  parser.parse_args()
    logging.basicConfig(format="%(asctime)s: %(levelname)s - %(message)s", level=args.loglevel)
    
    collect(args.interval,
            DeviceClassMap[args.device], 
            args.mac,
            args.mqttHost,
            args.mqttPort,
            args.topic)
