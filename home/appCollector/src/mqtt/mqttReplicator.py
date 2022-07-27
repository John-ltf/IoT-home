import argparse
import logging
import sys
import time
from mqttHandler import mqttConsumer, mqttProducerSecured

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MQTT Producer')
    parser.add_argument('-d', '--debug',
                        help="Print lots of debugging statements",
                        action="store_const", dest="loglevel", const=logging.DEBUG,
                        default=logging.WARNING,
    )
    parser.add_argument('-v', '--verbose',
                        help="Be verbose",
                        action="store_const", dest="loglevel", const=logging.INFO,
    )
    parser.add_argument('--id', 
                        type=str,
                        nargs='?',
                        default="replicator",
                        help='Client ID')
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
    parser.add_argument('--iotHubName',
                        type=str,
                        nargs='?',
                        default="iot-hub-ltf",
                        help='IoT Hub Name')
    parser.add_argument('--deviceId',
                        type=str,
                        nargs='?',
                        default="MosquittoJohn",
                        help='IoT Hub Device Id')
    parser.add_argument('--mqttAzurePort',
                        type=int,
                        nargs='?',
                        default=8883,
                        help='MQTT Azure port')
    parser.add_argument('--sas',
                        type=str,
                        nargs='?',
                        help='sas token')
    parser.add_argument('--certFile',
                        type=str,
                        nargs='?',
                        default="Baltimore.pem",
                        help='Root Cert File')
    parser.add_argument('--topic',
                        type=str,
                        nargs='?',
                        default="testTopic",
                        help='Topic Name')
    args =  parser.parse_args()

    logging.basicConfig(format="%(asctime)s: %(levelname)s - %(message)s", level=args.loglevel)

    mqttc = mqttConsumer(ID=args.id, mqttHost=args.mqttHost, mqttPort=args.mqttPort)
    mqttc.run_subscribe(args.topic)

    mqttr = mqttProducerSecured(iotHubName=args.iotHubName, deviceId=args.deviceId, sasToken=args.sas, mqttPort=args.mqttAzurePort, certFile=args.certFile)
    mqttr.run_replicate(args.topic)

    mqttc.getThread().join()
    mqttr.getThread().join()
    
    sys.exit(0)
