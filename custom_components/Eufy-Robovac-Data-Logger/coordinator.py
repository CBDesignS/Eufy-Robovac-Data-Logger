"""Data update coordinator for Eufy Robovac Data Logger integration with Enhanced Smart Investigation Mode v4.0."""
import asyncio
import logging
import time
import base64
from datetime import timedelta
from typing import Any, Dict, Optional, List
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, MONITORED_KEYS, ALL_MONITORED_KEYS, CONF_DEBUG_MODE, CONF_INVESTIGATION_MODE, CLEAN_SPEED_NAMES, WORK_STATUS_MAP
from .accessory_config_manager import AccessoryConfigManager

_LOGGER = logging.getLogger(__name__)


class EufyX10DebugCoordinator(DataUpdateCoordinator):
    """Eufy Robovac Debugging data coordinator with DPS-only data fetching and Enhanced Smart Investigation Mode v4.0."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.device_id = entry.data["device_id"]
        self.device_name = entry.data.get("device_name", "Unknown Device")
        self.device_model = entry.data.get("device_model", "T8213")
        self.username = entry.data["username"]
        self.password = entry.data["password"]
        self.openudid = entry.data.get("openudid", f"ha_debug_{self.device_id}")
        self.debug_mode = entry.data.get("debug_mode", True)
        
        # UPDATED: Enhanced Smart Investigation Mode v4.0 - Multi-Key Support
        self.investigation_mode = entry.options.get(
            CONF_INVESTIGATION_MODE,
            entry.data.get(CONF_INVESTIGATION_MODE, False)
        )
        
        # Store raw data for debugging
        self.raw_data: Dict[str, Any] = {}
        self.parsed_data: Dict[str, Any] = {}
        self.last_update: Optional[float] = None
        self.update_count = 0
        
        # SMART LOGGING - Reduced frequency with intelligence
        self.detailed_log_interval = 600 if not self.investigation_mode else 300  # Less frequent, smarter
        self.last_detailed_log = 0
        self.first_few_updates = 1  # Only log first update in detail
        
        # CHANGE DETECTION - only log when something changes
        self._last_logged_status = None
        self._quiet_updates_count = 0
        self._quiet_log_interval = 120  # Brief status every 2 minutes
        
        # Connection tracking - DPS ONLY
        self._eufy_login = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5  # NEW: Threshold before recreating login
        
        # Initialize AccessoryConfigManager
        integration_dir = Path(__file__).parent
        self.accessory_manager = AccessoryConfigManager(
            device_id=self.device_id,
            integration_dir=str(integration_dir)
        )
        self.accessory_sensors = {}
        self.previous_accessory_data = {}
        
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
                _LOGGER.info("🔍 Enhanced Smart Multi-Key Investigation Logger v4.0 initialized")
                _LOGGER.info("🗂️ Monitoring %d keys for comprehensive analysis", len(MONITORED_KEYS))
                
            except Exception as e:
                _LOGGER.error("❌ Failed to initialize multi-key investigation logger v4.0: %s", e)
                self.smart_investigation_logger = None
        
        # Debug logger for detailed debugging when needed
        self.debug_logger = None
        if self.debug_mode:
            try:
                from .async_debug_logger import AsyncEufyDebugLogger
                self.debug_logger = AsyncEufyDebugLogger(
                    device_id=self.device_id,
                    hass_config_dir=hass.config.config_dir
                )
            except Exception as e:
                _LOGGER.warning("⚠️ Failed to initialize debug logger: %s", e)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_setup(self) -> None:
        """Set up the coordinator."""
        await self._initialize_clients()
        await self._initialize_accessory_config()
        await self._initialize_multi_key_investigation_mode()

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy device with DPS-only and Enhanced Smart Investigation Mode v4.0."""
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
            
            # Fetch data using DPS-only (no REST API) with improved error handling
            await self._fetch_eufy_data_dps_only()
            
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
                    investigation_status = f" [✨ Enhanced v4.0: {smart_status['meaningful_logs']} files logged, {smart_status['efficiency_percentage']:.1f}% efficiency]"
                
                self._debug_log(f"✅ UPDATE #{self.update_count} COMPLETED - Battery: {self.parsed_data.get('battery', '?')}%, Raw keys: {len(self.raw_data)}, Monitored found: {len(self.parsed_data.get('monitored_keys_found', []))}/{len(MONITORED_KEYS)}{investigation_status}", "info")
                self._debug_log("=" * 60, "info")
            else:
                # Log brief status
                self._log_brief_status()
            
            # Return combined data
            return {
                **self.parsed_data,
                "last_update": self.last_update,
                "update_count": self.update_count,
                "raw_data_count": len(self.raw_data),
                "device_id": self.device_id,
            }
            
        except Exception as e:
            self._consecutive_failures += 1
            self._debug_log(f"❌ Update #{self.update_count} failed (consecutive failures: {self._consecutive_failures}): {e}", "error", force=True)
            
            # Only raise UpdateFailed if we've hit the threshold (this destroys login session)
            if self._consecutive_failures >= self._max_consecutive_failures:
                self._debug_log(f"🔄 Hit {self._max_consecutive_failures} consecutive failures - will recreate login session", "warning", force=True)
                raise UpdateFailed(f"Failed to fetch data after {self._consecutive_failures} attempts: {e}")
            else:
                # Return last known good data instead of failing completely
                self._debug_log(f"⚠️ Temporary failure {self._consecutive_failures}/{self._max_consecutive_failures} - keeping login session alive", "warning")
                return self.parsed_data or {}

    async def _fetch_eufy_data_dps_only(self) -> None:
        """Fetch data using DPS-only (basic login) - NO REST API with FIXED error handling."""
        try:
            # Use ONLY basic login/DPS for data fetching
            if self._eufy_login:
                try:
                    # Get device data with DPS
                    device_data = await self._eufy_login.getMqttDevice(self.device_id)
                    
                    if device_data and 'dps' in device_data:
                        self.raw_data = device_data['dps'].copy()
                        self.parsed_data["data_source"] = "DPS Only (Basic Login)"
                        
                        if self._should_do_detailed_logging():
                            self._debug_log(f"📱 Data fetched via DPS-only: {len(self.raw_data)} keys", "debug")
                    else:
                        # FIXED: Don't raise UpdateFailed for missing data - this is temporary
                        self._debug_log("⚠️ No DPS data in device response - keeping existing data", "warning")
                        # Keep existing raw_data instead of clearing it
                        if not hasattr(self, 'raw_data') or not self.raw_data:
                            self.raw_data = {}
                        
                except Exception as dps_error:
                    # FIXED: Don't raise UpdateFailed for DPS errors - these are often temporary
                    error_msg = str(dps_error).lower()
                    
                    # Check if this is an authentication error vs temporary network error
                    auth_error_indicators = ['unauthorized', 'invalid token', 'login failed', 'authentication']
                    is_auth_error = any(indicator in error_msg for indicator in auth_error_indicators)
                    
                    if is_auth_error:
                        self._debug_log(f"🔑 Authentication error detected: {dps_error}", "error")
                        raise Exception(f"Authentication failed: {dps_error}")  # This will trigger login recreation
                    else:
                        # Temporary network/data error - don't destroy login session
                        self._debug_log(f"📡 Temporary DPS error (keeping login session): {dps_error}", "warning")
                        # Keep existing data instead of failing
                        return
            else:
                # No login client - this needs to be recreated
                raise Exception("No DPS authentication client available")
                
        except Exception as e:
            # FIXED: Only log error and re-raise - let the main update handler decide what to do
            self._debug_log(f"❌ Data fetch error: {e}", "error")
            raise  # Re-raise to let main handler count failures and decide when to recreate login

    async def _process_sensor_data(self) -> None:
        """Process raw data into structured sensor data."""
        try:
            # Extract common sensor values
            self.parsed_data["battery"] = self._parse_battery()
            self.parsed_data["clean_speed"] = self._parse_clean_speed()
            self.parsed_data["work_status"] = self._parse_work_status()
            
            # Track which monitored keys we actually found
            found_keys = []
            for key in MONITORED_KEYS:
                if key in self.raw_data and self.raw_data[key] is not None:
                    found_keys.append(key)
            
            self.parsed_data["monitored_keys_found"] = found_keys
            
            if self._should_do_detailed_logging():
                self._debug_log(f"🔍 Found {len(found_keys)}/{len(MONITORED_KEYS)} monitored keys", "debug")
                
        except Exception as e:
            self._debug_log(f"❌ Sensor data processing error: {e}", "error")

    async def _process_enhanced_smart_multi_key_investigation_data(self) -> None:
        """Process Enhanced Smart Investigation Mode v4.0 with multi-key support."""
        try:
            if not self.smart_investigation_logger:
                return
            
            # Process multi-key investigation data
            investigation_file = await self.smart_investigation_logger.process_multi_key_update(self.raw_data)
            
            if investigation_file:
                self._debug_log(f"🔍 Enhanced Smart Investigation v4.0: Logged multi-key data to {Path(investigation_file).name}", "info")
            
        except Exception as e:
            self._debug_log(f"❌ Enhanced Smart Investigation v4.0 processing error: {e}", "error")

    async def _initialize_multi_key_investigation_mode(self) -> None:
        """Initialize Enhanced Smart Investigation Mode v4.0 with multi-key support."""
        if not self.investigation_mode or not self.smart_investigation_logger:
            return
        
        try:
            # Initialize the multi-key logger
            await self.smart_investigation_logger.initialize()
            
            self._debug_log("🔍 Enhanced Smart Multi-Key Investigation Mode v4.0 ready", "info", force=True)
            self._debug_log(f"🗂️ Monitoring {len(MONITORED_KEYS)} keys for comprehensive analysis", "info", force=True)
            self._debug_log(f"📁 Investigation files: {self.smart_investigation_logger.investigation_dir}", "info", force=True)
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize multi-key investigation mode v4.0: {e}", "error", force=True)

    def get_investigation_status(self) -> Dict[str, Any]:
        """Get investigation mode status information."""
        if not self.smart_investigation_logger:
            return {
                "enabled": False,
                "version": "4.0_multi_key",
                "status": "Investigation mode not enabled"
            }
        
        try:
            smart_status = self.smart_investigation_logger.get_smart_status()
            
            # Enhanced status with multi-key information
            status = {
                "enabled": True,
                "version": "4.0_multi_key",
                "session_id": smart_status["session_id"],
                "baseline_captured": smart_status["baseline_captured"],
                "current_mode": smart_status["current_mode"],
                "total_updates": smart_status["total_updates"],
                "meaningful_logs": smart_status["meaningful_logs"],
                "efficiency_percentage": smart_status["efficiency_percentage"],
                "monitored_keys_count": smart_status["monitored_keys_count"],
                "available_keys": [key for key in MONITORED_KEYS if key in self.raw_data and self.raw_data[key] is not None],
                "missing_keys": [key for key in MONITORED_KEYS if key not in self.raw_data or self.raw_data[key] is None],
                "investigation_directory": smart_status["investigation_directory"],
                "last_log_time": smart_status["last_log_time"],
                "key_change_summary": smart_status.get("key_change_summary", {}),
                "workflow_status": {
                    "next_action": "capture_baseline" if not smart_status["baseline_captured"] else "run_cleaning_cycle",
                    "available_services": [
                        "eufy_robovac_data_logger.capture_investigation_baseline",
                        "eufy_robovac_data_logger.capture_investigation_post_cleaning",
                        "eufy_robovac_data_logger.generate_investigation_summary"
                    ]
                }
            }
            
            return status
            
        except Exception as e:
            return {
                "enabled": True,
                "version": "4.0_multi_key",
                "status": f"Error getting status: {e}"
            }

    def _parse_battery(self) -> Optional[int]:
        """Parse battery level from Key 163."""
        # Key 163 is confirmed working for battery
        if "163" in self.raw_data:
            try:
                value = self.raw_data["163"]
                if isinstance(value, (int, float)):
                    return int(value)
            except:
                pass
        
        return None

    def _parse_clean_speed(self) -> Optional[str]:
        """Parse cleaning speed from available keys."""
        # Try Key 158 first (from your live data: Key 158: 3)
        if "158" in self.raw_data:
            try:
                value = self.raw_data["158"]
                if isinstance(value, (int, float)):
                    speed_int = int(value)
                    return CLEAN_SPEED_NAMES.get(speed_int, f"Unknown ({speed_int})")
            except:
                pass
        
        return None

    def _parse_work_status(self) -> Optional[str]:
        """Parse work status from available keys."""
        # Try Key 153 (from your live data: Key 153: ChADGgByAiIAegA=)
        if "153" in self.raw_data:
            try:
                value = self.raw_data["153"]
                if isinstance(value, str):
                    # Try to decode base64 and look for status bytes
                    decoded = base64.b64decode(value)
                    # Look for status-like bytes (0-10 range)
                    for byte_val in decoded:
                        if 0 <= byte_val <= 10:
                            return WORK_STATUS_MAP.get(byte_val, f"Unknown ({byte_val})")
                elif isinstance(value, (int, float)):
                    status_int = int(value)
                    return WORK_STATUS_MAP.get(status_int, f"Unknown ({status_int})")
            except:
                pass
        
        return None

    async def _process_accessory_data(self) -> None:
        """Process accessory data with change detection."""
        try:
            # Check if we have any accessory sensors configured
            if not self.accessory_sensors:
                self.parsed_data["accessory_sensors"] = {}
                return
            
            accessory_data = {}
            changes_detected = False
            
            for sensor_id, sensor_config in self.accessory_sensors.items():
                try:
                    key = str(sensor_config.get("key"))
                    byte_position = sensor_config.get("byte_position")
                    
                    if key in self.raw_data and self.raw_data[key] is not None:
                        # Extract value from raw data
                        raw_value = self.raw_data[key]
                        detected_value = await self._extract_accessory_value(raw_value, byte_position, sensor_config)
                        
                        # Calculate remaining hours and life
                        configured_life = sensor_config.get("current_life_remaining", 100)
                        max_hours = sensor_config.get("max_hours", 100)
                        hours_remaining = int((configured_life / 100) * max_hours)
                        
                        # Create sensor data
                        accessory_data[sensor_id] = {
                            "name": sensor_config.get("name"),
                            "description": sensor_config.get("description", ""),
                            "configured_life": configured_life,
                            "detected_value": detected_value,
                            "hours_remaining": hours_remaining,
                            "max_hours": max_hours,
                            "threshold": sensor_config.get("replacement_threshold", 10),
                            "detection_accuracy": self._calculate_detection_accuracy(detected_value, configured_life),
                            "enabled": sensor_config.get("enabled", True),
                            "key": key,
                            "byte_position": byte_position,
                            "notes": sensor_config.get("notes", ""),
                            "last_updated": sensor_config.get("last_updated")
                        }
                        
                        # Check for changes
                        if sensor_id not in self.previous_accessory_data or self.previous_accessory_data[sensor_id] != accessory_data[sensor_id]:
                            changes_detected = True
                    else:
                        # Key not available - create placeholder
                        accessory_data[sensor_id] = {
                            "name": sensor_config.get("name"),
                            "description": sensor_config.get("description", ""),
                            "configured_life": sensor_config.get("current_life_remaining", 100),
                            "detected_value": None,
                            "hours_remaining": 0,
                            "max_hours": sensor_config.get("max_hours", 100),
                            "threshold": sensor_config.get("replacement_threshold", 10),
                            "detection_accuracy": None,
                            "enabled": sensor_config.get("enabled", True),
                            "key": key,
                            "byte_position": byte_position,
                            "notes": sensor_config.get("notes", ""),
                            "last_updated": sensor_config.get("last_updated")
                        }
                        
                        self._debug_log(f"❌ {sensor_config['name']}: Key {key} not available", "debug")
                
                except Exception as sensor_error:
                    self._debug_log(f"⚠️ Error processing accessory {sensor_id}: {sensor_error}", "warning")
            
            # Store processed accessory data
            self.parsed_data["accessory_sensors"] = accessory_data
            
            # Update previous data for change detection
            self.previous_accessory_data = accessory_data.copy()
            
            if changes_detected:
                self._debug_log("🎯 Accessory changes detected - logged for enhanced investigation v4.0", "info")
            
            self._debug_log(f"✅ Processed {len(accessory_data)} accessory sensors", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Accessory data processing error: {e}", "error", force=True)
            self.parsed_data["accessory_sensors"] = {}

    async def _extract_accessory_value(self, raw_value: Any, byte_position: Optional[int], sensor_config: Dict[str, Any]) -> Optional[int]:
        """Extract accessory value from raw data."""
        try:
            if byte_position is None:
                return None
            
            if isinstance(raw_value, str):
                # Decode base64 and extract byte at position
                decoded = base64.b64decode(raw_value)
                if 0 <= byte_position < len(decoded):
                    return int(decoded[byte_position])
            elif isinstance(raw_value, (int, float)):
                # Direct numeric value
                if byte_position == 0:  # Position 0 means use the value directly
                    return int(raw_value)
            
            return None
            
        except Exception as e:
            self._debug_log(f"⚠️ Error extracting accessory value: {e}", "debug")
            return None

    def _calculate_detection_accuracy(self, detected: Optional[int], expected: int) -> Optional[float]:
        """Calculate detection accuracy percentage."""
        if detected is None:
            return None
        
        try:
            difference = abs(detected - expected)
            accuracy = max(0, 100 - (difference * 10))  # 10% penalty per 1% difference
            return round(accuracy, 1)
        except:
            return None

    async def _initialize_clients(self) -> None:
        """Initialize DPS-only login client (NO RestConnect)."""
        try:
            self._debug_log("📱 Initializing DPS-only login client...", "info", force=True)
            
            # Import here to avoid circular imports
            from .controllers.login import EufyLogin
            
            # Create login instance - DPS ONLY
            self._eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # Initialize login to get authentication
            await self._eufy_login.init()
            self._debug_log("✅ DPS-only EufyLogin initialized successfully", "info", force=True)
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize DPS login client: {e}", "error", force=True)
            raise UpdateFailed(f"Failed to initialize login: {e}")

    def _should_do_detailed_logging(self) -> bool:
        """Determine if we should do detailed logging this update."""
        current_time = time.time()
        
        # Always log first few updates in detail
        if self.update_count <= self.first_few_updates:
            return True
        
        # Log detailed every X minutes
        if current_time - self.last_detailed_log >= self.detailed_log_interval:
            self.last_detailed_log = current_time
            return True
        
        return False

    def _log_brief_status(self) -> None:
        """Log a brief status update between detailed logs."""
        try:
            current_time = time.time()
            
            # Only log brief status every 2 minutes to avoid spam
            if self._last_logged_status and current_time - self._last_logged_status < self._quiet_log_interval:
                self._quiet_updates_count += 1
                return
            
            # Create brief status
            battery = self.parsed_data.get("battery", "?")
            speed = self.parsed_data.get("clean_speed", "?")
            found_keys = len(self.parsed_data.get("monitored_keys_found", []))
            total_keys = len(MONITORED_KEYS)
            
            investigation_info = ""
            if self.investigation_mode and self.smart_investigation_logger:
                smart_status = self.smart_investigation_logger.get_smart_status()
                investigation_info = f" | 🔍 v4.0: {smart_status['meaningful_logs']} files"
            
            # Include consecutive failure count if any
            failure_info = ""
            if self._consecutive_failures > 0:
                failure_info = f" | ⚠️ Failures: {self._consecutive_failures}/{self._max_consecutive_failures}"
            
            self._debug_log(f"📊 Brief: Battery {battery}%, Speed {speed}, Keys {found_keys}/{total_keys}{investigation_info}{failure_info}", "info")
            
            self._last_logged_status = current_time
            self._quiet_updates_count = 0
            
        except Exception as e:
            self._debug_log(f"⚠️ Brief status error: {e}", "debug")

    async def _initialize_accessory_config(self) -> None:
        """Initialize the accessory configuration system."""
        try:
            self._debug_log("🔧 Initializing accessory configuration system...", "info", force=True)
            
            # Ensure default config exists
            await self.accessory_manager.ensure_default_config()
            
            # Load accessory sensors
            self.accessory_sensors = await self.accessory_manager.get_enabled_sensors()
            
            self._debug_log(f"✅ Loaded {len(self.accessory_sensors)} accessory sensors from config", "info", force=True)
            
            # Log loaded sensors
            for sensor_id, sensor_config in self.accessory_sensors.items():
                self._debug_log(f"   📍 {sensor_config['name']}: {sensor_config['current_life_remaining']}% "
                              f"(Key {sensor_config['key']}, Byte {sensor_config['byte_position']})", "info", force=True)
            
            # Get config file path for user reference
            config_path = self.accessory_manager.get_config_file_path()
            self._debug_log(f"📂 Config file location: {config_path}", "info", force=True)
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize accessory config: {e}", "error", force=True)
            self.accessory_sensors = {}

    def _debug_log(self, message: str, level: str = "info", force: bool = False) -> None:
        """Smart debug logging with level control."""
        try:
            # Always log if forced or if debug mode is on
            if force or self.debug_mode:
                if level == "error":
                    _LOGGER.error(message)
                elif level == "warning":
                    _LOGGER.warning(message)
                elif level == "debug":
                    _LOGGER.debug(message)
                else:
                    _LOGGER.info(message)
            
            # Also log to debug logger if available
            if self.debug_logger and hasattr(self.debug_logger, level):
                getattr(self.debug_logger, level)(message)
                
        except Exception as e:
            _LOGGER.error(f"Debug logging error: {e}")

    # Service methods for investigation mode
    async def capture_investigation_baseline(self) -> str:
        """Service: Capture investigation baseline."""
        if not self.smart_investigation_logger:
            return "Investigation mode not enabled"
        
        try:
            file_path = await self.smart_investigation_logger.capture_baseline(self.raw_data)
            self._debug_log(f"🔍 Baseline captured: {Path(file_path).name}", "info", force=True)
            return f"Baseline captured: {file_path}"
        except Exception as e:
            self._debug_log(f"❌ Failed to capture baseline: {e}", "error", force=True)
            return f"Error: {e}"

    async def capture_investigation_post_cleaning(self) -> str:
        """Service: Capture post-cleaning investigation data."""
        if not self.smart_investigation_logger:
            return "Investigation mode not enabled"
        
        try:
            file_path = await self.smart_investigation_logger.capture_post_cleaning(self.raw_data)
            self._debug_log(f"🔍 Post-cleaning captured: {Path(file_path).name}", "info", force=True)
            return f"Post-cleaning captured: {file_path}"
        except Exception as e:
            self._debug_log(f"❌ Failed to capture post-cleaning: {e}", "error", force=True)
            return f"Error: {e}"

    async def generate_investigation_summary(self) -> str:
        """Service: Generate investigation session summary."""
        if not self.smart_investigation_logger:
            return "Investigation mode not enabled"
        
        try:
            file_path = await self.smart_investigation_logger.generate_session_summary()
            self._debug_log(f"🔍 Session summary generated: {Path(file_path).name}", "info", force=True)
            return f"Session summary: {file_path}"
        except Exception as e:
            self._debug_log(f"❌ Failed to generate summary: {e}", "error", force=True)
            return f"Error: {e}"