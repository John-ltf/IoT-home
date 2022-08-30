import paho.mqtt.client as mqtt
from abc import ABCMeta, abstractmethod
import logging
import time
import sys
import ssl
import threading
import queue
import json

sys.path.insert(1, '../')
sys.path.insert(2, './IoTsdk')
from IoTsdk import IoTHub

def on_connect(mqttc, obj, flags, rc):
  if rc == 0:
    logging.info(f'Client {mqttc._client_id.decode("utf-8")} has been succesfully connected to MQTT {mqttc._host}:{mqttc._port}')
  else:
    logging.error(f'Client {mqttc._client_id.decode("utf-8")} has not been connected to MQTT {mqttc._host}:{mqttc._port}')

def on_message(mqttc, obj, msg):
  logging.info(f'[{msg.topic}]:[{msg.qos}]:[{msg.payload.decode("utf-8")}]')
  if 'messages' in globals():
      message = { 'topic': msg.topic, 'msg': msg.payload.decode('utf-8') }
      logging.debug(f"Add in Queue: {message}")
      messages.put(message)

def on_publish(mqttc, obj, mid):
  logging.debug(f'Message publish with ID:{mid}')
  pass

def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.info(f'Subscribed on topic with mid:{mid} and QOS:[{granted_qos}]')

def on_log(mqttc, obj, level, string):
  logging.info(string)


class mqttClient():
    def __init__(self, ID: str, mqttHost: str, mqttPort: int, keepalive: int = 60, qos: int = 2):
      self._ID = ID
      self._mqttHost = mqttHost
      self._port = mqttPort
      self._keepalive = keepalive
      self._qos = qos

      self._mqttc = mqtt.Client(self._ID)
      self._mqttc.on_message = on_message
      self._mqttc.on_connect = on_connect
      self._mqttc.on_publish = on_publish
      self._mqttc.on_subscribe = on_subscribe
      
      self.connectToMqtt()

    def connectToMqtt(self):
        connectionErrors = 0
        connected = True
        while True:
            try:
                self._mqttc.connect(self._mqttHost, self._port, self._keepalive)
            except Exception as e:
                logging.exception(e)
                connected = False
                connectionErrors += 1
                if connectionErrors == 5:
                    logging.error("Too many tries. Exiting..")
                    sys.exit(e.errno)
                time.sleep(10)
            if connected:
                break

class mqttProducer(mqttClient):
  def __init__(self, ID: str, mqttHost: str, mqttPort: int, keepalive: int = 60, qos: int = 2):
    mqttClient.__init__(self, ID, mqttHost, mqttPort, keepalive, qos)
    self._mqttc.loop_start()

  def send(self, topic: str, msg: str):
    infot = self._mqttc.publish(topic, msg, self._qos)
    infot.wait_for_publish()

class mqttConsumer(mqttClient):
  def __init__(self, ID: str, mqttHost: str, mqttPort: int, keepalive: int = 60, qos: int = 2):
    mqttClient.__init__(self, ID, mqttHost, mqttPort, keepalive, qos)

  def subscribe(self, topic: str):
    self._mqttc.subscribe(topic, self._qos)
    self._mqttc.loop_forever()

  def run_subscribe(self, topic: str):
      global messages
      messages = queue.Queue()
      logging.debug("starting thread for consuming messages")
      try:
          self.consumerThread = threading.Thread(target=self.subscribe, args=[topic], daemon = True)
          self.consumerThread.start()
      except threading.Thread:
          cleanup_stop_thread()
          sys.exit()


  def getThread(self):
      return self.consumerThread


class mqttClientSecure():
    def __init__(self, iotHubName: str, deviceId: str, connectionString: str, mqttPort: int, certFile: str, keepalive: int = 60, qos: int = 1):

      self.iotHubName = iotHubName
      self.iotHostName = f"{self.iotHubName}.azure-devices.net"
      self.deviceId = deviceId
      self.connectionString = connectionString
      self.username = f"{self.iotHubName}.azure-devices.net/{self.deviceId}/?api-version=2021-04-12"
      self.port = mqttPort
      self.certFile =  certFile
      self._keepalive = keepalive
      self._qos = qos
      self.topic = f"devices/{self.deviceId}/messages/events/"
      self._connect()

    def _connect(self):
      self.iot = IoTHub(iotHubName=self.iotHubName, deviceName=self.deviceId, connectionString=self.connectionString)
      self.iot.registerDevice()
      self.sasToken = self.iot.generateSaSToken()
      self._mqttc = mqtt.Client(client_id=self.deviceId, protocol=mqtt.MQTTv311)
      self._mqttc.on_message = on_message
      self._mqttc.on_connect = on_connect
      self._mqttc.on_publish = on_publish
      self._mqttc.on_subscribe = on_subscribe
      self._mqttc.username_pw_set(username=self.username, password=self.sasToken)
      self._mqttc.tls_set(ca_certs=self.certFile, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
      self._mqttc.tls_insecure_set(False)
      self._mqttc.connect(self.iotHostName, port=self.port)

    def _disconnect(self):
        self._mqttc.disconnect() 
        self._mqttc.loop_stop() 

class mqttProducerSecured(mqttClientSecure):
    def __init__(self, iotHubName: str, deviceId: str, connectionString: str,  mqttPort: int, certFile: str, keepalive: int = 60, qos: int = 1):
      mqttClientSecure.__init__(self, iotHubName, deviceId, connectionString, mqttPort, certFile, keepalive, qos)
      self._startProducer()

    def _startProducer(self):
        self._mqttc.loop_start()
    
    def send(self, msg: str, firstTry = True):
        try:
            infot = self._mqttc.publish(self.topic, msg, self._qos)
            infot.wait_for_publish()
        except:
            if firstTry:
                logging.debug("Renewing SaS token and reconnectingt to IoT Hub")
                self._disconnect()
                self._connect()
                self._startProducer()
                self.send(msg, False)
            else:
                logging.error("Cannot send message to IoT Hub")
                raise Exception("Cannot send message to IoT Hub")



class mqttReplicator:
    def __init__(self, iotHubName: str, mqttPort: int, certFile: str, connectionString: str):
        self.iotHubName = iotHubName
        self.mqttPort = mqttPort
        self.certFile = certFile
        self.connectionString = connectionString
        self.producers = {}

    def replicate(self):
        while True:
            element = messages.get()
            topic = element['topic']
            message = element['msg']
            logging.debug(f"Replicating {message} on device {topic}")
            if topic not in self.producers:
                self.producers[topic] = mqttProducerSecured(iotHubName=self.iotHubName, deviceId=topic, connectionString=self.connectionString, mqttPort=self.mqttPort, certFile=self.certFile)
            instance = self.producers[topic]
            instance.send(message)

    def run_replicate(self):
       logging.debug("starting thread for replicating messages")
       try:
           self.replicateThread = threading.Thread(target=self.replicate, args=[], daemon = True)
           self.replicateThread.start()
       except threading.Thread:
           cleanup_stop_thread()
           sys.exit()

    def getThread(self):
      return self.replicateThread



