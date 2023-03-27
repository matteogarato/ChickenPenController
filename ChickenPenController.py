import os
import time
import json
import Adafruit_DHT
import paho.mqtt.client as mqtt
from gpiozero import CPUTemperature

from ConfigFileParser import ConfigFileParser
if not __debug__:
    import RPi.GPIO as GPIO

dhtsensor = Adafruit_DHT.DHT22
configFilePath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'ChickenPenController.config')


fanStatus = False
heatherStatus = False
radioStatus = False
rpiFanStatus = False
configurationReaded: ConfigFileParser


def main():
    global configurationReaded
    configurationReaded = ConfigFileParser(configFilePath)
    if __debug__:
        print("***Application in DEBUG mode***")
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(configurationReaded.fanPin, GPIO.OUT)
        GPIO.setup(configurationReaded.heatherPin, GPIO.OUT)
    TurnOffHeather()
    TurnOffFan()
    if configurationReaded.mqttActive:
        client = mqtt.Client()
        client.username_pw_set(configurationReaded.mqttUser,
                               configurationReaded.mqttPassword)
        client.connect(configurationReaded.mqttHost)
        client.on_message = on_message
        client.loop_start()
    try:
        while True:
            try:
                cpuTemp = CPUTemperature()
                if cpuTemp.temperature > 40:
                    TurnOnRpiFan()
                else:
                    TurnOffRpiFan()
                extHumidity, extTemperature = SensorReading(
                    configurationReaded.dhtPinExternal)
                intHumidity, intTemperature = SensorReading(
                    configurationReaded.dhtPinInternal)
                if intTemperature <= configurationReaded.minTemp:
                    TurnOffFan()
                    TurnOnHeather()
                if (extTemperature <= intTemperature and
                        intTemperature >= configurationReaded.maxTemp):
                    TurnOffHeather()
                    TurnOnFan()
                if intHumidity > configurationReaded.maxHumidity:
                    TurnOnFan()
                if intHumidity < configurationReaded.minHumidity:
                    TurnOffFan()
                DataPublishing(client, extTemperature, extHumidity,
                               intTemperature, intHumidity)
                time.sleep(60/configurationReaded.refreshRate)
                del extHumidity
                del extTemperature
                del intHumidity
                del intTemperature
            except Exception as ex:
                client.loop_stop()
                client.disconnect()
                del client
                print(ex)
                main()
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        pass


def Average(lst):
    return sum(lst) / len(lst)


def DataPublishing(client: mqtt.Client, extTemperature, extHumidity,
                   intTemperature, intHumidity):
    global configurationReaded
    if __debug__:
        print(extTemperature)
        print(extHumidity)
        print(intTemperature)
        print(intHumidity)
        print(fanStatus)
        print(heatherStatus)
    if configurationReaded.mqttActive:
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
    return


def SensorReading(dhtpin):
    readedTemp = []
    readedHum = []
    for x in range(5):
        hum, tmp = Adafruit_DHT.read_retry(dhtsensor, dhtpin, 5)
        if hum is not None and tmp is not None:
            readedTemp.append(tmp)
            readedHum.append(hum)
    humidity = Average(readedHum)
    temperature = Average(readedTemp)
    return humidity, temperature


def TurnOnHeather():
    global configurationReaded
    global heatherStatus
    if not heatherStatus:
        heatherStatus = True
        if not __debug__:
            GPIO.output(configurationReaded.heatherPin, GPIO.HIGH)
        else:
            print("turning off heather")
    return


def TurnOffHeather():
    global configurationReaded
    global heatherStatus
    if heatherStatus:
        heatherStatus = False
        if not __debug__:
            GPIO.output(configurationReaded.heatherPin, GPIO.LOW)
        else:
            print("turning on heather")
    return


def TurnOnFan():
    global configurationReaded
    global fanStatus
    if not fanStatus:
        fanStatus = True
        if not __debug__:
            GPIO.output(configurationReaded.fanPin, GPIO.HIGH)
        else:
            print("turning on fan")
    return


def TurnOffFan():
    global configurationReaded
    global fanStatus
    if fanStatus:
        fanStatus = False
        if not __debug__:
            GPIO.output(configurationReaded.fanPin, GPIO.LOW)
        else:
            print("turning off fan")
    return


def TurnOnRpiFan():
    global configurationReaded
    global rpiFanStatus
    if not rpiFanStatus:
        rpiFanStatus = True
        if not __debug__:
            GPIO.output(configurationReaded.rpiFanPin, GPIO.HIGH)
        else:
            print("turning on rpi fan")
    return


def TurnOffRpiFan():
    global configurationReaded
    global rpiFanStatus
    if rpiFanStatus:
        rpiFanStatus = False
        if not __debug__:
            GPIO.output(configurationReaded.rpiFanPin, GPIO.LOW)
        else:
            print("turning off rpi fan")
    return


def TurnOnRadio():
    global configurationReaded
    global radioStatus
    if not radioStatus:
        radioStatus = True
        if not __debug__:
            GPIO.output(configurationReaded.radioPin, GPIO.HIGH)
        else:
            print("turning on radio")
    return


def TurnOffRadio():
    global configurationReaded
    global radioStatus
    if radioStatus:
        radioStatus = False
        if not __debug__:
            GPIO.output(configurationReaded.radioPin, GPIO.LOW)
        else:
            print("turning off radio")
    return


def on_message(client, userdata, message):
    if __debug__:
        print(str(message.payload.decode("utf-8")))
    mqttStatusSetter = json.loads(str(message.payload.decode("utf-8")))
    if mqttStatusSetter.ActiveRadio:
        TurnOnRadio()
    elif mqttStatusSetter.ActiveRadio is False:
        TurnOffRadio()


if __name__ == "__main__":
    main()
