"""Sensor platform for Eufy Robovac Data Logger integration."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DPS_KEYS_TO_LOG
from .coordinator import EufyDataLoggerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eufy Data Logger sensors."""
    coordinator: EufyDataLoggerCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Create just one status sensor
    entities = [
        EufyDataLoggerStatusSensor(coordinator),
    ]
    
    _LOGGER.info("Setting up sensor for device %s", coordinator.device_id)
    
    async_add_entities(entities)


class EufyDataLoggerStatusSensor(CoordinatorEntity, SensorEntity):
    """Status sensor for Eufy Data Logger."""

    def __init__(self, coordinator: EufyDataLoggerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_id = coordinator.device_id
        
        self._attr_unique_id = f"{self.device_id}_status"
        self._attr_name = f"Eufy Data Logger Status"
        self._attr_icon = "mdi:database"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=f"Eufy Data Logger {coordinator.device_name}",
            manufacturer="Eufy",
            model=coordinator.device_model,
            sw_version="1.0.0",
        )
        
        _LOGGER.debug("Initialized status sensor for device %s", self.device_id)

    @property
    def native_value(self) -> str:
        """Return the status."""
        if self.coordinator.data.get("is_connected"):
            keys_found = self.coordinator.data.get("target_keys_count", 0)
            total_keys = len(DPS_KEYS_TO_LOG)
            return f"{keys_found}/{total_keys} keys"
        else:
            return "Not Connected"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        attrs = {
            "device_id": self.device_id,
            "device_name": self.coordinator.device_name,
            "device_model": self.coordinator.device_model,
            "data_source": self.coordinator.data.get("data_source", "Unknown"),
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count", 0),
            "total_dps_keys": self.coordinator.data.get("total_keys", 0),
            "target_keys_found": self.coordinator.data.get("target_keys_count", 0),
            "target_keys_list": self.coordinator.data.get("target_keys_found", []),
            "consecutive_failures": self.coordinator.data.get("consecutive_failures", 0),
            "mqtt_connected": self.coordinator.data.get("mqtt_connected", False),
            "log_directory": f"/config/{self.coordinator.log_dir.name}",
            "service_call": f"eufy_robovac_data_logger.log_dps_data",
            "service_data": {"device_id": self.device_id},
        }
        
        # Add connection status
        if self.coordinator.data.get("is_connected"):
            attrs["connection_status"] = "Connected"
        else:
            attrs["connection_status"] = "Disconnected"
        
        return attrs