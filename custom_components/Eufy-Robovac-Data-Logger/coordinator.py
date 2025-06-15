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
            
            # Fetch data using DPS-only login
            await self._fetch_eufy_data_with_dps()
            
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
            
            # FIXED: Call the initialize method
            await self.smart_investigation_logger.initialize()
            
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
        """Get enhanced smart investigation session summary v4.0 - FIXED: Added missing method."""
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

    async def _fetch_eufy_data_with_dps(self) -> None:
        """Fetch data using DPS-only login."""
        try:
            if not self._eufy_login:
                await self._initialize_clients()
            
            # Get DPS data directly
            dps_data = await self._eufy_login.get_dps_data(self.device_id)
            
            if dps_data:
                self.raw_data = dps_data
                self.parsed_data.update({
                    "last_update": time.time(),
                    "update_count": self.update_count,
                    "data_source": "🔍 DPS Only - Enhanced Key 180 + Multi-Key Analysis"
                })
                
                if self._should_do_detailed_logging():
                    self._debug_log(f"📱 DPS data fetched: {len(self.raw_data)} keys available", "debug")
                    self._debug_log(f"🗂️ Monitored keys found: {len([k for k in MONITORED_KEYS if k in self.raw_data])}/{len(MONITORED_KEYS)}", "debug")
            else:
                raise UpdateFailed("No DPS data received")
                
        except Exception as e:
            self._debug_log(f"❌ DPS data fetch failed: {e}", "error")
            raise UpdateFailed(f"DPS communication failed: {e}")

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

    async def _process_sensor_data(self) -> None:
        """Process sensor data from raw DPS data."""
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

    async def _process_accessory_data(self) -> None:
        """Process accessory data with change detection."""
        try:
            if not self.accessory_sensors:
                return
            
            accessory_changes = []
            
            for sensor_id, sensor_config in self.accessory_sensors.items():
                try:
                    key = sensor_config["key"]
                    byte_position = sensor_config["byte_position"]
                    
                    if key in self.raw_data and byte_position is not None:
                        # Extract and analyze the byte value
                        detected_value = self._extract_byte_value(self.raw_data[key], byte_position)
                        configured_life = sensor_config["current_life_remaining"]
                        
                        # Store in parsed data
                        self.parsed_data[f"accessory_{sensor_id}"] = {
                            "detected_value": detected_value,
                            "configured_life": configured_life,
                            "detection_accuracy": self._calculate_accuracy(detected_value, configured_life),
                            "name": sensor_config["name"],
                            "key": key,
                            "byte_position": byte_position
                        }
                        
                        # Check for changes
                        if sensor_id in self.previous_accessory_data:
                            old_value = self.previous_accessory_data[sensor_id].get("detected_value")
                            if old_value != detected_value:
                                accessory_changes.append(f"{sensor_config['name']}: {old_value}% → {detected_value}%")
                        
                        # Update tracking
                        self.previous_accessory_data[sensor_id] = self.parsed_data[f"accessory_{sensor_id}"]
                        
                except Exception as e:
                    self._debug_log(f"⚠️ Error processing accessory {sensor_id}: {e}", "warning")
            
            # Log significant accessory changes
            if accessory_changes and self._should_do_detailed_logging():
                self._debug_log(f"🔧 Accessory changes detected: {', '.join(accessory_changes)}", "info")
                
        except Exception as e:
            self._debug_log(f"❌ Accessory data processing error: {e}", "error")

    def _extract_byte_value(self, raw_value: Any, byte_position: int) -> Optional[int]:
        """Extract byte value from raw data at specified position."""
        try:
            if isinstance(raw_value, str):
                # Base64 decode and extract byte
                decoded = base64.b64decode(raw_value)
                if 0 <= byte_position < len(decoded):
                    return int(decoded[byte_position])
            elif isinstance(raw_value, (int, float)):
                # Direct numeric value
                return int(raw_value)
        except:
            pass
        
        return None

    def _calculate_accuracy(self, detected: Optional[int], expected: int) -> Optional[float]:
        """Calculate accuracy percentage between detected and expected values."""
        if detected is None:
            return None
        
        try:
            difference = abs(detected - expected)
            accuracy = max(0, 100 - (difference * 10))  # 10% penalty per 1% difference
            return round(accuracy, 1)
        except:
            return None