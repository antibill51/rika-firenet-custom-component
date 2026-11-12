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
class HomeAssistantError(Exception): pass
class ServiceValidationError(Exception): pass
ha_mock.exceptions.ConfigEntryNotReady = ConfigEntryNotReady
ha_mock.exceptions.HomeAssistantError = HomeAssistantError
ha_mock.exceptions.ServiceValidationError = ServiceValidationError
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
    BUTTON = "button"
    TIME = "time"
ha_const_mock.Platform = Platform
ha_const_mock.EntityCategory = MagicMock()
ha_const_mock.PERCENTAGE = "%"
ha_const_mock.UnitOfMass = MagicMock()
ha_const_mock.UnitOfTemperature = MagicMock()
ha_const_mock.UnitOfTime = MagicMock()

ha_climate_const_mock.PRESET_COMFORT = "comfort"
ha_climate_const_mock.PRESET_NONE = "none"
class HVACMode:
    OFF = "off"
    HEAT = "heat"
    AUTO = "auto"
class HVACAction:
    OFF = "off"
    HEATING = "heating"
    IDLE = "idle"
class ClimateEntityFeature:
    TARGET_TEMPERATURE = 1
    PRESET_MODE = 16
    TURN_OFF = 128
    TURN_ON = 256
class ClimateEntity:
    pass
ha_climate_const_mock.HVACMode = HVACMode
ha_climate_const_mock.HVACAction = HVACAction
ha_climate_mock.ClimateEntity = ClimateEntity
ha_climate_mock.HVACMode = HVACMode
ha_climate_mock.ClimateEntityFeature = ClimateEntityFeature
ha_climate_mock.PRESET_COMFORT = "comfort"
ha_climate_mock.PRESET_NONE = "none"
ha_climate_mock.HVACAction = HVACAction
ha_const_mock.ATTR_TEMPERATURE = "temperature"

ha_sensor_mock = ModuleType("homeassistant.components.sensor")
class SensorDeviceClass:
    WEIGHT = "weight"
    DURATION = "duration"
    TEMPERATURE = "temperature"
    SIGNAL_STRENGTH = "signal_strength"
class SensorStateClass:
    TOTAL_INCREASING = "total_increasing"
    MEASUREMENT = "measurement"
    TOTAL = "total"
class SensorEntity:
    pass
ha_sensor_mock.SensorDeviceClass = SensorDeviceClass
ha_sensor_mock.SensorStateClass = SensorStateClass
ha_sensor_mock.SensorEntity = SensorEntity

ha_binary_sensor_mock = ModuleType("homeassistant.components.binary_sensor")
class BinarySensorDeviceClass:
    DOOR = "door"
    OPENING = "opening"
    PROBLEM = "problem"
    RUNNING = "running"
class BinarySensorEntity:
    pass
ha_binary_sensor_mock.BinarySensorDeviceClass = BinarySensorDeviceClass
ha_binary_sensor_mock.BinarySensorEntity = BinarySensorEntity

ha_switch_mock = ModuleType("homeassistant.components.switch")
class SwitchEntity:
    pass
ha_switch_mock.SwitchEntity = SwitchEntity

ha_number_mock = ModuleType("homeassistant.components.number")
class NumberEntity:
    pass
ha_number_mock.NumberEntity = NumberEntity

ha_button_mock = ModuleType("homeassistant.components.button")
class ButtonEntity:
    pass
ha_button_mock.ButtonEntity = ButtonEntity

ha_time_mock = ModuleType("homeassistant.components.time")
class TimeEntity:
    pass
ha_time_mock.TimeEntity = TimeEntity

ha_selector_mock = ModuleType("homeassistant.helpers.selector")
ha_selector_mock.EntitySelector = MagicMock(return_value=lambda x: x)
ha_selector_mock.EntitySelectorConfig = MagicMock(return_value=lambda x: x)

ha_ep_mock = ModuleType("homeassistant.helpers.entity_platform")
ha_ep_mock.AddEntitiesCallback = MagicMock
sys.modules["homeassistant.helpers.entity_platform"] = ha_ep_mock

class CoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = getattr(coordinator, "hass", None)
    @property
    def available(self):
        return getattr(self.coordinator, "last_update_success", True)

