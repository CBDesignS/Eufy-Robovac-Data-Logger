"""Eufy Robovac Data Logger integration for Home Assistant."""
import asyncio
import logging
import voluptuous as vol
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, UPDATE_INTERVAL
from .coordinator import EufyDataLoggerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

# Service schema for logging
SERVICE_LOG_DPS_DATA_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eufy Data Logger from a config entry."""
    _LOGGER.info("Setting up Eufy Data Logger integration")
    _LOGGER.info("Device: %s", entry.data.get("device_id"))
    _LOGGER.info("Device name: %s", entry.data.get("device_name", "Unknown"))
    _LOGGER.info("Device model: %s", entry.data.get("device_model", "Unknown"))
    _LOGGER.info("Debug mode: %s", entry.data.get("debug_mode", False))
    
    coordinator = EufyDataLoggerCoordinator(
        hass=hass,
        entry=entry,
    )
    
    # Fetch initial data
    try:
        _LOGGER.info("Fetching initial data...")
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.info("Initial data fetch successful")
    except Exception as err:
        _LOGGER.error("Failed to fetch initial data: %s", err)
        return False
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Setup platforms
    _LOGGER.info("Setting up platforms...")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _register_services(hass)
    
    _LOGGER.info("Eufy Data Logger integration setup completed successfully")
    _LOGGER.info("Update interval: %d seconds", UPDATE_INTERVAL)
    return True


async def _register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    _LOGGER.info("Registering services...")
    
    async def log_dps_data_service(call: ServiceCall) -> None:
        """Handle log DPS data service call."""
        device_id = call.data["device_id"]
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("Device not found: %s", device_id)
            return
        
        try:
            result = await coordinator.log_dps_data()
            _LOGGER.info("Log service result: %s", result)
        except Exception as e:
            _LOGGER.error("Log service failed: %s", e)
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        "log_dps_data",
        log_dps_data_service,
        schema=SERVICE_LOG_DPS_DATA_SCHEMA,
    )
    
    _LOGGER.info("Services registered successfully")


def _get_coordinator_by_device_id(hass: HomeAssistant, device_id: str) -> EufyDataLoggerCoordinator:
    """Find coordinator by device ID."""
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if hasattr(coordinator, 'device_id') and coordinator.device_id == device_id:
            return coordinator
    return None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Eufy Data Logger integration")
    _LOGGER.info("Device: %s", entry.data.get("device_id"))
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        _LOGGER.info("Integration unloaded successfully")
        
        # Unregister services if this was the last device
        if not hass.data.get(DOMAIN):
            _unregister_services(hass)
    else:
        _LOGGER.error("Failed to unload integration")
    
    return unload_ok


def _unregister_services(hass: HomeAssistant) -> None:
    """Unregister services when last device is removed."""
    service_names = ["log_dps_data"]
    
    for service_name in service_names:
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)
    
    _LOGGER.info("Services unregistered")


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("Reloading Eufy Data Logger integration")
    _LOGGER.info("Device: %s", entry.data.get("device_id"))
    
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    

    _LOGGER.info("Integration reloaded successfully")

