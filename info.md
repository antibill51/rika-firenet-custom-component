[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Community Forum][forum-shield]][forum]


**This component will set up the following platforms.**

Platform | Description
-- | --
`climate` | ...
`sensor` | ...

{% if not installed %}
## Installation

1. Click install.
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Rika Firenet".

{% endif %}

## Configuration is done in the UI

Supports both **Rika Firenet Cloud** (`rika-firenet.com`) and **Open Firenet Local HTTP** (`http://open-firenet.local`) connection modes via the Home Assistant Config Flow.

## Data list : 
```
{
   "name":"Rika DOMO",
   "stoveID":"27252457",
   "lastSeenMinutes":0,
   "lastConfirmedRevision":1700195687,
   "controls":{
      "revision":1700195687,
      "onOff":true,
      "operatingMode":0,
      "heatingPower":45,
      "targetTemperature":"21",
      "bakeTemperature":"180",
      "ecoMode":false,
      "heatingTimeMon1":"00000000",
      "heatingTimeMon2":"00000000",
      "heatingTimeTue1":"00000000",
      "heatingTimeTue2":"00000000",
      "heatingTimeWed1":"00000000",
      "heatingTimeWed2":"00000000",
      "heatingTimeThu1":"00000000",
      "heatingTimeThu2":"00000000",
      "heatingTimeFri1":"00000000",
      "heatingTimeFri2":"00000000",
      "heatingTimeSat1":"00000000",
      "heatingTimeSat2":"00000000",
      "heatingTimeSun1":"00000000",
      "heatingTimeSun2":"00000000",
      "heatingTimesActiveForComfort":false,
      "setBackTemperature":"12",
      "convectionFan1Active":false,
      "convectionFan1Level":0,
      "convectionFan1Area":0,
      "convectionFan2Active":true,
      "convectionFan2Level":2,
      "convectionFan2Area":0,
      "frostProtectionActive":false,
      "frostProtectionTemperature":"4",
      "temperatureOffset":"0",
      "RoomPowerRequest":2,
      "debug0":0,
      "debug1":0,
      "debug2":0,
      "debug3":0,
      "debug4":0
   },
   "sensors":{
      "inputRoomTemperature":"18.1",
      "inputFlameTemperature":100,
      "inputBakeTemperature":"1024",
      "statusError":0,
      "statusSubError":0,
      "statusWarning":0,
      "statusService":0,
      "outputDischargeMotor":360,
      "outputDischargeCurrent":31,
      "outputIDFan":1400,
      "outputIDFanTarget":1400,
      "outputInsertionMotor":0,
      "outputInsertionCurrent":0,
      "outputAirFlaps":0,
      "outputAirFlapsTargetPosition":0,
      "outputBurnBackFlapMagnet":false,
      "outputGridMotor":false,
      "outputIgnition":false,
      "inputUpperTemperatureLimiter":true,
      "inputPressureSwitch":true,
      "inputPressureSensor":0,
      "inputGridContact":true,
      "inputDoor":true,
      "inputCover":true,
      "inputExternalRequest":true,
      "inputBurnBackFlapSwitch":true,
      "inputFlueGasFlapSwitch":true,
      "inputBoardTemperature":"2.7",
      "inputCurrentStage":30,
      "inputTargetStagePID":70,
      "inputCurrentStagePID":30,
      "statusMainState":3,
      "statusSubState":1,
      "statusWifiStrength":-67,
      "parameterEcoModePossible":false,
      "parameterFabricationNumber":1,
      "parameterStoveTypeNumber":13,
      "parameterLanguageNumber":3,
      "parameterVersionMainBoard":229,
      "parameterVersionTFT":229,
      "parameterVersionWiFi":112,
      "parameterVersionMainBoardBootLoader":160,
      "parameterVersionTFTBootLoader":150,
      "parameterVersionWiFiBootLoader":101,
      "parameterVersionMainBoardSub":58512,
      "parameterVersionTFTSub":53404,
      "parameterVersionWiFiSub":13301,
      "parameterRuntimePellets":5024,
      "parameterRuntimeLogs":0,
      "parameterFeedRateTotal":4500,
      "parameterFeedRateService":978,
      "parameterServiceCountdownKg":22,
      "parameterServiceCountdownTime":0,
      "parameterIgnitionCount":2087,
      "parameterOnOffCycleCount":197,
      "parameterFlameSensorOffset":-2,
      "parameterPressureSensorOffset":0,
      "parameterErrorCount0":13,
      "parameterErrorCount1":0,
      "parameterErrorCount2":0,
      "parameterErrorCount3":1,
      "parameterErrorCount4":0,
      "parameterErrorCount5":0,
      "parameterErrorCount6":0,
      "parameterErrorCount7":0,
      "parameterErrorCount8":0,
      "parameterErrorCount9":0,
      "parameterErrorCount10":0,
      "parameterErrorCount11":0,
      "parameterErrorCount12":0,
      "parameterErrorCount13":0,
      "parameterErrorCount14":16,
      "parameterErrorCount15":3,
      "parameterErrorCount16":0,
      "parameterErrorCount17":0,
      "parameterErrorCount18":2,
      "parameterErrorCount19":0,
      "statusHeatingTimesNotProgrammed":true,
      "statusFrostStarted":false,
      "parameterSpiralMotorsTuning":-15,
      "parameterIDFanTuning":15,
      "parameterCleanIntervalBig":240,
      "parameterKgTillCleaning":1000,
      "parameterDebug0":0,
      "parameterDebug1":0,
      "parameterDebug2":0,
      "parameterDebug3":0,
      "parameterDebug4":0
   },
   "stoveType":"DOMO MultiAir",
   "stoveFeatures":{
      "multiAir1":true,
      "multiAir2":true,
      "insertionMotor":false,
      "airFlaps":false,
      "logRuntime":false,
      "bakeMode":false
   },
   "oem":"RIKA"
}
```
<!---->
***
Special thanks to the **[Open Firenet](https://github.com/openfirenet/open-firenet)** project for enabling local ESP32 control of Rika stoves.
Si besoin, les échanges en français sont également acceptés.
[rika_firenet]: https://github.com/antibill51/rika-firenet-custom-component
[commits]: https://github.com/antibill51/rika-firenet-custom-component/commits/main
[forum]: https://community.home-assistant.io/
[releases]: https://github.com/antibill51/rika-firenet-custom-component/releases
