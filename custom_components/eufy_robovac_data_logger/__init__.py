"""Eufy Robovac Data Logger integration for Home Assistant."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

# IMPORTS AT THE TOP LIKE EUFY-CLEAN DOES
from .EufyClean import EufyClean
from .constants.devices import EUFY_CLEAN_DEVICES

DOMAIN = "eufy_robovac_data_logger"
DEVICES = "devices"
VACS = "vacs"

PLATFORMS = [Platform.VACUUM, Platform.SENSOR, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)

# Service schema
SERVICE_LOG_DPS_DATA = "log_dps_data"
SERVICE_LOG_DPS_DATA_SCHEMA = vol.Schema({
    vol.Required("device_id"): cv.string,
})


async def async_setup(hass: HomeAssistant, _) -> bool:
    """Set up the Eufy Data Logger component."""
    hass.data.setdefault(DOMAIN, {VACS: {}, DEVICES: {}})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Eufy Data Logger from a config entry - EXACTLY like eufy-clean."""
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    # Get credentials - EXACTLY like eufy-clean
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    
    _LOGGER.info("Initializing Eufy Data Logger for user: %s", username)
    
    # Init EufyClean - EXACTLY like eufy-clean
    eufy_clean = EufyClean(username, password)
    await eufy_clean.init()
    
    # Load devices - EXACTLY like eufy-clean
    devices = await eufy_clean.get_devices()
    _LOGGER.info("Found %d devices", len(devices) if devices else 0)
    
    for vacuum in devices:
        device_id = vacuum.get('deviceId')
        if not device_id:
            _LOGGER.warning("Device without ID found, skipping")
            continue
            
        _LOGGER.info("Initializing device: %s", device_id)
        
        # Get device model for logging
        device_model = vacuum.get('deviceModel', 'Unknown')
        device_name = EUFY_CLEAN_DEVICES.get(device_model, device_model)
        _LOGGER.info("Device %s is model %s (%s)", device_id, device_model, device_name)
        
        # Init and connect device - EXACTLY like eufy-clean
        device = await eufy_clean.init_device(device_id)
        await device.connect()
        
        _LOGGER.info("Adding %s", device.device_id)
        hass.data[DOMAIN][DEVICES][device.device_id] = device
    
    # Setup platforms - EXACTLY like eufy-clean
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register our logging service
    await _register_services(hass)
    
    _LOGGER.info("Eufy Data Logger setup complete")
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle config entry updates."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Eufy Data Logger")
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Disconnect devices
        for device_id, device in hass.data[DOMAIN][DEVICES].items():
            _LOGGER.info("Disconnecting device %s", device_id)
            try:
                if hasattr(device, 'mqttClient') and device.mqttClient:
                    device.mqttClient.disconnect()
                    device.mqttClient.loop_stop()
            except Exception as e:
                _LOGGER.error("Error disconnecting %s: %s", device_id, e)
        
        # Clear data
        hass.data[DOMAIN][DEVICES].clear()
        hass.data[DOMAIN][VACS].clear()
    
    return unload_ok


async def _register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    
    async def log_dps_data_service(call: ServiceCall) -> None:
        """Handle log DPS data service call."""
        device_id = call.data["device_id"]
        _LOGGER.info("Log DPS data service called for device: %s", device_id)
        
        # Get the device
        device = hass.data[DOMAIN][DEVICES].get(device_id)
        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return
        
        # Get DPS data from robovac_data
        if hasattr(device, 'robovac_data'):
            # Extract DPS keys 150-180
            dps_data = {}
            for key in range(150, 181):
                str_key = str(key)
                if str_key in device.robovac_data:
                    dps_data[str_key] = device.robovac_data[str_key]
            
            if dps_data:
                # Log to file
                import json
                from datetime import datetime
                from pathlib import Path
                
                log_dir = Path(hass.config.config_dir) / "eufy_dps_logs" / device_id
                log_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"dps_log_{timestamp}.json"
                filepath = log_dir / filename
                
                log_data = {
                    "timestamp": datetime.now().isoformat(),
                    "device_id": device_id,
                    "device_model": device.device_model if hasattr(device, 'device_model') else "Unknown",
                    "keys": dps_data
                }
                
                with open(filepath, 'w') as f:
                    json.dump(log_data, f, indent=2)
                
                _LOGGER.info("Logged %d DPS keys to %s", len(dps_data), filename)
                hass.bus.async_fire(
                    f"{DOMAIN}_dps_logged",
                    {"device_id": device_id, "keys_count": len(dps_data), "file": str(filepath)}
                )
            else:
                _LOGGER.warning("No DPS keys 150-180 found for device %s", device_id)
        else:
            _LOGGER.error("Device %s has no robovac_data", device_id)
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_DPS_DATA,
        log_dps_data_service,
        schema=SERVICE_LOG_DPS_DATA_SCHEMA,
    )
    _LOGGER.info("Registered service: %s.%s", DOMAIN, SERVICE_LOG_DPS_DATA)