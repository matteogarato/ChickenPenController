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
remoteRelayStatus = False
rpiFanStatus = False
mqttConnected = False
configurationRead: ConfigFileParser
logger = logging.getLogger('ChickenPenController')


def main():
    global configurationRead, fanStatus, heatherStatus, mqttConnected, logger
    configurationRead = ConfigFileParser(configFilePath)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(configurationRead.fanPin, GPIO.OUT)
    GPIO.setup(configurationRead.rpiFanPin, GPIO.OUT)
    GPIO.setup(configurationRead.remoteRelayPin, GPIO.OUT)
    GPIO.setup(int(configurationRead.heatherPin), GPIO.OUT)
    GPIO.setup(int(configurationRead.heatherFanPin), GPIO.OUT)
    TurnHeather(False)
    TurnFan(False)
    TurnRemoteRelay(False)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if configurationRead.mqttActive:
        client.username_pw_set(configurationRead.mqttUser,
                               configurationRead.mqttPassword)
        client.on_message = on_message
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.connect(configurationRead.mqttHost)
        client.loop_start()
    try:
        while True:
            try:
                logger.info("start of cycle")
                configurationRead = ConfigFileParser(configFilePath)
                cpu_temp = CPUTemperature().temperature
                logger.info(f"cpu temp:{cpu_temp}")
                TurnRpiFan(cpu_temp > 40)

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
                        TurnHeather(True)
                        TurnFan(int_humidity > configurationRead.maxHumidity)

                    if (int_temperature < configurationRead.maxTemp and
                            int_temperature > configurationRead.minTemp):
                        TurnHeather(False)
                        TurnFan(int_humidity > configurationRead.maxHumidity)

                    if int_temperature > configurationRead.maxTemp:
                        TurnHeather(False)
                        TurnFan(True)

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
                    topic = configurationRead.chickenPenTopic
                    logger.debug("topic: " + topic)
                    if configurationRead.mqttActive and mqttConnected:
                        client.publish(topic, payload)
                        time.sleep(1)
                time.sleep(60 / configurationRead.refreshRate)
                logger.info("end of cycle")
            except KeyboardInterrupt:
                break

            except Exception as ex:
                if configurationRead.mqttActive:
                    client.loop_stop()
                    client.disconnect()
                GPIO.cleanup()
                logger.error(ex)

    finally:
        if configurationRead.mqttActive:
            client.loop_stop()
            client.disconnect()
        GPIO.cleanup()
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


def TurnHeather(status):
    global configurationRead, heatherStatus, logger
    if heatherStatus != status:
        heatherStatus = not heatherStatus
        GPIO.output(int(configurationRead.heatherPin),
                    heatherStatus if GPIO.HIGH else GPIO.LOW)
        GPIO.output(int(configurationRead.heatherFanPin),
                    heatherStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning heather status : {heatherStatus}")
    return


def TurnFan(status):
    global configurationRead, fanStatus, logger
    if fanStatus != status:
        fanStatus = not fanStatus
        GPIO.output(configurationRead.fanPin,
                    fanStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning fan status: {fanStatus}")
    return


def TurnRpiFan(status):
    global configurationRead, rpiFanStatus, logger
    if rpiFanStatus != status:
        rpiFanStatus = not rpiFanStatus
        GPIO.output(configurationRead.rpiFanPin,
                    rpiFanStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning rpi fan status: {rpiFanStatus}")
    return


def TurnRemoteRelay(status):
    global configurationRead, remoteRelayStatus, logger
    if remoteRelayStatus != status:
        remoteRelayStatus = not remoteRelayStatus
        GPIO.output(configurationRead.remoteRelayPin,
                    remoteRelayStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning remote relay status: {remoteRelayStatus}")
    return


def on_connect(client, userdata, flags, reasonCode, properties=None):
    global configurationRead, mqttConnected, logger
    if reasonCode == 0:
        mqttConnected = True
        logger.debug("Mqtt not connected")
        client.loop_start()
        client.subscribe(configurationRead.remoteRelayTopic)
    else:
        logger.warning("Mqtt not connected, reasonCode: "+str(reasonCode))
        time.sleep(5)
        client.connect(configurationRead.mqttHost)


def on_disconnect(client, userdata, flags, reasonCode, properties=None):
    global configurationRead, mqttConnected, logger
    logger.debug("Mqtt on_disconnect")
    mqttConnected = False
    client.connect(configurationRead.mqttHost)


def on_message(client, userdata, message):
    global logger
    msg = str(message.payload.decode("utf-8"))
    logger.debug(msg)
    mqttStatusSetter = json.loads(msg)
    TurnRemoteRelay(mqttStatusSetter.ActiveRemoteRelay)


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
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)
    main()
