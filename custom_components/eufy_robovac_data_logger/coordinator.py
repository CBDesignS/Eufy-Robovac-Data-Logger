"""Data update coordinator for Eufy Robovac Data Logger integration."""
import asyncio
import json
import logging
import time
import uuid
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
        # Generate openudid like eufy-clean does
        self.openudid = entry.data.get("openudid", f"E{str(uuid.uuid4()).replace('-', '').upper()[:31]}")
        self.debug_mode = entry.data.get(CONF_DEBUG_MODE, False)
        
        # Store raw DPS data for logging
        self.raw_dps_data: Dict[str, Any] = {}
        self.parsed_data: Dict[str, Any] = {}
        self.last_update: Optional[float] = None
        self.update_count = 0
        
        # Connection tracking - EXACTLY like eufy-clean
        self.eufy_login = None
        self.mqtt_device = None  # This will be the MqttConnect instance
        self._last_successful_update = None
        self._consecutive_failures = 0
        
        # Log directory setup
        self.log_dir = Path(hass.config.config_dir) / LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        _LOGGER.info("Initializing Eufy Data Logger for device: %s", self.device_id)
        _LOGGER.debug("Device Name: %s", self.device_name)
        _LOGGER.debug("Device Model: %s", self.device_model)
        _LOGGER.debug("OpenUDID: %s", self.openudid)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Handle first refresh - Initialize connection EXACTLY like eufy-clean."""
        _LOGGER.info("Starting first refresh for device %s", self.device_id)
        
        try:
            # Initialize connections following eufy-clean pattern
            await self._setup_device()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            
            _LOGGER.info("First refresh completed successfully")
            
        except Exception as e:
            _LOGGER.error("Failed during first refresh: %s", e, exc_info=True)
            raise

    async def _setup_device(self) -> None:
        """Setup device connection EXACTLY like eufy-clean does."""
        try:
            # Import the controllers - EXACTLY as eufy-clean does
            from .controllers.Login import EufyLogin
            from .controllers.MqttConnect import MqttConnect
            
            _LOGGER.info("Trying to login with username: %s", self.username)
            
            # Create EufyLogin instance - EXACTLY like eufy-clean
            self.eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # Initialize login and get devices - this is what eufy-clean does
            await self.eufy_login.init()
            
            # Get devices from mqtt_devices property
            devices = self.eufy_login.mqtt_devices
            
            if not devices:
                _LOGGER.error("No devices found in account")
                raise Exception("No devices found")
            
            _LOGGER.info("Found %d devices via Eufy MQTT", len(devices))
            
            # Find our specific device
            device_config = None
            for device in devices:
                if device.get('deviceId') == self.device_id:
                    device_config = device
                    _LOGGER.debug("Found device config for %s", self.device_id)
                    break
            
            if not device_config:
                _LOGGER.error("Device %s not found in account", self.device_id)
                raise Exception(f"Device {self.device_id} not found")
            
            # Create MqttConnect config - EXACTLY as eufy-clean expects
            mqtt_config = {
                'deviceId': device_config['deviceId'],
                'deviceModel': device_config['deviceModel'],
                'deviceName': device_config.get('deviceName', ''),
                'deviceModelName': device_config.get('deviceModelName', ''),
                'apiType': device_config.get('apiType', 'novel'),
                'mqtt': device_config.get('mqtt', True),
                'debug': self.debug_mode,
                'dps': device_config.get('dps', {})
            }
            
            # Create MqttConnect instance - EXACTLY as eufy-clean does
            self.mqtt_device = MqttConnect(
                config=mqtt_config,
                openudid=self.openudid,
                eufyCleanApi=self.eufy_login
            )
            
            # Add listener for data updates
            self.mqtt_device.add_listener(self._on_mqtt_update)
            
            # Connect to MQTT
            _LOGGER.info("Connecting to MQTT for device %s", self.device_id)
            await self.mqtt_device.connect()
            
            # Initial data fetch if available
            if hasattr(self.mqtt_device, 'robovac_data'):
                self._process_robovac_data()
                _LOGGER.debug("Initial data processed, %d keys found", len(self.raw_dps_data))
            
        except Exception as e:
            _LOGGER.error("Failed to setup device: %s", e, exc_info=True)
            # Set mqtt_device to None so we know it failed
            self.mqtt_device = None
            raise

    async def _on_mqtt_update(self):
        """Handle MQTT data update - called by MqttConnect when data arrives."""
        _LOGGER.debug("MQTT data update received")
        try:
            # Process the new data
            self._process_robovac_data()
            
            # Request coordinator refresh to update sensors
            await self.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Error processing MQTT update: %s", e)

    def _process_robovac_data(self):
        """Process robovac_data from MqttConnect to extract DPS keys 150-180."""
        if not self.mqtt_device or not hasattr(self.mqtt_device, 'robovac_data'):
            _LOGGER.debug("No robovac_data available")
            return
        
        # Get all data from robovac_data
        all_data = self.mqtt_device.robovac_data
        
        # Clear and repopulate raw_dps_data with keys 150-180
        self.raw_dps_data = {}
        
        # MqttConnect stores DPS keys as strings in robovac_data
        for key in range(150, 181):
            str_key = str(key)
            if str_key in all_data:
                self.raw_dps_data[str_key] = all_data[str_key]
                if self.debug_mode:
                    value = all_data[str_key]
                    if isinstance(value, str) and len(value) > 50:
                        _LOGGER.debug("DPS Key %s: %s... (truncated)", str_key, value[:50])
                    else:
                        _LOGGER.debug("DPS Key %s: %s", str_key, value)
        
        if self.raw_dps_data:
            _LOGGER.debug("Processed %d DPS keys (150-180)", len(self.raw_dps_data))

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch and process data."""
        try:
            self.update_count += 1
            
            # Check connection status
            if not self.mqtt_device:
                _LOGGER.warning("MQTT device not initialized")
                self.parsed_data["is_connected"] = False
                self.parsed_data["data_source"] = "Not connected"
                return self.parsed_data
            
            # Process current data
            self._process_robovac_data()
            
            # Update parsed data for sensors
            self.parsed_data["is_connected"] = True
            self.parsed_data["data_source"] = "MQTT"
            self.parsed_data["total_keys"] = len(self.raw_dps_data)
            self.parsed_data["target_keys_found"] = sorted(list(self.raw_dps_data.keys()))
            self.parsed_data["target_keys_count"] = len(self.raw_dps_data)
            self.parsed_data["update_count"] = self.update_count
            self.parsed_data["last_update"] = time.time()
            
            # Check MQTT connection status
            mqtt_connected = False
            if hasattr(self.mqtt_device, 'mqttClient') and self.mqtt_device.mqttClient:
                mqtt_connected = self.mqtt_device.mqttClient.is_connected()
            self.parsed_data["mqtt_connected"] = mqtt_connected
            
            # Update success/failure tracking
            if self.raw_dps_data:
                self._consecutive_failures = 0
                self._last_successful_update = time.time()
                if self.debug_mode:
                    _LOGGER.debug("Update %d successful, %d keys available", 
                                 self.update_count, len(self.raw_dps_data))
            else:
                self._consecutive_failures += 1
                if self.debug_mode:
                    _LOGGER.debug("Update %d - no data available", self.update_count)
            
            self.parsed_data["consecutive_failures"] = self._consecutive_failures
            self.last_update = time.time()
            
            return self.parsed_data
            
        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error("Update failed: %s", err)
            raise UpdateFailed(f"Error during update: {err}")

    async def log_dps_data(self) -> str:
        """Log DPS keys 150-180 to timestamped JSON file."""
        try:
            if not self.raw_dps_data:
                _LOGGER.warning("No DPS data available to log")
                return "No DPS data available to log"
            
            _LOGGER.info("Logging %d DPS keys for device %s", 
                        len(self.raw_dps_data), self.device_id)
            
            # Create device-specific subdirectory
            device_log_dir = self.log_dir / self.device_id
            device_log_dir.mkdir(exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dps_log_{timestamp}.json"
            filepath = device_log_dir / filename
            
            # Prepare log data
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.device_id,
                "device_name": self.device_name,
                "device_model": self.device_model,
                "update_count": self.update_count,
                "keys": self.raw_dps_data
            }
            
            # Write to file
            import aiofiles
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(log_data, indent=2))
            
            _LOGGER.info("Successfully logged %d DPS keys to %s", 
                        len(self.raw_dps_data), filename)
            
            return f"Logged {len(self.raw_dps_data)} keys to {filename}"
            
        except Exception as e:
            _LOGGER.error("Failed to log DPS data: %s", e, exc_info=True)
            return f"Error logging data: {e}"

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        _LOGGER.info("Shutting down coordinator for device %s", self.device_id)
        
        # Disconnect MQTT if connected
        if self.mqtt_device:
            try:
                if hasattr(self.mqtt_device, 'mqttClient') and self.mqtt_device.mqttClient:
                    if self.mqtt_device.mqttClient.is_connected():
                        self.mqtt_device.mqttClient.disconnect()
                    self.mqtt_device.mqttClient.loop_stop()
                    _LOGGER.debug("MQTT client disconnected")
            except Exception as e:
                _LOGGER.error("Error disconnecting MQTT: %s", e)
        
        # Clear references
        self.eufy_login = None
        self.mqtt_device = None
        
        _LOGGER.debug("Coordinator shutdown complete")