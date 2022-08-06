import argparse
import logging
import sys
import time
from mqttHandler import mqttConsumer, mqttReplicator

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
    parser.add_argument('--id', 
                        type=str,
                        nargs='?',
                        default="replicator",
                        help='Client ID',
                        required=True)
    parser.add_argument('--mqttHost', 
                        type=str,
                        nargs='?',
                        default="127.0.0.1",
                        help='MQTT host',
                        required=True)
    parser.add_argument('--mqttPort',
                        type=int,
                        nargs='?',
                        default=1883,
                        help='MQTT port',
                        required=True)
    parser.add_argument('--iotHubName',
                        type=str,
                        nargs='?',
                        default="iot-hub-ltf",
                        help='IoT Hub Name',
                        required=True)
    parser.add_argument('--connectionString',
                        type=str,
                        nargs='?',
                        help='Azure IoT Hub connection String',
                        required=True)
    parser.add_argument('--mqttAzurePort',
                        type=int,
                        nargs='?',
                        default=8883,
                        help='MQTT Azure port',
                        required=True)
    parser.add_argument('--certFile',
                        type=str,
                        nargs='?',
                        default="Baltimore.pem",
                        help='Root Cert File',
                        required=True)
    args =  parser.parse_args()

    logging.basicConfig(format="%(asctime)s: %(levelname)s - %(message)s", level=args.loglevel)

    mqttc = mqttConsumer(ID=args.id, mqttHost=args.mqttHost, mqttPort=args.mqttPort)
    mqttc.run_subscribe("#")

    replicator = mqttReplicator(iotHubName=args.iotHubName, connectionString=args.connectionString, mqttPort=args.mqttAzurePort, certFile=args.certFile)
    replicator.run_replicate()

    mqttc.getThread().join()
    replicator.getThread().join()
    
    sys.exit(0)
