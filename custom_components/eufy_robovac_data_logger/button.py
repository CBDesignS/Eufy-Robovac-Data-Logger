"""Button platform for Eufy Robovac Data Logger integration."""
import json
import logging
from datetime import datetime
from pathlib import Path

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .constants.devices import EUFY_CLEAN_DEVICES

DOMAIN = "eufy_robovac_data_logger"
DEVICES = "devices"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eufy Data Logger buttons - following eufy-clean pattern."""
    
    for device_id, device in hass.data[DOMAIN][DEVICES].items():
        _LOGGER.info("Adding log button for %s", device_id)
        
        # Create log button for this device
        log_button = EufyDataLoggerButton(hass, device, device_id)
        async_add_entities([log_button])


class EufyDataLoggerButton(ButtonEntity):
    """Button to trigger DPS data logging."""

    def __init__(self, hass: HomeAssistant, device, device_id: str) -> None:
        """Initialize the button."""
        self.hass = hass
        self.device = device
        self.device_id = device_id
        
        # Get device info
        self.device_model = device.device_model if hasattr(device, 'device_model') else "Unknown"
        self.device_name = device.device_model_desc if hasattr(device, 'device_model_desc') else device_id
        
        self._attr_unique_id = f"{device_id}_log_dps_data"
        self._attr_name = f"Log DPS Data"
        self._attr_icon = "mdi:file-export"
        
        # Device info - like eufy-clean does it
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=self.device_name,
            manufacturer="Eufy",
            model=self.device_model,
        )

    async def async_press(self) -> None:
        """Handle the button press - log DPS data."""
        _LOGGER.info("Log button pressed for device %s", self.device_id)
        
        # Get all robovac_data (includes DPS keys)
        robovac_data = getattr(self.device, 'robovac_data', {})
        
        if not robovac_data:
            _LOGGER.warning("No robovac_data available for device %s", self.device_id)
            return
            
        # Debug: Log all available keys
        all_keys = list(robovac_data.keys())
        _LOGGER.debug("All available keys: %s", all_keys)
        
        # Collect all DPS data (numeric keys from 150-180)
        dps_data = {}
        for key in robovac_data:
            try:
                # Check if key is numeric and in range 150-180
                if isinstance(key, str) and key.isdigit():
                    key_num = int(key)
                    if 150 <= key_num <= 180:
                        dps_data[key] = robovac_data[key]
            except (ValueError, TypeError):
                continue
                
        if not dps_data:
            _LOGGER.warning("No DPS data (keys 150-180) found for device %s", self.device_id)
            return
            
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dps_log_{timestamp}.json"
        
        # Create directory structure
        base_path = Path("/config/eufy_dps_logs")
        device_path = base_path / self.device_id
        device_path.mkdir(parents=True, exist_ok=True)
        
        # Full file path
        filepath = device_path / filename
        
        # Prepare data to write
        log_data = {
            "timestamp": timestamp,
            "device_id": self.device_id,
            "device_model": self.device_model,
            "dps_data": dps_data
        }
        
        # FIX: Use executor to avoid blocking call
        await self.hass.async_add_executor_job(
            self._write_json_file, filepath, log_data
        )
        
        _LOGGER.info("Successfully logged %d DPS keys (150-180) to %s", 
                    len(dps_data), filename)
        _LOGGER.info("Full path: %s", filepath)
    
    def _write_json_file(self, filepath, data):
        """Write JSON file - sync method for executor."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)