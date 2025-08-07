"""Config flow for Eufy Robovac Data Logger integration."""
import logging
import voluptuous as vol
import uuid

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_DEBUG_MODE

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_DEBUG_MODE, default=False): bool,
    }
)


class EufyDataLoggerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eufy Data Logger."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return EufyDataLoggerOptionsFlow(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self.discovered_devices = []
        self.user_input = {}
        self.openudid = None

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step - login and discover devices."""
        errors = {}

        if user_input is not None:
            # Basic validation
            if not user_input.get(CONF_USERNAME):
                errors["base"] = "invalid_username"
            elif not user_input.get(CONF_PASSWORD):
                errors["base"] = "invalid_password"
            else:
                # Try to login and discover devices
                try:
                    _LOGGER.info("Starting login and device discovery")
                    
                    # Create login instance with generated UDID
                    self.openudid = f"ha_debug_{str(uuid.uuid4())[:8]}"
                    
                    # Import with correct case sensitivity
                    from .controllers.Login import EufyLogin
                    
                    eufy_login = EufyLogin(
                        username=user_input[CONF_USERNAME],
                        password=user_input[CONF_PASSWORD],
                        openudid=self.openudid
                    )
                    
                    # Initialize and get devices
                    devices = await eufy_login.init()
                    
                    if not devices:
                        _LOGGER.error("No devices found for account")
                        errors["base"] = "no_devices_found"
                    elif len(devices) == 1:
                        # Single device found - auto-configure
                        device = devices[0]
                        device_id = device['deviceId']
                        device_name = device.get('deviceName', 'Unknown Device')
                        
                        _LOGGER.info("Single device found: %s (%s)", device_name, device_id)
                        
                        # Check if already configured
                        await self.async_set_unique_id(device_id)
                        self._abort_if_unique_id_configured()
                        
                        # Create entry with discovered device
                        entry_data = {
                            CONF_USERNAME: user_input[CONF_USERNAME],
                            CONF_PASSWORD: user_input[CONF_PASSWORD],
                            "device_id": device_id,
                            "device_name": device_name,
                            "device_model": device.get('deviceModel', 'T8213'),
                            "openudid": self.openudid,
                            CONF_DEBUG_MODE: user_input.get(CONF_DEBUG_MODE, False),
                        }
                        
                        _LOGGER.info("Creating config entry for: %s", device_name)
                        
                        return self.async_create_entry(
                            title=f"Eufy Data Logger - {device_name}",
                            data=entry_data,
                        )
                    else:
                        # Multiple devices found - let user choose
                        _LOGGER.info("Multiple devices found (%d), showing selection", len(devices))
                        self.discovered_devices = devices
                        self.user_input = user_input
                        return await self.async_step_device_selection()
                        
                except Exception as e:
                    _LOGGER.error("Login or device discovery failed: %s", e)
                    if "invalid username or password" in str(e).lower():
                        errors["base"] = "invalid_credentials"
                    elif "no response" in str(e).lower():
                        errors["base"] = "cannot_connect"
                    else:
                        errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_device_selection(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle device selection when multiple devices found."""
        if user_input is not None:
            selected_device_id = user_input["device"]
            
            # Find the selected device
            selected_device = next(
                (d for d in self.discovered_devices if d['deviceId'] == selected_device_id),
                None
            )
            
            if selected_device:
                device_id = selected_device['deviceId']
                device_name = selected_device.get('deviceName', 'Unknown Device')
                
                _LOGGER.info("User selected device: %s (%s)", device_name, device_id)
                
                # Check if already configured
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                
                # Create entry with selected device
                entry_data = {
                    CONF_USERNAME: self.user_input[CONF_USERNAME],
                    CONF_PASSWORD: self.user_input[CONF_PASSWORD],
                    "device_id": device_id,
                    "device_name": device_name,
                    "device_model": selected_device.get('deviceModel', 'T8213'),
                    "openudid": self.openudid,
                    CONF_DEBUG_MODE: self.user_input.get(CONF_DEBUG_MODE, False),
                }
                
                _LOGGER.info("Creating config entry for selected device: %s", device_name)
                
                return self.async_create_entry(
                    title=f"Eufy Data Logger - {device_name}",
                    data=entry_data,
                )
        
        # Create device selection schema
        device_options = {
            device['deviceId']: f"{device.get('deviceName', 'Unknown')} ({device['deviceId']})"
            for device in self.discovered_devices
        }
        
        device_selection_schema = vol.Schema({
            vol.Required("device"): vol.In(device_options)
        })
        
        _LOGGER.debug("Showing device selection with %d options", len(device_options))
        
        return self.async_show_form(
            step_id="device_selection",
            data_schema=device_selection_schema,
        )

    async def async_step_import(self, import_config: dict) -> FlowResult:
        """Import a config entry from configuration.yaml."""
        _LOGGER.info("Importing config from configuration.yaml")
        return await self.async_step_user(import_config)


class EufyDataLoggerOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Eufy Data Logger."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            _LOGGER.info("Saving options: debug_mode=%s", user_input.get(CONF_DEBUG_MODE))
            return self.async_create_entry(title="", data=user_input)

        current_debug_mode = self.config_entry.options.get(
            CONF_DEBUG_MODE, 
            self.config_entry.data.get(CONF_DEBUG_MODE, False)
        )
        
        _LOGGER.debug("Showing options form, current debug_mode=%s", current_debug_mode)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEBUG_MODE,
                        default=current_debug_mode,
                    ): bool,
                }
            ),
        )