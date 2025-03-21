import configparser


class ConfigFileParser:

    DEFAULT_MIN_TEMP = 15
    DEFAULT_MAX_TEMP = 30
    DEFAULT_MAX_HUMIDITY = 80
    DEFAULT_REFRESH_RATE = 1

    def __init__(self, configFilePath):
        config = configparser.ConfigParser()
        config.read(configFilePath)
        self.fanPin = config.getint('Sensor', 'fanPin')
        self.heatherPin, self.heatherFanPin = config.get(
            'Sensor', 'heatherPin').split(',')
        self.remoteRelayPin = config.getint('Sensor', 'remoteRelayPin')
        self.rpiFanPin = config.getint('Sensor', 'rpiFanPin')
        self.dhtPinInternal = config.getint('Sensor', 'dhtPinInternal')
        self.dhtPinExternal = config.getint('Sensor', 'dhtPinExternal')
        self.minTemp = self.DEFAULT_MIN_TEMP
        self.maxTemp = self.DEFAULT_MAX_TEMP
        self.maxHumidity = self.DEFAULT_MAX_HUMIDITY
        self.externalTempOffset = config.getint('Sensor', 'externalTempOffset')
        self.internalTempOffset = config.getint('Sensor', 'internalTempOffset')
        self.refreshRate = config.getint(
            'Sensor', 'refreshRate') or self.DEFAULT_REFRESH_RATE
        self.mqttActive = config.getboolean('MQTT', 'mqttActive')
        self.mqttUser = config.get('MQTT', 'user')
        self.mqttPassword = config.get('MQTT', 'password')
        self.mqttHost = config.get('MQTT', 'host')
        self.remoteRelayTopic = config.get('MQTT', 'remoteRelayTopic')
        self.chickenPenTopic = config.get('MQTT', 'chickenPenTopic')
