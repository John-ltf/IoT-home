import paho.mqtt.client as mqtt
from abc import ABCMeta, abstractmethod
import logging
import time
import sys
import ssl
import threading
import queue

def on_connect(mqttc, obj, flags, rc):
  if rc == 0:
    logging.info(f'Client {mqttc._client_id.decode("utf-8")} has been succesfully connected to MQTT {mqttc._host}:{mqttc._port}')
  else:
    logging.error(f'Client {mqttc._client_id.decode("utf-8")} has not been connected to MQTT {mqttc._host}:{mqttc._port}')

def on_message(mqttc, obj, msg):
  logging.info(f'[{msg.topic}]:[{msg.qos}]:[{msg.payload.decode("utf-8")}]')
  if 'messages' in globals():
      logging.debug(f"Add in Queue: {msg.payload.decode('utf-8')}")
      messages.put(msg.payload.decode("utf-8"))

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
          self.consumerThread = threading.Thread(target=self.subscribe, args=[topic])
          self.consumerThread.start()
      except threading.Thread:
          cleanup_stop_thread()
          sys.exit()


  def getThread(self):
      return self.consumerThread


class mqttClientSecure():
    def __init__(self, iotHubName: str, deviceId: str, sasToken: str,  mqttPort: int, certFile: str, keepalive: int = 60, qos: int = 1):

      self.iotHubName = iotHubName
      self.iotHostName = f"{self.iotHubName}.azure-devices.net"
      self.deviceId = deviceId
      self.sasToken = sasToken
      self.username = f"{self.iotHubName}.azure-devices.net/{self.deviceId}/?api-version=2021-04-12"
      self.port = mqttPort
      self.certFile =  certFile
      self._keepalive = keepalive
      self._qos = qos

      self._mqttc = mqtt.Client(client_id=self.deviceId, protocol=mqtt.MQTTv311)
      self._mqttc.on_message = on_message
      self._mqttc.on_connect = on_connect
      self._mqttc.on_publish = on_publish
      self._mqttc.on_subscribe = on_subscribe
      self._mqttc.username_pw_set(username=self.username, password=self.sasToken)
      self._mqttc.tls_set(ca_certs=self.certFile, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
      self._mqttc.tls_insecure_set(False)
      self._mqttc.connect(self.iotHostName, port=self.port)


class mqttProducerSecured(mqttClientSecure):
    def __init__(self, iotHubName: str, deviceId: str, sasToken: str, mqttPort: int, certFile: str, keepalive: int = 60, qos: int = 1):
      mqttClientSecure.__init__(self, iotHubName, deviceId, sasToken, mqttPort, certFile, keepalive, qos)
      self._mqttc.loop_start()

    def replicate(self, topic: str):
      topic = f"devices/{self.deviceId}/messages/events/"
      while True:
        message = messages.get()
        logging.debug(f"Replicating {message}")
        #message.task_done()
        self.send(topic, message)

    def send(self, topic: str, msg: str):
       infot = self._mqttc.publish(topic, msg, self._qos)
       infot.wait_for_publish()
#       self._mqttc.publish(topic, msg, self._qos)
#       self._mqttc.loop_forever()

    def run_replicate(self, topic: str):
       logging.debug("starting thread for replicating messages")
       try:
           self.replicateThread = threading.Thread(target=self.replicate, args=[topic])
           self.replicateThread.start()
       except threading.Thread:
           cleanup_stop_thread()
           sys.exit()

    def getThread(self):
      return self.replicateThread

