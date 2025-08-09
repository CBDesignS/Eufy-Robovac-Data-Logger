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

from .const import DOMAIN, UPDATE_INTERVAL, DPS_KEYS_TO_LOG, LOG_DIR, CONF_DEBUG_MODE

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
        
        # Store raw DPS data for logging
        self.raw_dps_data: Dict[str, Any] = {}
        self.parsed_data: Dict[str, Any] = {}
        self.last_update: Optional[float] = None
        self.update_count = 0
        
        # Connection tracking
        self._eufy_login = None
        self._mqtt_connect = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        
        # Log directory setup
        self.log_dir = Path(hass.config.config_dir) / LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        _LOGGER.info("=" * 60)
        _LOGGER.info("EUFY DATA LOGGER COORDINATOR INITIALIZED")
        _LOGGER.info("Device ID: %s", self.device_id)
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
        _LOGGER.info("=" * 60)
        _LOGGER.info("STARTING FIRST REFRESH")
        _LOGGER.info("=" * 60)
        
        try:
            # Initialize connections
            await self._initialize_connections()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            
            _LOGGER.info("First refresh completed successfully")
            
        except Exception as e:
            _LOGGER.error("FAILED DURING FIRST REFRESH: %s", e)
            import traceback
            _LOGGER.error("FULL TRACEBACK:\n%s", traceback.format_exc())
            raise

    async def _initialize_connections(self) -> None:
        """Initialize MQTT connection following eufy-clean pattern."""
        _LOGGER.info("=" * 60)
        _LOGGER.info("INITIALIZING EUFY CONNECTIONS")
        _LOGGER.info("=" * 60)
        
        try:
            # Import the controllers we need
            from .controllers.Login import EufyLogin
            from .controllers.MqttConnect import MqttConnect
            
            # STEP 1: Create Login instance
            _LOGGER.info("STEP 1: Creating EufyLogin instance")
            _LOGGER.info("  Username: %s", self.username)
            _LOGGER.info("  OpenUDID: %s", self.openudid)
            
            self._eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # STEP 2: Initialize login (this logs in and gets devices)
            _LOGGER.info("STEP 2: Calling EufyLogin.init() to login and get devices")
            result = await self._eufy_login.init()
            _LOGGER.info("  Login init returned: %s", result)
            
            # STEP 3: Get devices from the mqtt_devices property
            _LOGGER.info("STEP 3: Getting devices from mqtt_devices property")
            devices = self._eufy_login.mqtt_devices
            
            if not devices:
                _LOGGER.error("NO DEVICES FOUND!")
                raise Exception("No devices found in account")
            
            _LOGGER.info("  Found %d devices:", len(devices))
            for idx, device in enumerate(devices):
                _LOGGER.info("  Device %d:", idx + 1)
                _LOGGER.info("    Device ID: %s", device.get('deviceId'))
                _LOGGER.info("    Device Name: %s", device.get('deviceName'))
                _LOGGER.info("    Device Model: %s", device.get('deviceModel'))
                _LOGGER.info("    API Type: %s", device.get('apiType'))
                _LOGGER.info("    MQTT Enabled: %s", device.get('mqtt'))
                
                # Log DPS data if present
                if device.get('dps'):
                    dps_keys = list(device['dps'].keys())
                    _LOGGER.info("    DPS Keys Present: %s", dps_keys)
                    # Check for keys 150-180
                    keys_150_180 = [k for k in dps_keys if k.isdigit() and 150 <= int(k) <= 180]
                    if keys_150_180:
                        _LOGGER.info("    Keys 150-180: %s", sorted(keys_150_180))
            
            # STEP 4: Find our specific device
            _LOGGER.info("STEP 4: Finding our device: %s", self.device_id)
            device_config = None
            for device in devices:
                if device.get('deviceId') == self.device_id:
                    device_config = device
                    _LOGGER.info("  FOUND OUR DEVICE!")
                    break
            
            if not device_config:
                _LOGGER.error("  Device %s NOT FOUND!", self.device_id)
                _LOGGER.error("  Available device IDs: %s", [d.get('deviceId') for d in devices])
                raise Exception(f"Device {self.device_id} not found")
            
            # STEP 5: Check MQTT credentials
            _LOGGER.info("STEP 5: Checking MQTT credentials")
            if not self._eufy_login.mqtt_credentials:
                _LOGGER.error("  NO MQTT CREDENTIALS AVAILABLE!")
                raise Exception("No MQTT credentials from login")
            
            _LOGGER.info("  MQTT Credentials Available:")
            _LOGGER.info("    Thing Name: %s", self._eufy_login.mqtt_credentials.get('thing_name'))
            _LOGGER.info("    User ID: %s", self._eufy_login.mqtt_credentials.get('user_id'))
            _LOGGER.info("    Endpoint: %s", self._eufy_login.mqtt_credentials.get('endpoint_addr'))
            _LOGGER.info("    App Name: %s", self._eufy_login.mqtt_credentials.get('app_name'))
            
            # STEP 6: Create MqttConnect instance
            _LOGGER.info("STEP 6: Creating MqttConnect instance")
            
            # Create the config dict that MqttConnect expects
            mqtt_config = {
                'deviceId': device_config['deviceId'],
                'deviceModel': device_config['deviceModel'],
                'apiType': device_config.get('apiType', 'novel'),
                'mqtt': device_config.get('mqtt', True),
                'debug': self.debug_mode,
                'deviceName': device_config.get('deviceName', ''),
                'deviceModelName': device_config.get('deviceModelName', ''),
                'dps': device_config.get('dps', {})
            }
            
            _LOGGER.info("  Config for MqttConnect:")
            for key, value in mqtt_config.items():
                if key == 'dps':
                    _LOGGER.info("    %s: %d keys", key, len(value))
                else:
                    _LOGGER.info("    %s: %s", key, value)
            
            # Create MqttConnect with correct parameters
            self._mqtt_connect = MqttConnect(
                config=mqtt_config,
                openudid=self.openudid,
                eufyCleanApi=self._eufy_login
            )
            _LOGGER.info("  MqttConnect instance created")
            
            # STEP 7: Add listener for data updates
            _LOGGER.info("STEP 7: Adding data update listener")
            self._mqtt_connect.add_listener(self._handle_mqtt_data_update)
            
            # STEP 8: Connect to MQTT
            _LOGGER.info("STEP 8: Connecting to MQTT...")
            await self._mqtt_connect.connect()
            _LOGGER.info("  MQTT connect() completed")
            
            # STEP 9: Check initial data
            _LOGGER.info("STEP 9: Checking initial robovac_data")
            if hasattr(self._mqtt_connect, 'robovac_data'):
                data_keys = list(self._mqtt_connect.robovac_data.keys())
                _LOGGER.info("  Initial robovac_data has %d keys: %s", len(data_keys), data_keys)
                
                # Store initial DPS data
                self._store_dps_data()
            else:
                _LOGGER.warning("  No robovac_data attribute yet")
            
            _LOGGER.info("=" * 60)
            _LOGGER.info("CONNECTION INITIALIZATION COMPLETE")
            _LOGGER.info("=" * 60)
            
        except Exception as e:
            _LOGGER.error("=" * 60)
            _LOGGER.error("FAILED TO INITIALIZE CONNECTIONS")
            _LOGGER.error("Error: %s", e)
            import traceback
            _LOGGER.error("Full traceback:\n%s", traceback.format_exc())
            _LOGGER.error("=" * 60)
            raise

    async def _handle_mqtt_data_update(self):
        """Handle data update from MQTT - called when MqttConnect gets new data."""
        try:
            _LOGGER.debug("MQTT data update received - storing DPS data and refreshing")
            
            # Store the latest DPS data
            self._store_dps_data()
            
            # Request coordinator refresh
            await self.async_request_refresh()
            
        except Exception as e:
            _LOGGER.error("Error handling MQTT data update: %s", e)

    def _store_dps_data(self):
        """Store DPS data from MqttConnect's robovac_data."""
        if not self._mqtt_connect or not hasattr(self._mqtt_connect, 'robovac_data'):
            return
        
        # Get all data from robovac_data
        all_data = self._mqtt_connect.robovac_data.copy()
        
        # Clear existing DPS data
        self.raw_dps_data = {}
        
        # Store keys 150-180 (they should be stored as strings)
        for key in range(150, 181):
            str_key = str(key)
            if str_key in all_data:
                self.raw_dps_data[str_key] = all_data[str_key]
                if self.debug_mode:
                    value = all_data[str_key]
                    if isinstance(value, str) and len(value) > 50:
                        _LOGGER.debug("  DPS Key %s: %s... (truncated)", str_key, value[:50])
                    else:
                        _LOGGER.debug("  DPS Key %s: %s", str_key, value)
        
        if self.raw_dps_data:
            _LOGGER.info("Stored %d DPS keys (150-180): %s", 
                        len(self.raw_dps_data), 
                        sorted(self.raw_dps_data.keys()))

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch and process data."""
        try:
            self.update_count += 1
            
            if self.debug_mode:
                _LOGGER.debug("=" * 40)
                _LOGGER.debug("Update #%d starting", self.update_count)
            
            # Check MQTT connection and get latest data
            await self._check_mqtt_status()
            
            # Process data for sensors
            self._process_sensor_data()
            
            # Update success/failure tracking
            if self.raw_dps_data:
                self._consecutive_failures = 0
                self._last_successful_update = time.time()
            else:
                self._consecutive_failures += 1
            
            self.last_update = time.time()
            
            if self.debug_mode:
                _LOGGER.debug("Update #%d completed - %d DPS keys available", 
                             self.update_count, len(self.raw_dps_data))
                _LOGGER.debug("=" * 40)
            
            return self.parsed_data
            
        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error("Update #%d failed: %s", self.update_count, err)
            raise UpdateFailed(f"Error during update: {err}")

    async def _check_mqtt_status(self) -> None:
        """Check MQTT connection status and get latest data."""
        data_source = "Unknown"
        
        if self._mqtt_connect:
            # Check if MQTT client is connected
            mqtt_connected = False
            if hasattr(self._mqtt_connect, 'mqttClient') and self._mqtt_connect.mqttClient:
                mqtt_connected = self._mqtt_connect.mqttClient.is_connected()
            
            # Get latest DPS data
            if hasattr(self._mqtt_connect, 'robovac_data'):
                self._store_dps_data()
                
                if self.raw_dps_data:
                    data_source = "MQTT (DPS Data)"
                elif mqtt_connected:
                    data_source = "MQTT (Waiting for data)"
                else:
                    data_source = "MQTT (Disconnected)"
            else:
                data_source = "MQTT (No data attribute)"
        else:
            data_source = "Not connected"
        
        self.parsed_data["data_source"] = data_source
        self.parsed_data["mqtt_connected"] = mqtt_connected if self._mqtt_connect else False

    def _process_sensor_data(self) -> None:
        """Process data for status sensor."""
        # Count DPS keys 150-180
        target_keys_found = list(self.raw_dps_data.keys())
        
        self.parsed_data["target_keys_found"] = sorted(target_keys_found)
        self.parsed_data["target_keys_count"] = len(target_keys_found)
        self.parsed_data["total_keys"] = len(self.raw_dps_data)
        self.parsed_data["is_connected"] = bool(self._mqtt_connect)
        self.parsed_data["consecutive_failures"] = self._consecutive_failures
        self.parsed_data["last_update"] = self.last_update
        self.parsed_data["update_count"] = self.update_count

    async def log_dps_data(self) -> str:
        """Log DPS keys 150-180 to timestamped JSON file."""
        try:
            _LOGGER.info("=" * 60)
            _LOGGER.info("LOGGING DPS DATA TO FILE")
            _LOGGER.info("=" * 60)
            
            if not self.raw_dps_data:
                msg = "No DPS data available to log"
                _LOGGER.warning(msg)
                return msg
            
            _LOGGER.info("Have %d DPS keys to log", len(self.raw_dps_data))
            _LOGGER.info("Keys: %s", sorted(self.raw_dps_data.keys()))
            
            # Create device-specific subdirectory
            device_log_dir = self.log_dir / self.device_id
            device_log_dir.mkdir(exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dps_log_{timestamp}.json"
            filepath = device_log_dir / filename
            
            # Prepare log data with all DPS keys 150-180
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id,
                "device_name": self.device_name,
                "device_model": self.device_model,
                "update_count": self.update_count,
                "keys": self.raw_dps_data  # This already contains only keys 150-180
            }
            
            # Write to file
            import aiofiles
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(log_data, indent=2))
            
            _LOGGER.info("Successfully logged %d DPS keys", len(self.raw_dps_data))
            _LOGGER.info("File: %s", filepath)
            _LOGGER.info("=" * 60)
            
            return f"Logged {len(self.raw_dps_data)} keys to {filepath.name}"
            
        except Exception as e:
            _LOGGER.error("Failed to log DPS data: %s", e)
            import traceback
            _LOGGER.error("Traceback:\n%s", traceback.format_exc())
            return f"Error logging data: {e}"

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        _LOGGER.info("=" * 60)
        _LOGGER.info("SHUTTING DOWN COORDINATOR")
        _LOGGER.info("=" * 60)
        
        # Disconnect MQTT if connected
        if self._mqtt_connect:
            try:
                _LOGGER.info("Disconnecting MQTT...")
                if hasattr(self._mqtt_connect, 'mqttClient') and self._mqtt_connect.mqttClient:
                    if self._mqtt_connect.mqttClient.is_connected():
                        self._mqtt_connect.mqttClient.disconnect()
                    self._mqtt_connect.mqttClient.loop_stop()
                    _LOGGER.info("MQTT disconnected")
                else:
                    _LOGGER.info("No MQTT client to disconnect")
            except Exception as e:
                _LOGGER.error("Error disconnecting MQTT: %s", e)
        
        # Clear references
        self._eufy_login = None
        self._mqtt_connect = None
        
        _LOGGER.info("Coordinator shutdown complete")
        _LOGGER.info("=" * 60)