class DataUpdateCoordinator:
    def __init__(self, hass, logger, name, update_method, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_method = update_method
        self.update_interval = update_interval
        self.last_update_success = True
        self.data = {}
    async def async_refresh(self):
        try:
            self.data = await self.update_method()
            self.last_update_success = True
        except Exception:
            self.last_update_success = False
    async def async_request_refresh(self):
        await self.async_refresh()
    def async_update_listeners(self):
        pass

class UpdateFailed(Exception):
    pass

ha_coord_mock.DataUpdateCoordinator = DataUpdateCoordinator
ha_coord_mock.CoordinatorEntity = CoordinatorEntity
ha_coord_mock.UpdateFailed = UpdateFailed
ha_mock.core.callback = lambda f: f

class ConfigFlow:
    def __init_subclass__(cls, **kwargs):
        pass
    def async_create_entry(self, title, data):
        return {"type": "create_entry", "title": title, "data": data}
    def async_show_form(self, step_id, data_schema, errors=None):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

class OptionsFlow:
    pass

ha_config_entries.ConfigFlow = ConfigFlow
ha_config_entries.OptionsFlow = OptionsFlow
ha_config_entries.CONN_CLASS_CLOUD_POLL = "cloud_poll"

vol_mock = ModuleType("voluptuous")
vol_mock.Required = lambda k, default=None: k
vol_mock.Optional = lambda k, default=None: k
vol_mock.In = lambda x: x
vol_mock.Schema = lambda x: x
sys.modules["voluptuous"] = vol_mock

bs4_mock = ModuleType("bs4")
bs4_mock.BeautifulSoup = MagicMock()
sys.modules["bs4"] = bs4_mock
sys.modules["homeassistant"] = ha_mock
sys.modules["homeassistant.helpers"] = ha_helpers_mock
sys.modules["homeassistant.const"] = ha_const_mock
sys.modules["homeassistant.components.climate"] = ha_climate_mock
sys.modules["homeassistant.components.climate.const"] = ha_climate_const_mock
sys.modules["homeassistant.components.sensor"] = ha_sensor_mock
sys.modules["homeassistant.components.binary_sensor"] = ha_binary_sensor_mock
sys.modules["homeassistant.components.switch"] = ha_switch_mock
sys.modules["homeassistant.components.number"] = ha_number_mock
sys.modules["homeassistant.components.button"] = ha_button_mock
sys.modules["homeassistant.components.time"] = ha_time_mock
ha_dr_mock = ModuleType("homeassistant.helpers.device_registry")
class DeviceEntry: pass
ha_dr_mock.DeviceEntry = DeviceEntry
ha_dr_mock.async_get = MagicMock()
ha_dr_mock.async_entries_for_config_entry = MagicMock(return_value=[])
ha_er_mock = ModuleType("homeassistant.helpers.entity_registry")
class RegistryEntry: pass
ha_er_mock.RegistryEntry = RegistryEntry
ha_er_mock.async_get = MagicMock()
ha_er_mock.async_entries_for_device = MagicMock()
sys.modules["homeassistant.helpers.device_registry"] = ha_dr_mock
sys.modules["homeassistant.helpers.entity_registry"] = ha_er_mock
ha_helpers_mock.device_registry = ha_dr_mock
ha_helpers_mock.entity_registry = ha_er_mock
sys.modules["homeassistant.helpers.selector"] = ha_selector_mock
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
        self.assertEqual(sensors.get("inputBoardTemperature"), "27.0")
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
        self.assertEqual(controls.get("RoomPowerRequest"), 3)
        self.assertEqual(controls.get("frostProtectionActive"), True)
        self.assertEqual(controls.get("frostProtectionTemperature"), 8)
        self.assertEqual(controls.get("bakeTemperature"), 180)

        # Intégration Stove
        stove = RikaFirenetStove(coord, "stove_test", "Rika Test")
        stove.update_internal_state(norm)
        self.assertEqual(stove.get_room_temperature(), 22.5)
        self.assertEqual(stove.get_stove_temperature(), 18)
        self.assertEqual(stove.get_board_temperature(), 27.0)
        self.assertEqual(stove.get_bake_temperature(), 180)
        self.assertEqual(stove.get_stove_consumption(), 7065)
        self.assertEqual(stove.get_stove_operation_mode(), 2)
        self.assertEqual(stove.get_room_power_request(), 3)
        self.assertEqual(stove.get_configuration_url(), "http://192.168.1.50")
        self.assertTrue(stove.is_door_closed())
        self.assertTrue(stove.is_cover_closed())
        self.assertTrue(stove.is_grid_contact_ok())
        stove.set_bake_temperature(210)
        self.assertEqual(stove.get_bake_temperature(), 210)

    def test_edge_cases_manual_null_and_disconnected(self):
        """Vérifie le comportement en mode manuel (target_temperature=null), sans raw_sensors et poêle non lié."""
        coord = RikaFirenetCoordinator(
            self.hass,
            username=None,
            password=None,
            default_temperature=21,
            default_scan_interval=15,
            connection_type=CONNECTION_TYPE_LOCAL,
            host="192.168.1.50"
        )
        raw_edge = {
            "device": {"connected": False, "wifi_rssi": -65},
            "version_ack": False,
            "stove": {"state_code": 0, "sub_state": 0, "model_name": None},
            "sensors": {
                "room_temperature": None,
                "door_open": True,
                "hopper_open": True,
                "grid_problem": True,
                "external_request": True,
                "log_runtime_hours": 15,
                "air_flaps_percent": None,
            },
            "controls": {
                "on": True,
                "mode": "manual",
                "mode_code": 0,
                "target_temperature": None,
                "power_percent": 65,
                "room_power_request": 2,
                "eco_mode_possible": True,
            },
            "raw_sensors": {},
        }
        norm = coord._normalize_openfirenet_state(raw_edge, "stove_edge")
        self.assertEqual(norm["lastSeenMinutes"], 99)
        self.assertIsNone(norm["controls"]["targetTemperature"])
        self.assertEqual(norm["controls"]["RoomPowerRequest"], 2)
        self.assertTrue(norm["stoveFeatures"].get("ecoModePossible"))
        self.assertTrue(norm["stoveFeatures"].get("logRuntime"))
        self.assertFalse(norm["stoveFeatures"].get("airFlaps", False))

        stove = RikaFirenetStove(coord, "stove_edge", "Rika Edge")
        stove.update_internal_state(norm)
        self.assertEqual(stove.get_status_text(), "offline")
        self.assertFalse(stove.is_door_closed())
        self.assertFalse(stove.is_cover_closed())
        self.assertFalse(stove.is_grid_contact_ok())
        self.assertTrue(stove.is_external_request())
        self.assertEqual(stove.get_stove_runtime_logs(), 15)

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
            "heatingPower": 80,
            "bakeTemperature": 200,
            "heatTimeMon1": 6000800,
        })

        self.assertIsNotNone(res)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://192.168.1.50/api/controls")
        self.assertEqual(kwargs["json"], {
            "on": True,
            "mode": "comfort",
            "target_temperature": 21.5,
            "power_percent": 80,
            "bake_target_temperature": 200,
            "heatTimeMon1": 6000800,
        })

    def test_v28_eco_mode_exclusion_and_entities(self):
        """Vérifie l'exclusion de ecoModePossible sur profil V28 et l'instanciation de toutes les plateformes HA."""
        from custom_components.rika_firenet.climate import RikaFirenetStoveClimate
        from custom_components.rika_firenet.sensor import RikaFirenetStoveSensor, get_sensor_device_list
        from custom_components.rika_firenet.binary_sensor import RikaFirenetStoveBinarySensor, BINARY_SENSOR_ATTRIBUTES
        from custom_components.rika_firenet.switch import RikaFirenetStoveSwitch, get_switch_device_list
        from custom_components.rika_firenet.number import RikaFirenetStoveNumber, get_number_device_list

        coord = RikaFirenetCoordinator(
            self.hass,
            username=None,
            password=None,
            default_temperature=21,
            default_scan_interval=15,
            connection_type=CONNECTION_TYPE_LOCAL,
            host="192.168.1.50"
        )
        # 1. Test profil V28 : ecoModePossible doit être désactivé même si eco_mode_possible=True
        v28_state = dict(self.fixture_state)
        v28_state["version_frame"] = "V28"
        v28_state["controls"] = dict(self.fixture_state["controls"], eco_mode_possible=True)
        norm_v28 = coord._normalize_openfirenet_state(v28_state, "stove_v28")
        self.assertFalse(norm_v28["stoveFeatures"].get("ecoModePossible", False))

        # 2. Test toutes les entités sur l'état normalisé DOMO
        norm = coord._normalize_openfirenet_state(self.fixture_state, "stove_domo")
        stove = RikaFirenetStove(coord, "stove_domo", "Rika DOMO")
        stove.update_internal_state(norm)
        entry = MagicMock()

        # Climate
        clim = RikaFirenetStoveClimate(entry, stove, coord)
        self.assertEqual(clim.current_temperature, 22.5)
        self.assertEqual(clim.target_temperature, 18.0)
        self.assertEqual(clim.preset_mode, "comfort")
        self.assertEqual(clim.hvac_mode, "off")
        self.assertIn("http://192.168.1.50", clim.device_info["configuration_url"])

        # Sensors
        sensor_names = get_sensor_device_list(stove)
        self.assertIn("stove consumption", sensor_names)
        self.assertIn("board temperature", sensor_names)
        for s_name in sensor_names:
            s_ent = RikaFirenetStoveSensor(entry, stove, coord, s_name)
            _ = s_ent.native_value

        # Test airflaps & airflaps target
        af_state = dict(self.fixture_state)
        af_state["sensors"] = dict(self.fixture_state["sensors"], air_flaps_percent=12.5, air_flaps_target_percent=15.0)
        norm_af = coord._normalize_openfirenet_state(af_state, "stove_af")
        stove_af = RikaFirenetStove(coord, "stove_af", "Rika AF")
        stove_af.update_internal_state(norm_af)
        af_sensors = get_sensor_device_list(stove_af)
        self.assertIn("airflaps", af_sensors)
        self.assertIn("airflaps target", af_sensors)
        self.assertEqual(stove_af.get_outputAirFlaps(), 12.5)
        self.assertEqual(stove_af.get_outputAirFlapsTargetPosition(), 15.0)

        # Test notification de timeout local vs cloud
        coord._notify_command_timeout(stove, 305, 300)
        self.hass.services.call.assert_called()
        call_args = self.hass.services.call.call_args[0]
        self.assertIn("le pont local Open Firenet", call_args[2]["message"])

        # Binary Sensors
        for bs_name in BINARY_SENSOR_ATTRIBUTES:
            bs_ent = RikaFirenetStoveBinarySensor(entry, stove, coord, bs_name)
            self.assertIsInstance(bs_ent.is_on, bool)

        # Switches
        switch_names = get_switch_device_list(stove)
        self.assertIn("on off", switch_names)
        self.assertIn("convection fan1", switch_names)
        for sw_name in switch_names:
            sw_ent = RikaFirenetStoveSwitch(entry, stove, coord, sw_name)
            self.assertIsInstance(sw_ent.is_on, bool)

        # Numbers
        num_names = get_number_device_list(stove)
        self.assertIn("heating power", num_names)
        self.assertIn("set back temperature", num_names)
        for n_name in num_names:
            n_ent = RikaFirenetStoveNumber(entry, stove, coord, n_name)
            self.assertIsNotNone(n_ent.native_value)

    def test_config_flow_and_hacs_manifest(self):
        """Vérifie le ConfigFlow (Local & Cloud), le déchargement async_unload_entry et la conformité HACS/Translations."""
        import asyncio
        import os
        from custom_components.rika_firenet.config_flow import RikaFirenetFlowHandler
        from custom_components.rika_firenet import async_setup_entry, async_unload_entry

        flow = RikaFirenetFlowHandler()
        flow.hass = MagicMock()

        async def run_flow():
            # Test connexion locale réussie
            with patch.object(RikaFirenetFlowHandler, "_test_local_connection", return_value=True):
                res = await flow.async_step_user({
                    "connection_type": CONNECTION_TYPE_LOCAL,
                    "host": "192.168.1.50",
                })
                self.assertEqual(res["type"], "create_entry")
                self.assertEqual(res["title"], "Open Firenet (192.168.1.50)")

            # Test connexion locale échouée
            with patch.object(RikaFirenetFlowHandler, "_test_local_connection", return_value=False):
                res_err = await flow.async_step_user({
                    "connection_type": CONNECTION_TYPE_LOCAL,
                    "host": "192.168.1.99",
                })
                self.assertEqual(res_err["type"], "form")
                self.assertEqual(res_err["errors"]["base"], "cannot_connect")

            # Test setup & unload entry
            hass = MagicMock()
            hass.data = {}
            async def async_exec(func, *args):
                return func(*args)
            hass.async_add_executor_job = async_exec
            async def async_fwd(e, p):
                return True
            async def async_unl(e, p):
                return True
            hass.config_entries.async_forward_entry_setups = async_fwd
            hass.config_entries.async_unload_platforms = async_unl

            entry = MagicMock()
            entry.entry_id = "entry_local_1"
            entry.data = {"connection_type": CONNECTION_TYPE_LOCAL, "host": "192.168.1.50"}
            entry.options = {}

            with patch.object(RikaFirenetCoordinator, "setup", return_value=None), \
                 patch.object(RikaFirenetCoordinator, "update", return_value=None):
                ok = await async_setup_entry(hass, entry)
                self.assertTrue(ok)
                self.assertIn("entry_local_1", hass.data["rika_firenet"])
                unloaded = await async_unload_entry(hass, entry)
                self.assertTrue(unloaded)
                self.assertNotIn("entry_local_1", hass.data["rika_firenet"])

        asyncio.run(run_flow())

        # Conformité HACS & manifest.json & traductions JSON
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "hacs.json"), "r") as f:
            hacs_data = json.load(f)
        self.assertIn("name", hacs_data)

        manifest_path = os.path.join(base_dir, "custom_components", "rika_firenet", "manifest.json")
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        for req_key in ("domain", "name", "codeowners", "config_flow", "documentation", "iot_class", "issue_tracker", "requirements", "version"):
            self.assertIn(req_key, manifest)
        self.assertEqual(manifest["domain"], "rika_firenet")

        trans_dir = os.path.join(base_dir, "custom_components", "rika_firenet", "translations")
        for lang in ("fr.json", "en.json"):
            with open(os.path.join(trans_dir, lang), "r") as f:
                tr = json.load(f)
            self.assertIn("connection_type", tr["config"]["step"]["user"]["data"])
            self.assertIn("host", tr["config"]["step"]["user"]["data"])
            self.assertIn("cannot_connect", tr["config"]["error"])

    def test_schedule_and_buttons(self):
        """Tester le module schedule, l'encodage/décodage, la conversion helper HA et les boutons."""
        import asyncio
        from datetime import time
        from custom_components.rika_firenet.schedule import (
            decode_slot,
            encode_slot,
            slots_from_state,
            slots_from_ha_schedule,
            command_key,
            slot_index,
            TooManySlots,
        )
        from custom_components.rika_firenet.button import (
            RikaFirenetScheduleButton,
            BUTTON_TYPES,
            async_setup_entry as async_setup_button_entry,
        )
        from custom_components.rika_firenet.time import (
            RikaFirenetScheduleTime,
            async_setup_entry as async_setup_time_entry,
        )

        # 1. Encodage et décodage des plages
        t_start = time(7, 0)
        t_end = time(12, 30)
        slot_val = encode_slot(t_start, t_end)
        self.assertEqual(slot_val, 7001230)
        d_start, d_end = decode_slot(slot_val)
        self.assertEqual(d_start, t_start)
        self.assertEqual(d_end, t_end)

        # Slot off (0)
        self.assertEqual(encode_slot(t_start, t_start), 0)
        self.assertEqual(decode_slot(0), (time(0, 0), time(0, 0)))

        # Plage fin avant début -> erreur
        with self.assertRaises(ValueError):
            encode_slot(time(14, 0), time(10, 0))

        # 2. slots_from_state
        state_data = {
            "controls_pos": [0, 0, 0, 0, 0, 0, 0] + [7001230] + [0] * 13
        }
        slots = slots_from_state(state_data)
        self.assertEqual(len(slots), 14)
        self.assertEqual(slots[0], 7001230)
        self.assertEqual(slots[1], 0)

        # 3. slots_from_ha_schedule
        ha_plan = {
            "monday": [{"from": "06:30", "to": "09:00"}, {"from": "17:00", "to": "22:00"}],
            "tuesday": [{"from": "07:00", "to": "24:00"}],
            "wednesday": [],
            "thursday": [],
            "friday": [],
            "saturday": [],
            "sunday": [],
        }
        ha_slots = slots_from_ha_schedule(ha_plan)
        self.assertEqual(len(ha_slots), 14)
        self.assertEqual(ha_slots[0], 6300900)
        self.assertEqual(ha_slots[1], 17002200)
        self.assertEqual(ha_slots[2], 7002359)
        self.assertEqual(ha_slots[3], 0)

        # Trop de plages (>2)
        invalid_plan = {
            "monday": [{"from": "06:00", "to": "08:00"}, {"from": "11:00", "to": "13:00"}, {"from": "18:00", "to": "20:00"}]
        }
        with self.assertRaises(TooManySlots):
            slots_from_ha_schedule(invalid_plan)

        # 4. Coordinator schedule pending & send
        hass = MagicMock()
        coord = RikaFirenetCoordinator(hass, "user", "pass", 21, 15, connection_type=CONNECTION_TYPE_LOCAL, host="192.168.1.50")
        stove = RikaFirenetStove(coord, "STOVE123", "Poele Salon")
        stove._state = {
            "controls": {},
            "controls_pos": [0, 0, 0, 0, 0, 0, 0] + [6000800] + [0] * 13,
            "sensors": {},
        }
        coord._stoves = [stove]

        # Lecture initiale depuis state
        self.assertEqual(coord.schedule_time(0, "start", "STOVE123"), time(6, 0))
        self.assertEqual(coord.schedule_time(0, "end", "STOVE123"), time(8, 0))
        self.assertFalse(coord.schedule_has_pending)

        # Modification locale (pending)
        coord.schedule_set_pending(0, "start", time(7, 15))
        self.assertTrue(coord.schedule_has_pending)
        self.assertEqual(coord.schedule_time(0, "start", "STOVE123"), time(7, 15))

        # Discard
        coord.schedule_discard()
        self.assertFalse(coord.schedule_has_pending)
        self.assertEqual(coord.schedule_time(0, "start", "STOVE123"), time(6, 0))

        # Set pending et schedule_send
        coord.schedule_set_pending(0, "start", time(7, 30))
        captured_controls = {}
        def mock_set_controls(ctrls):
            captured_controls.update(ctrls)
        stove._set_controls = mock_set_controls

        async def run_sched_tests():
            async def async_exec(func, *args):
                return func(*args)
            hass.async_add_executor_job = async_exec
            hass.states.get.return_value = MagicMock()
            hass.services.has_service.return_value = True
            async def async_call_svc(domain, service, data, blocking=True, return_response=False):
                return {"schedule.heating": ha_plan}
            hass.services.async_call = async_call_svc
            async def mock_refresh():
                pass
            coord.async_request_refresh = mock_refresh

            await coord.schedule_send("STOVE123")
            self.assertEqual(captured_controls.get("heatTimeMon1"), 7300800)
            self.assertFalse(coord.schedule_has_pending)

            # schedule_copy_from
            captured_controls.clear()
            await coord.schedule_copy_from("schedule.heating", "STOVE123")
            self.assertEqual(captured_controls.get("heatTimeMon1"), 6300900)
            self.assertEqual(captured_controls.get("heatTimeTue1"), 7002359)

            # Boutons et Time setup
            entry = MagicMock()
            entry.entry_id = "test_entry"
            entry.options = {"schedule_entity": "schedule.heating"}
            hass.data = {"rika_firenet": {entry.entry_id: coord}}

            button_entities = []
            def add_btn_ents(ents, update=True):
                button_entities.extend(ents)
            await async_setup_button_entry(hass, entry, add_btn_ents)
            self.assertEqual(len(button_entities), 3)

            # Test appui sur bouton copy
            copy_btn = next(b for b in button_entities if b._button_key == "schedule_copy")
            captured_controls.clear()
            await copy_btn.async_press()
            self.assertEqual(captured_controls.get("heatTimeMon1"), 6300900)

            # Setup Time entities
            time_entities = []
            def add_time_ents(ents, update=True):
                time_entities.extend(ents)
            await async_setup_time_entry(hass, entry, add_time_ents)
            self.assertEqual(len(time_entities), 28)

        asyncio.run(run_sched_tests())


if __name__ == "__main__":
    unittest.main()
