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
celingFanStatus = False
rpiFanStatus = False
configurationRead: ConfigFileParser


def main():
    global configurationRead, fanStatus, heatherStatus
    configurationRead = ConfigFileParser(configFilePath)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(configurationRead.fanPin, GPIO.OUT)
    GPIO.setup(configurationRead.rpiFanPin, GPIO.OUT)
    GPIO.setup(configurationRead.celingFanPin, GPIO.OUT)
    GPIO.setup(int(configurationRead.heatherPin), GPIO.OUT)
    GPIO.setup(int(configurationRead.heatherFanPin), GPIO.OUT)
    TurnOffHeather()
    TurnOffFan()
    TurnOffCelingFan()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if configurationRead.mqttActive:
        client.username_pw_set(configurationRead.mqttUser,
                               configurationRead.mqttPassword)
        client.on_message = on_message
        client.on_connect = on_connect
    try:
        while True:
            try:
                logger.info("start of cicle")
                configurationRead = ConfigFileParser(configFilePath)
                cpu_temp = CPUTemperature().temperature
                logger.info(f"cpu temp:{cpu_temp}")
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

                if ext_humidity is None or ext_temperature is None or int_humidity is None or int_temperature is None:
                    logger.error("Invalid sensor reading")
                else:
                    if int_temperature < configurationRead.minTemp:
                        TurnOnHeather()
                        if int_humidity > configurationRead.maxHumidity:
                            TurnOffFan()
                            TurnOffCelingFan()
                        else:
                            TurnOffFan()
                            TurnOffCelingFan()

                    if (int_temperature < configurationRead.maxTemp and
                            int_temperature > configurationRead.minTemp):
                        TurnOffHeather()
                        if int_humidity > configurationRead.maxHumidity:
                            TurnOffFan()
                            TurnOffCelingFan()
                        else:
                            TurnOffFan()
                            TurnOffCelingFan()

                    if int_temperature > configurationRead.maxTemp:
                        TurnOffHeather()
                        TurnOnFan()
                        TurnOnCelingFan()

                    data = {
                        "extTemperature": ext_temperature,
                        "extHumidity": ext_humidity,
                        "intTemperature": int_temperature,
                        "intHumidity": int_humidity,
                        "fanStatus": fanStatus,
                        "heatherStatus": heatherStatus,
                        "rpiFanStatus": rpiFanStatus
                    }
                    payload = json.dumps(data)
                    logger.debug("payload: " + payload)
                    topic = configurationRead.ChickenPenTopic
                    logger.debug("topic: " + topic)
                    if configurationRead.mqttActive:
                        client.connect(configurationRead.mqttHost)
                        client.loop_start()
                        client.publish(topic, payload)
                        client.loop_stop()
                        client.disconnect()
                time.sleep(60 / configurationRead.refreshRate)
                del ext_humidity, ext_temperature, int_humidity, int_temperature
                logger.info("end of cicle")
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
    humidity = None
    temperature = None
    if len(read_hum) != 0:
        humidity = sum(read_hum) // len(read_hum)
    if len(read_temp) != 0:
        temperature = (sum(read_temp) // len(read_temp)) + temperatureOffset
    return humidity, temperature


def TurnOnHeather():
    global configurationRead, heatherStatus
    if not heatherStatus:
        heatherStatus = True
        GPIO.output(int(configurationRead.heatherPin), GPIO.HIGH)
        GPIO.output(int(configurationRead.heatherFanPin), GPIO.HIGH)
        logger.debug("turning on heather")
    return


def TurnOffHeather():
    global configurationRead, heatherStatus
    if heatherStatus:
        heatherStatus = False
        GPIO.output(int(configurationRead.heatherPin), GPIO.LOW)
        GPIO.output(int(configurationRead.heatherFanPin), GPIO.LOW)
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


def TurnOnCelingFan():
    global configurationRead, celingFanStatus
    if not celingFanStatus:
        celingFanStatus = True
        GPIO.output(configurationRead.celingFanPin, GPIO.HIGH)
        logger.debug("turning on celingFan")
    return


def TurnOffCelingFan():
    global configurationRead, celingFanStatus
    if celingFanStatus:
        celingFanStatus = False
        GPIO.output(configurationRead.celingFanPin, GPIO.LOW)
        logger.debug("turning off celingFan")
    return


def on_connect(client, userdata, flags, rc):
    global configurationRead
    logger.debug("Connected with result code "+str(rc))
    client.subscribe(configurationRead.celingFanChannel)


def on_message(client, userdata, message):
    msg = str(message.payload.decode("utf-8"))
    logger.debug(msg)
    mqttStatusSetter = json.loads(msg)
    if mqttStatusSetter.ActiveCelingFan:
        TurnOnCelingFan()
    elif mqttStatusSetter.ActiveCelingFan is False:
        TurnOffCelingFan()


if __name__ == "__main__":
    logging.basicConfig()
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
    logger.setLevel(logging.INFO)
    main()
