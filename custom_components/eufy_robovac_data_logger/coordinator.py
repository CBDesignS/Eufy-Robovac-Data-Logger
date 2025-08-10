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

# Get the logger for THIS module
_LOGGER = logging.getLogger(__name__)


class EufyDataLoggerCoordinator(DataUpdateCoordinator):
    """Eufy Robovac data coordinator for logging DPS data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.device_id = entry.data["device_id"]
        self.device_name = entry.data.get("device_name", "Unknown Device")
        self.device_model = entry.data.get("device_model", "Unknown")
        self.username = entry.data["username"]
        self.password = entry.data["password"]
        self.openudid = entry.data.get("openudid")
        if not self.openudid:
            # Generate like eufy-clean does
            self.openudid = f"E{str(uuid.uuid4()).replace('-', '').upper()[:31]}"
        self.debug_mode = entry.data.get(CONF_DEBUG_MODE, False)
        
        # Store DPS data
        self.raw_dps_data = {}
        self.parsed_data = {}
        self.last_update = None
        self.update_count = 0
        
        # Connection objects
        self.eufy_login = None
        self.mqtt_device = None
        self._consecutive_failures = 0
        
        # Log directory
        self.log_dir = Path(hass.config.config_dir) / LOG_DIR
        self.log_dir.mkdir(exist_ok=True)
        
        # Look up device name
        try:
            from .constants.devices import EUFY_CLEAN_DEVICES
            self.device_model_name = EUFY_CLEAN_DEVICES.get(self.device_model, self.device_model)
            _LOGGER.info("Device %s model %s is: %s", self.device_id, self.device_model, self.device_model_name)
        except Exception as e:
            _LOGGER.warning("Could not look up device model: %s", e)
            self.device_model_name = self.device_model
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        try:
            self.update_count += 1
            
            # Initialize connection if needed
            if not self.mqtt_device:
                await self._initialize_device()
            
            # Get current data
            if self.mqtt_device and hasattr(self.mqtt_device, 'robovac_data'):
                # Extract DPS keys 150-180
                self.raw_dps_data = {}
                for key in range(150, 181):
                    str_key = str(key)
                    if str_key in self.mqtt_device.robovac_data:
                        self.raw_dps_data[str_key] = self.mqtt_device.robovac_data[str_key]
                
                if self.raw_dps_data:
                    _LOGGER.debug("Found %d DPS keys", len(self.raw_dps_data))
                    self._consecutive_failures = 0
            
            # Update parsed data
            self.parsed_data = {
                "is_connected": bool(self.mqtt_device),
                "data_source": "MQTT" if self.mqtt_device else "Not connected",
                "total_keys": len(self.raw_dps_data),
                "target_keys_found": sorted(list(self.raw_dps_data.keys())),
                "target_keys_count": len(self.raw_dps_data),
                "update_count": self.update_count,
                "last_update": time.time(),
                "consecutive_failures": self._consecutive_failures,
            }
            
            self.last_update = time.time()
            return self.parsed_data
            
        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.error("Error updating data: %s", err)
            raise UpdateFailed(f"Error updating: {err}")

    async def _initialize_device(self):
        """Initialize the device connection."""
        _LOGGER.info("Initializing device connection for %s", self.device_id)
        
        try:
            # Import controllers
            from .controllers.Login import EufyLogin
            from .controllers.MqttConnect import MqttConnect
            
            # Create login
            _LOGGER.info("Creating login for user: %s", self.username)
            self.eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # Initialize and get devices
            _LOGGER.info("Logging in and getting devices...")
            await self.eufy_login.init()
            
            # Get devices
            devices = self.eufy_login.mqtt_devices
            if not devices:
                raise Exception("No devices found")
            
            _LOGGER.info("Found %d devices", len(devices))
            
            # Find our device
            device_config = None
            for device in devices:
                if device.get('deviceId') == self.device_id:
                    device_config = device
                    break
            
            if not device_config:
                raise Exception(f"Device {self.device_id} not found")
            
            _LOGGER.info("Found device config for %s", self.device_id)
            
            # Create MQTT config
            config = {
                'deviceId': device_config['deviceId'],
                'deviceModel': device_config['deviceModel'],
                'debug': self.debug_mode,
            }
            
            # Add optional fields if present
            for key in ['deviceName', 'deviceModelName', 'apiType', 'mqtt', 'dps']:
                if key in device_config:
                    config[key] = device_config[key]
            
            # Create MQTT connection
            _LOGGER.info("Creating MQTT connection...")
            self.mqtt_device = MqttConnect(
                config=config,
                openudid=self.openudid,
                eufyCleanApi=self.eufy_login
            )
            
            # Add update listener
            self.mqtt_device.add_listener(self._on_data_update)
            
            # Connect
            _LOGGER.info("Connecting to MQTT...")
            await self.mqtt_device.connect()
            
            _LOGGER.info("MQTT connection established")
            
        except Exception as e:
            _LOGGER.error("Failed to initialize device: %s", e, exc_info=True)
            self.mqtt_device = None
            raise

    async def _on_data_update(self):
        """Handle data update from MQTT."""
        _LOGGER.debug("Data update from MQTT")
        await self.async_request_refresh()

    async def log_dps_data(self) -> str:
        """Log DPS data to file."""
        if not self.raw_dps_data:
            _LOGGER.warning("No DPS data available to log")
            return "No DPS data available"
        
        # Create device subdirectory
        device_dir = self.log_dir / self.device_id
        device_dir.mkdir(exist_ok=True)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dps_log_{timestamp}.json"
        filepath = device_dir / filename
        
        # Prepare data
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_model": self.device_model,
            "device_model_name": self.device_model_name,
            "update_count": self.update_count,
            "keys": self.raw_dps_data
        }
        
        # Write file
        try:
            import aiofiles
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(log_data, indent=2))
            
            _LOGGER.info("Logged %d keys to %s", len(self.raw_dps_data), filename)
            return f"Logged {len(self.raw_dps_data)} keys to {filename}"
            
        except Exception as e:
            _LOGGER.error("Failed to write log file: %s", e)
            return f"Error: {e}"

    async def async_shutdown(self):
        """Shutdown coordinator."""
        _LOGGER.info("Shutting down coordinator")
        
        if self.mqtt_device:
            try:
                if hasattr(self.mqtt_device, 'mqttClient') and self.mqtt_device.mqttClient:
                    self.mqtt_device.mqttClient.disconnect()
                    self.mqtt_device.mqttClient.loop_stop()
            except Exception as e:
                _LOGGER.error("Error disconnecting: %s", e)
        
        self.eufy_login = None
        self.mqtt_device = None