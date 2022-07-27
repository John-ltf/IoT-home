# Installation

The directory includes
1. an Ansible playbook for the installation of processes and devices on home infrastructure
2. and python code to retrieve data from Xiaomi Mijia BLE Sensor 

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
1. Provide the Azure IoT Hub name using the variable `IoTHubName`
2. Provide the device ID that is registered on Azure IoT Hub name using the variable `deviceId`
3. Provide the SAS token that has been generated for the given device using the variable `sas`
1. To skip the installation of docker by adding `-t runCollectors,runMQTT`
2. To ovveride the pre-configured python 2.x by adding `-e 'ansible_python_interpreter=/usr/bin/python3`
3. To give as argument the root password by adding `--extra-vars "ansible_sudo_pass=<PASSWORD>"`

The complete ansible command should look like:

`ansible-playbook -i hosts.yaml run_apps.yaml -e 'ansible_python_interpreter=/usr/bin/python3' -t runCollectors,runMQTT --extra-vars "ansible_sudo_pass=<value> IoTHubName=<value> deviceId=<vale> sas='<value>'"`

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

