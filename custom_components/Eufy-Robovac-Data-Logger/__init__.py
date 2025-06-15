"""Eufy Robovac Data Logger integration for Home Assistant with Investigation Mode Services."""
import asyncio
import logging
import voluptuous as vol
from datetime import timedelta

# CRITICAL DEBUG: Add logging immediately at module level
_LOGGER = logging.getLogger(__name__)
_LOGGER.error("🚨 DEBUG: __init__.py module loading started")

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.const import Platform
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
    from homeassistant.helpers import config_validation as cv
    _LOGGER.error("✅ DEBUG: HomeAssistant imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: HomeAssistant import failed: {e}")
    raise

try:
    from .const import DOMAIN, UPDATE_INTERVAL
    _LOGGER.error(f"✅ DEBUG: const.py imports successful - DOMAIN: {DOMAIN}")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: const.py import failed: {e}")
    raise

try:
    from .coordinator import EufyX10DebugCoordinator
    _LOGGER.error("✅ DEBUG: coordinator.py import successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: coordinator.py import failed: {e}")
    raise

_LOGGER.error("🎯 DEBUG: All imports completed successfully")

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
    _LOGGER.error("🚨 DEBUG: async_setup_entry called!")
    _LOGGER.error("🚀 EUFY X10 DEBUGGING INTEGRATION SETUP")
    _LOGGER.error("📱 Setting up integration for device: %s", entry.data.get("device_id"))
    _LOGGER.error("🏷️ Device name: %s", entry.data.get("device_name", "Unknown"))
    _LOGGER.error("🔧 Device model: %s", entry.data.get("device_model", "Unknown"))
    _LOGGER.error("🐛 Debug mode: %s", entry.data.get("debug_mode", False))
    _LOGGER.error("🔍 Investigation mode: %s", entry.data.get("investigation_mode", False))
    
    try:
        _LOGGER.error("🔄 Creating coordinator...")
        coordinator = EufyX10DebugCoordinator(
            hass=hass,
            entry=entry,
        )
        _LOGGER.error("✅ Coordinator created successfully")
    except Exception as e:
        _LOGGER.error("❌ Failed to create coordinator: %s", e)
        return False
    
    # Fetch initial data
    try:
        _LOGGER.error("🔄 Fetching initial data...")
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.error("✅ Initial data fetch successful")
    except Exception as err:
        _LOGGER.error("❌ Failed to fetch initial data: %s", err)
        return False
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Setup platforms
    _LOGGER.error("🏭 Setting up platforms...")
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.error("✅ Platforms setup successful")
    except Exception as e:
        _LOGGER.error("❌ Failed to setup platforms: %s", e)
        return False
    
    # Register services
    try:
        _LOGGER.error("🛠️ Registering services...")
        await _register_services(hass)
        _LOGGER.error("✅ Services registered successfully")
    except Exception as e:
        _LOGGER.error("❌ Failed to register services: %s", e)
        return False
    
    _LOGGER.error("✅ Eufy X10 Debugging integration setup completed successfully")
    _LOGGER.error("📊 Update interval: %d seconds", UPDATE_INTERVAL)
    _LOGGER.error("🛠️ Services registered for investigation mode and debugging")
    return True


async def _register_services(hass: HomeAssistant) -> None:
    """Register all integration services."""
    _LOGGER.error("🛠️ Registering Investigation Mode services...")
    
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
            _LOGGER.error("🎯 Baseline capture result: %s", result)
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
            _LOGGER.error("🎯 Post-cleaning capture result: %s", result)
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
            result = await coordinator.generate_investigation_summary()
            _LOGGER.error("📊 Summary generation result: %s", result)
        except Exception as e:
            _LOGGER.error("❌ Summary generation failed: %s", e)
    
    async def force_update_service(call: ServiceCall) -> None:
        """Handle force update service call."""
        device_id = call.data["device_id"]
        phase = call.data.get("phase", "monitoring")
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        try:
            await coordinator.async_request_refresh()
            _LOGGER.error("🔄 Force update completed for device: %s (phase: %s)", device_id, phase)
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
            await coordinator.accessory_manager.reload_config()
            _LOGGER.error("🔄 Accessory config reloaded for device: %s", device_id)
        except Exception as e:
            _LOGGER.error("❌ Config reload failed: %s", e)
    
    async def update_accessory_service(call: ServiceCall) -> None:
        """Handle update accessory service call."""
        device_id = call.data["device_id"]
        accessory_id = call.data["accessory_id"]
        life_percentage = call.data["life_percentage"]
        notes = call.data.get("notes", "")
        
        coordinator = _get_coordinator_by_device_id(hass, device_id)
        
        if not coordinator:
            _LOGGER.error("❌ Device not found: %s", device_id)
            return
        
        try:
            result = await coordinator.accessory_manager.update_accessory_status(
                accessory_id, life_percentage, notes
            )
            _LOGGER.error("🔧 Accessory update result: %s", result)
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
        
        if not coordinator.debug_logger:
            _LOGGER.error("❌ Debug logger not available for device: %s", device_id)
            return
        
        try:
            result = await coordinator.debug_logger.analyze_key(key, analysis_type)
            _LOGGER.error("🔍 Debug key analysis result: %s", result)
        except Exception as e:
            _LOGGER.error("❌ Debug key analysis failed: %s", e)
    
    # Register all services
    services = [
        ("capture_investigation_baseline", capture_baseline_service, SERVICE_CAPTURE_BASELINE_SCHEMA),
        ("capture_investigation_post_cleaning", capture_post_cleaning_service, SERVICE_CAPTURE_POST_CLEANING_SCHEMA),
        ("generate_investigation_summary", generate_summary_service, SERVICE_GENERATE_SUMMARY_SCHEMA),
        ("force_update", force_update_service, SERVICE_FORCE_UPDATE_SCHEMA),
        ("reload_accessory_config", reload_config_service, SERVICE_RELOAD_CONFIG_SCHEMA),
        ("update_accessory_status", update_accessory_service, SERVICE_UPDATE_ACCESSORY_SCHEMA),
        ("debug_key_analysis", debug_key_service, SERVICE_DEBUG_KEY_SCHEMA),
    ]
    
    for service_name, service_handler, schema in services:
        hass.services.async_register(
            DOMAIN,
            service_name,
            service_handler,
            schema=schema,
        )
        _LOGGER.error(f"✅ Service registered: {service_name}")


def _get_coordinator_by_device_id(hass: HomeAssistant, device_id: str) -> Optional[EufyX10DebugCoordinator]:
    """Get coordinator by device ID."""
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if hasattr(coordinator, 'device_id') and coordinator.device_id == device_id:
            return coordinator
    return None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.error("🔄 Unloading Eufy X10 Debugging integration...")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.error("✅ Integration unloaded successfully")
    
    return unload_ok