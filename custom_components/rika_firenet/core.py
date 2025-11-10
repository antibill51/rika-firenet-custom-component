import logging
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from homeassistant.components.climate.const import HVACAction, HVACMode, PRESET_COMFORT, PRESET_NONE
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import (
    DOMAIN,
    LOGIN_URL,
    SUMMARY_URL,
    STATUS_URL,
    CONTROLS_URL
)

_LOGGER = logging.getLogger(__name__)

class RikaFirenetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, username, password, default_temperature, default_scan_interval):
        self.hass = hass
        self._username = username
        self._password = password
        self._default_temperature = int(default_temperature)
        self._default_scan_interval = timedelta(seconds=default_scan_interval)
        self._client = requests.session() # Keep a single session for all requests
        self._stoves: list[RikaFirenetStove] = [] # Type hinting for clarity
        self._number_fail = 0
        self.platforms = []

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.async_update_data,
            update_interval=self._default_scan_interval
        )

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

    def get_default_temperature(self):
        return self._default_temperature

    def get_number_fail(self):
        return self._number_fail

    def connect(self):
        if not self.is_authenticated():
            data = {'email': self._username, 'password': self._password}
            response = self._client.post(LOGIN_URL, data)
            if '/logout' not in response.text:
                raise Exception('Failed to connect with Rika Firenet')
            _LOGGER.info('Connected to Rika Firenet')

    def is_authenticated(self):
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
                            _LOGGER.warning(f"Failed to send controls for stove {stove.get_id()}, changes remain pending. Will retry on next update.")
                            # Do not clear pending changes so they are retried
                    else:
                         _LOGGER.warning(f"Cannot send controls for stove {stove.get_id()} because control state is missing.")
                else:
                    # _LOGGER.debug(f"Syncing state for stove {stove.get_id()}") # Removed, sync_state logs itself
                    stove.sync_state() # Retrieves and updates the stove's state

                # Restart logic 
                current_stove_state = stove.get_state()
                if current_stove_state and stove.get_main_state() == 6 and stove.is_stove_on():
                    _LOGGER.info(f'Stove {stove.get_id()} (mainState=6 and On) may need a restart.')
                    stove.set_stove_on_off(False) 
                    stove.set_stove_on_off(True)
            except Exception as e:
                _LOGGER.error(f"Error processing stove {stove.get_id()} in coordinator update: {e}", exc_info=True)

    def set_stove_controls(self, stove_id, controls):
        _LOGGER.debug(f"set_stove_controls for {stove_id}, data: {str(controls)}")
        # Ensure revision is present if the API requires it
        if 'revision' not in controls:
            current_state = self.get_stove_state(stove_id)
            if current_state and 'controls' in current_state and 'revision' in current_state['controls']:
                controls['revision'] = current_state['controls']['revision']
                _LOGGER.debug(f"Added revision {controls['revision']} to controls for {stove_id}")
            else:
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
            time.sleep(5)
            # Update revision before the next attempt, as it might have changed
            current_state_for_rev = self.get_stove_state(stove_id)
            if current_state_for_rev and 'controls' in current_state_for_rev and 'revision' in current_state_for_rev['controls']:
                controls['revision'] = current_state_for_rev['controls']['revision']
                _LOGGER.info(f"Updated revision to {controls['revision']} for stove {stove_id} before retry.")
            else:
                _LOGGER.warning(f"Could not get new revision for stove {stove_id} before retry.")
        _LOGGER.error(f'Failed to update stove {stove_id} controls after 3 attempts')
        return None # Indicate persistent failure

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

    def _mark_controls_changed(self):
        """Marks that controls have been modified and should be sent."""
        self._controls_changed = True
        _LOGGER.debug(f"Controls marked changed for stove {self._id}")

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

    def get_status(self):
        """Return the status image and text key based on a set of rules."""
        if not self._state:
            return ["https://www.rika-firenet.com/images/status/Warning_WifiSignal.svg", "unavailable"]

        for condition, result_func in STATUS_RULES:
            if condition(self):
                return result_func(self)

        return ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "unknown"]
