"""Data update coordinator for Eufy Robovac Data Logger integration with Investigation Mode."""
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
    """Eufy Robovac Debugging data coordinator with RestConnect and Investigation Mode."""

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
        
        # NEW: Investigation Mode
        self.investigation_mode = entry.data.get("investigation_mode", False)
        
        # Store raw data for debugging
        self.raw_data: Dict[str, Any] = {}
        self.parsed_data: Dict[str, Any] = {}
        self.last_update: Optional[float] = None
        self.update_count = 0
        
        # REDUCED LOGGING - only every 10 minutes (unless investigation mode)
        self.detailed_log_interval = 600 if not self.investigation_mode else 60  # More frequent in investigation mode
        self.last_detailed_log = 0
        self.first_few_updates = 1  # Only log first update in detail
        
        # CHANGE DETECTION - only log when something changes
        self._last_logged_status = None
        self._quiet_updates_count = 0
        self._quiet_log_interval = 60
        
        # Connection tracking
        self._eufy_login = None
        self._rest_client = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        
        # Initialize AccessoryConfigManager
        integration_dir = Path(__file__).parent
        self.accessory_manager = AccessoryConfigManager(str(integration_dir), self.device_id)
        self.accessory_sensors = {}
        self.previous_accessory_data = {}
        
        # NEW: Investigation Mode Components
        self.investigation_logger = None
        self.last_key180_data = None
        self.cleaning_cycle_detected = False
        self.baseline_captured = False
        
        # Initialize debug logger and investigation logger
        self.debug_logger = None
        if self.debug_mode:
            try:
                from .async_debug_logger import AsyncEufyDebugLogger
                self.debug_logger = AsyncEufyDebugLogger(self.device_id, hass.config.config_dir)
                _LOGGER.info("🚀 DEBUG MODE: Coordinator initialized with RestConnect + accessory config for device: %s", self.device_id)
            except Exception as e:
                _LOGGER.error("Failed to initialize async debug logger: %s", e)
        
        # Initialize investigation logger if investigation mode enabled
        if self.investigation_mode:
            try:
                from .investigation_logger import Key180InvestigationLogger
                self.investigation_logger = Key180InvestigationLogger(self.device_id, hass.config.config_dir)
                _LOGGER.info("🔍 INVESTIGATION MODE ENABLED: Key 180 comprehensive logging activated for device: %s", self.device_id)
                _LOGGER.info("📂 Investigation files will be saved to: %s", self.investigation_logger.get_investigation_directory())
            except Exception as e:
                _LOGGER.error("❌ Failed to initialize investigation logger: %s", e)
                self.investigation_mode = False  # Disable if can't initialize
        
        mode_description = []
        if self.debug_mode:
            mode_description.append("🐛 Debug")
        if self.investigation_mode:
            mode_description.append("🔍 Investigation")
        
        _LOGGER.info("🚀 Coordinator initialized for device: %s [%s]", self.device_id, " + ".join(mode_description) if mode_description else "Standard")
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Handle first refresh with accessory config and investigation setup."""
        try:
            # Initialize accessory configuration
            await self._initialize_accessory_config()
            
            # Initialize RestConnect (will fallback to basic login if REST not available)
            await self._initialize_rest_client()
            
            # Investigation mode first refresh
            if self.investigation_mode:
                await self._initialize_investigation_mode()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            
        except Exception as e:
            _LOGGER.error("❌ Failed during first refresh: %s", e)
            raise

    async def _initialize_investigation_mode(self) -> None:
        """Initialize investigation mode logging and setup."""
        if not self.investigation_logger:
            return
            
        try:
            self._debug_log("🔍 Initializing Investigation Mode for Key 180 analysis", "info", force=True)
            self._debug_log(f"📂 Investigation directory: {self.investigation_logger.get_investigation_directory()}", "info", force=True)
            self._debug_log(f"🔬 Session ID: {self.investigation_logger.get_session_id()}", "info", force=True)
            self._debug_log("🎯 TARGET: Key 180 comprehensive byte-by-byte analysis", "info", force=True)
            self._debug_log("📊 GOAL: Detect accessory wear changes between cleaning cycles", "info", force=True)
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize investigation mode: {e}", "error", force=True)

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

    async def _initialize_rest_client(self) -> None:
        """Initialize the RestConnect client with fallback to basic login."""
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
        
        # In investigation mode, log more frequently
        if self.investigation_mode:
            # Log every update for first 10 updates, then every minute
            if self.update_count <= 10:
                return True
            elif current_time - self.last_detailed_log >= 60:  # Every minute in investigation mode
                self.last_detailed_log = current_time
                return True
        else:
            # Standard mode - first update and every 10 minutes
            if self.update_count <= self.first_few_updates:
                return True
            elif current_time - self.last_detailed_log >= self.detailed_log_interval:
                self.last_detailed_log = current_time
                return True
        
        return False

    def _debug_log(self, message: str, level: str = "debug", force: bool = False):
        """Log to separate file if available, otherwise to main log."""
        # Log if forced, or if in detailed logging mode, or if investigation mode
        should_log = force or self._should_do_detailed_logging() or self.investigation_mode
        
        if not should_log:
            return
            
        if self.debug_logger:
            if level == "info":
                self.debug_logger.info(message)
            elif level == "warning":
                self.debug_logger.warning(message)
            elif level == "error":
                self.debug_logger.error(message)
            else:
                self.debug_logger.debug(message)
        elif self.debug_mode or self.investigation_mode:
            if level == "info":
                _LOGGER.info("[DEBUG] %s", message)
            elif level == "warning":
                _LOGGER.warning("[DEBUG] %s", message)
            elif level == "error":
                _LOGGER.error("[DEBUG] %s", message)
            else:
                _LOGGER.debug("[DEBUG] %s", message)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy API with Investigation Mode support."""
        try:
            self.update_count += 1
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                mode_indicators = []
                if self.investigation_mode:
                    mode_indicators.append("🔍 INVESTIGATION")
                if self.debug_mode:
                    mode_indicators.append("🐛 DEBUG")
                
                mode_str = " + ".join(mode_indicators) if mode_indicators else "STANDARD"
                
                self._debug_log("=" * 60, "info")
                self._debug_log(f"=== EUFY ROBOVAC UPDATE #{self.update_count} ({mode_str}) ===", "info")
                if self.investigation_mode:
                    self._debug_log("=== 🎯 Key 180 Investigation Mode Active ===", "info")
                self._debug_log("=" * 60, "info")
            
            # Fetch data using RestConnect (preferred) or fallback to basic login
            await self._fetch_eufy_data_with_rest()
            
            # INVESTIGATION MODE: Process Key 180 data immediately
            if self.investigation_mode and "180" in self.raw_data:
                await self._process_investigation_data()
            
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
                if self.investigation_mode:
                    investigation_status = f" [🔍 Key180: {'✅' if '180' in self.raw_data else '❌'}]"
                
                self._debug_log(f"✅ Update #{self.update_count} completed successfully{investigation_status}", "info")
            else:
                # Brief status update
                self._log_brief_status()
            
            return self.parsed_data
            
        except Exception as err:
            self._consecutive_failures += 1
            error_msg = f"❌ Update #{self.update_count} failed: {err}"
            self._debug_log(error_msg, "error", force=True)
            self._debug_log(f"🔄 Consecutive failures: {self._consecutive_failures}", "error", force=True)
            
            if self._consecutive_failures >= 3:
                _LOGGER.error("Multiple consecutive failures: %s", err)
            
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def _fetch_eufy_data_with_rest(self) -> None:
        """FIXED: Fetch data from Eufy API using RestConnect (preferred) or basic login fallback."""
        try:
            data_source = "Unknown"
            
            # Try RestConnect first (if available)
            if self._rest_client:
                try:
                    self._debug_log("🌐 Attempting RestConnect data fetch...", "debug")
                    
                    # FIXED: Use correct RestConnect methods
                    await self._rest_client.updateDevice()  # This updates the device data
                    rest_data = self._rest_client.get_raw_data()  # This gets the raw data
                    
                    if rest_data:
                        self.raw_data = rest_data
                        data_source = "🌐 RestConnect Enhanced"
                        self._debug_log(f"✅ RestConnect fetch successful: {len(self.raw_data)} keys", "debug")
                    else:
                        raise Exception("RestConnect returned no data")
                        
                except Exception as rest_error:
                    self._debug_log(f"⚠️ RestConnect failed: {rest_error}, falling back to basic login", "warning")
                    self._rest_client = None  # Disable for this session
                    # Fall through to basic login
            
            # Use basic login (fallback or primary)
            if not self._rest_client or not self.raw_data:
                self._debug_log("📱 Using basic login for data fetch...", "debug")
                
                if not self._eufy_login:
                    raise Exception("No authentication method available")
                
                # FIXED: Use correct EufyLogin method
                device_data = await self._eufy_login.getMqttDevice(self.device_id)  # This gets device data
                
                if device_data and 'dps' in device_data:
                    self.raw_data = device_data['dps']  # Extract DPS data
                    data_source = "📱 Basic Login"
                    self._debug_log(f"✅ Basic login fetch successful: {len(self.raw_data)} keys", "debug")
                else:
                    raise Exception("Basic login returned no data")
            
            # Store data source for sensors
            self.parsed_data["data_source"] = data_source
            self.parsed_data["raw_keys_count"] = len(self.raw_data)
            self.parsed_data["last_update"] = time.time()
            self.parsed_data["update_count"] = self.update_count
            
            self._debug_log(f"📊 Data fetch completed via {data_source}: {len(self.raw_data)} keys", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ All data fetch methods failed: {e}", "error", force=True)
            raise

    async def _process_sensor_data(self) -> None:
        """Process raw data into sensor values."""
        try:
            self._debug_log("🔄 Processing sensor data...", "debug")
            
            # Process battery (Key 163) - NEW Android app source, 100% accurate
            if "163" in self.raw_data:
                try:
                    battery_raw = self.raw_data["163"]
                    if isinstance(battery_raw, (int, float)):
                        battery_level = max(0, min(100, int(battery_raw)))
                    else:
                        battery_level = int(str(battery_raw))
                    
                    self.parsed_data["battery"] = battery_level
                    self._debug_log(f"🔋 Battery: {battery_level}% (Key 163)", "debug")
                except Exception as e:
                    self._debug_log(f"⚠️ Battery processing error: {e}", "warning")
            
            # Process clean speed (Key 158)
            if "158" in self.raw_data:
                try:
                    speed_raw = self.raw_data["158"]
                    if isinstance(speed_raw, (int, float)):
                        speed_index = int(speed_raw)
                        if 0 <= speed_index < len(CLEAN_SPEED_NAMES):
                            clean_speed = CLEAN_SPEED_NAMES[speed_index]
                        else:
                            clean_speed = f"unknown_{speed_index}"
                    else:
                        clean_speed = str(speed_raw)
                    
                    self.parsed_data["clean_speed"] = clean_speed
                    self._debug_log(f"⚡ Clean Speed: {clean_speed} (Key 158)", "debug")
                except Exception as e:
                    self._debug_log(f"⚠️ Clean speed processing error: {e}", "warning")
            
            # Process work status (Key 153)
            if "153" in self.raw_data:
                try:
                    status_raw = self.raw_data["153"]
                    if isinstance(status_raw, (int, float)):
                        status_code = int(status_raw)
                        work_status = WORK_STATUS_MAP.get(status_code, f"unknown_{status_code}")
                    else:
                        work_status = str(status_raw)
                    
                    self.parsed_data["work_status"] = work_status
                    self._debug_log(f"🔧 Work Status: {work_status} (Key 153)", "debug")
                except Exception as e:
                    self._debug_log(f"⚠️ Work status processing error: {e}", "warning")
            
            # Track monitored keys
            found_keys = []
            missing_keys = []
            
            for key in ALL_MONITORED_KEYS:
                if key in self.raw_data:
                    found_keys.append(key)
                else:
                    missing_keys.append(key)
            
            self.parsed_data["monitored_keys_found"] = found_keys
            self.parsed_data["monitored_keys_missing"] = missing_keys
            
            coverage = len(found_keys) / len(ALL_MONITORED_KEYS) * 100 if ALL_MONITORED_KEYS else 0
            self._debug_log(f"📊 Key coverage: {len(found_keys)}/{len(ALL_MONITORED_KEYS)} ({coverage:.1f}%)", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Sensor data processing error: {e}", "error", force=True)

    async def _process_accessory_data(self) -> None:
        """Process accessory data from configuration and detected values."""
        try:
            self._debug_log("🔧 Processing accessory data...", "debug")
            
            accessory_data = {}
            changes_detected = False
            
            # Process each configured accessory sensor
            for sensor_id, sensor_config in self.accessory_sensors.items():
                try:
                    key = sensor_config.get("key")
                    byte_position = sensor_config.get("byte_position")
                    
                    # Get the raw data for this key
                    if key in self.raw_data:
                        raw_value = self.raw_data[key]
                        detected_value = None
                        
                        # Try to extract byte value if it's base64 data
                        if isinstance(raw_value, str) and len(raw_value) > 10:
                            try:
                                # Decode base64 and extract byte
                                binary_data = base64.b64decode(raw_value)
                                if byte_position < len(binary_data):
                                    byte_value = binary_data[byte_position]
                                    
                                    # Only consider as percentage if in valid range
                                    if 1 <= byte_value <= 100:
                                        detected_value = byte_value
                                        
                            except Exception as decode_error:
                                self._debug_log(f"⚠️ Failed to decode {sensor_id} byte data: {decode_error}", "warning")
                        
                        # Store accessory data
                        accessory_data[sensor_id] = {
                            "configured_life": sensor_config.get("current_life_remaining", 100),
                            "detected_value": detected_value,
                            "hours_remaining": sensor_config.get("hours_remaining", 0),
                            "max_hours": sensor_config.get("max_life_hours", 0),
                            "threshold": sensor_config.get("replacement_threshold", 10),
                            "enabled": sensor_config.get("enabled", True),
                            "key": key,
                            "byte_position": byte_position,
                            "notes": sensor_config.get("notes", ""),
                            "last_updated": sensor_config.get("last_updated")
                        }
                        
                        # Check for changes (simple change detection)
                        previous = self.previous_accessory_data.get(sensor_id, {})
                        current_detected = detected_value
                        previous_detected = previous.get("detected_value")
                        
                        if current_detected != previous_detected:
                            changes_detected = True
                            self._debug_log(f"🔄 {sensor_config['name']} changed: {previous_detected} → {current_detected}", "info")
                        
                        self._debug_log(f"📍 {sensor_config['name']}: {detected_value}% detected, {sensor_config.get('current_life_remaining')}% configured", "debug")
                        
                    else:
                        # Key not available in current data
                        accessory_data[sensor_id] = {
                            "configured_life": sensor_config.get("current_life_remaining", 100),
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
                self._debug_log("🎯 Accessory changes detected - logged for investigation", "info")
            
            self._debug_log(f"✅ Processed {len(accessory_data)} accessory sensors", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Accessory data processing error: {e}", "error", force=True)
            self.parsed_data["accessory_sensors"] = {}

    def _log_brief_status(self) -> None:
        """Log a brief status update between detailed logs."""
        try:
            current_time = time.time()
            
            # Only log brief status every minute to avoid spam
            if current_time - self._last_logged_status < self._quiet_log_interval:
                self._quiet_updates_count += 1
                return
            
            # Create brief status
            battery = self.parsed_data.get("battery", "?")
            speed = self.parsed_data.get("clean_speed", "?")
            found_keys = len(self.parsed_data.get("monitored_keys_found", []))
            total_keys = len(self.raw_data)
            accessories = len(self.parsed_data.get("accessory_sensors", {}))
            data_source = self.parsed_data.get("data_source", "Unknown")
            
            # Data source emoji
            source_emoji = "🌐" if "RestConnect" in data_source else "📱"
            investigation_emoji = " 🔍" if self.investigation_mode and "180" in self.raw_data else ""
            
            brief_msg = f"Update #{self.update_count}: {source_emoji} Battery={battery}%, Speed={speed}, Keys={found_keys}/{len(ALL_MONITORED_KEYS)}, Total={total_keys}, Accessories={accessories}{investigation_emoji}"
            
            if self._quiet_updates_count > 0:
                brief_msg += f" (+ {self._quiet_updates_count} quiet updates)"
            
            self._debug_log(brief_msg, "info")
            
            # Reset quiet counter
            self._quiet_updates_count = 0
            self._last_logged_status = current_time
            
        except Exception as e:
            self._debug_log(f"⚠️ Brief status error: {e}", "warning")

    async def _process_investigation_data(self) -> None:
        """Process Key 180 data for investigation mode."""
        if not self.investigation_logger or "180" not in self.raw_data:
            return
            
        try:
            key180_data = self.raw_data["180"]
            
            # Log the Key 180 data with comprehensive analysis
            log_phase = "monitoring"
            
            # Auto-detect cleaning phases (basic detection based on other keys)
            if not self.baseline_captured:
                log_phase = "baseline"
            elif self._detect_cleaning_cycle_end():
                log_phase = "post_cleaning"
            
            # Log the data
            result_file = await self.investigation_logger.log_key180_data(
                self.raw_data, log_phase
            )
            
            if result_file:
                self._debug_log(f"🔍 Investigation: Key 180 {log_phase} data logged to {Path(result_file).name}", "info")
            
            # Update tracking
            if log_phase == "baseline":
                self.baseline_captured = True
                self._debug_log("🎯 Investigation: Baseline captured successfully", "info")
            elif log_phase == "post_cleaning":
                self._debug_log("🎯 Investigation: Post-cleaning data captured", "info")
            
            # Track changes
            if self.last_key180_data and self.last_key180_data != key180_data:
                self._debug_log("🔄 Investigation: Key 180 data changed since last update", "info")
            
            self.last_key180_data = key180_data
            
        except Exception as e:
            self._debug_log(f"❌ Investigation processing error: {e}", "error", force=True)

    def _detect_cleaning_cycle_end(self) -> bool:
        """Simple detection of cleaning cycle end based on work status."""
        try:
            # Check if work status indicates end of cleaning
            work_status_raw = self.raw_data.get("153")
            if work_status_raw:
                # If we can decode work status and it's "go_home" or "charging"
                # after a previous cleaning state, consider it end of cycle
                # This is a basic implementation - could be enhanced
                pass
            
            # For now, return False - user will manually trigger phases
            return False
            
        except Exception:
            return False

    def get_rest_connection_info(self) -> Dict[str, Any]:
        """Get RestConnect connection information for status sensor."""
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

    async def capture_investigation_baseline(self) -> str:
        """Manually capture baseline for investigation."""
        if not self.investigation_logger:
            return "Investigation mode not enabled"
            
        try:
            if "180" not in self.raw_data:
                return "No Key 180 data available"
            
            result_file = await self.investigation_logger.capture_baseline(self.raw_data)
            if result_file:
                self.baseline_captured = True
                return f"Baseline captured: {Path(result_file).name}"
            else:
                return "Failed to capture baseline"
                
        except Exception as e:
            return f"Error capturing baseline: {e}"

    async def capture_investigation_post_cleaning(self) -> str:
        """Manually capture post-cleaning data for investigation."""
        if not self.investigation_logger:
            return "Investigation mode not enabled"
            
        try:
            if "180" not in self.raw_data:
                return "No Key 180 data available"
            
            result_file = await self.investigation_logger.capture_post_cleaning(self.raw_data)
            if result_file:
                return f"Post-cleaning captured: {Path(result_file).name}"
            else:
                return "Failed to capture post-cleaning data"
                
        except Exception as e:
            return f"Error capturing post-cleaning: {e}"

    async def get_investigation_summary(self) -> str:
        """Get investigation session summary."""
        if not self.investigation_logger:
            return "Investigation mode not enabled"
            
        try:
            summary_file = await self.investigation_logger.generate_session_summary()
            return f"Session summary: {Path(summary_file).name}" if summary_file else "Failed to generate summary"
            
        except Exception as e:
            return f"Error generating summary: {e}"

    def get_investigation_status(self) -> Dict[str, Any]:
        """Get current investigation status."""
        if not self.investigation_mode:
            return {"enabled": False, "status": "Investigation mode disabled"}
            
        return {
            "enabled": True,
            "baseline_captured": self.baseline_captured,
            "session_id": self.investigation_logger.get_session_id() if self.investigation_logger else None,
            "investigation_directory": self.investigation_logger.get_investigation_directory() if self.investigation_logger else None,
            "key180_available": "180" in self.raw_data,
            "update_count": self.update_count,
            "last_key180_data_length": len(self.last_key180_data) if self.last_key180_data else 0
        }

    async def async_shutdown(self):
        """Shutdown the coordinator with investigation cleanup."""
        self._debug_log("🛑 Coordinator shutdown", "info", force=True)
        
        # Investigation mode cleanup
        if self.investigation_mode and self.investigation_logger:
            try:
                summary_file = await self.investigation_logger.generate_session_summary()
                self._debug_log(f"🔍 Investigation session summary saved: {Path(summary_file).name if summary_file else 'Failed'}", "info", force=True)
            except Exception as e:
                self._debug_log(f"❌ Error creating investigation summary: {e}", "error", force=True)
        
        # Shutdown RestConnect client
        if self._rest_client:
            try:
                await self._rest_client.stop_polling()
                self._debug_log("✅ RestConnect client disconnected", "info", force=True)
            except Exception as e:
                self._debug_log(f"❌ Error disconnecting RestConnect: {e}", "error", force=True)
        
        # Shutdown EufyLogin
        if self._eufy_login:
            try:
                # EufyLogin doesn't have disconnect method - just clean references
                self._eufy_login = None
                self._debug_log("✅ EufyLogin disconnected", "info", force=True)
            except Exception as e:
                self._debug_log(f"❌ Error disconnecting EufyLogin: {e}", "error", force=True)
        
        # Shutdown debug logger
        if self.debug_logger and hasattr(self.debug_logger, 'stop'):
            try:
                await self.debug_logger.stop()
                self._debug_log("✅ Debug logger stopped", "info", force=True)
            except Exception as e:
                self._debug_log(f"❌ Error stopping debug logger: {e}", "error", force=True)
        
        self._debug_log("🛑 Coordinator shutdown completed", "info", force=True)