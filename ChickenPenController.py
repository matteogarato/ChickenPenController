import os
import time
import json
import logging
import logging.handlers
import adafruit_dht
import board
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from gpiozero import CPUTemperature

from ConfigFileParser import ConfigFileParser

logFileName = "ChickenPenController.log"

configFilePath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'ChickenPenController.config')

fanStatus = False
heatherStatus = False
remoteRelayStatus = False
rpiFanStatus = False
mqttConnected = False
dht_ext_device = adafruit_dht.DHT22(board.D4)
dht_int_device = adafruit_dht.DHT22(board.D5)
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
    turn_heather(False)
    turn_fan(False)
    turn_remote_relay(False)
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
                turn_raspberry_fan(cpu_temp > 40)
                logger.info("before external reading")
                ext_humidity, ext_temperature = external_sensor_reading(
                    configurationRead.externalTempOffset)
                logger.info("after external reading")
                logger.info("before internal reading")
                int_humidity, int_temperature = internal_sensor_reading(
                    configurationRead.internalTempOffset)
                logger.info("after internal reading")

                if ext_humidity is None or ext_temperature is None or int_humidity is None or int_temperature is None:
                    logger.error("Invalid sensor reading")
                else:
                    if int_temperature < configurationRead.minTemp:
                        logger.info("turn on heather")
                        turn_heather(True)
                        turn_fan(int_humidity > configurationRead.maxHumidity)

                    if configurationRead.maxTemp > int_temperature > configurationRead.minTemp:
                        logger.info("turn off heather")
                        turn_heather(False)
                        turn_fan(int_humidity > configurationRead.maxHumidity)

                    if int_temperature > configurationRead.maxTemp:
                        logger.info("turn off heather")
                        turn_heather(False)
                        logger.info("turn on fan")
                        turn_fan(True)

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
                    logger.info("payload: " + payload)
                    topic = configurationRead.chickenPenTopic
                    logger.info("topic: " + topic)
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


def external_sensor_reading(temperature_offset):
    read_temp = []
    read_hum = []
    logger.info("external sensor reading - before for loop")
    for _ in range(5):
        time.sleep(2.0)
        try:
            read_temp.append(int(dht_ext_device.temperature))
            read_hum.append(int(dht_ext_device.humidity))
        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            print(error.args[0])
            time.sleep(2.0)
            continue
    logger.info("external sensor reading - after for loop")
    humidity = None
    temperature = None
    if len(read_hum) != 0:
        humidity = sum(read_hum) // len(read_hum)
    if len(read_temp) != 0:
        temperature = (sum(read_temp) // len(read_temp)) + temperature_offset
    logger.info("external sensor reading - after median")
    return humidity, temperature


def internal_sensor_reading(temperature_offset):
    read_temp = []
    read_hum = []
    logger.info("internal sensor reading - before for loop")
    for _ in range(5):
        time.sleep(2.0)
        try:
            read_temp.append(int(dht_int_device.temperature))
            read_hum.append(int(dht_int_device.humidity))
        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read, just keep going
            print(error.args[0])
            time.sleep(2.0)
            continue
    logger.info("internal sensor reading - after for loop")
    humidity = None
    temperature = None
    if len(read_hum) != 0:
        humidity = sum(read_hum) // len(read_hum)
    if len(read_temp) != 0:
        temperature = (sum(read_temp) // len(read_temp)) + temperature_offset
    logger.info("internal sensor reading - after median")
    return humidity, temperature


def turn_heather(status):
    global configurationRead, heatherStatus, logger
    if heatherStatus != status:
        heatherStatus = not heatherStatus
        GPIO.output(int(configurationRead.heatherPin),
                    heatherStatus if GPIO.HIGH else GPIO.LOW)
        GPIO.output(int(configurationRead.heatherFanPin),
                    heatherStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning heather status : {heatherStatus}")
    return


def turn_fan(status):
    global configurationRead, fanStatus, logger
    if fanStatus != status:
        fanStatus = not fanStatus
        GPIO.output(configurationRead.fanPin,
                    fanStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning fan status: {fanStatus}")
    return


def turn_raspberry_fan(status):
    global configurationRead, rpiFanStatus, logger
    if rpiFanStatus != status:
        rpiFanStatus = not rpiFanStatus
        GPIO.output(configurationRead.rpiFanPin,
                    rpiFanStatus if GPIO.HIGH else GPIO.LOW)
        logger.debug(f"turning rpi fan status: {rpiFanStatus}")
    return


def turn_remote_relay(status):
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
    mqtt_status_setter = json.loads(msg)
    turn_remote_relay(mqtt_status_setter.ActiveRemoteRelay)


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
