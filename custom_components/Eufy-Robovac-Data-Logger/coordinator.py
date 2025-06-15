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
    """Eufy Robovac Debugging data coordinator with RestConnect and Enhanced Smart Investigation Mode v4.0."""

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
        
        # Connection tracking
        self._eufy_login = None
        self._rest_client = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        
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
        """Fetch data from Eufy device with RestConnect and Enhanced Smart Investigation Mode v4.0."""
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
            
            return self.parsed_data
            
        except Exception as e:
            self._consecutive_failures += 1
            
            if self._consecutive_failures <= 3:
                self._debug_log(f"⚠️ Update failed (attempt {self._consecutive_failures}/3): {e}", "warning", force=True)
            else:
                self._debug_log(f"❌ Multiple consecutive failures ({self._consecutive_failures}): {e}", "error", force=True)
            
            raise UpdateFailed(f"Error communicating with Eufy device: {e}")

    async def _initialize_multi_key_investigation_mode(self) -> None:
        """Initialize Enhanced Smart Investigation Mode v4.0 with multi-key support."""
        if not self.smart_investigation_logger:
            return
            
        try:
            self._debug_log("🔍 Initializing Enhanced Smart Investigation Mode v4.0 for intelligent multi-key analysis", "info", force=True)
            self._debug_log(f"📂 Investigation directory: {self.smart_investigation_logger.investigation_dir}", "info", force=True)
            self._debug_log(f"🔬 Session ID: {self.smart_investigation_logger.session_id}", "info", force=True)
            self._debug_log(f"🗂️ Monitoring keys: {', '.join(self.smart_investigation_logger.monitored_keys)}", "info", force=True)
            self._debug_log("🧠 ENHANCED FEATURES v4.0: Multi-key support, sensors config integration, self-contained files", "info", force=True)
            self._debug_log("🎯 TARGET: ALL monitored keys analysis with cross-key correlation and water tank/battery discovery", "info", force=True)
            self._debug_log("📊 EFFICIENCY: 80-90% file reduction with complete reference data in each file", "info", force=True)
            self._debug_log("✨ NEW v4.0: Multi-key infrastructure replicating Key 180 analysis for all monitored keys", "info", force=True)
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize enhanced smart investigation mode v4.0: {e}", "error", force=True)

    async def _process_enhanced_smart_multi_key_investigation_data(self) -> None:
        """Process multi-key data using enhanced smart investigation logger v4.0."""
        if not self.smart_investigation_logger:
            return
            
        try:
            # UPDATED: Use new multi-key processing method
            result_file = await self.smart_investigation_logger.process_multi_key_update(self.raw_data)
            
            if result_file:
                filename = Path(result_file).name
                self._debug_log(f"✨ Enhanced Smart Investigation v4.0: Multi-key analysis file created: {filename}", "info")
                
                # Get enhanced smart status for logging
                smart_status = self.smart_investigation_logger.get_smart_status()
                efficiency = smart_status.get('efficiency_percentage', 0)
                total_changes = smart_status.get('key_change_summary', {}).get('total_changes', 0)
                self._debug_log(f"📊 Enhanced Stats v4.0: {smart_status['meaningful_logs']}/{smart_status['total_updates']} files "
                              f"({efficiency:.1f}% efficient, {smart_status['monitored_keys_count']} keys, {total_changes} changes)", "debug")
            else:
                # No file created - either no change or duplicate
                smart_status = self.smart_investigation_logger.get_smart_status()
                if smart_status['total_updates'] % 10 == 0:  # Log efficiency every 10 updates
                    efficiency = smart_status.get('efficiency_percentage', 0)
                    self._debug_log(f"✨ Enhanced Smart Investigation v4.0: No significant changes detected (Efficiency: {efficiency:.1f}%)", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Enhanced smart multi-key investigation v4.0 processing error: {e}", "error", force=True)

    async def capture_investigation_baseline(self) -> str:
        """Manually capture baseline for enhanced smart investigation v4.0."""
        if not self.smart_investigation_logger:
            return "Enhanced Smart Investigation mode v4.0 not enabled"
            
        try:
            # Check if we have any monitored keys available
            available_keys = [key for key in MONITORED_KEYS if key in self.raw_data and self.raw_data[key] is not None]
            if not available_keys:
                return "No monitored keys available for baseline capture"
            
            result_file = await self.smart_investigation_logger.capture_baseline(self.raw_data)
            if result_file:
                filename = Path(result_file).name
                self._debug_log(f"🎯 Manual enhanced multi-key baseline captured v4.0: {filename}", "info", force=True)
                return f"Enhanced smart multi-key baseline captured v4.0: {filename} ({len(available_keys)} keys)"
            else:
                return "Failed to capture enhanced multi-key baseline"
                
        except Exception as e:
            return f"Error capturing enhanced multi-key baseline v4.0: {e}"

    async def capture_investigation_post_cleaning(self) -> str:
        """Manually capture post-cleaning data for enhanced smart investigation v4.0."""
        if not self.smart_investigation_logger:
            return "Enhanced Smart Investigation mode v4.0 not enabled"
            
        try:
            # Check if we have any monitored keys available
            available_keys = [key for key in MONITORED_KEYS if key in self.raw_data and self.raw_data[key] is not None]
            if not available_keys:
                return "No monitored keys available for post-cleaning capture"
            
            result_file = await self.smart_investigation_logger.capture_post_cleaning(self.raw_data)
            if result_file:
                filename = Path(result_file).name
                self._debug_log(f"📊 Manual enhanced multi-key post-cleaning captured v4.0: {filename}", "info", force=True)
                return f"Enhanced smart multi-key post-cleaning captured v4.0: {filename} ({len(available_keys)} keys)"
            else:
                return "Failed to capture enhanced multi-key post-cleaning data"
                
        except Exception as e:
            return f"Error capturing enhanced multi-key post-cleaning v4.0: {e}"

    async def get_investigation_summary(self) -> str:
        """Get enhanced smart investigation session summary v4.0."""
        if not self.smart_investigation_logger:
            return "Enhanced Smart Investigation mode v4.0 not enabled"
            
        try:
            summary_file = await self.smart_investigation_logger.generate_session_summary()
            if summary_file:
                filename = Path(summary_file).name
                smart_status = self.smart_investigation_logger.get_smart_status()
                efficiency = smart_status.get('efficiency_percentage', 0)
                total_changes = smart_status.get('key_change_summary', {}).get('total_changes', 0)
                self._debug_log(f"📋 Enhanced smart multi-key session summary v4.0 created: {filename} "
                              f"(Efficiency: {efficiency:.1f}%, {total_changes} total changes tracked)", "info", force=True)
                return f"Enhanced smart multi-key session summary v4.0: {filename}"
            else:
                return "Failed to generate enhanced multi-key summary"
                
        except Exception as e:
            return f"Error generating enhanced multi-key summary v4.0: {e}"

    def get_investigation_status(self) -> Dict[str, Any]:
        """Get current enhanced smart investigation status v4.0."""
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

    async def _fetch_eufy_data_with_rest(self) -> None:
        """Fetch data using RestConnect with fallback to basic login."""
        try:
            if self._rest_client and self._rest_client.is_connected:
                # Try RestConnect first
                try:
                    await self._rest_client.updateDevice()
                    self.raw_data = self._rest_client.raw_data.copy()
                    self.parsed_data["data_source"] = "RestConnect Enhanced"
                    
                    if self._should_do_detailed_logging():
                        self._debug_log("🌐 Data fetched via RestConnect", "debug")
                    
                    return
                    
                except Exception as rest_error:
                    self._debug_log(f"⚠️ RestConnect failed, falling back to basic login: {rest_error}", "warning")
            
            # Fallback to basic login
            if self._eufy_login:
                try:
                    await self._eufy_login.updateDevice()
                    self.raw_data = self._eufy_login.raw_data.copy()
                    self.parsed_data["data_source"] = "Basic Login Fallback"
                    
                    if self._should_do_detailed_logging():
                        self._debug_log("📱 Data fetched via basic login fallback", "debug")
                        
                except Exception as login_error:
                    self._debug_log(f"❌ Basic login also failed: {login_error}", "error")
                    raise UpdateFailed(f"Both RestConnect and basic login failed: {login_error}")
            else:
                raise UpdateFailed("No authentication client available")
                
        except Exception as e:
            self._debug_log(f"❌ Data fetch failed: {e}", "error")
            raise UpdateFailed(f"Failed to fetch data: {e}")

    async def _process_sensor_data(self) -> None:
        """Process raw data into structured sensor data."""
        try:
            # Get found and missing keys for monitoring
            found_keys = []
            missing_keys = []
            
            for key in MONITORED_KEYS:
                if key in self.raw_data and self.raw_data[key] is not None:
                    found_keys.append(key)
                else:
                    missing_keys.append(key)
            
            # Store monitoring data
            self.parsed_data["monitored_keys_found"] = found_keys
            self.parsed_data["monitored_keys_missing"] = missing_keys
            
            # Parse known sensors
            self.parsed_data["battery"] = self._parse_battery()
            self.parsed_data["clean_speed"] = self._parse_clean_speed()
            self.parsed_data["work_status"] = self._parse_work_status()
            
            # Store update metadata
            self.parsed_data["last_update"] = time.time()
            self.parsed_data["update_count"] = self.update_count
            
            # Log key availability
            if self._should_do_detailed_logging():
                coverage = len(found_keys) / len(MONITORED_KEYS) * 100
                self._debug_log(f"📊 Key coverage: {len(found_keys)}/{len(MONITORED_KEYS)} ({coverage:.1f}%)", "debug")
                self._debug_log(f"✅ Found: {', '.join(found_keys)}", "debug")
                if missing_keys:
                    self._debug_log(f"❌ Missing: {', '.join(missing_keys)}", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Sensor data processing error: {e}", "error", force=True)

    def _parse_battery(self) -> Optional[int]:
        """Parse battery level from available keys."""
        # Try Key 163 first (from your live data: Key 163: 93)
        if "163" in self.raw_data:
            try:
                value = self.raw_data["163"]
                if isinstance(value, (int, float)) and 0 <= value <= 100:
                    return int(value)
            except:
                pass
        
        # Try other potential battery keys
        battery_candidates = ["162", "168"]
        for key in battery_candidates:
            if key in self.raw_data:
                try:
                    value = self.raw_data[key]
                    if isinstance(value, (int, float)) and 80 <= value <= 100:
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
            accessory_data = {}
            changes_detected = False
            
            # Process each configured accessory sensor
            for sensor_id, sensor_config in self.accessory_sensors.items():
                try:
                    key = sensor_config["key"]
                    byte_position = sensor_config.get("byte_position")
                    
                    if key in self.raw_data and self.raw_data[key] is not None:
                        # Extract value based on configuration
                        detected_value = await self._extract_accessory_value(
                            self.raw_data[key], byte_position, sensor_config
                        )
                        
                        # Check for changes
                        previous_value = self.previous_accessory_data.get(sensor_id, {}).get("detected_value")
                        if previous_value != detected_value:
                            changes_detected = True
                        
                        accessory_data[sensor_id] = {
                            "name": sensor_config["name"],
                            "current_life_remaining": sensor_config["current_life_remaining"],
                            "detected_value": detected_value,
                            "hours_remaining": sensor_config.get("hours_remaining", 0),
                            "max_hours": sensor_config.get("max_life_hours", 0),
                            "threshold": sensor_config.get("replacement_threshold", 10),
                            "enabled": sensor_config.get("enabled", True),
                            "key": key,
                            "byte_position": byte_position,
                            "notes": sensor_config.get("notes", ""),
                            "last_updated": sensor_config.get("last_updated"),
                            "detection_accuracy": self._calculate_detection_accuracy(
                                detected_value, sensor_config["current_life_remaining"]
                            ) if detected_value is not None else None
                        }
                        
                        if self._should_do_detailed_logging() and detected_value is not None:
                            self._debug_log(f"🔧 {sensor_config['name']}: {detected_value}% "
                                          f"(Expected: {sensor_config['current_life_remaining']}%, "
                                          f"Key {key}, Byte {byte_position})", "debug")
                    else:
                        # Key not available
                        accessory_data[sensor_id] = {
                            "name": sensor_config["name"],
                            "current_life_remaining": sensor_config["current_life_remaining"],
                            "detected_value": None,
                            "hours_remaining": sensor_config.get("hours_remaining", 0),
                            "max_hours": sensor_config.get("max_life_hours", 0),
                            "threshold": sensor_config.get("replacement_threshold", 10),
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
        """Initialize login and RestConnect clients."""
        try:
            self._debug_log("🌐 Initializing RestConnect client...", "info", force=True)
            
            # Import here to avoid circular imports
            from .controllers.login import EufyLogin
            
            # Create login instance first
            self._eufy_login = EufyLogin(
                username=self.username,
                password=self.password,
                openudid=self.openudid
            )
            
            # Initialize login to get authentication
            await self._eufy_login.init()
            self._debug_log("✅ EufyLogin initialized successfully", "info", force=True)
            
            # Try to create RestConnect client (if available)
            try:
                from .controllers.rest_connect import RestConnect
                
                rest_config = {
                    'deviceId': self.device_id,
                    'deviceModel': self.device_model,
                    'debug': self.debug_mode
                }
                
                self._rest_client = RestConnect(
                    config=rest_config,
                    openudid=self.openudid,
                    eufyCleanApi=self._eufy_login
                )
                
                # Set debug logger for RestConnect
                if self.debug_logger:
                    self._rest_client.debug_logger = self.debug_logger
                
                # Try to connect
                await self._rest_client.connect()
                self._debug_log("✅ RestConnect client initialized and connected", "info", force=True)
                
            except ImportError:
                self._debug_log("⚠️ RestConnect module not available, using basic login only", "warning", force=True)
                self._rest_client = None
            except Exception as rest_error:
                self._debug_log(f"⚠️ RestConnect not available: {rest_error}, using basic login only", "warning", force=True)
                self._rest_client = None
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize clients: {e}", "error", force=True)
            # Fall back to basic login only
            if not self._eufy_login:
                from .controllers.login import EufyLogin
                self._eufy_login = EufyLogin(
                    username=self.username,
                    password=self.password,
                    openudid=self.openudid
                )
            self._debug_log("⚠️ Using basic login only", "warning", force=True)

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
            
            self._debug_log(f"📊 Brief: Battery {battery}%, Speed {speed}, Keys {found_keys}/{total_keys}{investigation_info}", "info")
            
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

    def get_restconnect_info(self) -> Dict[str, Any]:
        """Get RestConnect connection information."""
        try:
            if not self._rest_client:
                return {
                    "is_connected": False,
                    "connection_mode": "Basic Login Fallback",
                    "last_update": self._last_successful_update,
                    "update_count": self.update_count,
                    "keys_received": len(self.raw_data),
                    "has_auth_token": bool(self._eufy_login),
                    "has_user_center_token": False,
                    "has_gtoken": False,
                    "device_id": self.device_id,
                    "user_id": None,
                    "api_endpoints_available": {}
                }
            
            # Get RestConnect status
            return self._rest_client.get_connection_info()
            
        except Exception as e:
            self._debug_log(f"❌ Error getting RestConnect info: {e}", "error")
            return {
                "is_connected": False,
                "connection_mode": "Error",
                "error": str(e),
                "last_update": self._last_successful_update,
                "update_count": self.update_count,
                "keys_received": len(self.raw_data),
                "has_auth_token": False,
                "has_user_center_token": False,
                "has_gtoken": False,
                "device_id": self.device_id,
                "user_id": None,
                "api_endpoints_available": {}
            }

    def _debug_log(self, message: str, level: str = "info", force: bool = False) -> None:
        """Smart debug logging with level control."""
        if not force and not self._should_do_detailed_logging():
            return
        
        # Add device identifier for multi-device setups
        prefixed_message = f"[{self.device_id[-6:]}] {message}"
        
        if level == "debug":
            _LOGGER.debug(prefixed_message)
        elif level == "info":
            _LOGGER.info(prefixed_message)
        elif level == "warning":
            _LOGGER.warning(prefixed_message)
        elif level == "error":
            _LOGGER.error(prefixed_message)
        else:
            _LOGGER.info(prefixed_message)
            
