#!/usr/bin/env python3
"""Test unitaire complet pour la compatibilité Open Firenet local dans rika_firenet."""
import json
import unittest
from unittest.mock import MagicMock, patch

# Mock des modules homeassistant avant import du composant
import sys
from types import ModuleType

ha_mock = ModuleType("homeassistant")
ha_mock.__path__ = []
ha_helpers_mock = ModuleType("homeassistant.helpers")
ha_helpers_mock.__path__ = []
ha_const_mock = ModuleType("homeassistant.const")
ha_climate_mock = ModuleType("homeassistant.components.climate")
ha_climate_const_mock = ModuleType("homeassistant.components.climate.const")
ha_coord_mock = ModuleType("homeassistant.helpers.update_coordinator")
ha_entity_mock = ModuleType("homeassistant.helpers.entity")
ha_config_entries = ModuleType("homeassistant.config_entries")
ha_cv_mock = ModuleType("homeassistant.helpers.config_validation")

class ConfigEntry:
    pass

ha_config_entries.ConfigEntry = ConfigEntry
ha_cv_mock.empty_config_schema = MagicMock(return_value=lambda x: x)
ha_mock.core = ModuleType("homeassistant.core")
ha_mock.core.HomeAssistant = MagicMock
ha_mock.exceptions = ModuleType("homeassistant.exceptions")
class ConfigEntryNotReady(Exception): pass
ha_mock.exceptions.ConfigEntryNotReady = ConfigEntryNotReady
sys.modules["homeassistant.core"] = ha_mock.core
sys.modules["homeassistant.exceptions"] = ha_mock.exceptions

ha_const_mock.CONF_USERNAME = "username"
ha_const_mock.CONF_PASSWORD = "password"
ha_const_mock.CONF_HOST = "host"
class Platform:
    CLIMATE = "climate"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    SWITCH = "switch"
    NUMBER = "number"
ha_const_mock.Platform = Platform
ha_const_mock.EntityCategory = MagicMock()
ha_const_mock.PERCENTAGE = "%"
ha_const_mock.UnitOfMass = MagicMock()
ha_const_mock.UnitOfTemperature = MagicMock()
ha_const_mock.UnitOfTime = MagicMock()

ha_climate_const_mock.PRESET_COMFORT = "comfort"
ha_climate_const_mock.PRESET_NONE = "none"
ha_climate_const_mock.HVACMode = MagicMock()
ha_climate_const_mock.HVACAction = MagicMock()

class DataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_method, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval

class UpdateFailed(Exception):
    pass

ha_coord_mock.DataUpdateCoordinator = DataUpdateCoordinator
ha_coord_mock.UpdateFailed = UpdateFailed

bs4_mock = ModuleType("bs4")
bs4_mock.BeautifulSoup = MagicMock()
sys.modules["bs4"] = bs4_mock
sys.modules["homeassistant"] = ha_mock
sys.modules["homeassistant.helpers"] = ha_helpers_mock
sys.modules["homeassistant.const"] = ha_const_mock
sys.modules["homeassistant.components.climate"] = ha_climate_mock
sys.modules["homeassistant.components.climate.const"] = ha_climate_const_mock
sys.modules["homeassistant.helpers.update_coordinator"] = ha_coord_mock
sys.modules["homeassistant.helpers.entity"] = ha_entity_mock
sys.modules["homeassistant.config_entries"] = ha_config_entries
sys.modules["homeassistant.helpers.config_validation"] = ha_cv_mock

# Imports du composant
from custom_components.rika_firenet.const import (
    CONNECTION_TYPE_LOCAL,
    CONNECTION_TYPE_CLOUD,
)
from custom_components.rika_firenet.core import (
    RikaFirenetCoordinator,
    RikaFirenetStove,
)


