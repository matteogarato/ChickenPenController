import configparser


class ConfigFileParser:

    DEFAULT_MIN_TEMP = 15
    DEFAULT_MAX_TEMP = 30
    DEFAULT_MIN_HUMIDITY = 30
    DEFAULT_MAX_HUMIDITY = 70
    DEFAULT_REFRESH_RATE = 1

    def __init__(self, configFilePath):
        config = configparser.ConfigParser()
        config.read(configFilePath)
        self.fanPin = config.getint('Sensor', 'fanPin')
        self.heatherPin = config.get('Sensor', 'heatherPin')
        self.radioPin = config.getint('Sensor', 'radioPin')
        self.rpiFanPin = config.getint('Sensor', 'rpiFanPin')
        self.dhtPinInternal = config.getint('Sensor', 'dhtPinInternal')
        self.dhtPinExternal = config.getint('Sensor', 'dhtPinExternal')
        self.minTemp = self.DEFAULT_MIN_TEMP
        self.maxTemp = self.DEFAULT_MAX_TEMP
        self.minHumidity = self.DEFAULT_MIN_HUMIDITY
        self.maxHumidity = self.DEFAULT_MAX_HUMIDITY
        self.externalTempOffset = config.getint('Sensor', 'externalTempOffset')
        self.internalTempOffset = config.getint('Sensor', 'internalTempOffset')
        self.refreshRate = config.getint(
            'Sensor', 'refreshRate') or self.DEFAULT_REFRESH_RATE
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
        self.radioChannel = config.get('MQTT', 'radioChannel')