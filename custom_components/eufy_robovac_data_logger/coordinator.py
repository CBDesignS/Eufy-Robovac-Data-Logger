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
        self._mqtt_connect = None  # Use proper name for MqttConnect
        self._last_successful_update = None
        self._consecutive_failures = 0
        self._event_loop = None
        
        # Log directory setup
        self.log_dir = Path(hass.config.config_dir) / LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        _LOGGER.info("=" * 60)
        _LOGGER.info("Coordinator initialized for device: %s", self.device_id)
        _LOGGER.info("Device Name: %s", self.device_name)
        _LOGGER.info("Device Model: %s", self.device_model)
        _LOGGER.info("OpenUDID: %s", self.openudid)
        _LOGGER.info("Debug Mode: %s", self.debug_mode)
        _LOGGER.info("Log Directory: %s", self.log_dir)
        _LOGGER.info("=" * 60)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Handle first refresh."""
        _LOGGER.info("Starting first refresh for device %s", self.device_id)
        try:
            # Store event loop for MQTT callbacks
            self._event_loop = asyncio.get_running_loop()
            _LOGGER.debug("Event loop stored: %s", self._event_loop)
            
            # Initialize connections
            await self._initialize_connections()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            _LOGGER.info("First refresh completed successfully")
            
        except Exception as e:
            _LOGGER.error("Failed during first refresh: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            raise

    async def _initialize_connections(self) -> None:
        """Initialize the connection clients."""
        _LOGGER.info("=" * 60)
        _LOGGER.info("INITIALIZING CONNECTIONS")
        _LOGGER.info("=" * 60)
        
        try:
            # Import with correct case sensitivity
            from .controllers.Login import EufyLogin
            from .controllers.MqttConnect import MqttConnect
            
            _LOGGER.info("Step 1: Creating EufyLogin instance")
            _LOGGER.info("  Username: %s", self.username)
            _LOGGER.info("  OpenUDID: %s", self.openudid)
            
            # Create login instance first
            self._eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            _LOGGER.info("Step 2: Calling EufyLogin.init()")
            # Initialize login to get authentication and devices
            await self._eufy_login.init()
            
            _LOGGER.info("Step 3: Getting devices from mqtt_devices property")
            devices = self._eufy_login.mqtt_devices  # Get from property
            
            if devices:
                _LOGGER.info("Found %d devices:", len(devices))
                for idx, device in enumerate(devices):
                    _LOGGER.info("  Device %d:", idx + 1)
                    _LOGGER.info("    Device ID: %s", device.get('deviceId'))
                    _LOGGER.info("    Device Name: %s", device.get('deviceName'))
                    _LOGGER.info("    Device Model: %s", device.get('deviceModel'))
                    _LOGGER.info("    API Type: %s", device.get('apiType'))
                    _LOGGER.info("    MQTT: %s", device.get('mqtt'))
                    _LOGGER.info("    DPS Keys Present: %s", list(device.get('dps', {}).keys()) if device.get('dps') else "None")
            else:
                _LOGGER.warning("No devices found!")
            
            _LOGGER.info("Step 4: Finding our device config for %s", self.device_id)
            # Find our device config
            device_config = None
            for device in devices:
                if device.get('deviceId') == self.device_id:
                    device_config = device
                    _LOGGER.info("Found matching device config!")
                    break
            
            if not device_config:
                _LOGGER.error("Device %s not found in login results", self.device_id)
                _LOGGER.error("Available device IDs: %s", [d.get('deviceId') for d in devices])
                raise Exception(f"Device {self.device_id} not found")
            
            _LOGGER.info("Step 5: Checking MQTT credentials")
            # Check if we have MQTT credentials
            if self._eufy_login.mqtt_credentials:
                _LOGGER.info("MQTT credentials available:")
                _LOGGER.info("  Thing Name: %s", self._eufy_login.mqtt_credentials.get('thing_name'))
                _LOGGER.info("  User ID: %s", self._eufy_login.mqtt_credentials.get('user_id'))
                _LOGGER.info("  Endpoint: %s", self._eufy_login.mqtt_credentials.get('endpoint_addr'))
                
                try:
                    _LOGGER.info("Step 6: Creating MqttConnect instance")
                    
                    # Create config for MqttConnect - THIS IS WHAT IT EXPECTS
                    mqtt_config = {
                        'deviceId': device_config['deviceId'],
                        'deviceModel': device_config['deviceModel'],
                        'apiType': device_config.get('apiType', 'novel'),
                        'mqtt': device_config.get('mqtt', True),
                        'debug': self.debug_mode,
                        'dps': device_config.get('dps', {})  # Include DPS data
                    }
                    
                    _LOGGER.info("MqttConnect config created:")
                    for key, value in mqtt_config.items():
                        if key != 'dps':
                            _LOGGER.info("  %s: %s", key, value)
                        else:
                            _LOGGER.info("  dps: %d keys present", len(value) if value else 0)
                    
                    # Create MqttConnect instance with correct arguments
                    self._mqtt_connect = MqttConnect(mqtt_config, self.openudid, self._eufy_login)
                    _LOGGER.info("MqttConnect instance created successfully")
                    
                    # Add listener for data updates
                    _LOGGER.info("Step 7: Adding update listener")
                    self._mqtt_connect.add_listener(self._handle_mqtt_update)
                    
                    # Connect to MQTT
                    _LOGGER.info("Step 8: Connecting to MQTT...")
                    await self._mqtt_connect.connect()
                    _LOGGER.info("MQTT connection initiated successfully")
                    
                    # Log initial robovac_data state
                    if hasattr(self._mqtt_connect, 'robovac_data'):
                        _LOGGER.info("Initial robovac_data keys: %s", list(self._mqtt_connect.robovac_data.keys()))
                    else:
                        _LOGGER.warning("MqttConnect has no robovac_data attribute yet")
                    
                except Exception as mqtt_error:
                    _LOGGER.error("Failed to initialize MqttConnect: %s", mqtt_error)
                    import traceback
                    _LOGGER.error("Traceback: %s", traceback.format_exc())
                    self._mqtt_connect = None
            else:
                _LOGGER.warning("No MQTT credentials available from login")
                self._mqtt_connect = None
            
            _LOGGER.info("=" * 60)
            _LOGGER.info("CONNECTION INITIALIZATION COMPLETE")
            _LOGGER.info("=" * 60)
            
        except Exception as e:
            _LOGGER.error("Failed to initialize connections: %s", e)
            import traceback
            _LOGGER.error("Full traceback: %s", traceback.format_exc())
            raise

    async def _handle_mqtt_update(self):
        """Handle update from MQTT - called by MqttConnect when data arrives."""
        try:
            _LOGGER.debug("MQTT update received - requesting coordinator refresh")
            # MQTT has updated the data, refresh our state
            await self.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Error handling MQTT update: %s", e)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy API."""
        try:
            self.update_count += 1
            
            if self.debug_mode:
                _LOGGER.debug("=" * 40)
                _LOGGER.debug("Update #%d starting", self.update_count)
            
            # Fetch data from MqttConnect
            await self._fetch_eufy_data()
            
            # Process basic data for status sensor
            self._process_basic_data()
            
            # Reset consecutive failures on success if we have data
            if self.raw_data:
                self._consecutive_failures = 0
                self._last_successful_update = time.time()
                if self.debug_mode:
                    _LOGGER.debug("Update successful, data available")
            else:
                self._consecutive_failures += 1
                if self.debug_mode:
                    _LOGGER.debug("No data available, consecutive failures: %d", self._consecutive_failures)
            
            self.last_update = time.time()
            
            if self.debug_mode:
                _LOGGER.debug("Update #%d completed, %d keys available", 
                             self.update_count, len(self.raw_data))
                _LOGGER.debug("=" * 40)
            
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
                _LOGGER.debug("Fetching data from MqttConnect...")
                
                # MqttConnect stores DPS data in robovac_data with mapped keys
                # The dps_map in Base.py maps friendly names to DPS keys
                # But the raw DPS data is also stored with the DPS key numbers
                
                if hasattr(self._mqtt_connect, 'robovac_data'):
                    # Get the raw robovac_data
                    self.raw_data = self._mqtt_connect.robovac_data.copy()
                    
                    if self.raw_data:
                        data_source = "MQTT (DPS Data)"
                        
                        # Log what keys we have
                        all_keys = list(self.raw_data.keys())
                        _LOGGER.debug("All keys in robovac_data: %s", all_keys)
                        
                        # Count keys 150-180 (they should be stored as strings)
                        keys_150_180 = []
                        for key in all_keys:
                            if key.isdigit() and 150 <= int(key) <= 180:
                                keys_150_180.append(key)
                        
                        if keys_150_180:
                            _LOGGER.info("Found %d DPS keys in range 150-180: %s", len(keys_150_180), sorted(keys_150_180))
                            # Log sample values for debugging
                            for key in sorted(keys_150_180)[:5]:  # First 5 keys
                                value = self.raw_data[key]
                                if isinstance(value, str) and len(value) > 50:
                                    _LOGGER.debug("  Key %s: %s... (truncated)", key, value[:50])
                                else:
                                    _LOGGER.debug("  Key %s: %s", key, value)
                        else:
                            _LOGGER.warning("No keys in range 150-180 found. Available keys: %s", all_keys)
                    else:
                        data_source = "MQTT (Waiting for data)"
                        _LOGGER.debug("MqttConnect has robovac_data but it's empty")
                else:
                    _LOGGER.warning("MqttConnect has no robovac_data attribute")
                    data_source = "MQTT (No data attribute)"
                
                # Check MQTT connection status
                if hasattr(self._mqtt_connect, 'mqttClient'):
                    if self._mqtt_connect.mqttClient:
                        is_connected = self._mqtt_connect.mqttClient.is_connected()
                        _LOGGER.debug("MQTT client connection status: %s", is_connected)
                        if not is_connected:
                            data_source = "MQTT (Disconnected)"
                    else:
                        _LOGGER.debug("MQTT client is None")
                        data_source = "MQTT (Client not initialized)"
            else:
                _LOGGER.warning("No MqttConnect instance available")
                data_source = "None (No MQTT)"
            
            # Store data source for status
            self.parsed_data["data_source"] = data_source
            self.parsed_data["total_keys"] = len(self.raw_data)
            self.parsed_data["last_update"] = time.time()
            self.parsed_data["update_count"] = self.update_count
            
            _LOGGER.debug("Data fetch complete - Source: %s, Total keys: %d", 
                         data_source, len(self.raw_data))
            
        except Exception as e:
            _LOGGER.error("Data fetch failed: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            raise

    def _process_basic_data(self) -> None:
        """Process basic data for status sensor."""
        try:
            # Count how many of our target keys (150-180) are present
            target_keys_found = []
            for key in DPS_KEYS_TO_LOG:
                str_key = str(key)
                if str_key in self.raw_data:
                    target_keys_found.append(str_key)
            
            self.parsed_data["target_keys_found"] = target_keys_found
            self.parsed_data["target_keys_count"] = len(target_keys_found)
            
            if self.debug_mode and target_keys_found:
                _LOGGER.debug("Target keys found: %s", sorted(target_keys_found))
            
            # Connection status
            self.parsed_data["is_connected"] = bool(self._mqtt_connect)
            self.parsed_data["consecutive_failures"] = self._consecutive_failures
            
            # Add MQTT status
            if self._mqtt_connect:
                if hasattr(self._mqtt_connect, 'mqttClient') and self._mqtt_connect.mqttClient:
                    self.parsed_data["mqtt_connected"] = self._mqtt_connect.mqttClient.is_connected()
                else:
                    self.parsed_data["mqtt_connected"] = False
            else:
                self.parsed_data["mqtt_connected"] = False
            
            _LOGGER.debug("Basic data processed - Connected: %s, MQTT: %s, Keys found: %d", 
                         self.parsed_data["is_connected"],
                         self.parsed_data["mqtt_connected"],
                         self.parsed_data["target_keys_count"])
            
        except Exception as e:
            _LOGGER.error("Error processing basic data: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())

    async def log_dps_data(self) -> str:
        """Log DPS keys 150-180 to timestamped file."""
        try:
            _LOGGER.info("=" * 60)
            _LOGGER.info("LOGGING DPS DATA")
            _LOGGER.info("=" * 60)
            
            if not self.raw_data:
                msg = "No data available to log"
                _LOGGER.warning(msg)
                return msg
            
            _LOGGER.info("Raw data has %d total keys", len(self.raw_data))
            
            # Filter for keys 150-180
            filtered_data = {}
            for key in DPS_KEYS_TO_LOG:
                str_key = str(key)
                if str_key in self.raw_data:
                    filtered_data[str_key] = self.raw_data[str_key]
                    _LOGGER.debug("Including key %s in log", str_key)
            
            if not filtered_data:
                msg = "No keys in range 150-180 found"
                _LOGGER.warning(msg)
                _LOGGER.warning("Available keys: %s", list(self.raw_data.keys()))
                return msg
            
            _LOGGER.info("Found %d keys in range 150-180 to log", len(filtered_data))
            
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
            
            _LOGGER.info("Successfully logged %d DPS keys to %s", len(filtered_data), filename)
            _LOGGER.info("Full path: %s", filepath)
            _LOGGER.info("=" * 60)
            
            return f"Logged {len(filtered_data)} keys to {filename}"
            
        except Exception as e:
            _LOGGER.error("Failed to log DPS data: %s", e)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return f"Error logging data: {e}"

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        _LOGGER.info("=" * 60)
        _LOGGER.info("COORDINATOR SHUTDOWN")
        _LOGGER.info("=" * 60)
        
        # Disconnect MqttConnect if exists
        if self._mqtt_connect:
            try:
                _LOGGER.info("Disconnecting MQTT client...")
                if hasattr(self._mqtt_connect, 'mqttClient') and self._mqtt_connect.mqttClient:
                    self._mqtt_connect.mqttClient.disconnect()
                    self._mqtt_connect.mqttClient.loop_stop()
                    _LOGGER.info("MQTT client disconnected successfully")
                else:
                    _LOGGER.warning("No MQTT client to disconnect")
            except Exception as e:
                _LOGGER.error("Error disconnecting MQTT: %s", e)
        
        # Clear references
        self._eufy_login = None
        self._mqtt_connect = None
        self._event_loop = None
        
        _LOGGER.info("Coordinator shutdown complete")
        _LOGGER.info("=" * 60)