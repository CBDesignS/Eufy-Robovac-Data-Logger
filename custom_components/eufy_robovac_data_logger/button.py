"""Button platform for Eufy Robovac Data Logger integration."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import EufyDataLoggerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eufy Data Logger button."""
    coordinator: EufyDataLoggerCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        EufyDataLoggerButton(coordinator),
    ])


class EufyDataLoggerButton(ButtonEntity):
    """Button to trigger DPS data logging."""

    def __init__(self, coordinator: EufyDataLoggerCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self.device_id = coordinator.device_id
        
        self._attr_unique_id = f"{self.device_id}_log_dps_data"
        self._attr_name = "Log DPS Data"
        self._attr_icon = "mdi:file-export"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=f"Eufy Data Logger {coordinator.device_name}",
            manufacturer="Eufy",
            model=coordinator.device_model,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        result = await self.coordinator.log_dps_data()
        _LOGGER.info("DPS data logged: %s", result)
