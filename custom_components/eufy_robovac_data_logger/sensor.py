"""Sensor platform for Eufy Robovac Data Logger integration."""
import logging
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .constants.devices import EUFY_CLEAN_DEVICES

# FIX: Use our DOMAIN and get devices directly
DOMAIN = "eufy_robovac_data_logger"
DEVICES = "devices"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eufy Data Logger sensors."""
    
    # FIX: Get devices from hass.data, not a coordinator
    devices = hass.data[DOMAIN][DEVICES]
    
    entities = []
    for device_id, device in devices.items():
        _LOGGER.info("Setting up sensor for device %s", device_id)
        entities.append(EufyDataLoggerStatusSensor(device, device_id))
    
    async_add_entities(entities)


class EufyDataLoggerStatusSensor(SensorEntity):
    """Status sensor for Eufy Data Logger."""

    def __init__(self, device, device_id: str) -> None:
        """Initialize the sensor."""
        self.device = device
        self.device_id = device_id
        
        # Get device info
        self.device_model = device.device_model if hasattr(device, 'device_model') else "Unknown"
        self.device_name = device.device_model_desc if hasattr(device, 'device_model_desc') else device_id
        self.device_model_name = EUFY_CLEAN_DEVICES.get(self.device_model, self.device_model)
        
        self._attr_unique_id = f"{device_id}_dps_status"
        self._attr_name = "DPS Data Status"
        self._attr_icon = "mdi:database"
        
        # Device info matching vacuum and button
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=self.device_name,
            manufacturer="Eufy",
            model=self.device_model,
        )
        
        # Track DPS data
        self._dps_keys_found = 0
        self._last_update = None

    @property
    def native_value(self) -> str:
        """Return the status."""
        if hasattr(self.device, 'robovac_data'):
            # Count DPS keys 150-180
            self._dps_keys_found = 0
            for key in range(150, 181):
                if str(key) in self.device.robovac_data:
                    self._dps_keys_found += 1
            
            if self._dps_keys_found > 0:
                return f"{self._dps_keys_found}/31 DPS keys"
            else:
                return "No DPS data"
        else:
            return "Not connected"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attrs = {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_model": f"{self.device_model} ({self.device_model_name})",
            "dps_keys_found": self._dps_keys_found,
        }
        
        # Add available DPS keys if any
        if hasattr(self.device, 'robovac_data'):
            available_keys = []
            for key in range(150, 181):
                if str(key) in self.device.robovac_data:
                    available_keys.append(str(key))
            if available_keys:
                attrs["available_dps_keys"] = sorted(available_keys)
            
            # Add total keys in robovac_data
            attrs["total_keys"] = len(self.device.robovac_data)
        
        # Add MQTT connection status
        if hasattr(self.device, 'mqttClient') and self.device.mqttClient:
            attrs["mqtt_connected"] = self.device.mqttClient.is_connected()
        else:
            attrs["mqtt_connected"] = False
        
        return attrs