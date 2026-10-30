import logging
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from homeassistant.components.climate.const import HVACAction, HVACMode, PRESET_COMFORT, PRESET_NONE
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN,
    LOGIN_URL,
    SUMMARY_URL,
    STATUS_URL,
    CONTROLS_URL,
    CONF_CONNECTION_TYPE,
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_LOCAL,
    CONF_HOST_DEFAULT,
)
from .schedule import (
    SLOT_COUNT,
    TooManySlots,
    command_key,
    decode_slot,
    encode_slot,
    slots_from_ha_schedule,
    slots_from_state,
)

_LOGGER = logging.getLogger(__name__)

class RikaFirenetCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass,
        username,
        password,
        default_temperature,
        default_scan_interval,
        pending_timeout=300,
        connection_type=CONNECTION_TYPE_CLOUD,
        host=None,
    ):
        self.hass = hass
        self._username = username
        self._password = password
        self._connection_type = connection_type or CONNECTION_TYPE_CLOUD
        self._host = (host or CONF_HOST_DEFAULT).strip()
        self._default_temperature = int(default_temperature)
        self._default_scan_interval = timedelta(seconds=default_scan_interval)
        self._pending_timeout = int(pending_timeout)
        self._client = requests.session() # Keep a single session for all requests
        self._stoves: list[RikaFirenetStove] = [] # Type hinting for clarity
        self._number_fail = 0
        self.platforms = []
        self._schedule_pending = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.async_update_data,
            update_interval=self._default_scan_interval
        )

    def is_local_mode(self) -> bool:
        """Return True if using local HTTP connection to Open Firenet."""
        return self._connection_type == CONNECTION_TYPE_LOCAL

    def get_host(self) -> str:
        """Return target host for local connection."""
        return self._host

    @staticmethod
    def test_local_connection(host: str) -> bool:
        """Test HTTP connectivity to Open Firenet /api/state."""
        clean_host = (host or CONF_HOST_DEFAULT).strip()
        if not clean_host.startswith("http://") and not clean_host.startswith("https://"):
            url = f"http://{clean_host}/api/state"
        else:
            url = f"{clean_host.rstrip('/')}/api/state"
        _LOGGER.debug("Testing Open Firenet local connection: %s", url)
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and ("sensors" in data or "controls" in data or "stove" in data):
                _LOGGER.debug("Open Firenet local connection test succeeded.")
                return True
            _LOGGER.warning("Open Firenet answered but JSON payload did not match expected schema.")
            return False
        except Exception as e:
            _LOGGER.warning("Open Firenet local connection test failed: %s", e)
            return False

    @staticmethod
    def test_authentication(username, password):
        """Test authentication with Rika Firenet credentials."""
        _LOGGER.debug("Testing Rika Firenet credentials.")
        client = requests.session()
        data = {'email': username, 'password': password}
        try:
            response = client.post(LOGIN_URL, data, timeout=10)
            response.raise_for_status()
            if '/logout' not in response.text:
                _LOGGER.warning("Authentication test failed: '/logout' not in response.")
                return False
            _LOGGER.debug("Authentication test successful.")
            return True
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Authentication test failed due to network error: {e}")
            return False

    async def async_update_data(self):
        try:
            # The update method will now handle command sending logic
            # and state synchronization.
            await self.hass.async_add_executor_job(self.update)

            # Build the data dictionary for HA entities
            # This dictionary will be available via self.coordinator.data in entities
            data = {}
            if not self._stoves:
                _LOGGER.info("No stoves configured to update data for.")
                return {}

            for stove in self._stoves:
                stove_state = stove.get_state() # Utilise la méthode get_state()
                if stove_state is not None: # Uses the get_state() method
                    data[stove.get_id()] = stove_state
                else:
                    _LOGGER.warning(f"State for stove {stove.get_id()} is None after update. It will be unavailable in HA.")
            
            if not data and self._stoves:
                raise UpdateFailed("Failed to fetch data for any stove.")

            _LOGGER.debug(f"Coordinator async_update_data returning data for stoves: {list(data.keys())}")
            return data

        except Exception as exception:
            _LOGGER.error(f'Update failed for Rika Firenet: {exception}', exc_info=True)
            raise UpdateFailed(f"Error communicating with API: {exception}") from exception

    def setup(self):
        _LOGGER.info("Setting up coordinator")
        try:
            self._stoves = self.setup_stoves()
            if not self._stoves:
                _LOGGER.warning("No stoves found during Rika Firenet setup.")
            else:
                _LOGGER.info(f"Found {len(self._stoves)} stoves:")
                for stove in self._stoves:
                    _LOGGER.info(f"  - ID: {stove.get_id()}, Name: {stove.get_name()}") # Initial state synchronization for each stove
                    stove.sync_state() # sync_state itself logs "Syncing state..."
        except Exception as e:
            _LOGGER.error(f"Error during RikaFirenetCoordinator setup_stoves: {e}", exc_info=True) # Re-raise for ConfigEntryNotReady to be triggered
            raise # Relancer pour que ConfigEntryNotReady soit déclenché

    def get_stoves(self):
        return self._stoves

    def get_stove(self, stove_id):
        """Return stove by ID."""
        for stove in self._stoves:
            if str(stove.get_id()) == str(stove_id):
                return stove
        return None

    def get_default_temperature(self):
        return self._default_temperature

    def get_number_fail(self):
        return self._number_fail

    def _get_local_url(self, endpoint: str) -> str:
        """Construct full URL for local Open Firenet endpoint."""
        clean_host = self._host
        if not clean_host.startswith("http://") and not clean_host.startswith("https://"):
            return f"http://{clean_host}/{endpoint.lstrip('/')}"
        return f"{clean_host.rstrip('/')}/{endpoint.lstrip('/')}"

    def connect(self):
        if self.is_local_mode():
            return
        if not self.is_authenticated():
            data = {'email': self._username, 'password': self._password}
            response = self._client.post(LOGIN_URL, data, timeout=10)
            if '/logout' not in response.text:
                raise Exception('Failed to connect with Rika Firenet')
            _LOGGER.info('Connected to Rika Firenet')

    def is_authenticated(self):
        if self.is_local_mode():
            return True
        sid_cookie = None
        for cookie in self._client.cookies:
            if cookie.name == 'connect.sid':
                sid_cookie = cookie
                break

        if not sid_cookie:
            return False

        if sid_cookie.expires and sid_cookie.expires <= int(datetime.now().timestamp()):
            _LOGGER.debug("Rika Firenet session cookie expired.")
            return False

        return True

    def get_stove_state(self, stove_id):
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                if self.is_local_mode():
                    url = self._get_local_url("/api/state")
                    response = self._client.get(url, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    # Si la réponse est au format natif Open Firenet, on la normalise
                    normalized = self._normalize_openfirenet_state(data, stove_id)
                    _LOGGER.debug(f'get_stove_state local for {stove_id}: {str(normalized)}...')
                    return normalized

                self.connect() # Ensure connection
                url = STATUS_URL.format(stove_id=stove_id) + f'?nocache={int(time.time())}'
                response = self._client.get(url, timeout=10)
                response.raise_for_status() # Raise an exception for HTTP error codes
                data = response.json()
                
                # Validation des données critiques pour les statistiques
                if 'sensors' in data:
                    sensors = data['sensors']
                    critical_fields = ['parameterFeedRateTotal', 'parameterRuntimePellets', 'parameterRuntimeLogs']
                    for field in critical_fields:
                        if field in sensors and sensors[field] is not None:
                            try:
                                int(sensors[field])  # Vérifier que la valeur peut être convertie en entier
                            except (ValueError, TypeError):
                                _LOGGER.warning(f"Invalid {field} value in stove {stove_id} state: {sensors[field]}")
                                data['sensors'][field] = None  # Invalider la valeur
                
                _LOGGER.debug(f'get_stove_state for {stove_id}: {str(data)}...')
                return data
            except requests.exceptions.Timeout:
                _LOGGER.warning(f"Timeout getting state for stove {stove_id} (attempt {attempt + 1}/{MAX_RETRIES})")
            except requests.exceptions.RequestException as e:
                _LOGGER.error(f"RequestException getting state for stove {stove_id} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            except ValueError: # JSON decoding error
                _LOGGER.error(f"Error decoding JSON for stove {stove_id} state (attempt {attempt + 1}/{MAX_RETRIES})")
            
            if attempt < MAX_RETRIES - 1:  # Ne pas attendre après la dernière tentative
                time.sleep(2)  # Attendre 2 secondes avant de réessayer
                
        return None # Return None après l'échec de toutes les tentatives

    def setup_stoves(self):
        if self.is_local_mode():
            url = self._get_local_url("/api/state")
            response = self._client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            stove_id = "local"
            stove_name = "Open Firenet"
            if isinstance(data, dict):
                stove_meta = data.get("stove", {})
                device_meta = data.get("device", {})
                raw_sensors = data.get("raw_sensors", {})
                model_name = stove_meta.get("model_name")
                fab_number = raw_sensors.get("fabNumber") or stove_meta.get("fab_number")
                if fab_number:
                    stove_id = str(fab_number)
                elif device_meta.get("mac"):
                    stove_id = str(device_meta.get("mac")).replace(":", "").lower()
                
                if model_name:
                    stove_name = f"Rika {model_name}"
                elif device_meta.get("name"):
                    stove_name = device_meta.get("name")

            stove = RikaFirenetStove(self, stove_id, stove_name)
            _LOGGER.info(f"Discovered local Open Firenet stove: ID={stove.get_id()}, Name='{stove.get_name()}'")
            return [stove]

        self.connect()
        stoves = []
        response = self._client.get(SUMMARY_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        stove_list = soup.find("ul", {"id": "stoveList"})

        if stove_list:
            for stove_item in stove_list.find_all('li'): # Corrected: use stove_item here
                stove_link = stove_item.find('a', href=True) # Corrected: use stove_item here
                if stove_link and stove_link.attrs['href']:
                    stove_id_from_link = stove_link.attrs['href'].rsplit('/', 1)[-1]
                    stove_display_name = stove_link.text.strip()
                    if not stove_id_from_link:
                        _LOGGER.warning(f"Could not extract stove ID from link: {stove_link.attrs['href']}")
                        continue
                    stove = RikaFirenetStove(self, stove_id_from_link, stove_display_name)
                    _LOGGER.info(f"Discovered stove: ID={stove.get_id()}, Name='{stove.get_name()}'")
                    stoves.append(stove)
                else:
                    _LOGGER.warning(f"Could not find valid link in stove list item: {stove_item}")
        return stoves

    def update(self):
        _LOGGER.debug("Coordinator synchronous update started")

        for stove in self._stoves:
            try:
                if stove.has_pending_changes() and stove.get_state(): # Check if state exists
                    _LOGGER.debug(f"Stove {stove.get_id()} has pending changes. Sending controls.")
                    current_controls = stove.get_control_state()
                    if current_controls:
                        updated_state_after_send = self.set_stove_controls(stove.get_id(), current_controls)
                        if updated_state_after_send:
                            stove.update_internal_state(updated_state_after_send) # Update the stove's internal state
                            stove.clear_pending_changes() # Mark changes as sent
                        else:
                            elapsed = time.time() - (stove.get_controls_changed_time() or time.time())
                            max_pending_time = getattr(self, '_pending_timeout', 300)
                            if elapsed < max_pending_time:
                                _LOGGER.warning(
                                    f"Failed to send controls for stove {stove.get_id()} ({int(elapsed)}s/{max_pending_time}s). "
                                    "Changes remain pending and will be retried on next update."
                                )
                            else:
                                _LOGGER.error(
                                    f"Failed to send controls for stove {stove.get_id()} after {int(elapsed)}s. "
                                    "Clearing pending changes, firing event, and notifying user."
                                )
                                self._notify_command_timeout(stove, elapsed, max_pending_time)
                                stove.clear_pending_changes()
                                stove.sync_state()
                    else:
                        _LOGGER.warning(f"Cannot send controls for stove {stove.get_id()} because control state is missing. Resyncing.")
                        stove.clear_pending_changes()
                        stove.sync_state()
                else:
                    # _LOGGER.debug(f"Syncing state for stove {stove.get_id()}") # Removed, sync_state logs itself
                    stove.sync_state() # Retrieves and updates the stove's state
            except Exception as e:
                _LOGGER.error(f"Error processing stove {stove.get_id()} in coordinator update: {e}", exc_info=True)

    def _normalize_openfirenet_state(self, raw_data: dict, stove_id: str) -> dict:
        """Normalize Open Firenet /api/state response to Rika Firenet cloud schema."""
        if not isinstance(raw_data, dict):
            return {}

        # S'il a déjà les blocs sensors et controls conformes cloud
        if "sensors" in raw_data and "controls" in raw_data and "statusMainState" in raw_data.get("sensors", {}):
            return raw_data

        sensors_dict = {}
        controls_dict = {}
        stove_features = {}

        # 1. Traitement des sensors
        of_sensors = raw_data.get("sensors", {})
        of_stove = raw_data.get("stove", {})
        raw_s = raw_data.get("raw_sensors", {})
        ctrl_pos = raw_data.get("controls_pos", [])

        # Températures
        room_temp = of_sensors.get("room_temperature")
        if room_temp is not None:
            sensors_dict["inputRoomTemperature"] = str(room_temp)
        elif "roomTemp" in raw_s and raw_s["roomTemp"] != 1024:
            sensors_dict["inputRoomTemperature"] = str(float(raw_s["roomTemp"]) / 10.0)

        flame_temp = of_sensors.get("combustion_temperature")
        if flame_temp is not None:
            sensors_dict["inputFlameTemperature"] = int(float(flame_temp))
        elif "flame" in raw_s:
            sensors_dict["inputFlameTemperature"] = int(raw_s["flame"])

        board_temp = of_sensors.get("board_temperature")
        if board_temp is not None:
            sensors_dict["inputBoardTemperature"] = str(board_temp)
        elif "boardSensor" in raw_s:
            sensors_dict["inputBoardTemperature"] = str(raw_s["boardSensor"])

        # Consommation & heures
        if of_sensors.get("pellets_total_kg") is not None:
            sensors_dict["parameterFeedRateTotal"] = int(of_sensors["pellets_total_kg"])
        elif "pelletsTotal" in raw_s:
            sensors_dict["parameterFeedRateTotal"] = int(raw_s["pelletsTotal"])

        if of_sensors.get("pellet_hours") is not None:
            sensors_dict["parameterRuntimePellets"] = int(of_sensors["pellet_hours"])
        elif "pelletHours" in raw_s:
            sensors_dict["parameterRuntimePellets"] = int(raw_s["pelletHours"])

        if "logRuntime" in raw_s and raw_s["logRuntime"] is not None and int(raw_s["logRuntime"]) >= 0:
            sensors_dict["parameterRuntimeLogs"] = int(raw_s["logRuntime"])
        elif of_sensors.get("log_runtime_hours") is not None:
            sensors_dict["parameterRuntimeLogs"] = int(of_sensors["log_runtime_hours"]) * 60

        if of_sensors.get("service_countdown_kg") is not None:
            sensors_dict["parameterFeedRateService"] = int(of_sensors["service_countdown_kg"])
        elif "serviceCountdown" in raw_s:
            sensors_dict["parameterFeedRateService"] = int(raw_s["serviceCountdown"])

        # Moteurs et ventilateurs
        if of_sensors.get("fan_speed_rpm") is not None:
            sensors_dict["outputIDFan"] = int(of_sensors["fan_speed_rpm"])
        elif "idFanMeas" in raw_s:
            sensors_dict["outputIDFan"] = int(raw_s["idFanMeas"])

        if of_sensors.get("auger_speed_rpm") is not None:
            sensors_dict["outputDischargeMotor"] = int(of_sensors["auger_speed_rpm"])
        elif "augerSet" in raw_s:
            sensors_dict["outputDischargeMotor"] = int(raw_s["augerSet"])

        if of_sensors.get("air_flaps_percent") is not None:
            sensors_dict["outputAirFlaps"] = float(of_sensors["air_flaps_percent"]) * 10.0
        elif "airFlaps" in raw_s and raw_s["airFlaps"] is not None:
            sensors_dict["outputAirFlaps"] = float(raw_s["airFlaps"])

        if of_sensors.get("air_flaps_target_percent") is not None:
            sensors_dict["outputAirFlapsTargetPosition"] = float(of_sensors["air_flaps_target_percent"]) * 10.0
        elif "airFlapsTarget" in raw_s and raw_s["airFlapsTarget"] is not None:
            sensors_dict["outputAirFlapsTargetPosition"] = float(raw_s["airFlapsTarget"])

        # États et sous-états
        if of_stove.get("state_code") is not None:
            sensors_dict["statusMainState"] = int(of_stove["state_code"])
        elif "mainState" in raw_s:
            sensors_dict["statusMainState"] = int(raw_s["mainState"])

        if of_stove.get("sub_state") is not None:
            sensors_dict["statusSubState"] = int(of_stove["sub_state"])
        elif "subState" in raw_s:
            sensors_dict["statusSubState"] = int(raw_s["subState"])

        if of_stove.get("error_code") is not None:
            sensors_dict["statusError"] = int(of_stove["error_code"])
        elif "errMask32" in raw_s:
            sensors_dict["statusError"] = int(raw_s["errMask32"])

        if of_stove.get("error_sub") is not None:
            sensors_dict["statusSubError"] = int(of_stove["error_sub"])
        elif "errSub" in raw_s:
            sensors_dict["statusSubError"] = int(raw_s["errSub"])

        if of_stove.get("warning_code") is not None:
            sensors_dict["statusWarning"] = int(of_stove["warning_code"])
        elif "statusWarning" in raw_s:
            sensors_dict["statusWarning"] = int(raw_s["statusWarning"])

        # Booléens & capteurs physiques (avec repli sur of_sensors.*)
        if "door" in raw_s:
            sensors_dict["inputDoor"] = int(raw_s["door"])
        elif "door_open" in of_sensors and of_sensors["door_open"] is not None:
            sensors_dict["inputDoor"] = 0 if bool(of_sensors["door_open"]) else 1

        if "hopperLidClosed" in raw_s:
            sensors_dict["inputCover"] = int(raw_s["hopperLidClosed"])
        elif "hopper_open" in of_sensors and of_sensors["hopper_open"] is not None:
            sensors_dict["inputCover"] = 0 if bool(of_sensors["hopper_open"]) else 1

        if "gridContact" in raw_s:
            sensors_dict["inputGridContact"] = int(raw_s["gridContact"])
        elif "grid_problem" in of_sensors and of_sensors["grid_problem"] is not None:
            sensors_dict["inputGridContact"] = 0 if bool(of_sensors["grid_problem"]) else 1

        if "externalRequest" in raw_s:
            sensors_dict["inputExternalRequest"] = int(raw_s["externalRequest"])
        elif "external_request" in of_sensors and of_sensors["external_request"] is not None:
            sensors_dict["inputExternalRequest"] = 1 if bool(of_sensors["external_request"]) else 0

        if "frostStarted" in raw_s:
            sensors_dict["statusFrostStarted"] = bool(raw_s["frostStarted"])

        # Wifi & Firmware
        device_meta = raw_data.get("device", {})
        if device_meta.get("wifi_rssi") is not None:
            sensors_dict["statusWifiStrength"] = int(device_meta["wifi_rssi"])
        elif of_sensors.get("wifi_rssi") is not None:
            sensors_dict["statusWifiStrength"] = int(of_sensors["wifi_rssi"])
        elif "rssi" in raw_s:
            sensors_dict["statusWifiStrength"] = int(raw_s["rssi"])

        if of_stove.get("mainboard_version") is not None:
            mb_ver = str(of_stove["mainboard_version"]).replace(".", "")
            try:
                sensors_dict["parameterVersionMainBoard"] = int(mb_ver)
            except ValueError:
                sensors_dict["parameterVersionMainBoard"] = of_stove["mainboard_version"]
        elif "appVerBoard" in raw_s:
            sensors_dict["parameterVersionMainBoard"] = int(raw_s["appVerBoard"])

        # 2. Traitement des controls
        of_controls = raw_data.get("controls", {})
        if "on" in of_controls and of_controls["on"] is not None:
            controls_dict["onOff"] = bool(of_controls["on"])
        if of_controls.get("mode_code") is not None:
            controls_dict["operatingMode"] = int(of_controls["mode_code"])
        elif of_controls.get("mode") is not None:
            mode_map = {"manual": 0, "auto": 1, "comfort": 2}
            controls_dict["operatingMode"] = mode_map.get(str(of_controls["mode"]).lower(), 0)

        if of_controls.get("target_temperature") is not None:
            controls_dict["targetTemperature"] = float(of_controls["target_temperature"])
        else:
            controls_dict["targetTemperature"] = None

        if of_controls.get("power_percent") is not None:
            controls_dict["heatingPower"] = int(of_controls["power_percent"])

        if of_controls.get("room_power_request") is not None:
            controls_dict["RoomPowerRequest"] = int(of_controls["room_power_request"])
        elif "roomSensorPower" in raw_s:
            controls_dict["RoomPowerRequest"] = int(raw_s["roomSensorPower"])
        else:
            controls_dict["RoomPowerRequest"] = 3

        if "heating_times_active" in of_controls and of_controls["heating_times_active"] is not None:
            controls_dict["heatingTimesActiveForComfort"] = bool(of_controls["heating_times_active"])
        if of_controls.get("setback_temperature") is not None:
            controls_dict["setBackTemperature"] = float(of_controls["setback_temperature"])

        if "convection_fan1_active" in of_controls and of_controls["convection_fan1_active"] is not None:
            controls_dict["convectionFan1Active"] = bool(of_controls["convection_fan1_active"])
        if of_controls.get("convection_fan1_level") is not None:
            controls_dict["convectionFan1Level"] = int(of_controls["convection_fan1_level"])
        if of_controls.get("convection_fan1_area") is not None:
            controls_dict["convectionFan1Area"] = int(of_controls["convection_fan1_area"])

        if "convection_fan2_active" in of_controls and of_controls["convection_fan2_active"] is not None:
            controls_dict["convectionFan2Active"] = bool(of_controls["convection_fan2_active"])
        if of_controls.get("convection_fan2_level") is not None:
            controls_dict["convectionFan2Level"] = int(of_controls["convection_fan2_level"])
        if of_controls.get("convection_fan2_area") is not None:
            controls_dict["convectionFan2Area"] = int(of_controls["convection_fan2_area"])

        if "frost_protection_active" in of_controls and of_controls["frost_protection_active"] is not None:
            controls_dict["frostProtectionActive"] = bool(of_controls["frost_protection_active"])
        if of_controls.get("frost_protection_temperature") is not None:
            controls_dict["frostProtectionTemperature"] = int(round(float(of_controls["frost_protection_temperature"])))
        if of_controls.get("bake_target_temperature") is not None:
            controls_dict["bakeTemperature"] = int(round(float(of_controls["bake_target_temperature"])))
        if of_controls.get("room_temperature_offset") is not None:
            controls_dict["temperatureOffset"] = float(of_controls["room_temperature_offset"])
        if "eco_mode" in of_controls and of_controls["eco_mode"] is not None:
            controls_dict["ecoMode"] = bool(of_controls["eco_mode"])

        controls_dict["revision"] = int(raw_data.get("revision", 0))

        # 3. Stove features (aligné avec open-firenet.ino::mqttDiscoveryStep)
        version_frame = str(raw_data.get("version_frame", "")).upper()
        if (
            of_sensors.get("air_flaps_percent") is not None
            or of_sensors.get("air_flaps_target_percent") is not None
            or (raw_s.get("airFlaps") or 0) > 0
            or (raw_s.get("airFlapsTarget") or 0) > 0
        ):
            stove_features["airFlaps"] = True
        if (of_controls.get("eco_mode_possible") is True or raw_s.get("ecoModePossible") == 1) and version_frame != "V28":
            stove_features["ecoModePossible"] = True
        if (
            "convection_fan1_active" in of_controls
            or "convection_fan1_level" in of_controls
            or (isinstance(ctrl_pos, list) and len(ctrl_pos) > 23)
        ):
            stove_features["multiAir1"] = True
        if (
            "convection_fan2_active" in of_controls
            or "convection_fan2_level" in of_controls
            or (isinstance(ctrl_pos, list) and len(ctrl_pos) > 26)
        ):
            stove_features["multiAir2"] = True
        if (raw_s.get("logRuntime") or 0) > 0 or (of_sensors.get("log_runtime_hours") or 0) > 0:
            stove_features["logRuntime"] = True

        model_name = of_stove.get("model_name") or raw_data.get("model_name")
        is_linked = bool(raw_data.get("version_ack", True)) and bool(device_meta.get("connected", True))

        return {
            "stoveId": stove_id,
            "stoveType": model_name,
            "lastSeenMinutes": 0 if is_linked else 99,
            "sensors": sensors_dict,
            "controls": controls_dict,
            "stoveFeatures": stove_features,
            "raw": raw_data,
        }

    def _notify_command_timeout(self, stove, elapsed: float, timeout: int):
        """Notify the user and fire an event when stove commands exceed the timeout."""
        try:
            # 1. Fire Home Assistant event on bus
            self.hass.bus.fire(
                "rika_firenet_command_timeout",
                {
                    "stove_id": stove.get_id(),
                    "stove_name": stove.get_name(),
                    "elapsed_seconds": int(elapsed),
                    "timeout_seconds": int(timeout),
                },
            )
            # 2. Create persistent notification in HA UI
            target_label = "le pont local Open Firenet" if self.is_local_mode() else "le cloud"
            self.hass.services.call(
                "persistent_notification",
                "create",
                {
                    "title": f"Rika Firenet - Commande non confirmée ({stove.get_name()})",
                    "message": (
                        f"Les réglages envoyés au poêle **{stove.get_name()}** (ID: {stove.get_id()}) "
                        f"n'ont pas pu être confirmés par {target_label} après {int(elapsed)} secondes "
                        f"(délai configuré : {int(timeout)} s).\n\n"
                        "L'état précédent a été restauré pour garantir la cohérence."
                    ),
                    "notification_id": f"rika_firenet_timeout_{stove.get_id()}",
                },
            )
            _LOGGER.info(f"Dispatched command timeout notification and event for stove {stove.get_id()}")
        except Exception as ex:
            _LOGGER.error(f"Error dispatching timeout notification for stove {stove.get_id()}: {ex}")

    def set_stove_controls(self, stove_id, controls):
        _LOGGER.debug(f"set_stove_controls for {stove_id}, data: {str(controls)}")
        
        if self.is_local_mode():
            # Formatage de la commande pour l'API REST locale Open Firenet: POST /api/controls
            payload = {}
            if "onOff" in controls:
                payload["on"] = bool(controls["onOff"])
            if "operatingMode" in controls:
                mode_int = int(controls["operatingMode"])
                mode_map = {0: "manual", 1: "auto", 2: "comfort"}
                payload["mode"] = mode_map.get(mode_int, "manual")
            if "targetTemperature" in controls and controls["targetTemperature"] is not None:
                payload["target_temperature"] = float(controls["targetTemperature"])
            if "heatingPower" in controls and controls["heatingPower"] is not None:
                payload["power_percent"] = int(controls["heatingPower"])
            if "RoomPowerRequest" in controls and controls["RoomPowerRequest"] is not None:
                rpr = int(controls["RoomPowerRequest"])
                if 1 <= rpr <= 4:
                    payload["room_power_request"] = rpr
            if "heatingTimesActiveForComfort" in controls:
                payload["heating_times_active"] = bool(controls["heatingTimesActiveForComfort"])
            if "setBackTemperature" in controls and controls["setBackTemperature"] is not None:
                payload["setback_temperature"] = float(controls["setBackTemperature"])
            if "convectionFan1Active" in controls:
                payload["convection_fan1_active"] = bool(controls["convectionFan1Active"])
            if "convectionFan1Level" in controls and controls["convectionFan1Level"] is not None:
                payload["convection_fan1_level"] = int(controls["convectionFan1Level"])
            if "convectionFan1Area" in controls and controls["convectionFan1Area"] is not None:
                payload["convection_fan1_area"] = int(controls["convectionFan1Area"])
            if "convectionFan2Active" in controls:
                payload["convection_fan2_active"] = bool(controls["convectionFan2Active"])
            if "convectionFan2Level" in controls and controls["convectionFan2Level"] is not None:
                payload["convection_fan2_level"] = int(controls["convectionFan2Level"])
            if "convectionFan2Area" in controls and controls["convectionFan2Area"] is not None:
                payload["convection_fan2_area"] = int(controls["convectionFan2Area"])
            if "frostProtectionActive" in controls:
                payload["frost_protection_active"] = bool(controls["frostProtectionActive"])
            if "frostProtectionTemperature" in controls and controls["frostProtectionTemperature"] is not None:
                payload["frost_protection_temperature"] = int(controls["frostProtectionTemperature"])
            if "bakeTemperature" in controls and controls["bakeTemperature"] is not None:
                payload["bake_target_temperature"] = int(controls["bakeTemperature"])
            if "temperatureOffset" in controls and controls["temperatureOffset"] is not None:
                payload["room_temperature_offset"] = float(controls["temperatureOffset"])
            if "ecoMode" in controls:
                payload["eco_mode"] = bool(controls["ecoMode"])
            for slot_key in (
                "heatTimeMon1", "heatTimeMon2", "heatTimeTue1", "heatTimeTue2",
                "heatTimeWed1", "heatTimeWed2", "heatTimeThu1", "heatTimeThu2",
                "heatTimeFri1", "heatTimeFri2", "heatTimeSat1", "heatTimeSat2",
                "heatTimeSun1", "heatTimeSun2",
            ):
                if slot_key in controls and controls[slot_key] is not None:
                    payload[slot_key] = int(controls[slot_key])

            for attempt in range(3):
                _LOGGER.info(f'Attempting to update local Open Firenet controls ({attempt + 1}/3)')
                try:
                    url = self._get_local_url("/api/controls")
                    response = self._client.post(url, json=payload, timeout=10)
                    if response.status_code in [200, 204]:
                        _LOGGER.info('Open Firenet controls updated successfully via local HTTP API.')
                        self._number_fail = 0
                        return self.get_stove_state(stove_id)
                    elif response.status_code == 503:
                        _LOGGER.warning(
                            "Local Open Firenet stove is not ready yet (503 stove_not_ready): %s",
                            response.text,
                        )
                    else:
                        _LOGGER.warning(f"Local Open Firenet returned error: {response.status_code} - {response.text}")
                except requests.exceptions.RequestException as e:
                    _LOGGER.warning(f"Network error on attempt {attempt + 1} for local Open Firenet: {e}")

                self._number_fail += 1
                if attempt < 2:
                    time.sleep(1)
            _LOGGER.error(f'Failed to update local Open Firenet controls after 3 attempts')
            return None

        # Mode Cloud Rika Firenet d'origine
        # Always obtain the fresh revision from the cloud to prevent 404 Outdated Revision
        current_state = self.get_stove_state(stove_id)
        if current_state and 'controls' in current_state and 'revision' in current_state['controls']:
            controls['revision'] = current_state['controls']['revision']
            _LOGGER.debug(f"Refreshed revision to {controls['revision']} for stove {stove_id}")
        elif 'revision' not in controls:
            _LOGGER.warning(f"Could not get revision for stove {stove_id}. Sending controls without it.")

        for attempt in range(3): # Reduce the number of attempts for faster feedback
            _LOGGER.info(f'Attempting to update stove {stove_id} controls ({attempt + 1}/3)')
            try:
                response = self._client.post(
                    CONTROLS_URL.format(stove_id=stove_id), json=controls, timeout=15
                )
                if 'OK' in response.text:
                    _LOGGER.info(f'Stove {stove_id} controls updated successfully via API.')
                    self._number_fail = 0
                    # Return fresh state after successful update
                    return self.get_stove_state(stove_id) # Important to get the latest revision
                else:
                    _LOGGER.warning(f"Update for stove {stove_id} API call returned not OK: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                _LOGGER.warning(f"Network error on attempt {attempt + 1} for stove {stove_id}: {e}")

            # This block runs if the update was not successful (not "OK" or a network error)
            self._number_fail += 1
            if attempt < 2:
                time.sleep(2)
                # Update revision before the next attempt, as it might have changed
                current_state_for_rev = self.get_stove_state(stove_id)
                if current_state_for_rev and 'controls' in current_state_for_rev and 'revision' in current_state_for_rev['controls']:
                    controls['revision'] = current_state_for_rev['controls']['revision']
                    _LOGGER.info(f"Updated revision to {controls['revision']} for stove {stove_id} before retry.")
                else:
                    _LOGGER.warning(f"Could not get new revision for stove {stove_id} before retry.")
        _LOGGER.error(f'Failed to update stove {stove_id} controls after 3 attempts')
        return None # Indicate persistent failure

    # --- heating schedule support (local Open Firenet & cloud) -----------------

    @property
    def schedule_has_pending(self) -> bool:
        return bool(self._schedule_pending)

    def schedule_time(self, index: int, edge: str, stove_id: str | None = None):
        """Start or end of a slot: the pending change if there is one, else the stove's value."""
        pending = self._schedule_pending.get((index, edge))
        if pending is not None:
            return pending

        stove = None
        if stove_id:
            stove = self.get_stove(stove_id)
        elif self._stoves:
            stove = self._stoves[0]

        state = stove._state if stove else None
        slots = slots_from_state(state)
        decoded = decode_slot(slots[index]) if slots and index < len(slots) else None
        if decoded is None:
            return None
        return decoded[0] if edge == "start" else decoded[1]

    def schedule_set_pending(self, index: int, edge: str, value) -> None:
        """Keep a changed time; nothing is sent to the stove before schedule_send()."""
        self._schedule_pending[(index, edge)] = value.replace(second=0, microsecond=0)
        self.async_update_listeners()

    def schedule_discard(self) -> None:
        self._schedule_pending.clear()
        self.async_update_listeners()

    async def schedule_send(self, stove_id: str | None = None) -> None:
        """Send every slot that has a pending change, in one command."""
        stove = None
        if stove_id:
            stove = self.get_stove(stove_id)
        elif self._stoves:
            stove = self._stoves[0]

        if not stove:
            raise HomeAssistantError("No stove available to send schedule.")

        slots = slots_from_state(stove._state)
        if slots is None:
            raise HomeAssistantError("Stove not ready to receive schedule.")

        command: dict[str, int] = {}
        for index in sorted({i for i, _ in self._schedule_pending}):
            start = self.schedule_time(index, "start", stove.get_id())
            end = self.schedule_time(index, "end", stove.get_id())
            if start is None or end is None:
                raise HomeAssistantError("Stove schedule slot values are not available.")
            try:
                command[command_key(index)] = encode_slot(start, end)
            except ValueError as err:
                raise ServiceValidationError(
                    f"Slot {command_key(index).removeprefix('heatTime')}: the end ({end.strftime('%H:%M')}) is before the start ({start.strftime('%H:%M')})."
                ) from err

        if not command:
            return

        await self.hass.async_add_executor_job(stove._set_controls, command)
        self._schedule_pending.clear()
        await self.async_request_refresh()

    async def schedule_copy_from(self, schedule_entity: str | None, stove_id: str | None = None) -> None:
        """Send the weekly plan of a Home Assistant schedule to the stove: all 14 slots, in one command."""
        if not schedule_entity:
            raise ServiceValidationError("No schedule entity is chosen in options.")

        if self.hass.states.get(schedule_entity) is None or not self.hass.services.has_service("schedule", "get_schedule"):
            raise ServiceValidationError(f"The schedule entity '{schedule_entity}' cannot be read.")

        response = await self.hass.services.async_call(
            "schedule", "get_schedule", {"entity_id": schedule_entity}, blocking=True, return_response=True
        )
        plan = (response or {}).get(schedule_entity)
        if not isinstance(plan, dict):
            raise ServiceValidationError(f"The schedule plan for '{schedule_entity}' is empty or invalid.")

        try:
            slots = slots_from_ha_schedule(plan)
        except TooManySlots as err:
            raise ServiceValidationError(
                f"The stove takes two time ranges per day, and {err.weekday} has {err.count} in this schedule."
            ) from err

        stove = None
        if stove_id:
            stove = self.get_stove(stove_id)
        elif self._stoves:
            stove = self._stoves[0]

        if not stove:
            raise HomeAssistantError("No stove available to send schedule.")

        command = {command_key(i): slots[i] for i in range(SLOT_COUNT)}
        await self.hass.async_add_executor_job(stove._set_controls, command)
        self._schedule_pending.clear()
        await self.async_request_refresh()

STATUS_RULES = [
    # Priority 1: Errors, connectivity, and critical warnings
    (lambda s: s.get_last_seen_minutes() > 2,
     lambda s: ["https://www.rika-firenet.com/images/status/Warning_WifiSignal.svg", "offline"]),
    (lambda s: s.get_status_warning() == 2,
     lambda s: ["https://www.rika-firenet.com/images/status/Any_Warning.svg", "pellet_lid_open"]),
    (lambda s: s.get_status_error() == 1 and s.get_status_sub_error() == 1,
     lambda s: ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_Error.svg", "Error"]),
    (lambda s: s.get_status_error() == 1 and s.get_status_sub_error() == 2,
     lambda s: ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_Empty.svg", "empty_tank"]),
    (lambda s: s.get_status_error() == 8 and s.get_status_sub_error() == 16,
     lambda s: ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_Error.svg", "not_ignited"]),
    (lambda s: s.get_status_error() == 1,
     lambda s: ["/", "statusSubError" + str(s.get_status_sub_error())]),
    (lambda s: s.get_status_error() == 32768,
     lambda s: ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_smoke_fan.svg", "smoke_fan"]),
    (lambda s: s.is_frost_protection_started(),
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Freeze.svg", "frost_protection"]),

    # Priority 2: Main operational states
    (lambda s: s.get_main_state() == 1 and s.get_sub_state() == 0,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "stove_off"]),
    (lambda s: s.get_main_state() == 1 and s.get_sub_state() in [1, 2, 3],
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Standby.svg", "external_request" if s.get_sub_state() == 2 else "standby"]),
    (lambda s: s.get_main_state() == 1,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "sub_state_unknown"]),
    (lambda s: s.get_main_state() == 2,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Ignition.svg", "ignition_on"]),
    (lambda s: s.get_main_state() == 3,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Ignition.svg", "starting_up"]),
    (lambda s: s.get_main_state() == 4,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Control.svg", "running"]),
    (lambda s: s.get_main_state() == 5 and s.get_sub_state() in [3, 4],
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Clean.svg", "big_clean"]),
    (lambda s: s.get_main_state() == 5,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_Clean.svg", "clean"]),
    (lambda s: s.get_main_state() == 6,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_BurnOff.svg", "burn_off"]),

    # Priority 3: Special modes (e.g., split log)
    (lambda s: s.get_main_state() in [11, 13, 14, 16, 17, 50],
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_check"]),
    (lambda s: s.get_main_state() == 21 and s.get_sub_state() == 12 and s.get_stove_temperature() is not None and 300 <= s.get_stove_temperature() <= 350,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_refuel"]),
    (lambda s: s.get_main_state() == 21 and s.get_sub_state() == 12 and s.get_stove_temperature() is not None and s.get_stove_temperature() < 300,
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_stop_refuel"]),
    (lambda s: s.get_main_state() == 20 and s.is_stove_eco_mode(),
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_ecomode"]),
    (lambda s: s.get_main_state() in [20, 21],
     lambda s: ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_mode"]),
]

class RikaFirenetStove:
    def __init__(self, coordinator, stove_id, name):
        self._coordinator = coordinator
        self._id = stove_id
        self._name = name
        self._state = None
        self._controls_changed = False # Change indicator for this stove
        self._controls_changed_time = None

    def __repr__(self):
        return f'Stove(id={self._id}, name={self._name})'

    def update_internal_state(self, new_state):
        """Updates the stove's internal state."""
        self._state = new_state

    def has_pending_changes(self):
        """Checks if there are pending control changes to be sent."""
        return self._controls_changed

    def clear_pending_changes(self):
        """Resets the pending changes indicator."""
        self._controls_changed = False
        self._controls_changed_time = None

    def _mark_controls_changed(self):
        """Marks that controls have been modified and should be sent."""
        self._controls_changed = True
        if self._controls_changed_time is None:
            self._controls_changed_time = time.time()
        _LOGGER.debug(f"Controls marked changed for stove {self._id}")

    def get_controls_changed_time(self):
        """Return the timestamp when controls were marked changed."""
        return self._controls_changed_time

    def _set_control(self, key: str, value):
        """Helper to set a control value and mark for update."""
        _LOGGER.debug(f"Setting control '{key}' to '{value}' for stove {self._id}")
        if self._state and 'controls' in self._state:
            self._state['controls'][key] = value
            self._mark_controls_changed()
        else:
            _LOGGER.warning(f"Cannot set control '{key}': stove state not available for stove {self._id}.")

    def _set_controls(self, controls_to_set: dict):
        """Helper to set multiple control values and mark for update."""
        _LOGGER.debug(f"Setting multiple controls: {controls_to_set} for stove {self._id}")
        if self._state and 'controls' in self._state:
            for key, value in controls_to_set.items():
                self._state['controls'][key] = value
            self._mark_controls_changed()
        else:
            _LOGGER.warning(f"Cannot set controls: stove state not available for stove {self._id}.")

    def sync_state(self):
        _LOGGER.debug(f"Syncing state for stove {self._id}")
        try:
            new_state = self._coordinator.get_stove_state(self._id)
            if new_state is not None:
                self._state = new_state
            else:
                # Keep the old state if retrieval fails to avoid losing info
                _LOGGER.warning(f"Failed to sync state for stove {self._id}; state remains: {self._state is not None}")
        except Exception as e:
            _LOGGER.error(f"Exception during sync_state for stove {self._id}: {e}", exc_info=True)
            # Optionnel: mettre self._state à None pour indiquer l'indisponibilité
            # self._state = None

# Send command
    def set_temperatureOffset(self, temperature):
        self._set_control('temperatureOffset', float(temperature))

    def set_stove_temperature(self, temperature):
        self._set_control('targetTemperature', float(temperature))

    def set_frost_protection_temperature(self, temperature):
        self._set_control('frostProtectionTemperature', int(temperature))

    def set_stove_set_back_temperature(self, temperature):
        self._set_control('setBackTemperature', float(temperature))

    def set_stove_operation_mode(self, mode):
        self._set_control('operatingMode', int(mode))

    def set_heating_times_active_for_comfort(self, active):
        self._set_controls({
            'onOff': True, # Assumed: changing heating times implies stove should be on or remain on
            'heatingTimesActiveForComfort': bool(active)
        })

    def set_room_power_request(self, power):
        self._set_control('RoomPowerRequest', int(power))

    def set_heating_power(self, power):
        self._set_control('heatingPower', int(power))

    def set_convection_fan1_level(self, level):
        self._set_control('convectionFan1Level', int(level))

    def set_convection_fan1_area(self, area):
        self._set_control('convectionFan1Area', int(area))

    def set_convection_fan2_level(self, level):
        self._set_control('convectionFan2Level', int(level))

    def set_convection_fan2_area(self, area):
        self._set_control('convectionFan2Area', int(area))

    def set_stove_on_off(self, on_off):
        self._set_control('onOff', bool(on_off))

    def turn_heating_times_on(self): 
        controls_to_set = {
            'onOff': True,
            'heatingTimesActiveForComfort': True
        }
        if self.get_stove_operation_mode() != 2:
            controls_to_set['operatingMode'] = 1
        self._set_controls(controls_to_set)

    def turn_heating_times_off(self):
        controls_to_set = {
            'onOff': True, # The stove remains on, only the scheduled heating mode is deactivated
            'heatingTimesActiveForComfort': False
        }
        if self.get_stove_operation_mode() != 2:
            controls_to_set['operatingMode'] = 0 # Mode manuel
        self._set_controls(controls_to_set)

    def turn_convection_fan1_on_off(self, on_off=True):
        self._set_control('convectionFan1Active', bool(on_off))

    def turn_convection_fan2_on_off(self, on_off=True):
        self._set_control('convectionFan2Active', bool(on_off))

    def turn_on_off_eco_mode(self, on_off=False):
        self._set_control('ecoMode', bool(on_off))

    def turn_on_off_frost_protection(self, on_off=False):
        self._set_control('frostProtectionActive', bool(on_off))

# End

    def get_control_state(self):
        if self._state and 'controls' in self._state:
            return self._state['controls']
        return None # Return None if state or controls are not available

    def is_stove_on(self):
        if self._state and 'controls' in self._state and 'onOff' in self._state['controls']:
            return bool(self._state['controls']['onOff'])
        return False # By default, consider off if info is not present

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_state(self):
        return self._state
    
    # Add checks for all get_* methods accessing self._state
    # Example for get_room_temperature:
    def get_room_temperature(self):
        if self._state and 'sensors' in self._state and 'inputRoomTemperature' in self._state['sensors']:
            try:
                return float(self._state['sensors']['inputRoomTemperature'])
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid room temperature value for {self._id}: {self._state['sensors']['inputRoomTemperature']}")
                return None
        return None

    def get_temperatureOffset(self):
        if self._state and 'controls' in self._state and 'temperatureOffset' in self._state['controls']:
            value = self._state['controls']['temperatureOffset']
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid temperatureOffset value for {self._id}: {value}")
                return None
        return None

    def get_room_thermostat(self):
        if self._state and 'controls' in self._state and 'targetTemperature' in self._state['controls']:
            value = self._state['controls']['targetTemperature']
            if value is None:
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid targetTemperature value for {self._id}: {value}")
                return None
        return None

    def is_stove_eco_mode(self):
        return bool(self._state.get('controls', {}).get('ecoMode')) if self._state else False

    def is_frost_protection(self):
        return bool(self._state.get('controls', {}).get('frostProtectionActive')) if self._state else False

    def is_frost_protection_started(self):
        return bool(self._state.get('sensors', {}).get('statusFrostStarted', False)) if self._state else False

    def get_last_seen_minutes(self):
        if self._state and 'lastSeenMinutes' in self._state:
            try:
                return int(self._state['lastSeenMinutes'])
            except (ValueError, TypeError):
                return 99 # Return a high value to indicate an issue
        return 99 # Default to a high value if not present

    def get_stove_set_back_temperature(self):
        if self._state and 'controls' in self._state and 'setBackTemperature' in self._state['controls']:
            value = self._state['controls']['setBackTemperature']
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid setBackTemperature value for {self._id}: {value}")
                return None
        return None

    def get_stove_operation_mode(self):
        return self._state.get('controls', {}).get('operatingMode') if self._state else None

    def is_stove_heating_times_on(self):
        op_mode = self.get_stove_operation_mode()
        if op_mode == 1: # Auto mode is always considered "heating times on"
            return True
        if op_mode == 2: # Comfort mode depends on the specific flag
            return self.is_heating_times_active_for_comfort()
        # Covers op_mode 0 (Manual), None, or any other unexpected value
        return False

    def is_heating_times_active_for_comfort(self):
        return bool(self._state.get('controls', {}).get('heatingTimesActiveForComfort')) if self._state else False

    def get_room_power_request(self):
        if self._state and 'controls' in self._state and 'RoomPowerRequest' in self._state['controls']:
            value = self._state['controls']['RoomPowerRequest']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid RoomPowerRequest value for {self._id}: {value}")
                return None
        return None

    def get_heating_power(self):
        if self._state and 'controls' in self._state and 'heatingPower' in self._state['controls']:
            value = self._state['controls']['heatingPower']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid heatingPower value for {self._id}: {value}")
                return None
        return None

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            self.set_stove_on_off(False)
        elif hvac_mode == HVACMode.AUTO:
            _LOGGER.debug(f"Setting HVAC mode to AUTO for {self._id} (Turn heating times on)")
            self.turn_heating_times_on()
        elif hvac_mode == HVACMode.HEAT:
            _LOGGER.debug(f"Setting HVAC mode to HEAT for {self._id} (Turn heating times off / manual)")
            self.turn_heating_times_off()

    def set_preset_mode(self, preset_mode):
        """Set the stove's operating mode based on a preset."""
        _LOGGER.debug(f"Setting preset_mode for {self._id} to: {preset_mode}")
        if preset_mode == PRESET_COMFORT:
            # Comfort mode is operatingMode 2
            self.set_stove_operation_mode(2)
        else:  # PRESET_NONE
            # PRESET_NONE implies manual control.
            # If heating times are active, turn them off, which will switch to manual mode.
            # Otherwise, just ensure we are in manual mode (0).
            if self.is_stove_heating_times_on():
                self.turn_heating_times_off()
            else:
                self.set_stove_operation_mode(0)

    def is_stove_convection_fan1_on(self):
        return bool(self._state.get('controls', {}).get('convectionFan1Active')) if self._state else False

    def get_convection_fan1_level(self):
        if self._state and 'controls' in self._state and 'convectionFan1Level' in self._state['controls']:
            value = self._state['controls']['convectionFan1Level']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid convectionFan1Level value for {self._id}: {value}")
                return None
        return None

    def get_convection_fan1_area(self):
        if self._state and 'controls' in self._state and 'convectionFan1Area' in self._state['controls']:
            value = self._state['controls']['convectionFan1Area']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid convectionFan1Area value for {self._id}: {value}")
                return None
        return None

    def is_stove_convection_fan2_on(self):
        return bool(self._state.get('controls', {}).get('convectionFan2Active')) if self._state else False

    def get_convection_fan2_level(self):
        if self._state and 'controls' in self._state and 'convectionFan2Level' in self._state['controls']:
            value = self._state['controls']['convectionFan2Level']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid convectionFan2Level value for {self._id}: {value}")
                return None
        return None

    def get_convection_fan2_area(self):
        if self._state and 'controls' in self._state and 'convectionFan2Area' in self._state['controls']:
            value = self._state['controls']['convectionFan2Area']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid convectionFan2Area value for {self._id}: {value}")
                return None
        return None

    def get_hvac_mode(self): # Must be based on the current state
        if not self.is_stove_on(): # Uses the method that checks self._state
            return HVACMode.OFF
        elif self.is_stove_heating_times_on(): # Uses the method that checks self._state
            return HVACMode.AUTO
        # If on but not in AUTO mode (scheduled), then it's HEAT (manual)
        return HVACMode.HEAT

    def get_hvac_action(self) -> HVACAction:
        """Return current operation ie. heat, cool, idle."""
        # First, check if the stove is commanded to be off. This is the most reliable state.
        if not self._state or not self._state.get('controls', {}).get('onOff'):
            return HVACAction.OFF

        main_state = self.get_main_state()
        sub_state = self.get_sub_state()

        # States indicating active heating (ignition, running, split log mode)
        HEATING_STATES = [2, 3, 4, 11, 13, 14, 16, 17, 20, 21, 50]
        # States indicating the stove is on but not actively producing heat (standby, cleaning, burn-off)
        IDLE_STATES = [5, 6]

        if main_state in HEATING_STATES:
            return HVACAction.HEATING
        elif main_state in IDLE_STATES:
            return HVACAction.IDLE
        elif main_state == 1:  # Special handling for standby/off states
            if sub_state == 0:  # Explicitly off
                return HVACAction.OFF
            return HVACAction.IDLE # Other sub-states are standby
        return HVACAction.OFF # Default for unknown or off states

    def get_preset_mode(self):
        """Return the current preset mode."""
        op_mode = self.get_stove_operation_mode()
        return PRESET_COMFORT if op_mode == 2 else PRESET_NONE

    def is_stove_burning(self):
        return self.get_main_state() in [4, 5]

    def get_stove_consumption(self):
        if self._state and 'sensors' in self._state and 'parameterFeedRateTotal' in self._state['sensors']:
            value = self._state['sensors']['parameterFeedRateTotal']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid parameterFeedRateTotal value for {self._id}: {value}")
                return None
        return None

    def get_stove_runtime_pellets(self):
        if self._state and 'sensors' in self._state and 'parameterRuntimePellets' in self._state['sensors']:
            value = self._state['sensors']['parameterRuntimePellets']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid parameterRuntimePellets value for {self._id}: {value}")
                return None
        return None

    def get_stove_runtime_logs(self):
        if self._state and 'sensors' in self._state and 'parameterRuntimeLogs' in self._state['sensors']:
            value = self._state['sensors']['parameterRuntimeLogs']
            try:
                return int(value) // 60
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid parameterRuntimeLogs value for {self._id}: {value}")
                return None
        return None

    def get_pellets_before_service(self):
        if self._state and 'sensors' in self._state and 'parameterFeedRateService' in self._state['sensors']:
            value = self._state['sensors']['parameterFeedRateService']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid parameterFeedRateService value for {self._id}: {value}")
                return None
        return None

    def get_stove_temperature(self):
        if self._state and 'sensors' in self._state and 'inputFlameTemperature' in self._state['sensors']:
            value = self._state['sensors']['inputFlameTemperature']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid inputFlameTemperature value for {self._id}: {value}")
                return None
        return None

    def get_diag_motor(self):
        if self._state and 'sensors' in self._state and 'outputDischargeMotor' in self._state['sensors']:
            value = self._state['sensors']['outputDischargeMotor']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid outputDischargeMotor value for {self._id}: {value}")
                return None
        return None

    def get_fan_velocity(self):
        if self._state and 'sensors' in self._state and 'outputIDFan' in self._state['sensors']:
            value = self._state['sensors']['outputIDFan']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid outputIDFan value for {self._id}: {value}")
                return None
        return None

    def get_status_text(self):
        return self.get_status()[1]

    def get_status_picture(self):
        return self.get_status()[0]
    
    def get_main_state(self):
        if self._state and 'sensors' in self._state and 'statusMainState' in self._state['sensors']:
            value = self._state['sensors']['statusMainState']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid statusMainState value for {self._id}: {value}")
                return None
        return None

    def get_sub_state(self):
        if self._state and 'sensors' in self._state and 'statusSubState' in self._state['sensors']:
            value = self._state['sensors']['statusSubState']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid statusSubState value for {self._id}: {value}")
                return None
        return None
    
    def get_status_error(self):
        if self._state and 'sensors' in self._state and 'statusError' in self._state['sensors']:
            value = self._state['sensors']['statusError']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid statusError value for {self._id}: {value}")
                return None
        return None

    def get_status_sub_error(self):
        if self._state and 'sensors' in self._state and 'statusSubError' in self._state['sensors']:
            value = self._state['sensors']['statusSubError']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid statusSubError value for {self._id}: {value}")
                return None
        return None
    
    def get_status_warning(self):
        if self._state and 'sensors' in self._state and 'statusWarning' in self._state['sensors']:
            value = self._state['sensors']['statusWarning']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid statusWarning value for {self._id}: {value}")
                return None
        return None

    def get_outputAirFlaps(self):
        if self._state and 'sensors' in self._state and 'outputAirFlaps' in self._state['sensors']:
            value = self._state['sensors']['outputAirFlaps']
            try:
                return float(value) / 10.0
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid outputAirFlaps value for {self._id}: {value}")
                return None
        return None
    
    def is_airFlapsPossible(self):
        return bool(self._state.get('stoveFeatures', {}).get('airFlaps')) if self._state else False

    def is_ecoModePossible(self):
        return bool(self._state.get('stoveFeatures', {}).get('ecoModePossible')) if self._state else False

    def is_logRuntimePossible(self):
        return bool(self._state.get('stoveFeatures', {}).get('logRuntime')) if self._state else False

    def is_multiAir1(self):
        return bool(self._state.get('stoveFeatures', {}).get('multiAir1')) if self._state else False

    def is_multiAir2(self):
        return bool(self._state.get('stoveFeatures', {}).get('multiAir2')) if self._state else False

    def get_frost_protection_temperature(self):
        if self._state and 'controls' in self._state and 'frostProtectionTemperature' in self._state['controls']:
            value = self._state['controls']['frostProtectionTemperature']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid frostProtectionTemperature value for {self._id}: {value}")
                return None
        return None

    def get_board_temperature(self):
        """Return the main board temperature in °C."""
        if self._state and 'sensors' in self._state and 'inputBoardTemperature' in self._state['sensors']:
            value = self._state['sensors']['inputBoardTemperature']
            try:
                return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid inputBoardTemperature value for {self._id}: {value}")
                return None
        return None

    def get_outputAirFlapsTargetPosition(self):
        """Return the target air flaps position in %."""
        if self._state and 'sensors' in self._state and 'outputAirFlapsTargetPosition' in self._state['sensors']:
            value = self._state['sensors']['outputAirFlapsTargetPosition']
            try:
                return float(value) / 10.0
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid outputAirFlapsTargetPosition value for {self._id}: {value}")
                return None
        return None

    def get_bake_temperature(self):
        """Return the bake target temperature in °C (DOMO BACK)."""
        if self._state and 'controls' in self._state and 'bakeTemperature' in self._state['controls']:
            value = self._state['controls']['bakeTemperature']
            try:
                return int(value)
            except (ValueError, TypeError):
                _LOGGER.warning(f"Invalid bakeTemperature value for {self._id}: {value}")
                return None
        return None

    def set_bake_temperature(self, temperature):
        """Set the bake target temperature in °C (DOMO BACK)."""
        self._set_control('bakeTemperature', int(temperature))

    def get_stove_type(self):
        """Return the stove model type (e.g. 'DOMO MultiAir')."""
        if self._state:
            return self._state.get('stoveType') or self._state.get('sensors', {}).get('stoveType')
        return None

    def get_firmware_version(self):
        """Return the main board firmware version formatted (e.g. 228 -> '2.28')."""
        if self._state and 'sensors' in self._state:
            version_int = self._state['sensors'].get('parameterVersionMainBoard')
            if version_int is not None:
                try:
                    v_str = str(version_int)
                    if len(v_str) >= 2:
                        return f"{v_str[0]}.{v_str[1:]}"
                    return v_str
                except Exception:
                    return str(version_int)
        return None

    def get_wifi_strength(self):
        """Return Wi-Fi signal strength in dBm."""
        if self._state and 'sensors' in self._state:
            val = self._state['sensors'].get('statusWifiStrength')
            try:
                return int(val)
            except (ValueError, TypeError):
                return None
        return None

    def is_door_closed(self):
        """Return True if door is closed."""
        if self._state and 'sensors' in self._state:
            val = self._state['sensors'].get('inputDoor')
            return bool(val) if val is not None else True
        return True

    def is_cover_closed(self):
        """Return True if pellet cover/lid is closed."""
        if self._state and 'sensors' in self._state:
            val = self._state['sensors'].get('inputCover')
            return bool(val) if val is not None else True
        return True

    def is_grid_contact_ok(self):
        """Return True if grid contact is OK."""
        if self._state and 'sensors' in self._state:
            val = self._state['sensors'].get('inputGridContact')
            return bool(val) if val is not None else True
        return True

    def is_external_request(self):
        """Return True if external thermostat request contact is active."""
        if self._state and 'sensors' in self._state:
            val = self._state['sensors'].get('inputExternalRequest')
            return bool(val) if val is not None else False
        return False

    def get_configuration_url(self) -> str:
        """Return the device configuration URL (local Open Firenet UI or cloud web page)."""
        if self._coordinator.is_local_mode():
            host = self._coordinator.get_host()
            if not host.startswith("http://") and not host.startswith("https://"):
                return f"http://{host}"
            return host.rstrip('/')
        return f"https://www.rika-firenet.com/web/stove/{self._id}"

    def get_status(self):
        """Return the status image and text key based on a set of rules."""
        if not self._state:
            return ["https://www.rika-firenet.com/images/status/Warning_WifiSignal.svg", "unavailable"]

        for condition, result_func in STATUS_RULES:
            if condition(self):
                return result_func(self)

        return ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "unknown"]
