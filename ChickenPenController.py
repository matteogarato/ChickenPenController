import os
import time
import json
import logging
import logging.handlers
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
    GPIO.setup(configurationRead.rpiFanPin, GPIO.OUT)
    heather, fan = configurationRead.heatherPin.split(',')
    GPIO.setup(int(heather), GPIO.OUT)
    GPIO.setup(int(fan), GPIO.OUT)
    TurnOffHeather()
    TurnOffFan()
    TurnOffRadio()
    client = mqtt.Client()
    if configurationRead.mqttActive:
        client.username_pw_set(configurationRead.mqttUser,
                               configurationRead.mqttPassword)
        client.on_message = on_message
        client.on_connect = on_connect
        client.connect(configurationRead.mqttHost)
        client.loop_start()
    try:
        while True:
            try:
                cpu_temp = CPUTemperature().temperature
                if cpu_temp > 40:
                    TurnOnRpiFan()
                else:
                    TurnOffRpiFan()
                ext_humidity, ext_temperature = SensorReading(
                    configurationRead.dhtPinExternal,
                    configurationRead.externalTempOffset)
                int_humidity, int_temperature = SensorReading(
                    configurationRead.dhtPinInternal,
                    configurationRead.internalTempOffset)

                if int_temperature <= configurationRead.minTemp:
                    TurnOffFan()
                    TurnOnHeather()

                if (ext_temperature <= int_temperature and
                        int_temperature >= configurationRead.maxTemp):
                    TurnOffHeather()
                    TurnOnFan()

                if int_humidity > configurationRead.maxHumidity:
                    TurnOnFan()

                if int_humidity < configurationRead.minHumidity:
                    TurnOffFan()

                data = {
                    "extTemperature": ext_temperature,
                    "extHumidity": ext_humidity,
                    "intTemperature": int_temperature,
                    "intHumidity": int_humidity,
                    "fanStatus": fanStatus,
                    "heatherStatus": heatherStatus,
                    "rpiFanStatus": rpiFanStatus
                }
                DataPublishing(client, data)

                time.sleep(60 / configurationRead.refreshRate)

                del ext_humidity, ext_temperature, int_humidity, int_temperature

            except KeyboardInterrupt:
                break

            except Exception as ex:
                if configurationRead.mqttActive:
                    client.loop_stop()
                    client.disconnect()
                    del client
                logger.error(ex)

    finally:
        if configurationRead.mqttActive:
            client.loop_stop()
            client.disconnect()
            del client
        logger.error("Keyboard Interrupt")


def SensorReading(dhtPin, temperatureOffset):
    read_temp = []
    read_hum = []
    for _ in range(5):
        hum, tmp = Adafruit_DHT.read_retry(dhtSensor, dhtPin, 5)
        if hum is not None and tmp is not None:
            read_temp.append(int(tmp))
            read_hum.append(int(hum))
    humidity = sum(read_hum) // len(read_hum)
    temperature = (sum(read_temp) // len(read_temp)) + temperatureOffset
    return humidity, temperature


def DataPublishing(client, data):
    global configurationRead
    logger.debug(
        "extTem:{}, extHum:{}, intTemp:{}, intHum:{}, fanStatus:{}, heatherStatus:{}, rpiFanStatus:{}"
        .format(data.extTemperature, data.extHumidity, data.intTemperature, data.intHumidity, fanStatus, heatherStatus, rpiFanStatus))
    if configurationRead.mqttActive:
        client.loop_start()
        for key, value in data.items():
            topic = configurationRead.mqttTopic + \
                getattr(configurationRead, key + "Channel")
            payload = json.dumps({key: value})
            client.publish(topic, payload)
    return


def TurnOnHeather():
    global configurationRead, heatherStatus
    if not heatherStatus:
        heatherStatus = True
        heather, fan = configurationRead.heatherPin.split(',')
        GPIO.output(heather, GPIO.HIGH)
        GPIO.output(fan, GPIO.HIGH)
        logger.debug("turning on heather")
    return


def TurnOffHeather():
    global configurationRead, heatherStatus
    if heatherStatus:
        heatherStatus = False
        heather, fan = configurationRead.heatherPin.split(',')
        GPIO.output(heather, GPIO.LOW)
        GPIO.output(fan, GPIO.LOW)
        logger.debug("turning off heather")
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


def on_connect(client, userdata, flags, rc):
    global configurationRead
    logger.debug("Connected with result code "+str(rc))
    client.subscribe(configurationRead.radioChannel)


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
        '%(asctime)s Pid [%(process)d]: %(message)s',
        '%b %d %H:%M:%S')
    formatter.converter = time.localtime
    log_handler.setFormatter(formatter)
    logger = logging.getLogger('ChickenPenController')
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)
    main()
