import os
import time
import json
import configparser
import Adafruit_DHT
import paho.mqtt.client as mqtt
if not __debug__:
    import RPi.GPIO as GPIO

dhtsensor = Adafruit_DHT.DHT22
config = configparser.RawConfigParser()
configFilePath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'MqttTempsensor.config')

fanPin = 6
heatherPin = 7
dhtPinInternal = 5
dhtPinExternal = 4
minTemp = 15
maxTemp = 30
minHumidity = 30
maxHumidity = 70
refreshRate = 2
fanStatus = False
heatherStatus = False
mqttUser = ""
mqttPassword = ""
mqttTopic = ""
mqttHost = ""
externalTemperatureChannel = ""
externalHumidityChannel = ""
internalTemperatureChannel = ""
internalHumidityChannel = ""
fanStatusChannel = ""
heatherStatusChannel = ""


def main():
    Setup()
    try:
        while True:
            try:
                extHumidity, extTemperature = SensorReading(dhtPinExternal)
                intHumidity, intTemperature = SensorReading(dhtPinInternal)
                if intTemperature <= minTemp:
                    TurnOffFan()
                    TurnOnHeather()
                if (extTemperature <= intTemperature and
                        intTemperature >= maxTemp):
                    TurnOffHeather()
                    TurnOnFan()
                if intHumidity > maxHumidity:
                    TurnOnFan()
                DataPublishing(extTemperature, extHumidity,
                               intTemperature, intHumidity)
                time.sleep(55/refreshRate)
            except Exception:
                main()
    except KeyboardInterrupt:
        pass


def Average(lst):
    return sum(lst) / len(lst)


def Setup():
    if __debug__:
        print("***Application in DEBUG mode***")
    ConfigurationReading()
    if not __debug__:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(fanPin, GPIO.OUT)
        GPIO.setup(heatherPin, GPIO.OUT)
    TurnOffHeather()
    TurnOffFan()
    return


def ConfigurationReading():
    global fanPin
    global heatherPin
    global mqttUser
    global mqttPassword
    global mqttTopic
    global mqttHost
    global externalTemperatureChannel
    global externalHumidityChannel
    global internalTemperatureChannel
    global internalHumidityChannel
    global dhtPinExternal
    global dhtPinInternal
    global refreshRate
    global fanStatusChannel
    global heatherStatusChannel
    config.read(configFilePath)
    refreshRate = config.getint('Sensor', 'refreshRate')
    if refreshRate is None or refreshRate == 0:
        refreshRate = 1
    dhtPinExternal = config.getint('Sensor', 'dhtPinExternal')
    dhtPinInternal = config.getint('Sensor', 'dhtPinInternal')
    fanPin = config.getint('Sensor', 'fanPin')
    heatherPin = config.getint('Sensor', 'heatherPin')
    mqttHost = config.get('MQTT', 'host')
    externalTemperatureChannel = config.get(
        'MQTT', 'externalTemperatureChannel')
    externalHumidityChannel = config.get('MQTT', 'externalHumidityChannel')
    internalTemperatureChannel = config.get(
        'MQTT', 'internalTemperatureChannel')
    internalHumidityChannel = config.get('MQTT', 'internalHumidityChannel')
    fanStatusChannel = config.get('MQTT', 'fanStatusChannel')
    heatherStatusChannel = config.get('MQTT', 'heatherStatusChannel')
    mqttUser = config.get('MQTT', 'user')
    mqttPassword = config.get('MQTT', 'password')
    mqttTopic = config.get('MQTT', 'topic')+"/"
    return


def DataPublishing(extTemperature, extHumidity, intTemperature, intHumidity):
    if __debug__:
        print(extTemperature)
        print(extHumidity)
        print(intTemperature)
        print(intHumidity)
        print(fanStatus)
        print(heatherStatus)
    try:
        client = mqtt.Client()
        client.username_pw_set(mqttUser, mqttPassword)
        client.connect(mqttHost)
        client.loop_start()
        client.publish(mqttTopic+externalTemperatureChannel,
                       json.dumps({"temperature": extTemperature}))
        client.publish(mqttTopic+externalHumidityChannel,
                       json.dumps({"humidity": extHumidity}))
        client.publish(mqttTopic+internalTemperatureChannel,
                       json.dumps({"temperature": intTemperature}))
        client.publish(mqttTopic+internalHumidityChannel,
                       json.dumps({"humidity": intHumidity}))
        client.publish(mqttTopic+fanStatusChannel,
                       json.dumps({"fan": fanStatus}))
        client.publish(mqttTopic+heatherStatusChannel,
                       json.dumps({"heather": heatherStatus}))
        client.loop_stop()
        client.disconnect()
    except Exception:
        return
    return


def SensorReading(dhtPin):
    readedTemp = []
    readedHum = []
    for x in range(5):
        hum, tmp = Adafruit_DHT.read_retry(dhtsensor, dhtPin, 5, 1)
        if hum is not None and tmp is not None:
            readedTemp.append(tmp)
            readedHum.append(hum)
            time.sleep(1)

    humidity = Average(readedHum)
    temperature = Average(readedTemp)
    return humidity, temperature


def TurnOnHeather():
    global heatherStatus
    if not heatherStatus:
        heatherStatus = True
        if not __debug__:
            GPIO.output(heatherPin, GPIO.HIGH)
    return


def TurnOffHeather():
    global heatherStatus
    if heatherStatus:
        heatherStatus = False
        if not __debug__:
            GPIO.output(heatherPin, GPIO.LOW)
    return


def TurnOnFan():
    global fanStatus
    if not fanStatus:
        fanStatus = True
        if not __debug__:
            GPIO.output(fanPin, GPIO.HIGH)
    return


def TurnOffFan():
    global fanStatus
    if fanStatus:
        fanStatus = False
        if not __debug__:
            GPIO.output(fanPin, GPIO.LOW)
    return


if __name__ == "__main__":
    main()
