# Rika Firenet (forked from Fockaert/rika-firenet-custom-component)

_Component to integrate with Rika Firenet [rikafirenet]._

## Installation

Use [hacs](https://hacs.xyz/). (Recommended method)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=antibill51&repository=rika-firenet-custom-component)

or:

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `rika_firenet`.
4. Download _all_ the files from the `custom_components/rika_firenet/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Rika Firenet"

## Configuration is done in the UI

## Lovelace: 

![alt text](https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/Screenshot/capture.png)

### HA config :
```yaml
sensor:
  - platform: template
    sensors:
      stove_activity:
        friendly_name: Stove activity
        value_template: >
          {% if states.sensor.rika_domo_stove_burning.state == 'True' %}
            {{states.number.rika_domo_heating_power.state}}
          {%else %}
            {{0}}
          {% endif %}
        unit_of_measurement: "%"
```

### Cards needed :

custom:config-template-card
custom:stack-in-card
custom:simple-thermostat

For pellet in stock : 
I use GSG2.0 for Pellet stock. https://domotique-home.fr/gestion-de-chauffage-stock-de-granules-gsg/

### Lovelace card basic example : 
#### MANUAL (power in percent) : 
```yaml
type: custom:config-template-card
variables:
  IMG: states['climate.rika_domo'].attributes.entity_picture
  POWER: |
    { (states['number.rika_domo_heating_power'].state)*1 }
  STEP: states['number.rika_domo_heating_power'].attributes.step
entities:
  - climate.rika_domo
  - number.rika_domo_heating_power
card:
  type: custom:stack-in-card
  cards:
    - type: picture-elements
      image: https://upload.wikimedia.org/wikipedia/commons/5/59/Empty.png
      elements:
        - type: image
          entity: climate.rika_domo
          image: ${IMG}
          filter: none
          style:
            top: 42%
            left: 50%
            width: 30%
        - type: state-label
          entity: sensor.rika_domo_stove_status
          tap_action: none
          hold_action: none
          style:
            top: 17%
            left: 50%
            font-size: 15px
        - type: state-label
          entity: climate.rika_domo
          attribute: friendly_name
          tap_action: none
          hold_action: none
          style:
            top: 08%
            left: 17%
            font-size: 18px
        - type: state-label
          entity: sensor.stove_activity
          prefix: 'Puissance de chauffe : '
          tap_action: none
          hold_action: none
          style:
            top: 97%
            left: 50%
            font-size: 15px
            color: red
        - type: state-label
          entity: sensor.rika_domo_pellets_before_service
          prefix: 'Service : '
          tap_action: none
          hold_action: none
          style:
            top: 97%
            left: 90%
            font-size: 11px
        - type: state-label
          entity: climate.rika_domo
          attribute: current_temperature
          suffix: °C
          tap_action: none
          hold_action: none
          style:
            color: '#3498db'
            top: 88%
            left: 50%
            font-size: 27px
        - type: state-label
          entity: number.rika_domo_heating_power
          tap_action: none
          hold_action: none
          style:
            top: 42%
            left: 85%
            font-size: 35px
            color: orange
        - type: icon
          icon: mdi:chevron-up
          title: ${POWER+STEP}
          tap_action:
            action: call-service
            service: number.set_value
            service_data:
              entity_id: number.rika_domo_heating_power
              value: ${POWER+STEP}
          hold_action: none
          style:
            top: 20%
            left: 79%
            transform: scale(1,1)
        - type: icon
          icon: mdi:chevron-down
          title: ${POWER-STEP}
          tap_action:
            action: call-service
            service: number.set_value
            service_data:
              entity_id: number.rika_domo_heating_power
              value: ${POWER-STEP}
          hold_action: none
          style:
            top: 54%
            left: 79%
            transform: scale(1,1)
    - type: custom:simple-thermostat
      style: |
        ha-card {
          --st-spacing: 1.5px;
        }
      entity: climate.rika_domo
      show_header: true
      decimals: '1'
      unit: °c
      step_size: '0.5'
      setpoints: false
      header: false
      control: true
      hide:
        state: true
        temperature: true
      layout:
        mode:
          names: true
          icons: false
          headings: false
      control:control:
        - hvac
        - preset
      step_layout: column
```
#### COMFORT (Temperature) : 
```yaml
type: custom:config-template-card
variables:
  IMG: states['climate.rika_domo'].attributes.entity_picture
  POWER: |
    { (states['number.rika_domo_heating_power'].state)*1 }
  TEMP: states['climate.rika_domo'].attributes.temperature
  STEP: states['climate.rika_domo'].attributes.target_temp_step
entities:
  - climate.rika_domo
  - number.rika_domo_heating_power
card:
  type: custom:stack-in-card
  cards:
    - type: picture-elements
      image: https://upload.wikimedia.org/wikipedia/commons/5/59/Empty.png
      elements:
        - type: image
          entity: climate.rika_domo
          image: ${IMG}
          filter: none
          style:
            top: 42%
            left: 50%
            width: 30%
        - type: state-label
          entity: sensor.rika_domo_stove_status
          tap_action: none
          hold_action: none
          style:
            top: 17%
            left: 50%
            font-size: 15px
        - type: state-label
          entity: climate.rika_domo
          attribute: friendly_name
          tap_action: none
          hold_action: none
          style:
            top: 08%
            left: 17%
            font-size: 18px
        - type: state-label
          entity: number.rika_domo_room_power_request
          prefix: 'Puissance de chauffe : '
          suffix: '/4'
          tap_action: none
          hold_action: none
          style:
            top: 97%
            left: 50%
            font-size: 15px
            color: red
        - type: state-label
          entity: sensor.rika_domo_pellets_before_service
          prefix: 'Service : '
          tap_action: none
          hold_action: none
          style:
            top: 97%
            left: 90%
            font-size: 11px
        - type: state-label
          entity: climate.rika_domo
          attribute: current_temperature
          suffix: °C
          tap_action: none
          hold_action: none
          style:
            color: '#3498db'
            top: 88%
            left: 50%
            font-size: 27px
        - type: state-label
          entity: climate.rika_domo
          suffix: °C
          attribute: temperature
          tap_action: none
          hold_action: none
          style:
            top: 42%
            left: 85%
            font-size: 35px
            color: orange
        - type: icon
          icon: mdi:chevron-up
          title: ${TEMP+STEP}
          tap_action:
            action: call-service
            service: climate.set_temperature
            target:
              entity_id: climate.rika_domo
            service_data:
              temperature: ${TEMP+STEP}
          hold_action: none
          style:
            top: 20%
            left: 79%
            transform: scale(1,1)
        - type: icon
          icon: mdi:chevron-down
          title: ${TEMP-STEP}
          tap_action:
            action: call-service
            service: climate.set_temperature
            service_data:
              entity_id: climate.rika_domo
              temperature: ${TEMP-STEP}
          hold_action: none
          style:
            top: 54%
            left: 79%
            transform: scale(1,1)
      card_mod:
        style: |
          ha-card {
            border: none;
            }
    - type: custom:simple-thermostat
      style: |
        ha-card {
          --st-spacing: 1.5px;
        }
      entity: climate.rika_domo
      show_header: true
      decimals: '1'
      unit: °c
      step_size: '0.5'
      setpoints: false
      header: false
      control: true
      hide:
        state: true
        temperature: true
      layout:
        mode:
          names: true
          icons: false
          headings: false
      control:control:
        - hvac
        - preset
      step_layout: column
```

### Informations: 

I bypass Rika built'in thermostat with PID Thermostat.

More examples are in HA config folder. (lovelace / automations / ...)

rika_domo: name of the stove from this component. Replace with your's.

climate.rika: PID thermostat using https://github.com/ScratMan/HASmartThermostat.
climate.rika_z2: PID thermostat for multiair2.

If I forgot elements, ask for it ;)


## Utility meters example: (I don't use it)
```yaml
utility_meter:
  hourly_stove_consumption:
    source: sensor.<stove>_stove_consumption
    cycle: hourly
  daily_stove_consumption:
    source: sensor.<stove>_stove_consumption
    cycle: daily
  weekly_stove_consumption:
    source: sensor.<stove>_stove_consumption
    cycle: weekly
  monthly_stove_consumption:
    source: sensor.<stove>_stove_consumption
    cycle: monthly

  hourly_stove_runtime:
    source: sensor.<stove>_stove_runtime
    cycle: hourly
  daily_stove_runtime:
    source: sensor.<stove>_stove_runtime
    cycle: daily
  weekly_stove_runtime:
    source: sensor.<stove>_stove_runtime
    cycle: weekly
  monthly_stove_runtime:
    source: sensor.<stove>_stove_runtime
    cycle: monthly
```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

Si besoin, les échanges en français sont également acceptés.

***

[rikafirenet]: https://github.com/antibill51/rika-firenet-custom-component
[forum]: https://community.home-assistant.io/
[releases]: https://github.com/antibill51/rika-firenet-custom-component/releases
