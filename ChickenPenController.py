import json
import logging
import logging.handlers
import os
import time

import Adafruit_DHT
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from gpiozero import CPUTemperature

from ConfigFileParser import ConfigFileParser

logFileName = "ChickenPenController.log"

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
                if int(cpuTemp.temperature) > 40:
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
                logger.error(ex)
                main()
    except KeyboardInterrupt:
        if configurationRead.mqttActive:
            client.loop_stop()
            client.disconnect()
            del client
            logger.error("Keyboard Interrupt")
        pass


def Average(lst):
    return sum(lst) / len(lst)


def DataPublishing(client: mqtt.Client, extTemperature, extHumidity,
                   intTemperature, intHumidity):
    global configurationRead
    logger.debug(
        "extTemperature:{}, extHumidity:{}, intTemperature:{}, intHumidity:{} ,fanStatus:{} ,heatherStatus{}"
        .format(extTemperature, extHumidity, intTemperature, intHumidity, fanStatus, heatherStatus))
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
            readTemp.append(int(tmp))
            readHum.append(int(hum))
    humidity = Average(readHum)
    temperature = Average(readTemp)
    return humidity, temperature


def TurnOnHeather():
    global configurationRead, heatherStatus
    if not heatherStatus:
        heatherStatus = True
        GPIO.output(configurationRead.heatherPin, GPIO.HIGH)
        logger.debug("turning off heather")
    return


def TurnOffHeather():
    global configurationRead, heatherStatus
    if heatherStatus:
        heatherStatus = False
        GPIO.output(configurationRead.heatherPin, GPIO.LOW)
        logger.debug("turning on heather")
    return


def TurnOnFan():
    global configurationRead, fanStatus
    if not fanStatus:
        fanStatus = True
        GPIO.output(configurationRead.fanPin, GPIO.HIGH)
        logger.debug("turning on fan")
    return


def TurnOffFan():
    global configurationRead, fanStatus
    if fanStatus:
        fanStatus = False
        GPIO.output(configurationRead.fanPin, GPIO.LOW)
        logger.debug("turning off fan")
    return


def TurnOnRpiFan():
    global configurationRead, rpiFanStatus
    if not rpiFanStatus:
        rpiFanStatus = True
        GPIO.output(configurationRead.rpiFanPin, GPIO.HIGH)
        logger.debug("turning on rpi fan")
    return


def TurnOffRpiFan():
    global configurationRead, rpiFanStatus
    if rpiFanStatus:
        rpiFanStatus = False
        GPIO.output(configurationRead.rpiFanPin, GPIO.LOW)
        logger.debug("turning off rpi fan")
    return


def TurnOnRadio():
    global configurationRead, radioStatus
    if not radioStatus:
        radioStatus = True
        GPIO.output(configurationRead.radioPin, GPIO.HIGH)
        logger.debug("turning on radio")
    return


def TurnOffRadio():
    global configurationRead, radioStatus
    if radioStatus:
        radioStatus = False
        GPIO.output(configurationRead.radioPin, GPIO.LOW)
        logger.debug("turning off radio")
    return


def on_message(client, userdata, message):
    logger.debug(str(message.payload.decode("utf-8")))
    mqttStatusSetter = json.loads(str(message.payload.decode("utf-8")))
    if mqttStatusSetter.ActiveRadio:
        TurnOnRadio()
    elif mqttStatusSetter.ActiveRadio is False:
        TurnOffRadio()


if __name__ == "__main__":
    log_handler = logging.handlers.TimedRotatingFileHandler(
        logFileName,
        when="d",
        interval=1,
        backupCount=5)
    formatter = logging.Formatter(
        '%(asctime)s program_name [%(process)d]: %(message)s',
        '%b %d %H:%M:%S')
    formatter.converter = time.localtime
    log_handler.setFormatter(formatter)
    logger = logging.getLogger('ChickenPenController')
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)
    main()
