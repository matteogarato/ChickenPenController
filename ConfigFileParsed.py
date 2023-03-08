class ConfigFileParsed:
    def __init__(self,
                 fanPin,
                 heatherPin,
                 dhtPinInternal,
                 dhtPinExternal,
                 minTemp,
                 maxTemp,
                 minHumidity,
                 maxHumidity,
                 refreshRate,
                 mqttUser,
                 mqttPassword,
                 mqttTopic,
                 mqttHost,
                 externalTemperatureChannel,
                 externalHumidityChannel,
                 internalTemperatureChannel,
                 internalHumidityChannel,
                 fanStatusChannel,
                 heatherStatusChannel):
        self.fanPin = fanPin
        self.heatherPin = heatherPin
        self.dhtPinInternal = dhtPinInternal
        self.dhtPinExternal = dhtPinExternal
        self.minTemp = minTemp
        self.maxTemp = maxTemp
        self.minHumidity = minHumidity
        self.maxHumidity = maxHumidity
        self.refreshRate = refreshRate
        self.mqttUser = mqttUser
        self.mqttPassword = mqttPassword
        self.mqttTopic = mqttTopic
        self.mqttHost = mqttHost
        self.externalTemperatureChannel = externalTemperatureChannel
        self.externalHumidityChannel = externalHumidityChannel
        self.internalTemperatureChannel = internalTemperatureChannel
        self.internalHumidityChannel = internalHumidityChannel
        self.fanStatusChannel = fanStatusChannel
        self.heatherStatusChannel = heatherStatusChannel
