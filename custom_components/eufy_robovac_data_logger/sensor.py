"""Sensor platform for Eufy Robovac Data Logger integration."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .constants.hass import DOMAIN, DEVICES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Robovac battery sensors."""
    
    sensors = []
    
    for device_id, device in hass.data[DOMAIN][DEVICES].items():
        _LOGGER.info("Adding battery sensor for device %s", device_id)
        battery_sensor = RobovacBatterySensor(device)
        sensors.append(battery_sensor)
    
    if sensors:
        async_add_entities(sensors, True)

class RobovacBatterySensor(SensorEntity):
    """Battery sensor for Eufy Robovac."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_suggested_display_precision = 0
    _attr_entity_category = None  # None makes it available for automations

    def __init__(self, robovac):
        super().__init__()
        self.robovac = robovac
        self._attr_unique_id = f"{robovac.device_id}_battery"
        self._attr_name = f"{robovac.device_model_desc} Battery"
        self._attr_native_value = None
        self._attr_available = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, robovac.device_id)},
            name=robovac.device_model_desc,
            manufacturer="Eufy",
            model=robovac.device_model,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if hasattr(self.robovac, 'add_listener'):
            def _threadsafe_update():
                if self.hass:
                    self.hass.create_task(self.async_update_ha_state(force_refresh=True))
            self.robovac.add_listener(_threadsafe_update)

    @property
    def native_value(self):
        return self._attr_native_value

    @property
    def available(self) -> bool:
        """Ensure the sensor is available for automations."""
        return self._attr_available and self.robovac is not None

    @property
    def extra_state_attributes(self) -> dict:
        """Add useful attributes for automations."""
        return {
            "battery_level": self._attr_native_value,
            "device_id": self.robovac.device_id if self.robovac else None,
            "device_model": self.robovac.device_model if hasattr(self.robovac, 'device_model') else None
        }

    async def async_update(self) -> None:
        """Update the battery level."""
        if self.robovac:
            try:
                battery_level = await self.robovac.get_battery_level()
                self._attr_native_value = battery_level
                self._attr_available = True
            except Exception as e:
                _LOGGER.error("Failed to update battery level: %s", e)
                self._attr_available = False