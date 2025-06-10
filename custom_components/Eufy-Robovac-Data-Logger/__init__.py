"""Eufy Robovac Data Logger integration for Home Assistant with enhanced logging."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import EufyX10DebugCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eufy X10 Debugging from a config entry."""
    _LOGGER.info("🚀 EUFY X10 DEBUGGING INTEGRATION SETUP")
    _LOGGER.info("📱 Setting up integration for device: %s", entry.data.get("device_id"))
    _LOGGER.info("🏷️ Device name: %s", entry.data.get("device_name", "Unknown"))
    _LOGGER.info("🔧 Device model: %s", entry.data.get("device_model", "Unknown"))
    _LOGGER.info("🐛 Debug mode: %s", entry.data.get("debug_mode", False))
    
    coordinator = EufyX10DebugCoordinator(
        hass=hass,
        entry=entry,
    )
    
    # Fetch initial data
    try:
        _LOGGER.info("🔄 Fetching initial data...")
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.info("✅ Initial data fetch successful")
    except Exception as err:
        _LOGGER.error("❌ Failed to fetch initial data: %s", err)
        return False
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Setup platforms
    _LOGGER.info("🏭 Setting up platforms...")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("✅ Eufy X10 Debugging integration setup completed successfully")
    _LOGGER.info("📊 Update interval: %d seconds", UPDATE_INTERVAL)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("🛑 EUFY X10 DEBUGGING INTEGRATION UNLOAD")
    _LOGGER.info("📱 Unloading integration for device: %s", entry.data.get("device_id"))
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        _LOGGER.info("✅ Integration unloaded successfully")
    else:
        _LOGGER.error("❌ Failed to unload integration")
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("🔄 EUFY X10 DEBUGGING INTEGRATION RELOAD")
    _LOGGER.info("📱 Reloading integration for device: %s", entry.data.get("device_id"))
    
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    
    _LOGGER.info("✅ Integration reloaded successfully")
