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
        
        # Get DPS data from robovac_data
        if hasattr(self.device, 'robovac_data'):
            # Extract DPS keys 150-180
            dps_data = {}
            all_keys = list(self.device.robovac_data.keys())
            _LOGGER.debug("All available keys: %s", all_keys)
            
            for key in range(150, 181):
                str_key = str(key)
                if str_key in self.device.robovac_data:
                    dps_data[str_key] = self.device.robovac_data[str_key]
            
            if dps_data:
                # Log to file
                log_dir = Path(self.hass.config.config_dir) / "eufy_dps_logs" / self.device_id
                log_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"dps_log_{timestamp}.json"
                filepath = log_dir / filename
                
                # Get model name from constants
                model_name = EUFY_CLEAN_DEVICES.get(self.device_model, self.device_model)
                
                log_data = {
                    "timestamp": datetime.now().isoformat(),
                    "device_id": self.device_id,
                    "device_name": self.device_name,
                    "device_model": self.device_model,
                    "device_model_name": model_name,
                    "total_keys": len(all_keys),
                    "logged_keys": len(dps_data),
                    "keys": dps_data
                }
                
                with open(filepath, 'w') as f:
                    json.dump(log_data, f, indent=2)
                
                _LOGGER.info("Successfully logged %d DPS keys (150-180) to %s", 
                            len(dps_data), filename)
                _LOGGER.info("Full path: %s", filepath)
                
                # Fire an event
                self.hass.bus.async_fire(
                    f"{DOMAIN}_dps_logged",
                    {
                        "device_id": self.device_id,
                        "keys_count": len(dps_data),
                        "file": str(filepath)
                    }
                )
            else:
                _LOGGER.warning("No DPS keys in range 150-180 found for device %s", self.device_id)
                _LOGGER.info("Available keys: %s", sorted(all_keys) if all_keys else "None")
        else:
            _LOGGER.error("Device %s has no robovac_data attribute", self.device_id)