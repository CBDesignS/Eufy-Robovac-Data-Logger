"""Data update coordinator for Eufy Robovac Data Logger integration with Enhanced Smart Investigation Mode v4.0."""
import asyncio
import logging
import time
import base64
from datetime import timedelta
from typing import Any, Dict, Optional, List
from pathlib import Path

# CRITICAL DEBUG: Add logging immediately at module level
_LOGGER = logging.getLogger(__name__)
_LOGGER.error("🚨 DEBUG: coordinator.py module loading started")

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
    _LOGGER.error("✅ DEBUG: HomeAssistant coordinator imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: HomeAssistant coordinator import failed: {e}")
    raise

try:
    from .const import DOMAIN, UPDATE_INTERVAL, MONITORED_KEYS, ALL_MONITORED_KEYS, CONF_DEBUG_MODE, CONF_INVESTIGATION_MODE, CLEAN_SPEED_NAMES, WORK_STATUS_MAP
    _LOGGER.error("✅ DEBUG: const.py imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: const.py import failed: {e}")
    raise

try:
    from .accessory_config_manager import AccessoryConfigManager
    _LOGGER.error("✅ DEBUG: AccessoryConfigManager import successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: AccessoryConfigManager import failed: {e}")
    raise

_LOGGER.error("🎯 DEBUG: coordinator.py all imports completed successfully")


