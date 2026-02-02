from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    Platform,
)
from homeassistant.components.climate.const import (
    PRESET_COMFORT,
    PRESET_NONE,
)

# Configuration
CONF_ENABLED = "enabled"
# CONF_USERNAME et CONF_PASSWORD sont importés depuis homeassistant.const
CONF_DEFAULT_TEMPERATURE = "defaultTemperature"
CONF_DEFAULT_SCAN_INTERVAL  = "defaultScanInterval"
DATA = "data"
UPDATE_TRACK = "update_track"

# Platforms
# Utilisation de l'enum Platform (standard moderne)
PLATFORMS = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]

# Types
SUPPORT_PRESET = [PRESET_NONE, PRESET_COMFORT]

# API Endpoints
BASE_URL = "https://www.rika-firenet.com"
LOGIN_URL = f"{BASE_URL}/web/login"
SUMMARY_URL = f"{BASE_URL}/web/summary"
STATUS_URL = f"{BASE_URL}/api/client/{{stove_id}}/status"
CONTROLS_URL = f"{BASE_URL}/api/client/{{stove_id}}/controls"

VERSION = "2.29.39"
DOMAIN = "rika_firenet"

UNIQUE_ID = "unique_id"

DEFAULT_NAME = "RIKA"
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
