"""Data update coordinator for Eufy Robovac Data Logger integration with Enhanced Smart Investigation Mode v3.0."""
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
    """Eufy Robovac Debugging data coordinator with RestConnect and Enhanced Smart Investigation Mode v3.0."""

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
        
        # NEW: Enhanced Smart Investigation Mode v3.0
        self.investigation_mode = entry.data.get("investigation_mode", False)
        
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
        self.accessory_manager = AccessoryConfigManager(str(integration_dir), self.device_id)
        self.accessory_sensors = {}
        self.previous_accessory_data = {}
        
        # NEW: Enhanced Smart Investigation Mode Components v3.0
        self.smart_investigation_logger = None
        self.last_key180_data = None
        self.cleaning_cycle_detected = False
        self.baseline_captured = False
        
        # Initialize debug logger and enhanced smart investigation logger
        self.debug_logger = None
        if self.debug_mode:
            try:
                from .async_debug_logger import AsyncEufyDebugLogger
                self.debug_logger = AsyncEufyDebugLogger(self.device_id, hass.config.config_dir)
                _LOGGER.info("🚀 DEBUG MODE: Coordinator initialized with RestConnect + enhanced smart investigation v3.0 for device: %s", self.device_id)
            except Exception as e:
                _LOGGER.error("Failed to initialize async debug logger: %s", e)
        
        # Initialize ENHANCED investigation logger v3.0 if investigation mode enabled
        if self.investigation_mode:
            try:
                from .enhanced_smart_investigation_logger import EnhancedSmartKey180InvestigationLogger
                self.smart_investigation_logger = EnhancedSmartKey180InvestigationLogger(
                    self.device_id, 
                    hass.config.config_dir,
                    str(integration_dir)  # NEW: Integration directory for sensors config access
                )
                _LOGGER.info("🔍 ENHANCED SMART INVESTIGATION MODE v3.0 ENABLED: Self-contained analysis with sensors config integration for device: %s", self.device_id)
                _LOGGER.info("📂 Investigation files: %s", self.smart_investigation_logger.get_investigation_directory())
                _LOGGER.info("🧠 Enhanced features: Sensors config integration, Position 15 focus, Android app comparison")
                _LOGGER.info("✨ v3.0 Features: Self-contained files, complete reference data, enhanced change detection")
            except Exception as e:
                _LOGGER.error("❌ Failed to initialize enhanced smart investigation logger v3.0: %s", e)
                self.investigation_mode = False  # Disable if can't initialize
        
        mode_description = []
        if self.debug_mode:
            mode_description.append("🐛 Debug")
        if self.investigation_mode:
            mode_description.append("🔍 Enhanced Smart Investigation v3.0")
        
        _LOGGER.info("🚀 Coordinator initialized for device: %s [%s]", self.device_id, " + ".join(mode_description) if mode_description else "Standard")
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Handle first refresh with accessory config and enhanced smart investigation setup v3.0."""
        try:
            # Initialize accessory configuration
            await self._initialize_accessory_config()
            
            # Initialize RestConnect (will fallback to basic login if REST not available)
            await self._initialize_rest_client()
            
            # Enhanced smart investigation mode v3.0 first refresh
            if self.investigation_mode:
                await self._initialize_enhanced_smart_investigation_mode()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            
        except Exception as e:
            _LOGGER.error("❌ Failed during first refresh: %s", e)
            raise

    async def _initialize_enhanced_smart_investigation_mode(self) -> None:
        """Initialize enhanced smart investigation mode v3.0 logging and setup."""
        if not self.smart_investigation_logger:
            return
            
        try:
            self._debug_log("🔍 Initializing Enhanced Smart Investigation Mode v3.0 for intelligent Key 180 analysis", "info", force=True)
            self._debug_log(f"📂 Investigation directory: {self.smart_investigation_logger.get_investigation_directory()}", "info", force=True)
            self._debug_log(f"🔬 Session ID: {self.smart_investigation_logger.get_session_id()}", "info", force=True)
            self._debug_log("🧠 ENHANCED FEATURES v3.0: Sensors config integration, self-contained files, Position 15 focus", "info", force=True)
            self._debug_log("🎯 TARGET: Key 180 enhanced analysis with Android app comparison and config validation", "info", force=True)
            self._debug_log("📊 EFFICIENCY: 80-90% file reduction with complete reference data in each file", "info", force=True)
            self._debug_log("✨ NEW v3.0: Complete sensors.json reference data included in every analysis file", "info", force=True)
            
        except Exception as e:
            self._debug_log(f"❌ Failed to initialize enhanced smart investigation mode v3.0: {e}", "error", force=True)

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
        
        # In investigation mode, log more frequently but smarter
        if self.investigation_mode:
            # Log every update for first 5 updates, then every 5 minutes
            if self.update_count <= 5:
                return True
            elif current_time - self.last_detailed_log >= 300:  # Every 5 minutes in investigation mode
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
        # Log if forced, or if in detailed logging mode, or if investigation mode and important
        should_log = force or self._should_do_detailed_logging() or (self.investigation_mode and level in ["info", "warning", "error"])
        
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
        """Fetch data from Eufy API with Enhanced Smart Investigation Mode v3.0 support."""
        try:
            self.update_count += 1
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                mode_indicators = []
                if self.investigation_mode:
                    mode_indicators.append("🔍 ENHANCED SMART INVESTIGATION v3.0")
                if self.debug_mode:
                    mode_indicators.append("🐛 DEBUG")
                
                mode_str = " + ".join(mode_indicators) if mode_indicators else "STANDARD"
                
                self._debug_log("=" * 60, "info")
                self._debug_log(f"=== EUFY ROBOVAC UPDATE #{self.update_count} ({mode_str}) ===", "info")
                if self.investigation_mode:
                    self._debug_log("=== ✨ Enhanced Smart Key 180 Investigation v3.0 Active ===", "info")
                self._debug_log("=" * 60, "info")
            
            # Fetch data using RestConnect (preferred) or fallback to basic login
            await self._fetch_eufy_data_with_rest()
            
            # ENHANCED SMART INVESTIGATION MODE v3.0: Process Key 180 data with sensors config integration
            if self.investigation_mode and "180" in self.raw_data:
                await self._process_enhanced_smart_investigation_data()
            
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
                    investigation_status = f" [✨ Enhanced v3.0: {smart_status['meaningful_logs']}/{smart_status['total_updates']} files, {smart_status['efficiency_percentage']:.1f}% efficient]"
                
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
        """Fetch data from Eufy API using RestConnect (preferred) or basic login fallback."""
        try:
            data_source = "Unknown"
            
            # Try RestConnect first (if available)
            if self._rest_client:
                try:
                    self._debug_log("🌐 Attempting RestConnect data fetch...", "debug")
                    
                    # Set detailed logging flag for RestConnect
                    if hasattr(self._rest_client, '_detailed_logging_enabled'):
                        self._rest_client._detailed_logging_enabled = self._should_do_detailed_logging()
                    
                    # Use correct RestConnect methods
                    await self._rest_client.updateDevice()
                    rest_data = self._rest_client.get_raw_data()
                    
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
                
                # Use correct EufyLogin method
                device_data = await self._eufy_login.getMqttDevice(self.device_id)
                
                if device_data and 'dps' in device_data:
                    self.raw_data = device_data['dps']
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
                    
                    # Store for enhanced smart investigation cleaning detection
                    if hasattr(self, '_last_work_status'):
                        if self._last_work_status != work_status:
                            self._debug_log(f"🔄 Work status changed: {self._last_work_status} → {work_status}", "info")
                    self._last_work_status = work_status
                    
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
                self._debug_log("🎯 Accessory changes detected - logged for enhanced investigation v3.0", "info")
            
            self._debug_log(f"✅ Processed {len(accessory_data)} accessory sensors", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Accessory data processing error: {e}", "error", force=True)
            self.parsed_data["accessory_sensors"] = {}

    async def _process_enhanced_smart_investigation_data(self) -> None:
        """Process Key 180 data using enhanced smart investigation logger v3.0."""
        if not self.smart_investigation_logger or "180" not in self.raw_data:
            return
            
        try:
            # Use enhanced smart logger v3.0 to process the update with sensors config integration
            result_file = await self.smart_investigation_logger.process_key180_update(self.raw_data)
            
            if result_file:
                filename = Path(result_file).name
                self._debug_log(f"✨ Enhanced Smart Investigation v3.0: Self-contained analysis file created: {filename}", "info")
                
                # Get enhanced smart status for logging
                smart_status = self.smart_investigation_logger.get_smart_status()
                efficiency = smart_status.get('efficiency_percentage', 0)
                self._debug_log(f"📊 Enhanced Stats v3.0: {smart_status['meaningful_logs']}/{smart_status['total_updates']} files ({efficiency:.1f}% efficient, sensors config integrated)", "debug")
            else:
                # No file created - either no change or duplicate
                smart_status = self.smart_investigation_logger.get_smart_status()
                if smart_status['total_updates'] % 10 == 0:  # Log efficiency every 10 updates
                    efficiency = smart_status.get('efficiency_percentage', 0)
                    self._debug_log(f"✨ Enhanced Smart Investigation v3.0: No change detected (Efficiency: {efficiency:.1f}%)", "debug")
            
        except Exception as e:
            self._debug_log(f"❌ Enhanced smart investigation v3.0 processing error: {e}", "error", force=True)

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
            total_keys = len(self.raw_data)
            accessories = len(self.parsed_data.get("accessory_sensors", {}))
            data_source = self.parsed_data.get("data_source", "Unknown")
            
            # Data source emoji
            source_emoji = "🌐" if "RestConnect" in data_source else "📱"
            
            # Enhanced smart investigation status v3.0
            investigation_emoji = ""
            if self.investigation_mode and self.smart_investigation_logger:
                smart_status = self.smart_investigation_logger.get_smart_status()
                efficiency = smart_status.get('efficiency_percentage', 0)
                investigation_emoji = f" ✨{efficiency:.0f}%"
            elif self.investigation_mode and "180" in self.raw_data:
                investigation_emoji = " 🔍"
            
            brief_msg = f"Update #{self.update_count}: {source_emoji} Battery={battery}%, Speed={speed}, Keys={found_keys}/{len(ALL_MONITORED_KEYS)}, Total={total_keys}, Accessories={accessories}{investigation_emoji}"
            
            if self._quiet_updates_count > 0:
                brief_msg += f" (+ {self._quiet_updates_count} quiet updates)"
            
            self._debug_log(brief_msg, "info")
            
            # Reset quiet counter
            self._quiet_updates_count = 0
            self._last_logged_status = current_time
            
        except Exception as e:
            self._debug_log(f"⚠️ Brief status error: {e}", "warning")

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
        """Manually capture baseline for enhanced smart investigation v3.0."""
        if not self.smart_investigation_logger:
            return "Enhanced Smart Investigation mode v3.0 not enabled"
            
        try:
            if "180" not in self.raw_data:
                return "No Key 180 data available"
            
            result_file = await self.smart_investigation_logger.capture_baseline(self.raw_data)
            if result_file:
                filename = Path(result_file).name
                self._debug_log(f"🎯 Manual enhanced baseline captured v3.0: {filename}", "info", force=True)
                return f"Enhanced smart baseline captured v3.0: {filename}"
            else:
                return "Failed to capture enhanced baseline"
                
        except Exception as e:
            return f"Error capturing enhanced baseline v3.0: {e}"

    async def capture_investigation_post_cleaning(self) -> str:
        """Manually capture post-cleaning data for enhanced smart investigation v3.0."""
        if not self.smart_investigation_logger:
            return "Enhanced Smart Investigation mode v3.0 not enabled"
            
        try:
            if "180" not in self.raw_data:
                return "No Key 180 data available"
            
            result_file = await self.smart_investigation_logger.capture_post_cleaning(self.raw_data)
            if result_file:
                filename = Path(result_file).name
                self._debug_log(f"📊 Manual enhanced post-cleaning captured v3.0: {filename}", "info", force=True)
                return f"Enhanced smart post-cleaning captured v3.0: {filename}"
            else:
                return "Failed to capture enhanced post-cleaning data"
                
        except Exception as e:
            return f"Error capturing enhanced post-cleaning v3.0: {e}"

    async def get_investigation_summary(self) -> str:
        """Get enhanced smart investigation session summary v3.0."""
        if not self.smart_investigation_logger:
            return "Enhanced Smart Investigation mode v3.0 not enabled"
            
        try:
            summary_file = await self.smart_investigation_logger.generate_session_summary()
            if summary_file:
                filename = Path(summary_file).name
                smart_status = self.smart_investigation_logger.get_smart_status()
                efficiency = smart_status.get('efficiency_percentage', 0)
                self._debug_log(f"📋 Enhanced smart session summary v3.0 created: {filename} (Efficiency: {efficiency:.1f}%)", "info", force=True)
                return f"Enhanced smart session summary v3.0: {filename}"
            else:
                return "Failed to generate enhanced summary"
                
        except Exception as e:
            return f"Error generating enhanced summary v3.0: {e}"

    def get_investigation_status(self) -> Dict[str, Any]:
        """Get current enhanced smart investigation status v3.0."""
        if not self.investigation_mode:
            return {"enabled": False, "status": "Enhanced Smart Investigation mode v3.0 disabled"}
        
        if not self.smart_investigation_logger:
            return {"enabled": True, "status": "Enhanced Smart Investigation logger v3.0 not initialized", "error": True}
            
        try:
            smart_status = self.smart_investigation_logger.get_smart_status()
            
            return {
                "enabled": True,
                "version": "3.0_enhanced",
                "mode": smart_status.get('mode', 'unknown'),
                "baseline_captured": smart_status.get('baseline_captured', False),
                "session_id": smart_status.get('session_id'),
                "investigation_directory": smart_status.get('investigation_directory'),
                "key180_available": "180" in self.raw_data,
                "update_count": self.update_count,
                "total_updates_received": smart_status.get('total_updates', 0),
                "meaningful_logs_created": smart_status.get('meaningful_logs', 0),
                "duplicates_skipped": smart_status.get('duplicates_skipped', 0),
                "efficiency_percentage": smart_status.get('efficiency_percentage', 0),
                "last_log_time": smart_status.get('last_log_time'),
                "sensors_config_integration": smart_status.get('sensors_config_integration', False),
                "enhanced_features_v3": [
                    "✨ Self-contained analysis files with complete reference data",
                    "🧠 Sensors.json config integration for Android app comparison",
                    "🎯 Position 15 focus for Brush Guard confirmation testing",
                    "🔍 Enhanced change detection with config validation",
                    "📊 Complete audit trail with sensors configuration",
                    "🗑️ Automatic duplicate prevention and file cleanup",
                    "📈 80-90% efficiency with intelligent logging decisions"
                ]
            }
            
        except Exception as e:
            return {
                "enabled": True,
                "status": f"Error getting enhanced smart status v3.0: {e}",
                "error": True
            }

    async def async_shutdown(self):
        """Shutdown the coordinator with enhanced smart investigation cleanup v3.0."""
        self._debug_log("🛑 Coordinator shutdown", "info", force=True)
        
        # Enhanced smart investigation mode cleanup v3.0
        if self.investigation_mode and self.smart_investigation_logger:
            try:
                summary_file = await self.smart_investigation_logger.generate_session_summary()
                if summary_file:
                    filename = Path(summary_file).name
                    smart_status = self.smart_investigation_logger.get_smart_status()
                    efficiency = smart_status.get('efficiency_percentage', 0)
                    self._debug_log(f"✨ Enhanced Smart Investigation v3.0 session summary saved: {filename} (Efficiency: {efficiency:.1f}%)", "info", force=True)
                else:
                    self._debug_log("❌ Failed to create enhanced smart investigation summary v3.0", "error", force=True)
            except Exception as e:
                self._debug_log(f"❌ Error creating enhanced smart investigation summary v3.0: {e}", "error", force=True)
        
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
        
        self._debug_log("🛑 Enhanced Smart Investigation Coordinator v3.0 shutdown completed", "info", force=True)