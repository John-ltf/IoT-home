# IoT Home On Cloud

A set of tools, code, applications and CI/CD mechanisms to leverage IoT home devices via Azure Cloud.

The repo consists of python collector application, a Dockerfile and ansible playbooks for the installation of processes/devices on home infrastructure. The collector application retrieves data from home IoT devices and uploads them to Azure IoT Hub using the azure-iot-hub and azure-iot-device SDKs. However, there are also optionally installed a local mqtt broker and a python proccess that replicates the messages from local MQTT to Azure IoT Hub.

The repo currently supports the Xiaomi Mijia LYWSD03MMC thermometer and Xiaomi Mi Scale V2 (MIBFS) devices. However it is easy to extend it and add more devices and controls.

# Installation

The directory includes
1. an Ansible playbook for the installation of processes and devices on home infrastructure
2. and python code to retrieve data from Xiaomi Mijia BLE Sensor and Xiaomi Mi Scale V2

## Prerequisites

Python3 and Ansible should be pre-installed to deploy the collector/controller applications and an MQTT on the home side.

```
apt install python3.8, ansible
```

The below Ansible galaxy collection will be also needed.

```
ansible-galaxy collection install community.docker
ansible-galaxy collection install ansible.posix
```

To install the applications, run:

```
ansible-playbook -i hosts.yaml run_apps.yaml
```

You may need:
1. To skip the installation of docker by adding `-t runCollectors,runMQTT,IoTsync`
2. To ovveride the pre-configured python 2.x by adding `-e 'ansible_python_interpreter=/usr/bin/python3`
3. To give as argument the root password by adding `--extra-vars "ansible_sudo_pass=<PASSWORD>"`
4. To configure the Azure IoT Hub name by adding `IoTHubName='<IoTHubName>'`
5. To configure the Azure IoT Hub connection string by adding `connectionString='<connectionString>'`


You may also configure the collector devices in [conf](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/ansible/roles/runCollectors/vars/vars.yaml) file.
1. The `telemetryToMqtt` setting enables the streaming of telemetry data from devices to local Mqtt broker
2. The `telemetryToIoTHub` setting enables the streaming of telemetry data (directly) from devices to Azure IoT Hub
3. The `collectors` array allows the definition of the sensor devices:
	* device: the device type
	* name: the device name. The value is used to create topic/Device on Mqtt/Azure IoT Hub

The complete ansible command should look like:
`ansible-playbook -i hosts.yaml run_apps.yaml -e 'ansible_python_interpreter=/usr/bin/python3' -t runCollectors,runMQTT,IoTsync --extra-vars "ansible_sudo_pass=<value> IoTHubName='<IoTHubName> connectionString='<connectionString>"`

After the installation of playbook, the below will be up and running:
1. A docker container collecting data from Xiaomi Mijia BLE Sensor and sending them to MQTT
2. An MQTT instance
3. A python proccess that replicates the messages from local broker to Azure IoT Hub

Note: The sensor devices must be available during ansible runtime to be discovered by the host bluetooth

## Configuration

You may configure the `devices` and `mqttHost` in the Ansible [hosts](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/ansible/hosts.yaml) file.

The configuration of the collector application can be found [here](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/ansible/roles/runCollectors/vars/vars.yaml)
and the configuration file of MQTT is [here](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/ansible/roles/runMQTT/files/mosquitto.conf)

## Collector Application

The `appCollector/src` folder includes a [python application](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/appCollector/src/collectData.py) that collects data from sensor devices.

The code allows extendability to support more devices by adding new classes which collect data collection by various sensor devices.

This is achieved by dynamically loading a python class which implements the inerface of the [collectorI](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/appCollector/src/collectors/collectorInterface.py)
interface.

You can implement your own subclass and place it under [folder](https://github.com/John-ltf/smartHomeOnCloud/tree/master/home/appCollector/src/collectors)
You can select your implementation running the python app and using the `--device` argument.

To include the new implementation in the Ansible playbook you can add your implementation (class name) in the [config file](https://github.com/John-ltf/smartHomeOnCloud/blob/master/home/ansible/roles/runCollectors/vars/vars.yaml)

