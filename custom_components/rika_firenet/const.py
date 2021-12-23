from homeassistant.components.climate.const import (PRESET_COMFORT,
                                                    PRESET_NONE)

# Configuration
CONF_ENABLED = "enabled"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEFAULT_TEMPERATURE = "defaultTemperature"
DATA = "data"
UPDATE_TRACK = "update_track"

# Platforms
CLIMATE = "climate"
SENSOR = "sensor"
SWITCH = "switch"
NUMBER = "number"
PLATFORMS = [CLIMATE, SENSOR, SWITCH, NUMBER]

# Types

SUPPORT_PRESET = [PRESET_NONE, PRESET_COMFORT]

VERSION = "0.0.2"
DOMAIN = "rika_firenet"

UNIQUE_ID = "unique_id"

DEFAULT_NAME = "Rika"
NAME = "Rika Firenet"

UPDATE_LISTENER = "update_listener"
ISSUE_URL = "https://github.com/antibill51/rika-firenet-custom-component/issues"

# Defaults
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
