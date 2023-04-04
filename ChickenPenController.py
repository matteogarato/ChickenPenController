import os
import time
import json
import Adafruit_DHT
import paho.mqtt.client as mqtt
from gpiozero import CPUTemperature

from ConfigFileParser import ConfigFileParser
if not __debug__:
    import RPi.GPIO as GPIO

dhtSensor = Adafruit_DHT.DHT22
configFilePath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'ChickenPenController.config')


fanStatus = False
heatherStatus = False
radioStatus = False
rpiFanStatus = False
configurationRead: ConfigFileParser


def main():
    global configurationRead
    configurationRead = ConfigFileParser(configFilePath)
    if __debug__:
        print("***Application in DEBUG mode***")
    else:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(configurationRead.fanPin, GPIO.OUT)
        GPIO.setup(configurationRead.heatherPin, GPIO.OUT)
    TurnOffHeather()
    TurnOffFan()
    TurnOffRadio()
    if configurationRead.mqttActive:
        client = mqtt.Client()
        client.username_pw_set(configurationRead.mqttUser,
                               configurationRead.mqttPassword)
        client.connect(configurationRead.mqttHost)
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
                    configurationRead.dhtPinExternal)
                intHumidity, intTemperature = SensorReading(
                    configurationRead.dhtPinInternal)
                if intTemperature <= configurationRead.minTemp:
                    TurnOffFan()
                    TurnOnHeather()
                if (extTemperature <= intTemperature and
                        intTemperature >= configurationRead.maxTemp):
                    TurnOffHeather()
                    TurnOnFan()
                if intHumidity > configurationRead.maxHumidity:
                    TurnOnFan()
                if intHumidity < configurationRead.minHumidity:
                    TurnOffFan()
                DataPublishing(client, extTemperature, extHumidity,
                               intTemperature, intHumidity)
                time.sleep(60/configurationRead.refreshRate)
                del extHumidity
                del extTemperature
                del intHumidity
                del intTemperature
            except Exception as ex:
                if configurationRead.mqttActive:
                    client.loop_stop()
                    client.disconnect()
                    del client
                print(ex)
                main()
    except KeyboardInterrupt:
        if configurationRead.mqttActive:
            client.loop_stop()
            client.disconnect()
            del client
        pass


def Average(lst):
    return sum(lst) / len(lst)


def DataPublishing(client: mqtt.Client, extTemperature, extHumidity,
                   intTemperature, intHumidity):
    global configurationRead
    if __debug__:
        print(extTemperature)
        print(extHumidity)
        print(intTemperature)
        print(intHumidity)
        print(fanStatus)
        print(heatherStatus)
    if configurationRead.mqttActive:
        client.loop_start()
        client.publish(configurationRead.mqttTopic +
                       configurationRead.externalTemperatureChannel,
                       json.dumps({"temperature": extTemperature}))
        client.publish(configurationRead.mqttTopic +
                       configurationRead.externalHumidityChannel,
                       json.dumps({"humidity": extHumidity}))
        client.publish(configurationRead.mqttTopic +
                       configurationRead.internalTemperatureChannel,
                       json.dumps({"temperature": intTemperature}))
        client.publish(configurationRead.mqttTopic +
                       configurationRead.internalHumidityChannel,
                       json.dumps({"humidity": intHumidity}))
        client.publish(configurationRead.mqttTopic +
                       configurationRead.fanStatusChannel,
                       json.dumps({"fan": fanStatus}))
        client.publish(configurationRead.mqttTopic +
                       configurationRead.heatherStatusChannel,
                       json.dumps({"heather": heatherStatus}))
    return


def SensorReading(dhtPin):
    readTemp = []
    readHum = []
    for x in range(5):
        hum, tmp = Adafruit_DHT.read_retry(dhtSensor, dhtPin, 5)
        if hum is not None and tmp is not None:
            readTemp.append(tmp)
            readHum.append(hum)
    humidity = Average(readHum)
    temperature = Average(readTemp)
    return humidity, temperature


def TurnOnHeather():
    global configurationRead, heatherStatus
    if not heatherStatus:
        heatherStatus = True
        if not __debug__:
            GPIO.output(configurationRead.heatherPin, GPIO.HIGH)
        else:
            print("turning off heather")
    return


def TurnOffHeather():
    global configurationRead, heatherStatus
    if heatherStatus:
        heatherStatus = False
        if not __debug__:
            GPIO.output(configurationRead.heatherPin, GPIO.LOW)
        else:
            print("turning on heather")
    return


def TurnOnFan():
    global configurationRead, fanStatus
    if not fanStatus:
        fanStatus = True
        if not __debug__:
            GPIO.output(configurationRead.fanPin, GPIO.HIGH)
        else:
            print("turning on fan")
    return


def TurnOffFan():
    global configurationRead, fanStatus
    if fanStatus:
        fanStatus = False
        if not __debug__:
            GPIO.output(configurationRead.fanPin, GPIO.LOW)
        else:
            print("turning off fan")
    return


def TurnOnRpiFan():
    global configurationRead, rpiFanStatus
    if not rpiFanStatus:
        rpiFanStatus = True
        if not __debug__:
            GPIO.output(configurationRead.rpiFanPin, GPIO.HIGH)
        else:
            print("turning on rpi fan")
    return


def TurnOffRpiFan():
    global configurationRead, rpiFanStatus
    if rpiFanStatus:
        rpiFanStatus = False
        if not __debug__:
            GPIO.output(configurationRead.rpiFanPin, GPIO.LOW)
        else:
            print("turning off rpi fan")
    return


def TurnOnRadio():
    global configurationRead, radioStatus
    if not radioStatus:
        radioStatus = True
        if not __debug__:
            GPIO.output(configurationRead.radioPin, GPIO.HIGH)
        else:
            print("turning on radio")
    return


def TurnOffRadio():
    global configurationRead, radioStatus
    if radioStatus:
        radioStatus = False
        if not __debug__:
            GPIO.output(configurationRead.radioPin, GPIO.LOW)
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
