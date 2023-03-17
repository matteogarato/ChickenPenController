import os
import time
import json
import Adafruit_DHT
import paho.mqtt.client as mqtt

from ConfigFileParser import ConfigFileParser
if not __debug__:
    import RPi.GPIO as GPIO

dhtsensor = Adafruit_DHT.DHT22
configFilePath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'ChickenPenController.config')


fanStatus = False
heatherStatus = False


def main():
    if __debug__:
        print("***Application in DEBUG mode***")
    configurationReaded = ConfigFileParser(configFilePath)
    if not __debug__:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(configurationReaded.fanPin, GPIO.OUT)
        GPIO.setup(configurationReaded.heatherPin, GPIO.OUT)
    TurnOffHeather(configurationReaded.heatherPin)
    TurnOffFan(configurationReaded.fanPin)
    try:
        while True:
            try:
                extHumidity, extTemperature = SensorReading(
                    configurationReaded.dhtPinExternal)
                intHumidity, intTemperature = SensorReading(
                    configurationReaded.dhtPinInternal)
                if intTemperature <= configurationReaded.minTemp:
                    TurnOffFan(configurationReaded.fanPin)
                    TurnOnHeather(configurationReaded.heatherPin)
                if (extTemperature <= intTemperature and
                        intTemperature >= configurationReaded.maxTemp):
                    TurnOffHeather(configurationReaded.heatherPin)
                    TurnOnFan(configurationReaded.fanPin)
                if intHumidity > configurationReaded.maxHumidity:
                    TurnOnFan(configurationReaded.fanPin)
                if configurationReaded.mqttActive:
                    DataPublishing(extTemperature, extHumidity,
                                   intTemperature, intHumidity,
                                   configurationReaded)
                time.sleep(55/configurationReaded.refreshRate)
                del extHumidity
                del extTemperature
                del intHumidity
                del intTemperature
            except Exception as ex:
                print(ex)
                main()
    except KeyboardInterrupt:
        pass


def Average(lst):
    return sum(lst) / len(lst)


def DataPublishing(extTemperature, extHumidity, intTemperature,
                   intHumidity, configurationReaded):
    if __debug__:
        print(extTemperature)
        print(extHumidity)
        print(intTemperature)
        print(intHumidity)
        print(fanStatus)
        print(heatherStatus)
    try:
        client = mqtt.Client()
        client.username_pw_set(configurationReaded.mqttUser,
                               configurationReaded.mqttPassword)
        client.connect(configurationReaded.mqttHost)
        client.loop_start()
        client.publish(configurationReaded.mqttTopic +
                       configurationReaded.externalTemperatureChannel,
                       json.dumps({"temperature": extTemperature}))
        client.publish(configurationReaded.mqttTopic +
                       configurationReaded.externalHumidityChannel,
                       json.dumps({"humidity": extHumidity}))
        client.publish(configurationReaded.mqttTopic +
                       configurationReaded.internalTemperatureChannel,
                       json.dumps({"temperature": intTemperature}))
        client.publish(configurationReaded.mqttTopic +
                       configurationReaded.internalHumidityChannel,
                       json.dumps({"humidity": intHumidity}))
        client.publish(configurationReaded.mqttTopic +
                       configurationReaded.fanStatusChannel,
                       json.dumps({"fan": fanStatus}))
        client.publish(configurationReaded.mqttTopic +
                       configurationReaded.heatherStatusChannel,
                       json.dumps({"heather": heatherStatus}))
        client.loop_stop()
        client.disconnect()
        del client
    except Exception as ex:
        print(ex)
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


def TurnOnHeather(heatherPin):
    global heatherStatus
    if not heatherStatus:
        heatherStatus = True
        if not __debug__:
            GPIO.output(heatherPin, GPIO.HIGH)
    return


def TurnOffHeather(heatherPin):
    global heatherStatus
    if heatherStatus:
        heatherStatus = False
        if not __debug__:
            GPIO.output(heatherPin, GPIO.LOW)
    return


def TurnOnFan(fanPin):
    global fanStatus
    if not fanStatus:
        fanStatus = True
        if not __debug__:
            GPIO.output(fanPin, GPIO.HIGH)
    return


def TurnOffFan(fanPin):
    global fanStatus
    if fanStatus:
        fanStatus = False
        if not __debug__:
            GPIO.output(fanPin, GPIO.LOW)
    return


if __name__ == "__main__":
    main()