class EufyX10DebugCoordinator(DataUpdateCoordinator):
    """Eufy Robovac Debugging data coordinator with RestConnect and Enhanced Smart Investigation Mode v4.0."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        _LOGGER.error("🚨 DEBUG: EufyX10DebugCoordinator.__init__ called")
        
        try:
            self.entry = entry
            self.device_id = entry.data["device_id"]
            self.device_name = entry.data.get("device_name", "Unknown Device")
            self.device_model = entry.data.get("device_model", "T8213")
            self.username = entry.data["username"]
            self.password = entry.data["password"]
            self.openudid = entry.data.get("openudid", f"ha_debug_{self.device_id}")
            self.debug_mode = entry.data.get("debug_mode", True)
            _LOGGER.error("✅ DEBUG: Basic attributes set successfully")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to set basic attributes: {e}")
            raise
        
        try:
            # UPDATED: Enhanced Smart Investigation Mode v4.0 - Multi-Key Support
            self.investigation_mode = entry.options.get(
                CONF_INVESTIGATION_MODE,
                entry.data.get(CONF_INVESTIGATION_MODE, False)
            )
            _LOGGER.error(f"✅ DEBUG: Investigation mode set: {self.investigation_mode}")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to set investigation mode: {e}")
            raise
        
        try:
            # Store raw data for debugging
            self.raw_data: Dict[str, Any] = {}
            self.parsed_data: Dict[str, Any] = {}
            self.last_update: Optional[float] = None
            self.update_count = 0
            _LOGGER.error("✅ DEBUG: Data storage attributes initialized")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to initialize data storage: {e}")
            raise
        
        try:
            # SMART LOGGING - Reduced frequency with intelligence
            self.detailed_log_interval = 600 if not self.investigation_mode else 300  # Less frequent, smarter
            self.last_detailed_log = 0
            self.first_few_updates = 1  # Only log first update in detail
            
            # CHANGE DETECTION - only log when something changes
            self._logged_status = None
            self._quiet_updates_count = 0
            self._quiet_log_interval = 120  # Brief status every 2 minutes
            _LOGGER.error("✅ DEBUG: Logging configuration set")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to set logging configuration: {e}")
            raise
        
        try:
            # Connection tracking
            self._eufy_login = None
            self._rest_client = None
            self._last_successful_update = None
            self._consecutive_failures = 0
            _LOGGER.error("✅ DEBUG: Connection tracking initialized")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to initialize connection tracking: {e}")
            raise
        
        try:
            # Initialize AccessoryConfigManager
            integration_dir = Path(__file__).parent
            self.accessory_manager = AccessoryConfigManager(
                device_id=self.device_id,
                integration_dir=str(integration_dir)
            )
            self.accessory_sensors = {}
            self.previous_accessory_data = {}
            _LOGGER.error("✅ DEBUG: AccessoryConfigManager initialized successfully")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to initialize AccessoryConfigManager: {e}")
            raise
        
        try:
            # UPDATED: Enhanced Smart Investigation Logger v4.0 - Multi-Key Support
            self.smart_investigation_logger = None
            if self.investigation_mode:
                try:
                    # Import updated multi-key investigation logger
                    from .enhanced_smart_investigation_logger import EnhancedSmartMultiKeyInvestigationLogger
                    
                    self.smart_investigation_logger = EnhancedSmartMultiKeyInvestigationLogger(
                        device_id=self.device_id,
                        hass_config_dir=hass.config.config_dir,
                        integration_dir=str(integration_dir),
                        monitored_keys=MONITORED_KEYS  # Pass the monitored keys list
                    )
                    _LOGGER.error("🔍 Enhanced Smart Multi-Key Investigation Logger v4.0 initialized")
                    _LOGGER.error("🗂️ Monitoring %d keys for comprehensive analysis", len(MONITORED_KEYS))
                    
                except Exception as e:
                    _LOGGER.error("❌ Failed to initialize multi-key investigation logger v4.0: %s", e)
                    self.smart_investigation_logger = None
            _LOGGER.error("✅ DEBUG: Investigation logger initialization completed")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to initialize investigation logger: {e}")
            raise
        
        try:
            # Debug logger for detailed debugging when needed
            self.debug_logger = None
            if self.debug_mode:
                try:
                    from .async_debug_logger import AsyncEufyDebugLogger
                    self.debug_logger = AsyncEufyDebugLogger(
                        device_id=self.device_id,
                        hass_config_dir=hass.config.config_dir
                    )
                    _LOGGER.error("✅ DEBUG: AsyncEufyDebugLogger initialized successfully")
                except Exception as e:
                    _LOGGER.error("⚠️ Failed to initialize debug logger: %s", e)
            _LOGGER.error("✅ DEBUG: Debug logger initialization completed")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to initialize debug logger: {e}")
            raise

        try:
            super().__init__(
                hass,
                _LOGGER,
                name=DOMAIN,
                update_interval=timedelta(seconds=UPDATE_INTERVAL),
            )
            _LOGGER.error("✅ DEBUG: DataUpdateCoordinator superclass initialized successfully")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: Failed to initialize DataUpdateCoordinator superclass: {e}")
            raise
        
        _LOGGER.error("🎯 DEBUG: EufyX10DebugCoordinator.__init__ completed successfully")

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        _LOGGER.error("🚨 DEBUG: _async_setup called")
        try:
            await self._initialize_clients()
            _LOGGER.error("✅ DEBUG: _initialize_clients completed")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: _initialize_clients failed: {e}")
            raise
        
        try:
            await self._initialize_accessory_config()
            _LOGGER.error("✅ DEBUG: _initialize_accessory_config completed")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: _initialize_accessory_config failed: {e}")
            raise
        
        try:
            await self._initialize_multi_key_investigation_mode()
            _LOGGER.error("✅ DEBUG: _initialize_multi_key_investigation_mode completed")
        except Exception as e:
            _LOGGER.error(f"❌ DEBUG: _initialize_multi_key_investigation_mode failed: {e}")
            raise
        
        _LOGGER.error("🎯 DEBUG: _async_setup completed successfully")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy device with RestConnect and Enhanced Smart Investigation Mode v4.0."""
        _LOGGER.error("🚨 DEBUG: _async_update_data called")
        
        try:
            self.update_count += 1
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                mode_indicators = []
                if self.investigation_mode:
                    mode_indicators.append("🔍 ENHANCED SMART INVESTIGATION v4.0 MULTI-KEY")
                if self.debug_mode:
                    mode_indicators.append("🐛 DEBUG")
                
                mode_str = " + ".join(mode_indicators) if mode_indicators else "STANDARD"
                
                self._debug_log("=" * 60, "info")
                self._debug_log(f"=== EUFY ROBOVAC UPDATE #{self.update_count} ({mode_str}) ===", "info")
                if self.investigation_mode:
                    self._debug_log("=== ✨ Enhanced Smart Multi-Key Investigation v4.0 Active ===", "info")
                    self._debug_log(f"=== 🗂️ Monitoring {len(MONITORED_KEYS)} keys for comprehensive analysis ===", "info")
                self._debug_log("=" * 60, "info")
            
            # Fetch data using RestConnect (preferred) or fallback to basic login
            await self._fetch_eufy_data_with_rest()
            
            # UPDATED: ENHANCED SMART INVESTIGATION MODE v4.0: Process MULTI-KEY data
            if self.investigation_mode:
                await self._process_enhanced_smart_multi_key_investigation_data()
            
            # Process the sensor data
            await self._process_sensor_data()
            
            # Process accessory data and check for changes
            await self._process_accessory_data()
            
            # Reset consecutive failures on success
            self._consecutive_failures = 0
            self._last_successful_update = time.time()
            
            self.last_update = time.time()
            
            if do_detailed:
                investigation_status = ""
                if self.investigation_mode and self.smart_investigation_logger:
                    smart_status = self.smart_investigation_logger.get_smart_status()
                    investigation_status = f" [✨ Enhanced v4.0: {smart_status['meaningful_logs']}/{smart_status['total_updates']} files, {smart_status['monitored_keys_count']} keys]"
                
                self._debug_log(f"✅ Update #{self.update_count} complete{investigation_status}", "info")
                self._debug_log("=" * 60, "info")
            else:
                self._log_brief_status()
            
            _LOGGER.error("✅ DEBUG: _async_update_data completed successfully")
            return self.parsed_data
            
        except Exception as e:
            self._consecutive_failures += 1
            
            if self._consecutive_failures <= 3:
                self._debug_log(f"⚠️ Update failed (attempt {self._consecutive_failures}/3): {e}", "warning", force=True)
            else:
                self._debug_log(f"❌ Multiple consecutive failures ({self._consecutive_failures}): {e}", "error", force=True)
            
            _LOGGER.error(f"❌ DEBUG: _async_update_data failed: {e}")
            raise UpdateFailed(f"Error communicating with Eufy device: {e}")

    # Add placeholder methods to prevent AttributeError
    def _should_do_detailed_logging(self) -> bool:
        """Determine if detailed logging should be done."""
        return True  # For debug purposes, always do detailed logging
    
    def _debug_log(self, message: str, level: str = "info", force: bool = False) -> None:
        """Debug logging method."""
        if level == "error" or force:
            _LOGGER.error(message)
        elif level == "warning":
            _LOGGER.warning(message)
        else:
            _LOGGER.info(message)
    
    def _log_brief_status(self) -> None:
        """Log brief status."""
        _LOGGER.error(f"📊 Brief status update #{self.update_count}")
    
    async def _initialize_clients(self) -> None:
        """Initialize Eufy clients."""
        _LOGGER.error("🚨 DEBUG: _initialize_clients called")
        # Placeholder for client initialization
        pass
    
    async def _initialize_accessory_config(self) -> None:
        """Initialize accessory configuration."""
        _LOGGER.error("🚨 DEBUG: _initialize_accessory_config called")
        # Placeholder for accessory config initialization
        pass
    
    async def _initialize_multi_key_investigation_mode(self) -> None:
        """Initialize multi-key investigation mode."""
        _LOGGER.error("🚨 DEBUG: _initialize_multi_key_investigation_mode called")
        # Placeholder for investigation mode initialization
        pass
    
    async def _fetch_eufy_data_with_rest(self) -> None:
        """Fetch Eufy data with REST."""
        _LOGGER.error("🚨 DEBUG: _fetch_eufy_data_with_rest called")
        # Placeholder - set basic parsed data
        self.parsed_data = {
            "battery": 35,
            "clean_speed": 1,
            "work_status": 2,
            "debug_test": True
        }
    
    async def _process_enhanced_smart_multi_key_investigation_data(self) -> None:
        """Process enhanced smart multi-key investigation data."""
        _LOGGER.error("🚨 DEBUG: _process_enhanced_smart_multi_key_investigation_data called")
        # Placeholder for investigation data processing
        pass
    
    async def _process_sensor_data(self) -> None:
        """Process sensor data."""
        _LOGGER.error("🚨 DEBUG: _process_sensor_data called")
        # Placeholder for sensor data processing
        pass
    
    async def _process_accessory_data(self) -> None:
        """Process accessory data."""
        _LOGGER.error("🚨 DEBUG: _process_accessory_data called")
        # Placeholder for accessory data processing
        pass