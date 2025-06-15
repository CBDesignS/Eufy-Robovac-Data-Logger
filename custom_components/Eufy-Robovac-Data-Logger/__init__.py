"""Eufy Robovac Data Logger integration for Home Assistant with Investigation Mode Services."""
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
from .coordinator import EufyX10DebugCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Service schemas for Investigation Mode
SERVICE_CAPTURE_BASELINE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

SERVICE_CAPTURE_POST_CLEANING_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

SERVICE_GENERATE_SUMMARY_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

SERVICE_FORCE_UPDATE_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Optional("phase", default="monitoring"): vol.In(["baseline", "post_cleaning", "monitoring", "manual_test"]),
})

SERVICE_RELOAD_CONFIG_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})

SERVICE_UPDATE_ACCESSORY_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("accessory_id"): cv.string,
    vol.Required("life_percentage"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    vol.Optional("notes", default=""): cv.string,
})

SERVICE_DEBUG_KEY_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
    vol.Required("key"): cv.string,
    vol.Optional("analysis_type", default="complete"): vol.In([
        "complete", "byte_dump", "percentage_scan", "change_detection", "accessory_hunt"
    ]),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eufy X10 Debugging from a config entry with services."""
    _LOGGER.info("🚀 EUFY X10 DEBUGGING INTEGRATION SETUP")
    _LOGGER.info("📱 Setting up integration for device: %s", entry.data.get("device_id"))
    _LOGGER.info("🏷️ Device name: %s", entry.data.get("device_name", "Unknown"))
    _LOGGER.info("🔧 Device model: %s", entry.data.get("device_model", "Unknown"))
    _LOGGER.info("🐛 Debug mode: %s", entry.data.get("debug_mode", False))
    _LOGGER.info("🔍 Investigation mode: %s", entry.data.get("investigation_mode", False))
    
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
    
    # Register services
    await _register_services(hass)
    
    _LOGGER.info("✅ Eufy X10 Debugging integration setup completed successfully")
    _LOGGER.info("📊 Update interval: %d seconds", UPDATE_INTERVAL)
    _LOGGER.info("🛠️ Services registered for investigation mode and debugging")
    return True


async def _register_services(hass: HomeAssistant) -> None:
    """Register all integration services."""
    _LOGGER.info("🛠️ Registering Investigation Mode services...")
    
    async def capture_baseline_service(call: ServiceCall) -> None:
        """Handle capture baseline service call."""
        device_id = call.data["device_id"]
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        if not coordinator.investigation_mode:
            _LOGGER.error("❌ Investigation mode not enabled for device: %s", device_id)
            return
        
        try:
            result = await coordinator.capture_investigation_baseline()
            _LOGGER.info("🎯 Baseline capture result: %s", result)
        except Exception as e:
            _LOGGER.error("❌ Baseline capture failed: %s", e)
    
    async def capture_post_cleaning_service(call: ServiceCall) -> None:
        """Handle capture post-cleaning service call."""
        device_id = call.data["device_id"]
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        if not coordinator.investigation_mode:
            _LOGGER.error("❌ Investigation mode not enabled for device: %s", device_id)
            return
        
        try:
            result = await coordinator.capture_investigation_post_cleaning()
            _LOGGER.info("📊 Post-cleaning capture result: %s", result)
        except Exception as e:
            _LOGGER.error("❌ Post-cleaning capture failed: %s", e)
    
    async def generate_summary_service(call: ServiceCall) -> None:
        """Handle generate summary service call."""
        device_id = call.data["device_id"]
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        if not coordinator.investigation_mode:
            _LOGGER.error("❌ Investigation mode not enabled for device: %s", device_id)
            return
        
        try:
            result = await coordinator.get_investigation_summary()
            _LOGGER.info("📋 Summary generation result: %s", result)
        except Exception as e:
            _LOGGER.error("❌ Summary generation failed: %s", e)
    
    async def force_update_service(call: ServiceCall) -> None:
        """Handle force investigation update service call."""
        device_id = call.data["device_id"]
        phase = call.data.get("phase", "monitoring")
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        try:
            # Force an immediate coordinator update
            await coordinator.async_request_refresh()
            _LOGGER.info("🔄 Force update completed for device: %s (phase: %s)", device_id, phase)
        except Exception as e:
            _LOGGER.error("❌ Force update failed: %s", e)
    
    async def reload_config_service(call: ServiceCall) -> None:
        """Handle reload accessory config service call."""
        device_id = call.data["device_id"]
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        try:
            # Reload accessory configuration
            await coordinator.accessory_manager.load_config(force_reload=True)
            coordinator.accessory_sensors = await coordinator.accessory_manager.get_enabled_sensors()
            
            # Trigger a coordinator update to apply new config
            await coordinator.async_request_refresh()
            _LOGGER.info("🔄 Accessory config reloaded for device: %s", device_id)
        except Exception as e:
            _LOGGER.error("❌ Config reload failed: %s", e)
    
    async def update_accessory_service(call: ServiceCall) -> None:
        """Handle update accessory life service call."""
        device_id = call.data["device_id"]
        accessory_id = call.data["accessory_id"]
        life_percentage = call.data["life_percentage"]
        notes = call.data.get("notes", "")
        
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        try:
            # Update the accessory life in configuration
            success = await coordinator.accessory_manager.update_accessory_life(
                accessory_id, life_percentage, notes
            )
            
            if success:
                # Reload the updated config
                coordinator.accessory_sensors = await coordinator.accessory_manager.get_enabled_sensors()
                await coordinator.async_request_refresh()
                _LOGGER.info("🔧 Updated %s life to %d%% for device: %s", accessory_id, life_percentage, device_id)
            else:
                _LOGGER.error("❌ Failed to update accessory life")
        except Exception as e:
            _LOGGER.error("❌ Accessory update failed: %s", e)
    
    async def debug_key_service(call: ServiceCall) -> None:
        """Handle debug key analysis service call."""
        device_id = call.data["device_id"]
        key = call.data["key"]
        analysis_type = call.data.get("analysis_type", "complete")
        
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        try:
            # Perform key analysis
            if key in coordinator.raw_data:
                value = coordinator.raw_data[key]
                _LOGGER.info("🔍 Debug analysis for Key %s (%s): %s", key, analysis_type, value)
                
                # Log to debug logger if available
                if coordinator.debug_logger:
                    coordinator.debug_logger.log_key_analysis(key, value, {
                        "analysis_type": analysis_type,
                        "requested_by": "service_call",
                        "device_id": device_id
                    })
                    
                    if analysis_type == "byte_dump" and isinstance(value, str):
                        coordinator.debug_logger.log_byte_analysis(key, value)
            else:
                _LOGGER.warning("⚠️ Key %s not found in current data for device: %s", key, device_id)
        except Exception as e:
            _LOGGER.error("❌ Debug key analysis failed: %s", e)
    
    # Register all services
    hass.services.async_register(
        DOMAIN,
        "capture_investigation_baseline",
        capture_baseline_service,
        schema=SERVICE_CAPTURE_BASELINE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "capture_investigation_post_cleaning",
        capture_post_cleaning_service,
        schema=SERVICE_CAPTURE_POST_CLEANING_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "generate_investigation_summary",
        generate_summary_service,
        schema=SERVICE_GENERATE_SUMMARY_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "force_investigation_update",
        force_update_service,
        schema=SERVICE_FORCE_UPDATE_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "reload_accessory_config",
        reload_config_service,
        schema=SERVICE_RELOAD_CONFIG_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "update_accessory_life",
        update_accessory_service,
        schema=SERVICE_UPDATE_ACCESSORY_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "debug_key_analysis",
        debug_key_service,
        schema=SERVICE_DEBUG_KEY_SCHEMA,
    )
    
    _LOGGER.info("✅ All services registered successfully")


def _get_coordinator_by_device_id(hass: HomeAssistant, device_id: str) -> EufyX10DebugCoordinator:
    """Find coordinator by device ID."""
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if hasattr(coordinator, 'device_id') and coordinator.device_id == device_id:
            return coordinator
    return None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("🛑 EUFY X10 DEBUGGING INTEGRATION UNLOAD")
    _LOGGER.info("📱 Unloading integration for device: %s", entry.data.get("device_id"))
    
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        _LOGGER.info("✅ Integration unloaded successfully")
        
        # Unregister services if this was the last device
        if not hass.data.get(DOMAIN):
            _unregister_services(hass)
    else:
        _LOGGER.error("❌ Failed to unload integration")
    
    return unload_ok


def _unregister_services(hass: HomeAssistant) -> None:
    """Unregister services when last device is removed."""
    service_names = [
        "capture_investigation_baseline",
        "capture_investigation_post_cleaning", 
        "generate_investigation_summary",
        "force_investigation_update",
        "reload_accessory_config",
        "update_accessory_life",
        "debug_key_analysis",
    ]
    
    for service_name in service_names:
        if hass.services.has_service(DOMAIN, service_name):
            hass.services.async_remove(DOMAIN, service_name)
    
    _LOGGER.info("🛠️ All services unregistered")


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.info("🔄 EUFY X10 DEBUGGING INTEGRATION RELOAD")
    _LOGGER.info("📱 Reloading integration for device: %s", entry.data.get("device_id"))
    
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    
    _LOGGER.info("✅ Integration reloaded successfully")