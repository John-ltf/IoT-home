import argparse
import logging
import sys
import time
from mqttHandler import mqttProducer

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
                        default="producer",
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
    parser.add_argument('--topic',
                        type=str,
                        nargs='?',
                        default="testTopic",
                        help='Topic Name')
    args =  parser.parse_args()

    logging.basicConfig(format="%(asctime)s: %(levelname)s - %(message)s", level=args.loglevel)
    
    mqttc = mqttProducer(ID=args.id, mqttHost=args.mqttHost, mqttPort=args.mqttPort)

    mqttc.send(args.topic, "hello")
    mqttc.send(args.topic, "I am the publisher")
    mqttc.send(args.topic, "Good bye")

    time.sleep(4)
    sys.exit(0)
