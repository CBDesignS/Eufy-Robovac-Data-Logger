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
        self._rest_client = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        
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
            
            # Import here to avoid circular imports
            from .controllers.login import EufyLogin
            
            # Create login instance first
            self._eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # Initialize login to get authentication
            await self._eufy_login.init()
            _LOGGER.info("EufyLogin initialized successfully")
            
            # Try to create RestConnect client
            try:
                from .controllers.rest_connect import RestConnect
                
                rest_config = {
                    'deviceId': self.device_id,
                    'deviceModel': self.device_model,
                    'debug': self.debug_mode
                }
                
                self._rest_client = RestConnect(
                    config=rest_config,
                    openudid=self.openudid,
                    eufyCleanApi=self._eufy_login
                )
                
                # Try to connect
                await self._rest_client.connect()
                _LOGGER.info("RestConnect client initialized and connected")
                
            except Exception as rest_error:
                _LOGGER.warning("RestConnect not available: %s, using basic login only", rest_error)
                self._rest_client = None
            
        except Exception as e:
            _LOGGER.error("Failed to initialize connections: %s", e)
            raise

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy API."""
        try:
            self.update_count += 1
            
            if self.debug_mode:
                _LOGGER.debug("Update #%d starting", self.update_count)
            
            # Fetch data using RestConnect or fallback to basic login
            await self._fetch_eufy_data()
            
            # Process basic data for status sensor
            self._process_basic_data()
            
            # Reset consecutive failures on success
            self._consecutive_failures = 0
            self._last_successful_update = time.time()
            
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
        """Fetch data from Eufy API using RestConnect or basic login."""
        try:
            data_source = "Unknown"
            
            # Try RestConnect first (if available)
            if self._rest_client:
                try:
                    # Use RestConnect to get data
                    await self._rest_client.updateDevice()
                    rest_data = self._rest_client.get_raw_data()
                    
                    if rest_data:
                        self.raw_data = rest_data
                        data_source = "RestConnect"
                        if self.debug_mode:
                            _LOGGER.debug("RestConnect fetch successful: %d keys", len(self.raw_data))
                    else:
                        raise Exception("RestConnect returned no data")
                        
                except Exception as rest_error:
                    _LOGGER.warning("RestConnect failed: %s, falling back to basic login", rest_error)
                    self._rest_client = None
            
            # Use basic login (fallback or primary)
            if not self._rest_client or not self.raw_data:
                if self.debug_mode:
                    _LOGGER.debug("Using basic login for data fetch...")
                
                if not self._eufy_login:
                    raise Exception("No authentication method available")
                
                # Get device data with DPS
                device_data = await self._eufy_login.getMqttDevice(self.device_id)
                
                if device_data and 'dps' in device_data:
                    self.raw_data = device_data['dps']
                    data_source = "Basic Login"
                    if self.debug_mode:
                        _LOGGER.debug("Basic login fetch successful: %d keys", len(self.raw_data))
                else:
                    raise Exception("Basic login returned no data")
            
            # Store data source for status
            self.parsed_data["data_source"] = data_source
            self.parsed_data["total_keys"] = len(self.raw_data)
            self.parsed_data["last_update"] = time.time()
            self.parsed_data["update_count"] = self.update_count
            
        except Exception as e:
            _LOGGER.error("All data fetch methods failed: %s", e)
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
            self.parsed_data["is_connected"] = len(self.raw_data) > 0
            self.parsed_data["consecutive_failures"] = self._consecutive_failures
            
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
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(log_data, f, indent=2)
            
            _LOGGER.info("Logged %d DPS keys to %s", len(filtered_data), filename)
            return f"Logged {len(filtered_data)} keys to {filename}"
            
        except Exception as e:
            _LOGGER.error("Failed to log DPS data: %s", e)
            return f"Error logging data: {e}"

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        _LOGGER.info("Coordinator shutdown")
        
        # Shutdown RestConnect client if exists
        if self._rest_client:
            try:
                await self._rest_client.stop_polling()
                _LOGGER.info("RestConnect client disconnected")
            except Exception as e:
                _LOGGER.error("Error disconnecting RestConnect: %s", e)
        
        # Clear references
        self._eufy_login = None
        self._rest_client = None