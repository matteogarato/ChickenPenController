import os
import time
import json
import configparser
import Adafruit_DHT
import paho.mqtt.client as mqtt

MQTT_TOPIC = "homeassistant/"
dhtsensor = Adafruit_DHT.DHT22
config = configparser.RawConfigParser()
configFilePath = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'MqttTempsensor.config')


def main():
    config.read(configFilePath)
    refreshRate = config.getint('Sensor', 'refreshRate')
    if refreshRate is None or refreshRate == 0:
        refreshRate = 1
    dhtPin = config.getint('Sensor', 'dhtPin')
    if dhtPin is None or dhtPin == 0:
        dhtPin = 4
    mqttHost = config.get('Sensor', 'mqttHost')
    if mqttHost is None or mqttHost == '':
        return
    tempChannel = config.get('Sensor', 'tempChannel')
    humidityChannel = config.get('Sensor', 'humidityChannel')
    client = mqtt.Client()
    client.username_pw_set("mqtt_user", "")
    client.connect(mqttHost)
    client.loop_start()
    try:
        while True:
            readedTemp = []
            readedHum = []
            errorcounter = 0
            for x in range(5):
                if errorcounter > 4:
                    client.disconnect()
                    main()
                humidity, temperature = Adafruit_DHT.read_retry(
                    dhtsensor, dhtPin)
                if humidity is None or temperature is None:
                    print("Failed to retrieve data from sensor")
                    errorcounter += 1
                else:
                    readedTemp.append(temperature)
                    readedHum.append(humidity)
                time.sleep(1)

            humidity = Average(readedHum)
            temperature = Average(readedTemp)
            readedTemp = []
            readedHum = []
            print(temperature)
            print(humidity)
            client.publish(MQTT_TOPIC+tempChannel,
                           json.dumps({"temperature": temperature}))
            client.publish(MQTT_TOPIC+humidityChannel,
                           json.dumps({"humidity": humidity}))
            time.sleep(55/refreshRate)
    except KeyboardInterrupt:
        pass

    client.loop_stop()
    client.disconnect()


def Average(lst):
    return sum(lst) / len(lst)


if __name__ == "__main__":
    main()
