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
        self._shared_connect = None  # Changed from _mqtt_connect to _shared_connect
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
            await self._eufy_login.init()
            devices = self._eufy_login.mqtt_devices  # Get from property
            _LOGGER.info("EufyLogin initialized successfully, found %d devices", len(devices) if devices else 0)
            
            # Find our device config
            device_config = None
            for device in devices:
                if device.get('deviceId') == self.device_id:
                    device_config = device
                    break
            
            if not device_config:
                _LOGGER.error("Device %s not found in login results", self.device_id)
                raise Exception(f"Device {self.device_id} not found")
            
            # Check if we have MQTT credentials
            if self._eufy_login.mqtt_credentials:
                try:
                    # Import SharedConnect - WORKING IN ORIGINAL
                    from .controllers.SharedConnect import SharedConnect
                    
                    # Create config for SharedConnect - USE CAMELCASE KEYS LIKE SHAREDCONNECT EXPECTS
                    shared_config = {
                        'deviceId': device_config['deviceId'],     # SharedConnect expects 'deviceId'
                        'deviceModel': device_config['deviceModel'], # SharedConnect expects 'deviceModel'
                        'apiType': device_config.get('apiType', 'novel'),
                        'mqtt': device_config.get('mqtt', True),
                        'debug': self.debug_mode,
                        'openudid': self.openudid,
                        'eufyCleanApi': self._eufy_login
                    }
                    
                    _LOGGER.info("Creating SharedConnect with config: %s", shared_config)
                    
                    # Create SharedConnect instance - ONLY CONFIG ARGUMENT
                    self._shared_connect = SharedConnect(shared_config)
                    
                    # Store event loop reference for callbacks
                    self._shared_connect._loop = self._event_loop
                    
                    # Add listener for data updates
                    self._shared_connect.add_listener(self._handle_mqtt_update)
                    
                    # Connect to MQTT and send initial commands to get DPS data
                    _LOGGER.info("Connecting SharedConnect...")
                    await self._shared_connect.connect()
                    _LOGGER.info("SharedConnect connected successfully - DPS data should start flowing")
                    
                except Exception as shared_error:
                    _LOGGER.error(f"Failed to initialize SharedConnect: {shared_error}")
                    import traceback
                    _LOGGER.error(traceback.format_exc())
                    self._shared_connect = None
            else:
                _LOGGER.warning("No MQTT credentials available from login")
                self._shared_connect = None
            
        except Exception as e:
            _LOGGER.error("Failed to initialize connections: %s", e)
            import traceback
            _LOGGER.error(traceback.format_exc())
            raise

    async def _handle_mqtt_update(self):
        """Handle update from MQTT - called by SharedConnect when data arrives."""
        try:
            # MQTT has updated the data, refresh our state
            _LOGGER.debug("MQTT data update received from SharedConnect")
            await self.async_request_refresh()
        except Exception as e:
            _LOGGER.error(f"Error handling MQTT update: {e}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy API."""
        try:
            self.update_count += 1
            
            if self.debug_mode:
                _LOGGER.debug("Update #%d starting", self.update_count)
            
            # Fetch data from SharedConnect
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
        """Fetch data from SharedConnect."""
        try:
            data_source = "Unknown"
            
            if self._shared_connect:
                # MqttConnect on_message stores DPS in self.robovac_data
                # Line 186-187 in MqttConnect: self.robovac_data[command_name] = payload_data[command_name]
                # This IS the raw DPS data - keys like '150', '151', etc
                
                if hasattr(self._shared_connect, 'robovac_data'):
                    # This HAS the DPS keys!
                    self.raw_data = self._shared_connect.robovac_data.copy()
                    
                    if self.raw_data:
                        data_source = "MQTT (DPS Data)"
                        # Count keys 150-180
                        keys_150_180 = [k for k in self.raw_data.keys() if k.isdigit() and 150 <= int(k) <= 180]
                        if keys_150_180:
                            _LOGGER.info("Got %d DPS keys in range 150-180: %s", len(keys_150_180), keys_150_180)
                        _LOGGER.debug("Total DPS keys available: %d", len(self.raw_data))
                    else:
                        data_source = "MQTT (Waiting for data)"
                        _LOGGER.debug("Connected but no DPS data yet")
            else:
                _LOGGER.warning("No SharedConnect instance available")
                data_source = "None"
            
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
            self.parsed_data["is_connected"] = bool(self._shared_connect)
            self.parsed_data["consecutive_failures"] = self._consecutive_failures
            
            # Add MQTT status
            if self._shared_connect:
                if hasattr(self._shared_connect, 'mqttClient') and self._shared_connect.mqttClient:
                    self.parsed_data["mqtt_connected"] = self._shared_connect.mqttClient.is_connected()
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
        
        # Disconnect SharedConnect if exists
        if self._shared_connect:
            try:
                # SharedConnect inherits from MqttConnect so has mqttClient
                if hasattr(self._shared_connect, 'mqttClient') and self._shared_connect.mqttClient:
                    self._shared_connect.mqttClient.disconnect()
                    self._shared_connect.mqttClient.loop_stop()
                _LOGGER.info("MQTT client disconnected")
            except Exception as e:
                _LOGGER.error("Error disconnecting MQTT: %s", e)
        
        # Clear references
        self._eufy_login = None
        self._shared_connect = None
        self._event_loop = None