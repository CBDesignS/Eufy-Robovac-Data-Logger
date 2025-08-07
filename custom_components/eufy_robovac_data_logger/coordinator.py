"""Data update coordinator for Eufy Robovac Data Logger integration."""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, DPS_KEYS_TO_LOG, LOG_DIR, CONF_DEBUG_MODE, MONITORED_KEYS

_LOGGER = logging.getLogger(__name__)


class EufyDataLoggerCoordinator(DataUpdateCoordinator):
    """Eufy Robovac data coordinator for logging DPS data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.device_id = entry.data["device_id"]
        self.device_name = entry.data.get("device_name", "Unknown Device")
        self.device_model = entry.data.get("device_model", "T8213")
        self.username = entry.data["username"]
        self.password = entry.data["password"]
        self.openudid = entry.data.get("openudid", f"ha_debug_{self.device_id}")
        self.debug_mode = entry.data.get(CONF_DEBUG_MODE, False)
        
        # Store raw data for logging
        self.raw_data: Dict[str, Any] = {}
        self.parsed_data: Dict[str, Any] = {}
        self.last_update: Optional[float] = None
        self.update_count = 0
        
        # Connection tracking
        self._eufy_login = None
        self._mqtt_connect = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        self._event_loop = None
        
        # Log directory setup
        self.log_dir = Path(hass.config.config_dir) / LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        _LOGGER.info("Coordinator initialized for device: %s", self.device_id)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Handle first refresh."""
        try:
            # Store event loop for MQTT callbacks
            self._event_loop = asyncio.get_running_loop()
            
            # Initialize connections
            await self._initialize_connections()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            
        except Exception as e:
            _LOGGER.error("Failed during first refresh: %s", e)
            raise

    async def _initialize_connections(self) -> None:
        """Initialize the connection clients."""
        try:
            _LOGGER.info("Initializing connections...")
            
            # Import with correct case sensitivity
            from .controllers.Login import EufyLogin
            
            # Create login instance first
            self._eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # Initialize login to get authentication and devices
            devices = await self._eufy_login.init()
            _LOGGER.info("EufyLogin initialized successfully, found %d devices", len(devices) if devices else 0)
            
            # Check if we have MQTT credentials
            if self._eufy_login.mqtt_credentials:
                try:
                    # Import MqttConnect with correct case
                    from .controllers.MqttConnect import MqttConnect
                    
                    # Create config for MqttConnect
                    mqtt_config = {
                        'deviceId': self.device_id,
                        'deviceModel': self.device_model,
                        'debug': self.debug_mode
                    }
                    
                    # Create MqttConnect instance
                    self._mqtt_connect = MqttConnect(
                        config=mqtt_config,
                        openudid=self.openudid,
                        eufyCleanApi=self._eufy_login
                    )
                    
                    # Store event loop reference in MqttConnect for callbacks
                    self._mqtt_connect._loop = self._event_loop
                    
                    # Add listener for data updates
                    self._mqtt_connect.add_listener(self._handle_mqtt_update)
                    
                    # Connect to MQTT
                    await self._mqtt_connect.connect()
                    _LOGGER.info("MqttConnect initialized and connected successfully")
                    
                except Exception as mqtt_error:
                    _LOGGER.error(f"Failed to initialize MqttConnect: {mqtt_error}")
                    self._mqtt_connect = None
            else:
                _LOGGER.warning("No MQTT credentials available from login")
                self._mqtt_connect = None
            
        except Exception as e:
            _LOGGER.error("Failed to initialize connections: %s", e)
            raise

    async def _handle_mqtt_update(self):
        """Handle update from MQTT - called by MqttConnect when data arrives."""
        try:
            # MQTT has updated the data, refresh our state
            _LOGGER.debug("MQTT data update received")
            await self.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error handling MQTT update: {e}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy API."""
        try:
            self.update_count += 1
            
            if self.debug_mode:
                _LOGGER.debug("Update #%d starting", self.update_count)
            
            # Fetch data from MQTT connection
            await self._fetch_eufy_data()
            
            # Process basic data for status sensor
            self._process_basic_data()
            
            # Reset consecutive failures on success if we have data
            if self.raw_data:
                self._consecutive_failures = 0
                self._last_successful_update = time.time()
            else:
                self._consecutive_failures += 1
            
            self.last_update = time.time()
            
            if self.debug_mode:
                _LOGGER.debug("Update #%d completed, %d keys available", 
                             self.update_count, len(self.raw_data))
            
            return self.parsed_data
            
        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error("Update #%d failed: %s", self.update_count, err)
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def _fetch_eufy_data(self) -> None:
        """Fetch data from MqttConnect."""
        try:
            data_source = "Unknown"
            
            if self._mqtt_connect:
                # Get the raw DPS data from MqttConnect
                # MqttConnect stores data in robovac_data dictionary
                mqtt_data = await self._mqtt_connect.get_robovac_data()
                
                if mqtt_data:
                    # Map the data to our expected format
                    # The robovac_data has semantic keys, but we need DPS keys for logging
                    # We need to reverse map from semantic names to DPS keys
                    dps_data = {}
                    
                    # Get the dps_map from MqttConnect
                    for semantic_key, dps_key in self._mqtt_connect.dps_map.items():
                        if semantic_key in mqtt_data:
                            dps_data[dps_key] = mqtt_data[semantic_key]
                    
                    # Also check if there's raw DPS data directly
                    # MqttConnect might have raw DPS keys too
                    for key in range(150, 181):
                        str_key = str(key)
                        if str_key in mqtt_data:
                            dps_data[str_key] = mqtt_data[str_key]
                    
                    self.raw_data = dps_data
                    data_source = "MQTT"
                    
                    if self.debug_mode:
                        _LOGGER.debug(f"MQTT fetch: {len(dps_data)} DPS keys")
                else:
                    # No data yet from MQTT (might be waiting for first message)
                    if not self.raw_data:
                        _LOGGER.info("Waiting for MQTT data...")
                    data_source = "MQTT (waiting)"
            else:
                # Try to get data directly from login if no MQTT
                if self._eufy_login:
                    try:
                        device = await self._eufy_login.getMqttDevice(self.device_id)
                        if device and 'dps' in device:
                            self.raw_data = device['dps']
                            data_source = "API"
                            if self.debug_mode:
                                _LOGGER.debug(f"API fetch: {len(self.raw_data)} keys")
                    except Exception as api_error:
                        _LOGGER.error(f"API fetch failed: {api_error}")
                        data_source = "Failed"
            
            # Store data source for status
            self.parsed_data["data_source"] = data_source
            self.parsed_data["total_keys"] = len(self.raw_data)
            self.parsed_data["last_update"] = time.time()
            self.parsed_data["update_count"] = self.update_count
            
        except Exception as e:
            _LOGGER.error("Data fetch failed: %s", e)
            raise

    def _process_basic_data(self) -> None:
        """Process basic data for status sensor."""
        try:
            # Count how many of our target keys (150-180) are present
            target_keys_found = []
            for key in DPS_KEYS_TO_LOG:
                if str(key) in self.raw_data:
                    target_keys_found.append(str(key))
            
            self.parsed_data["target_keys_found"] = target_keys_found
            self.parsed_data["target_keys_count"] = len(target_keys_found)
            
            # Connection status
            self.parsed_data["is_connected"] = bool(self._mqtt_connect or self._eufy_login)
            self.parsed_data["consecutive_failures"] = self._consecutive_failures
            
            # Add MQTT status
            if self._mqtt_connect:
                if hasattr(self._mqtt_connect, 'mqttClient') and self._mqtt_connect.mqttClient:
                    self.parsed_data["mqtt_connected"] = self._mqtt_connect.mqttClient.is_connected()
                else:
                    self.parsed_data["mqtt_connected"] = False
            else:
                self.parsed_data["mqtt_connected"] = False
            
        except Exception as e:
            _LOGGER.error("Error processing basic data: %s", e)

    async def log_dps_data(self) -> str:
        """Log DPS keys 150-180 to timestamped file."""
        try:
            if not self.raw_data:
                return "No data available to log"
            
            # Filter for keys 150-180
            filtered_data = {}
            for key in DPS_KEYS_TO_LOG:
                str_key = str(key)
                if str_key in self.raw_data:
                    filtered_data[str_key] = self.raw_data[str_key]
            
            if not filtered_data:
                return "No keys in range 150-180 found"
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dps_log_{self.device_id}_{timestamp}.json"
            filepath = self.log_dir / filename
            
            # Prepare log data
            log_data = {
                "device_id": self.device_id,
                "device_name": self.device_name,
                "device_model": self.device_model,
                "timestamp": datetime.now().isoformat(),
                "update_count": self.update_count,
                "data_source": self.parsed_data.get("data_source", "Unknown"),
                "keys_logged": len(filtered_data),
                "dps_data": filtered_data
            }
            
            # Write to file asynchronously
            import aiofiles
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(log_data, indent=2))
            
            _LOGGER.info("Logged %d DPS keys to %s", len(filtered_data), filename)
            return f"Logged {len(filtered_data)} keys to {filename}"
            
        except Exception as e:
            _LOGGER.error("Failed to log DPS data: %s", e)
            return f"Error logging data: {e}"

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        _LOGGER.info("Coordinator shutdown")
        
        # Disconnect MQTT if exists
        if self._mqtt_connect:
            try:
                # MqttConnect has mqttClient that needs to be disconnected
                if hasattr(self._mqtt_connect, 'mqttClient') and self._mqtt_connect.mqttClient:
                    self._mqtt_connect.mqttClient.disconnect()
                    self._mqtt_connect.mqttClient.loop_stop()
                _LOGGER.info("MQTT client disconnected")
            except Exception as e:
                _LOGGER.error("Error disconnecting MQTT: %s", e)
        
        # Clear references
        self._eufy_login = None
        self._mqtt_connect = None
        self._event_loop = None