class TestOpenFirenetCompatibility(unittest.TestCase):
    def setUp(self):
        self.hass = MagicMock()
        with open("/home/sandbox/github/open-firenet/tools/screenshot_fixtures/state.json", "r") as f:
            self.fixture_state = json.load(f)

    def test_normalization_openfirenet_state(self):
        """Vérifie la normalisation du JSON Open Firenet vers le modèle Rika Firenet."""
        coord = RikaFirenetCoordinator(
            self.hass,
            username=None,
            password=None,
            default_temperature=21,
            default_scan_interval=15,
            connection_type=CONNECTION_TYPE_LOCAL,
            host="192.168.1.50"
        )
        norm = coord._normalize_openfirenet_state(self.fixture_state, "stove_test")

        self.assertIn("sensors", norm)
        self.assertIn("controls", norm)
        self.assertIn("stoveFeatures", norm)

        # Vérifications sensors
        sensors = norm["sensors"]
        self.assertEqual(sensors.get("inputRoomTemperature"), "22.5")
        self.assertEqual(sensors.get("inputFlameTemperature"), 18)
        self.assertEqual(sensors.get("parameterFeedRateTotal"), 7065)
        self.assertEqual(sensors.get("parameterRuntimePellets"), 4354)
        self.assertEqual(sensors.get("parameterFeedRateService"), 699)
        self.assertEqual(sensors.get("statusMainState"), 1)
        self.assertEqual(sensors.get("statusSubState"), 0)
        self.assertEqual(sensors.get("statusWifiStrength"), -51)
        self.assertEqual(sensors.get("inputDoor"), 1)
        self.assertEqual(sensors.get("inputCover"), 1)
        self.assertEqual(sensors.get("inputGridContact"), 1)

        # Vérifications controls
        controls = norm["controls"]
        self.assertEqual(controls.get("onOff"), False)
        self.assertEqual(controls.get("operatingMode"), 2)
        self.assertEqual(controls.get("targetTemperature"), 18.0)
        self.assertEqual(controls.get("heatingPower"), 70)
        self.assertEqual(controls.get("frostProtectionActive"), True)
        self.assertEqual(controls.get("frostProtectionTemperature"), 8)

        # Intégration Stove
        stove = RikaFirenetStove(coord, "stove_test", "Rika Test")
        stove.update_internal_state(norm)
        self.assertEqual(stove.get_room_temperature(), 22.5)
        self.assertEqual(stove.get_stove_temperature(), 18)
        self.assertEqual(stove.get_stove_consumption(), 7065)
        self.assertEqual(stove.get_stove_operation_mode(), 2)
        self.assertEqual(stove.get_configuration_url(), "http://192.168.1.50")
        self.assertTrue(stove.is_door_closed())
        self.assertTrue(stove.is_cover_closed())
        self.assertTrue(stove.is_grid_contact_ok())

    @patch("requests.Session.get")
    def test_setup_stoves_local(self, mock_get):
        """Vérifie la découverte locale du poêle via GET /api/state."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.fixture_state
        mock_get.return_value = mock_resp

        coord = RikaFirenetCoordinator(
            self.hass,
            username=None,
            password=None,
            default_temperature=21,
            default_scan_interval=15,
            connection_type=CONNECTION_TYPE_LOCAL,
            host="open-firenet.local"
        )
        stoves = coord.setup_stoves()
        self.assertEqual(len(stoves), 1)
        self.assertEqual(stoves[0].get_id(), "1")  # fabNumber: 1 dans le fixture
        self.assertEqual(stoves[0].get_name(), "Rika DOMO")
        self.assertEqual(stoves[0].get_configuration_url(), "http://open-firenet.local")

    @patch("requests.Session.post")
    @patch("requests.Session.get")
    def test_set_stove_controls_local(self, mock_get, mock_post):
        """Vérifie l'envoi des commandes via POST /api/controls."""
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = self.fixture_state
        mock_get.return_value = mock_get_resp

        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.text = "OK"
        mock_post.return_value = mock_post_resp

        coord = RikaFirenetCoordinator(
            self.hass,
            username=None,
            password=None,
            default_temperature=21,
            default_scan_interval=15,
            connection_type=CONNECTION_TYPE_LOCAL,
            host="192.168.1.50"
        )

        res = coord.set_stove_controls("1", {
            "onOff": True,
            "operatingMode": 2,
            "targetTemperature": 21.5,
            "heatingPower": 80
        })

        self.assertIsNotNone(res)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://192.168.1.50/api/controls")
        self.assertEqual(kwargs["json"], {
            "on": True,
            "mode": "comfort",
            "target_temperature": 21.5,
            "power_percent": 80
        })


if __name__ == "__main__":
    unittest.main()
