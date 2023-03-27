import configparser


class ConfigFileParser:
    def __init__(self, configFilePath):
        config = configparser.RawConfigParser()
        config.read(configFilePath)
        refreshRate = config.getint('Sensor', 'refreshRate')
        if refreshRate is None or refreshRate == 0:
            refreshRate = 1
        self.fanPin = config.getint('Sensor', 'fanPin')
        self.heatherPin = config.getint('Sensor', 'heatherPin')
        self.radioPin = config.getint('Sensor', 'radioPin')
        self.rpiFanPin = config.getint('Sensor', 'rpiFanPin')
        self.dhtPinInternal = config.getint('Sensor', 'dhtPinInternal')
        self.dhtPinExternal = config.getint('Sensor', 'dhtPinExternal')
        self.minTemp = 15
        self.maxTemp = 30
        self.minHumidity = 30
        self.maxHumidity = 70
        self.refreshRate = refreshRate
        self.mqttActive = config.getboolean('MQTT', 'mqttActive')
        self.mqttUser = config.get('MQTT', 'user')
        self.mqttPassword = config.get('MQTT', 'password')
        self.mqttTopic = config.get('MQTT', 'topic')+"/"
        self.mqttHost = config.get('MQTT', 'host')
        self.externalTemperatureChannel = config.get(
            'MQTT', 'externalTemperatureChannel')
        self.externalHumidityChannel = config.get(
            'MQTT', 'externalHumidityChannel')
        self.internalTemperatureChannel = config.get(
            'MQTT', 'internalTemperatureChannel')
        self.internalHumidityChannel = config.get(
            'MQTT', 'internalHumidityChannel')
        self.fanStatusChannel = config.get('MQTT', 'fanStatusChannel')
        self.heatherStatusChannel = config.get('MQTT', 'heatherStatusChannel')
