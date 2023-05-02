# ChickenPenController

Small project to control the temperature in a chicken pen, integrated with HomeAssistant

## Schematics

![schematics](Schematics.png "Schematics")

## Configuration

The script need a ChickenPenController.config to work:

[Sensor]

refreshRate=2 how many times the script check the sensors

dhtPinExternal=4 control pin for the external humidity/temperature sensor, BCM mode

dhtPinInternal=5 control pin for the internal humidity/temperature sensor, BCM mode

fanPin=6 control pin for the fan of the chicken pen, BCM mode

heatherPin=7,8 control pins for for the heather and heather fan of the chicken pen, BCM mode

radioPin=9 control pin for the radio, BCM mode

rpiFanPin=10 control pin for the raspberry fan, BCM mode

externalTempOffset=0 temperature offset to add precision on the temperature reading

internalTempOffset=0temperature offset to add precision on the temperature reading

[MQTT]

mqttActive=False start the communication with the HomeAssistant server

host= ip of the server

user= user to login

password= password to login

topic=homeassistant topic subscription

externalTemperatureChannel=externalTemperatureChannel

externalHumidityChannel=externalHumidityChannel

internalTemperatureChannel=internalTemperatureChannel

internalHumidityChannel=internalHumidityChannel

fanStatusChannel=fanStatusChannel

heatherStatusChannel=heatherStatusChannel