import logging
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from homeassistant.components.climate.const import HVACMode
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class RikaFirenetCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, username, password, default_temperature, default_scan_interval, config_flow=False):
        self.hass = hass
        self._username = username
        self._password = password
        self._default_temperature = int(default_temperature)
        self._default_scan_interval = timedelta(seconds=default_scan_interval)
        self._client = requests.session()
        self._stoves = []
        self._number_fail = 0
        self._NeedSend = False
        self.platforms = []
        # Storage pour les données de pellets
        self._pellet_data = {}

        if not config_flow:
            super().__init__(
                hass,
                _LOGGER,
                name=DOMAIN,
                update_method=self.async_update_data,
                update_interval=self._default_scan_interval
            )

    async def async_update_data(self):
        try:
            await self.hass.async_add_executor_job(self.update)
        except Exception as exception:
            _LOGGER.error('Update failed to Rika Firenet')
            raise UpdateFailed(exception)

    def setup(self):
        _LOGGER.info("Setting up coordinator")
        self._stoves = self.setup_stoves()
        # Charger les données persistantes
        self._load_pellet_data()

    def get_stoves(self):
        return self._stoves

    def get_default_temperature(self):
        return self._default_temperature

    def get_number_fail(self):
        return self._number_fail

    def set_NeedSend(self):
        self._NeedSend = True

    def connect(self):
        if not self.is_authenticated():
            data = {'email': self._username, 'password': self._password}
            response = self._client.post('https://www.rika-firenet.com/web/login', data)
            if '/logout' not in response.text:
                raise Exception('Failed to connect with Rika Firenet')
            _LOGGER.info('Connected to Rika Firenet')

    def is_authenticated(self):
        if 'connect.sid' not in self._client.cookies:
            return False
        expiresIn = list(self._client.cookies)[0].expires
        epochNow = int(datetime.now().strftime('%s'))
        if expiresIn <= epochNow:
            return False
        return True

    def get_stove_state(self, stove_id):
        self.connect()
        url = f'https://www.rika-firenet.com/api/client/{stove_id}/status?nocache={int(time.time())}'
        data = self._client.get(url, timeout=10).json()
        _LOGGER.debug('get_stove_state : ' + str(data))
        return data

    def setup_stoves(self):
        self.connect()
        stoves = []
        response = self._client.get('https://www.rika-firenet.com/web/summary', timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        stove_list = soup.find("ul", {"id": "stoveList"})

        if stove_list:
            for stove in stove_list.find_all('li'):
                stove_link = stove.find('a', href=True)
                stove_name = stove_link.attrs['href'].rsplit('/', 1)[-1]
                stove = RikaFirenetStove(self, stove_name, stove_link.text)
                _LOGGER.info(f"Found stove: {stove}")
                stoves.append(stove)
        return stoves

    def _load_pellet_data(self):
        """Charge les données persistantes de pellets depuis le stockage de Home Assistant."""
        try:
            # Essayer de charger les données depuis la persistance de Home Assistant
            storage_file = self.hass.config.path(f"{DOMAIN}_pellet_data.json")
            import json
            import os
            if os.path.exists(storage_file):
                with open(storage_file, 'r') as f:
                    self._pellet_data = json.load(f)
                    _LOGGER.info(f"Loaded pellet data from storage: {self._pellet_data}")
                    
                # Appliquer les données chargées aux poêles
                for stove in self._stoves:
                    stove_id = stove.get_id()
                    if stove_id in self._pellet_data:
                        data = self._pellet_data[stove_id]
                        stove._pellet_stock = data.get('stock', stove._pellet_stock_capacity)
                        stove._pellet_stock_capacity = data.get('capacity', 15)
                        stove._last_consumption = data.get('last_consumption', 0)
                        _LOGGER.info(f"Restored pellet data for stove {stove_id}: Stock={stove._pellet_stock}, Capacity={stove._pellet_stock_capacity}")
        except Exception as e:
            _LOGGER.error(f"Failed to load pellet data: {e}")
    
    def _save_pellet_data(self):
        """Sauvegarde les données de pellets pour persistance."""
        try:
            # Récupérer les données à sauvegarder
            data_to_save = {}
            for stove in self._stoves:
                stove_id = stove.get_id()
                data_to_save[stove_id] = {
                    'stock': stove._pellet_stock,
                    'capacity': stove._pellet_stock_capacity,
                    'last_consumption': getattr(stove, '_last_consumption', 0)
                }
            
            # Sauvegarder dans un fichier
            import json
            storage_file = self.hass.config.path(f"{DOMAIN}_pellet_data.json")
            with open(storage_file, 'w') as f:
                json.dump(data_to_save, f)
            
            _LOGGER.debug(f"Saved pellet data to storage: {data_to_save}")
        except Exception as e:
            _LOGGER.error(f"Failed to save pellet data: {e}")

    def update(self):
        _LOGGER.debug("Update triggered by timeout")

        for stove in self._stoves:
            if stove._state and self._NeedSend:
                stove._state = self.set_stove_controls(stove._id, stove.get_control_state())
            else:
                stove.sync_state()

            if stove.get_main_state() == 6 and stove.is_stove_on():
                _LOGGER.debug('statusMainState=6 and OnOff=on, restarting stove')
                stove.set_stove_on_off(False)
                stove.set_stove_on_off(True)
                
        # Après chaque mise à jour, sauvegarder les données de pellets
        self._save_pellet_data()

    def set_stove_controls(self, stove_id, controls):
        _LOGGER.debug("set_stove_control data: " + str(controls))
        for attempt in range(10):
            _LOGGER.info(f'Attempting to update stove controls ({attempt + 1}/10)')
            response = self._client.post(
                f'https://www.rika-firenet.com/api/client/{stove_id}/controls', controls
            )
            if 'OK' in response.text:
                _LOGGER.info('Stove controls updated successfully')
                self._number_fail = 0
                self._NeedSend = False
                return self.get_stove_state(stove_id)
            else:
                self._number_fail += 1
                time.sleep(5)
                controls['revision'] = self.get_stove_state(stove_id)['controls']['revision']

        _LOGGER.error('Failed to update stove controls after 10 attempts')
        return controls

class RikaFirenetStove:
    def __init__(self, coordinator, stove_id, name):
        self._coordinator = coordinator
        self._id = stove_id
        self._name = name
        self._state = None
        self._pellet_stock_capacity = 15  # Valeur par défaut en kg
        self._pellet_stock = self._pellet_stock_capacity  # Initialiser au maximum

    def __repr__(self):
        return f'Stove(id={self._id}, name={self._name})'

    def sync_state(self):
        _LOGGER.debug(f"Syncing state for stove {self._id}")
        self._state = self._coordinator.get_stove_state(self._id)

    def get_number_fail(self):
        return int(self._coordinator.get_number_fail())

    def set_temperatureOffset(self, temperature):
        _LOGGER.debug("set_offset_temperature(): " + str(temperature))
        self._state['controls']['temperatureOffset'] = float(temperature)
        self._coordinator.set_NeedSend()

    def set_stove_temperature(self, temperature):
        _LOGGER.debug("set_stove_temperature(): " + str(temperature))
        self._state['controls']['targetTemperature'] = float(temperature)
        self._coordinator.set_NeedSend()

    def set_frost_protection_temperature(self, temperature):
        _LOGGER.debug("set_frost_protection_temperature(): " + str(temperature))
        self._state['controls']['frostProtectionTemperature'] = int(temperature)
        self._coordinator.set_NeedSend()

    def set_stove_set_back_temperature(self, temperature):
        _LOGGER.debug("set_back_temperature(): " + str(temperature))
        self._state['controls']['setBackTemperature'] = float(temperature)
        self._coordinator.set_NeedSend()

    def set_stove_operation_mode(self, mode):
        _LOGGER.debug("set_stove_operation_mode(): " + str(mode))
        self._state['controls']['operatingMode'] = int(mode)
        self._coordinator.set_NeedSend()

    def set_heating_times_active_for_comfort(self, active):
        _LOGGER.debug("set_heating_times_active_for_comfort(): " + str(active))
        self._state['controls']['onOff'] = True
        self._state['controls']['heatingTimesActiveForComfort'] = bool(active)
        self._coordinator.set_NeedSend()

    def set_room_power_request(self, power):
        _LOGGER.debug("set_room_power_request(): " + str(power))
        self._state['controls']['RoomPowerRequest'] = int(power)
        self._coordinator.set_NeedSend()

    def set_heating_power(self, power):
        _LOGGER.debug("set_heating_power(): " + str(power))
        self._state['controls']['heatingPower'] = int(power)
        self._coordinator.set_NeedSend()

    def set_convection_fan1_level(self, level):
        _LOGGER.debug("set_convection_fan1_level(): " + str(level))
        self._state['controls']['convectionFan1Level'] = int(level)
        self._coordinator.set_NeedSend()

    def set_convection_fan1_area(self, area):
        _LOGGER.debug("set_convection_fan1_area(): " + str(area))
        self._state['controls']['convectionFan1Area'] = int(area)
        self._coordinator.set_NeedSend()

    def set_convection_fan2_level(self, level):
        _LOGGER.debug("set_convection_fan2_level(): " + str(level))
        self._state['controls']['convectionFan2Level'] = int(level)
        self._coordinator.set_NeedSend()

    def set_convection_fan2_area(self, area):
        _LOGGER.debug("set_convection_fan2_area(): " + str(area))
        self._state['controls']['convectionFan2Area'] = int(area)
        self._coordinator.set_NeedSend()

    def set_stove_on_off(self, on_off):
        _LOGGER.debug(f"Setting stove {self._id} On/Off: {on_off}")
        self._state['controls']['onOff'] = on_off
        self._coordinator.set_NeedSend()
        

    def turn_heating_times_on(self): 
        self._state['controls']['onOff'] = True
        self._state['controls']['heatingTimesActiveForComfort'] = True
        if not self.get_stove_operation_mode() == 2:
            self._state['controls']['operatingMode'] = int(1)
        self._coordinator.set_NeedSend()

    def turn_heating_times_off(self):
        self._state['controls']['onOff'] = True
        self._state['controls']['heatingTimesActiveForComfort'] = False
        if not self.get_stove_operation_mode() == 2:
            self._state['controls']['operatingMode'] = int(0)
        self._coordinator.set_NeedSend()

    def turn_convection_fan1_on_off(self, on_off=True):
        _LOGGER.debug("turn_convection_fan1_on_off(): " + str(on_off))
        self._state['controls']['convectionFan1Active'] = on_off
        self._coordinator.set_NeedSend()

    def turn_convection_fan2_on_off(self, on_off=True):
        _LOGGER.debug("turn_convection_fan2_on_off(): " + str(on_off))
        self._state['controls']['convectionFan2Active'] = on_off
        self._coordinator.set_NeedSend()

    def turn_on_off_eco_mode(self, on_off=False):
        _LOGGER.info("Set Eco Mode: " + str(on_off))
        self._state['controls']['ecoMode'] = on_off
        self._coordinator.set_NeedSend()

    def turn_on_off_frost_protection(self, on_off=False):
        _LOGGER.info("Set Frost Protection: " + str(on_off))
        self._state['controls']['frostProtectionActive'] = on_off
        self._coordinator.set_NeedSend()

    def get_control_state(self):
        return self._state['controls']

    def is_stove_on(self):
        return self._state['controls']['onOff']

    def get_id(self):
        return self._id

    def get_name(self):
        return self._name

    def get_state(self):
        return self._state

    def get_room_temperature(self):
        return float(self._state['sensors']['inputRoomTemperature'])

    def get_temperatureOffset(self):
        return float(self._state['controls']['temperatureOffset'])

    def get_room_thermostat(self):
        return float(self._state['controls']['targetTemperature'])

    def is_stove_eco_mode(self):
        return self._state['controls'].get('ecoMode')

    def is_frost_protection(self):
        return self._state['controls'].get('frostProtectionActive')

    def get_stove_set_back_temperature(self):
        return float(self._state['controls']['setBackTemperature'])

    def get_stove_operation_mode(self):
        return self._state['controls'].get('operatingMode')

    def get_hvac_mode(self):
        if not self.is_stove_on():
            return HVACMode.OFF
        elif self.is_stove_heating_times_on():
            return HVACMode.AUTO    
        elif not self.is_stove_heating_times_on(): 
            return HVACMode.HEAT

    def is_stove_heating_times_on(self):
        if self.get_stove_operation_mode() == 2:
            if not self.is_heating_times_active_for_comfort():
                return False
            else:
                return True
        elif self.get_stove_operation_mode() == 0:
            return False
        elif self.get_stove_operation_mode() == 1:
            return True

    def is_heating_times_active_for_comfort(self):
        return self._state['controls'].get('heatingTimesActiveForComfort')

    def get_room_power_request(self):
        return self._state['controls'].get('RoomPowerRequest')

    def get_heating_power(self):
        return self._state['controls'].get('heatingPower')

    def set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            self.set_stove_on_off(False)
        elif hvac_mode == HVACMode.AUTO:
            _LOGGER.debug("Turn heating times on")
            self.turn_heating_times_on()
        elif hvac_mode == HVACMode.HEAT:
            _LOGGER.debug("Turn heating times off")
            self.turn_heating_times_off()

    def is_stove_convection_fan1_on(self):
        return self._state['controls'].get('convectionFan1Active')

    def get_convection_fan1_level(self):
        return self._state['controls'].get('convectionFan1Level')

    def get_convection_fan1_area(self):
        return self._state['controls'].get('convectionFan1Area')

    def is_stove_convection_fan2_on(self):
        return self._state['controls'].get('convectionFan2Active')

    def get_convection_fan2_level(self):
        return self._state['controls'].get('convectionFan2Level')

    def get_convection_fan2_area(self):
        return self._state['controls'].get('convectionFan2Area')

    def is_stove_burning(self):
        if self.get_main_state() == 4 or self.get_main_state() == 5:
            return True
        else:
            return False

    def get_stove_consumption(self):
        return self._state['sensors'].get('parameterFeedRateTotal')

    def get_stove_runtime_pellets(self):
        return self._state['sensors'].get('parameterRuntimePellets')

    def get_stove_runtime_logs(self):
        minutes = self._state['sensors'].get('parameterRuntimeLogs') or 0  # Remplace None par 0
        return minutes // 60

    def get_pellets_before_service(self):
        return self._state['sensors'].get('parameterFeedRateService')

    def get_stove_temperature(self):
        return self._state['sensors'].get('inputFlameTemperature')

    def get_diag_motor(self):
        return self._state['sensors'].get('outputDischargeMotor')

    def get_fan_velocity(self):
        return self._state['sensors'].get('outputIDFan')

    def get_status_text(self):
        return self.get_status()[1]

    def get_status_picture(self):
        return self.get_status()[0]

    def get_main_state(self):
        return self._state['sensors'].get('statusMainState')

    def get_sub_state(self):
        return self._state['sensors'].get('statusSubState')
    
    def get_status_error(self):
        return self._state['sensors'].get('statusError')

    def get_status_sub_error(self):
        return self._state['sensors'].get('statusSubError')
    
    def get_outputAirFlaps(self):
        flaps = self._state['sensors'].get('outputAirFlaps')
        return float(flaps / 10)
    
    def is_airFlapsPossible(self):
        return self._state['stoveFeatures'].get('airFlaps')

    def is_logRuntimePossible(self):
        return self._state['stoveFeatures'].get('logRuntime')

    def is_multiAir1(self):
        return self._state['stoveFeatures'].get('multiAir1')

    def is_multiAir2(self):
        return self._state['stoveFeatures'].get('multiAir2')

    def get_frost_protection_temperature(self):
        return int(self._state['controls'].get('frostProtectionTemperature'))

    def get_status(self):
        main_state = self.get_main_state()
        sub_state = self.get_sub_state()
        frost_started = bool(self._state['sensors']['statusFrostStarted'])
        statusError = self.get_status_error()
        statusSubError = self.get_status_sub_error()
        lastSeenMinutes = int(self._state['lastSeenMinutes'])
        stove_temp = self.get_stove_temperature()
        eco_mode = bool(self._state['controls'].get('ecoMode'))

        if lastSeenMinutes != 0:
            _LOGGER.debug("lastSeenMinutes: " + str(lastSeenMinutes))
        if statusError != 0:
            _LOGGER.debug("statusError: " + str(statusError))
        if statusSubError != 0:
            _LOGGER.debug("statusSubError: " + str(statusSubError))
        if lastSeenMinutes > 2:
            return ["https://www.rika-firenet.com/images/status/Warning_WifiSignal.svg", "offline"]
        if statusError == 1:
            if statusSubError == 1:
                return ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_Error.svg", "Error"]
            elif statusSubError == 2:
                return ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_Empty.svg", "empty_tank"]
            return ["/", "statusSubError" + str(statusSubError)]
        if statusError == 32768:
            return ["https://raw.githubusercontent.com/antibill51/rika-firenet-custom-component/main/images/status/Visu_smoke_fan.svg", "smoke_fan"]
        if frost_started:
            return ["https://www.rika-firenet.com/images/status/Visu_Freeze.svg", "frost_protection"]
        if main_state == 1:
            if sub_state == 0:
                return ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "stove_off"]
            elif sub_state == 1:
                return ["https://www.rika-firenet.com/images/status/Visu_Standby.svg", "standby"]
            elif sub_state == 2:
                return ["https://www.rika-firenet.com/images/status/Visu_Standby.svg", "external_request"]
            elif sub_state == 3:
                return ["https://www.rika-firenet.com/images/status/Visu_Standby.svg", "standby"]
            return ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "sub_state_unknown"]
        elif main_state == 2:
            return ["https://www.rika-firenet.com/images/status/Visu_Ignition.svg", "ignition_on"]
        elif main_state == 3:
            return ["https://www.rika-firenet.com/images/status/Visu_Ignition.svg", "starting_up"]
        elif main_state == 4:
            return ["https://www.rika-firenet.com/images/status/Visu_Control.svg", "running"]
        elif main_state == 5:
            if sub_state == 3 or sub_state == 4:
                return ["https://www.rika-firenet.com/images/status/Visu_Clean.svg", "big_clean"]
            else:
                return ["https://www.rika-firenet.com/images/status/Visu_Clean.svg", "clean"]
        elif main_state == 6:
            return ["https://www.rika-firenet.com/images/status/Visu_BurnOff.svg", "burn_off"]
        elif main_state == 11 or main_state == 13 or main_state == 14 or main_state == 16 or main_state == 17 or main_state == 50:
            return ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_check"]
        elif main_state == 21 and sub_state == 12 and stove_temp <=350 and stove_temp >= 300:
            return ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_refuel"]
        elif main_state == 21 and sub_state == 12 and stove_temp < 300:
            return ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_stop_refuel"]
        elif main_state == 20 and eco_mode:
            return ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_ecomode"]
        elif main_state == 20 or main_state == 21:
            return ["https://www.rika-firenet.com/images/status/Visu_SpliLog.svg", "split_log_mode"]
        return ["https://www.rika-firenet.com/images/status/Visu_Off.svg", "unknown"]

    def get_pellet_stock_capacity(self):
        """Retourne la capacité du stock de pellets en kg."""
        return self._pellet_stock_capacity
    
    def set_pellet_stock_capacity(self, capacity):
        """Définit la capacité du stock de pellets en kg."""
        _LOGGER.debug(f"set_pellet_stock_capacity(): {capacity}")
        self._pellet_stock_capacity = float(capacity)
        # Ajuster le stock actuel si nécessaire
        if self._pellet_stock > self._pellet_stock_capacity:
            self._pellet_stock = self._pellet_stock_capacity
    
    def get_pellet_stock(self):
        """Retourne le stock actuel de pellets en kg."""
        # Calculer la consommation depuis la dernière mise à jour
        consumption = self.get_stove_consumption() or 0
        
        # Ajouter du débogage pour comprendre les valeurs
        _LOGGER.debug(f"Current consumption: {consumption}, Capacity: {self._pellet_stock_capacity}")
        
        # Si c'est la première fois qu'on appelle cette méthode, initialiser last_consumption
        if not hasattr(self, '_last_consumption'):
            _LOGGER.info(f"Initializing pellet stock tracking with consumption: {consumption}")
            self._last_consumption = consumption
            # Stocker aussi le moment où on a commencé à suivre
            self._last_consumption_time = datetime.now()
            return self._pellet_stock
            
        # Ajouter du débogage pour voir la différence
        _LOGGER.debug(f"Last consumption: {self._last_consumption}, Difference: {consumption - self._last_consumption}")
        
        # S'il y a eu une réinitialisation du compteur sur le poêle ou si la valeur a diminué
        if consumption < self._last_consumption:
            _LOGGER.info(f"Consumption counter reset or decreased: {self._last_consumption} -> {consumption}")
            self._last_consumption = consumption
            return self._pellet_stock
            
        # Calculer la différence de consommation et l'appliquer au stock
        consumed = consumption - self._last_consumption
        
        # Ne mettre à jour que si la consommation a changé de manière significative
        if consumed > 0.01:  # 10 grammes minimum pour éviter les erreurs de précision
            _LOGGER.info(f"Pellet consumed: {consumed}kg, Remaining stock: {self._pellet_stock - consumed}kg")
            self._pellet_stock = max(0, self._pellet_stock - consumed)
            self._last_consumption = consumption
            # Mettre à jour le temps de la dernière consommation
            self._last_consumption_time = datetime.now()
        
        return self._pellet_stock
    
    def reset_pellet_stock(self):
        """Réinitialise le stock de pellets à la capacité maximale."""
        _LOGGER.info(f"Resetting pellet stock to {self._pellet_stock_capacity}kg")
        self._pellet_stock = self._pellet_stock_capacity
        
        # Enregistrer la consommation actuelle comme référence
        current_consumption = self.get_stove_consumption() or 0
        self._last_consumption = current_consumption
        self._last_consumption_time = datetime.now()
        
        _LOGGER.info(f"Reset complete. Reference consumption: {current_consumption}kg")
        
        # Forcer une mise à jour du state pour que Home Assistant prenne en compte le changement
        self.sync_state()

    def get_pellet_remaining_percentage(self):
        """Retourne le pourcentage de pellets restants."""
        if self._pellet_stock_capacity > 0:
            return (self.get_pellet_stock() / self._pellet_stock_capacity) * 100
        return 0
