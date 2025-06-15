"""Config flow for Eufy Robovac Data Logger integration."""
import asyncio
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

# CRITICAL DEBUG: Add logging immediately at module level
_LOGGER = logging.getLogger(__name__)
_LOGGER.error("🚨 DEBUG: config_flow.py module loading started")

try:
    from homeassistant import config_entries
    from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResult
    from homeassistant.exceptions import HomeAssistantError
    _LOGGER.error("✅ DEBUG: HomeAssistant config_flow imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: HomeAssistant config_flow import failed: {e}")
    raise

try:
    from .const import DOMAIN, CONF_DEBUG_MODE, CONF_INVESTIGATION_MODE
    _LOGGER.error("✅ DEBUG: const.py config_flow imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: const.py config_flow import failed: {e}")
    raise

_LOGGER.error("🎯 DEBUG: config_flow.py all imports completed successfully")

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_DEBUG_MODE, default=True): bool,
        vol.Optional(CONF_INVESTIGATION_MODE, default=False): bool,
    }
)


class EufyRobovacConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eufy Robovac Data Logger."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        _LOGGER.error("🚨 DEBUG: async_step_user called")
        
        if user_input is None:
            _LOGGER.error("🔄 DEBUG: Showing user form")
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            _LOGGER.error("🔄 DEBUG: Validating user input")
            info = await validate_input(self.hass, user_input)
            _LOGGER.error(f"✅ DEBUG: Validation successful: {info}")
        except CannotConnect:
            _LOGGER.error("❌ DEBUG: Cannot connect error")
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            _LOGGER.error("❌ DEBUG: Invalid auth error")
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.error("❌ DEBUG: Unknown error during validation")
            errors["base"] = "unknown"

        if errors:
            _LOGGER.error(f"🔄 DEBUG: Showing form with errors: {errors}")
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
            )

        _LOGGER.error("✅ DEBUG: Creating config entry")
        return self.async_create_entry(title=info["title"], data=user_input)


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""
    _LOGGER.error("🚨 DEBUG: validate_input called")
    
    try:
        username = data[CONF_USERNAME]
        password = data[CONF_PASSWORD]
        debug_mode = data.get(CONF_DEBUG_MODE, True)
        investigation_mode = data.get(CONF_INVESTIGATION_MODE, False)
        
        _LOGGER.error(f"🔄 DEBUG: Validating credentials for user: {username}")
        _LOGGER.error(f"🔧 DEBUG: Debug mode: {debug_mode}")
        _LOGGER.error(f"🔍 DEBUG: Investigation mode: {investigation_mode}")
        
        # For debug purposes, create a basic successful validation
        # In real implementation, this would test Eufy login
        
        # Simulate device discovery
        device_id = "AMP96X0E33100080"  # Your known device ID
        device_name = "Eufy RoboVac Debug"
        device_model = "T8213"
        
        _LOGGER.error(f"✅ DEBUG: Mock validation successful for device: {device_id}")
        
        # Store additional device info in the data
        data.update({
            "device_id": device_id,
            "device_name": device_name,
            "device_model": device_model,
            "openudid": f"ha_debug_{device_id}",
        })
        
        return {"title": f"{device_name} ({device_id})"}
        
    except Exception as e:
        _LOGGER.error(f"❌ DEBUG: Validation error: {e}")
        raise CannotConnect from e


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""