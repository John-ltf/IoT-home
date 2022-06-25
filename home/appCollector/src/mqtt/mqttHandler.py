import paho.mqtt.client as mqtt
from abc import ABCMeta, abstractmethod
import logging

def on_connect(mqttc, obj, flags, rc):
  if rc == 0:
    logging.info(f'Client {mqttc._client_id.decode("utf-8")} has been succesfully connected to MQTT {mqttc._host}:{mqttc._port}')
  else:
    logging.error(f'Client {mqttc._client_id.decode("utf-8")} has been succesfully connected to MQTT {mqttc._host}:{mqttc._port}')

def on_message(mqttc, obj, msg):
  logging.info(f'[{msg.topic}]:[{msg.qos}]:[{msg.payload.decode("utf-8")}]')

def on_publish(mqttc, obj, mid):
  logging.debug(f'Message publish with ID:{mid}')
  pass

def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.info(f'Subscribed on topic with mid:{mid} and QOS:[{granted_qos}]')

def on_log(mqttc, obj, level, string):
  logging.info(string)


class mqttClient:
    __metaclass__ = ABCMeta

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

      self._mqttc.connect(self._mqttHost, self._port, self._keepalive)

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
