"""Data update coordinator for Eufy Robovac Data Logger integration with Accessory Config Manager."""
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict, Optional
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, MONITORED_KEYS, CONF_DEBUG_MODE
from .accessory_config_manager import AccessoryConfigManager

_LOGGER = logging.getLogger(__name__)


class EufyX10DebugCoordinator(DataUpdateCoordinator):
    """Eufy X10 Debugging data coordinator with accessory config management."""

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
        
        # Store raw data for debugging
        self.raw_data: Dict[str, Any] = {}
        self.parsed_data: Dict[str, Any] = {}
        self.last_update: Optional[float] = None
        self.update_count = 0
        
        # Logging control - detailed log every 5 minutes (300 seconds)
        self.detailed_log_interval = 300  # 5 minutes in seconds
        self.last_detailed_log = 0
        self.first_few_updates = 3  # Always log first 3 updates in detail
        
        # Connection tracking
        self._eufy_login = None
        self._last_successful_update = None
        self._consecutive_failures = 0
        
        # Initialize AccessoryConfigManager
        integration_dir = Path(__file__).parent
        self.accessory_manager = AccessoryConfigManager(str(integration_dir), self.device_id)
        self.accessory_sensors = {}
        self.previous_accessory_data = {}
        
        # Initialize async debug logger
        self.debug_logger = None
        if self.debug_mode:
            try:
                # Import the async logger
                from .async_debug_logger import AsyncEufyDebugLogger
                self.debug_logger = AsyncEufyDebugLogger(self.device_id, hass.config.config_dir)
                _LOGGER.info("🚀 DEBUG MODE: Coordinator initialized with accessory config management for device: %s", self.device_id)
            except Exception as e:
                _LOGGER.error("Failed to initialize async debug logger: %s", e)
                _LOGGER.info("🚀 DEBUG MODE: Coordinator initialized (file logging disabled) for device: %s", self.device_id)
        else:
            _LOGGER.info("🚀 Coordinator initialized for device: %s", self.device_id)
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.device_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_config_entry_first_refresh(self) -> None:
        """Handle first refresh with accessory config setup."""
        try:
            # Initialize accessory configuration
            await self._initialize_accessory_config()
            
            # Call parent first refresh
            await super().async_config_entry_first_refresh()
            
        except Exception as e:
            _LOGGER.error("❌ Failed during first refresh with accessory config: %s", e)
            raise

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
            # Don't raise - continue without accessory config if needed
            self.accessory_sensors = {}

    def _should_do_detailed_logging(self) -> bool:
        """Determine if we should do detailed logging this update."""
        current_time = time.time()
        
        # Always log first few updates
        if self.update_count <= self.first_few_updates:
            return True
        
        # Log every 5 minutes after that
        if current_time - self.last_detailed_log >= self.detailed_log_interval:
            self.last_detailed_log = current_time
            return True
        
        return False

    def _debug_log(self, message: str, level: str = "debug", force: bool = False):
        """Log to separate file if available, otherwise to main log."""
        # Only log if it's forced (errors) or if we're in detailed logging mode
        if not force and not self._should_do_detailed_logging():
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
        elif self.debug_mode:
            if level == "info":
                _LOGGER.info("[DEBUG] %s", message)
            elif level == "warning":
                _LOGGER.warning("[DEBUG] %s", message)
            elif level == "error":
                _LOGGER.error("[DEBUG] %s", message)
            else:
                _LOGGER.debug("[DEBUG] %s", message)

    def _log_brief_status(self):
        """Log a brief status update (used for non-detailed updates)."""
        if self.debug_logger:
            battery = self.parsed_data.get('battery', 'N/A')
            clean_speed = self.parsed_data.get('clean_speed', 'N/A')
            keys_found = len(self.parsed_data.get('monitored_keys_found', []))
            total_keys = len(self.raw_data)
            accessories_tracked = len([a for a in self.parsed_data.get('accessory_sensors', {}).values() if a.get('enabled')])
            
            brief_msg = (f"Update #{self.update_count}: Battery={battery}%, "
                        f"Speed={clean_speed}, Keys={keys_found}/{len(MONITORED_KEYS)}, "
                        f"Total={total_keys}, Accessories={accessories_tracked}")
            
            self.debug_logger.info(brief_msg)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from Eufy API."""
        try:
            self.update_count += 1
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                self._debug_log("=" * 60, "info")
                self._debug_log(f"=== EUFY X10 DETAILED UPDATE #{self.update_count} ===", "info")
                self._debug_log(f"=== Next detailed log in {self.detailed_log_interval/60:.1f} minutes ===", "info")
                self._debug_log("=" * 60, "info")
            
            # Fetch real data from Eufy API
            await self._fetch_eufy_data()
            
            # Process the data
            await self._process_sensor_data()
            
            # Process accessory data and check for changes
            await self._process_accessory_data()
            
            # Reset consecutive failures on success
            self._consecutive_failures = 0
            self._last_successful_update = time.time()
            
            self.last_update = time.time()
            
            if do_detailed:
                self._debug_log(f"✅ Detailed update #{self.update_count} completed successfully", "info")
            else:
                # Brief status update
                self._log_brief_status()
            
            return self.parsed_data
            
        except Exception as err:
            self._consecutive_failures += 1
            error_msg = f"❌ Update #{self.update_count} failed: {err}"
            self._debug_log(error_msg, "error", force=True)  # Always log errors
            self._debug_log(f"🔄 Consecutive failures: {self._consecutive_failures}", "error", force=True)
            
            # Only log to main HA log if it's a serious issue
            if self._consecutive_failures >= 3:
                _LOGGER.error("Multiple consecutive failures: %s", err)
            
            raise UpdateFailed(f"Error communicating with API: {err}")

    async def _fetch_eufy_data(self):
        """Fetch data from the Eufy API."""
        try:
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                self._debug_log("🔄 Fetching data from Eufy API...", "info")
            
            # Import here to avoid circular imports
            from .controllers.login import EufyLogin
            
            # Create login instance if not exists
            if not self._eufy_login:
                self._eufy_login = EufyLogin(
                    username=self.username,
                    password=self.password,
                    openudid=self.openudid
                )
            
            # Get device data from real API
            devices = await self._eufy_login.init()
            
            if devices:
                if do_detailed:
                    self._debug_log(f"✅ API data fetch successful - {len(devices)} devices found", "info")
                
                # Find our specific device
                target_device = None
                for device in devices:
                    if device.get('deviceId') == self.device_id:
                        target_device = device
                        break
                
                if target_device:
                    # Get DPS data from our device
                    dps_data = target_device.get('dps', {})
                    if dps_data:
                        if do_detailed:
                            self._debug_log(f"📊 DPS data keys found: {list(dps_data.keys())}", "info")
                        self.raw_data = dps_data  # Use real data only
                        
                        # Log raw data to separate file (only during detailed logging)
                        if do_detailed and self.debug_logger:
                            self.debug_logger.log_raw_data(dps_data)
                    else:
                        self._debug_log("⚠️ No DPS data found for device", "warning", force=True)
                        # Clear raw data if no DPS data available
                        self.raw_data = {}
                else:
                    error_msg = f"Target device {self.device_id} not found in device list"
                    self._debug_log(f"❌ {error_msg}", "error", force=True)
                    raise UpdateFailed(error_msg)
            else:
                error_msg = "No devices returned from API"
                self._debug_log(f"❌ {error_msg}", "error", force=True)
                raise UpdateFailed(error_msg)
                
        except Exception as e:
            self._debug_log(f"❌ Failed to fetch Eufy data: {e}", "error", force=True)
            # Clear raw data on API failure
            self.raw_data = {}
            raise

    async def _process_sensor_data(self):
        """Process raw data into sensor values - CLEANED UP VERSION."""
        do_detailed = self._should_do_detailed_logging()
        
        if do_detailed:
            self._debug_log("🔧 Processing sensor data (cleaned version)...", "info")
        
        # Only process if we have raw data
        if not self.raw_data:
            self._debug_log("⚠️ No raw data available for processing", "warning", force=True)
            # Set basic structure with no sensor values
            self.parsed_data = {
                "device_id": self.device_id,
                "battery": None,
                "clean_speed": None,
                "raw_keys": [],
                "monitored_keys_found": [],
                "monitored_keys_missing": MONITORED_KEYS.copy(),
                "last_update": time.time(),
                "update_count": self.update_count,
                "consecutive_failures": self._consecutive_failures,
                "accessory_sensors": {},
            }
            return
        
        # Process the data with real values - REMOVED INCORRECT SENSORS
        self.parsed_data = {
            "device_id": self.device_id,
            "battery": self._extract_battery(),  # ✅ Keep - Key 163 works
            "clean_speed": self._extract_clean_speed(),  # ✅ Keep - Key 158 works
            # ❌ Removed water_tank - moved to JSON config for testing
            # ❌ Removed work_status - unknown source, unreliable
            # ❌ Removed play_pause - unknown source, unreliable
            "raw_keys": list(self.raw_data.keys()),
            "monitored_keys_found": [k for k in MONITORED_KEYS if k in self.raw_data],
            "monitored_keys_missing": [k for k in MONITORED_KEYS if k not in self.raw_data],
            "last_update": time.time(),
            "update_count": self.update_count,
            "consecutive_failures": self._consecutive_failures,
            "accessory_sensors": {},  # Will be populated by _process_accessory_data
        }
        
        # Detailed processing summary (only during detailed logging)
        if do_detailed:
            self._debug_log("📊 CLEANED SENSOR DATA PROCESSED:", "info")
            self._debug_log(f"   🔋 Battery: {self.parsed_data['battery']}", "info")
            self._debug_log(f"   ⚡ Clean Speed: {self.parsed_data['clean_speed']}", "info")
            self._debug_log(f"   🔑 Keys Found: {self.parsed_data['monitored_keys_found']}", "info")
            self._debug_log(f"   ❌ Keys Missing: {self.parsed_data['monitored_keys_missing']}", "info")
            self._debug_log(f"   📊 Total Raw Keys: {len(self.parsed_data['raw_keys'])}", "info")
            self._debug_log("   ⚠️ Removed unreliable sensors: work_status, play_pause", "info")
            self._debug_log("   🔄 Moved water_tank to JSON config for testing", "info")
            
            # Log monitoring status to separate file
            if self.debug_logger:
                self.debug_logger.log_monitored_keys_status(
                    self.parsed_data['monitored_keys_found'],
                    self.parsed_data['monitored_keys_missing']
                )

    async def _process_accessory_data(self):
        """Process accessory sensor data from JSON configuration."""
        try:
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                self._debug_log("🔧 Processing accessory sensors from JSON config...", "info")
            
            # Reload config to get any user updates
            self.accessory_sensors = await self.accessory_manager.get_enabled_sensors()
            
            accessory_data = {}
            changes_detected = []
            
            for sensor_id, sensor_config in self.accessory_sensors.items():
                key = sensor_config.get('key')
                byte_position = sensor_config.get('byte_position')
                expected_life = sensor_config.get('current_life_remaining', 100)
                
                # Extract current value from raw data
                current_value = await self._extract_accessory_value(key, byte_position, sensor_id)
                
                # Store accessory data
                accessory_data[sensor_id] = {
                    "name": sensor_config.get('name'),
                    "configured_life": expected_life,
                    "detected_value": current_value,
                    "hours_remaining": sensor_config.get('hours_remaining', 0),
                    "max_hours": sensor_config.get('max_life_hours', 0),
                    "threshold": sensor_config.get('replacement_threshold', 10),
                    "enabled": sensor_config.get('enabled', True),
                    "key": key,
                    "byte_position": byte_position,
                    "last_updated": sensor_config.get('last_updated'),
                    "notes": sensor_config.get('notes', ''),
                }
                
                # Check for changes if we have previous data
                if sensor_id in self.previous_accessory_data:
                    prev_value = self.previous_accessory_data[sensor_id].get('detected_value')
                    if prev_value is not None and current_value is not None and prev_value != current_value:
                        change_info = f"{sensor_config['name']}: {prev_value} → {current_value}"
                        changes_detected.append(change_info)
                        
                        if do_detailed:
                            self._debug_log(f"🎯 ACCESSORY CHANGE: {change_info}", "info")
            
            # Update parsed data
            self.parsed_data["accessory_sensors"] = accessory_data
            
            # Log detected changes
            if changes_detected and self.debug_logger:
                self.debug_logger.info("🔄 ACCESSORY CHANGES DETECTED:")
                for change in changes_detected:
                    self.debug_logger.info(f"   {change}")
            
            # Store current data for next comparison
            self.previous_accessory_data = accessory_data.copy()
            
            if do_detailed:
                self._debug_log(f"✅ Processed {len(accessory_data)} accessory sensors", "info")
                if changes_detected:
                    self._debug_log(f"🎯 Detected {len(changes_detected)} accessory changes", "info")
                    
        except Exception as e:
            self._debug_log(f"❌ Error processing accessory data: {e}", "error", force=True)
            # Set empty accessory data on error
            self.parsed_data["accessory_sensors"] = {}

    async def _extract_accessory_value(self, key: str, byte_position: int, sensor_id: str) -> Optional[int]:
        """Extract accessory value from specific key and byte position."""
        try:
            if key not in self.raw_data:
                return None
            
            raw_value = self.raw_data[key]
            
            # Handle base64 encoded data
            if isinstance(raw_value, str) and len(raw_value) > 10:
                try:
                    import base64
                    binary_data = base64.b64decode(raw_value)
                    
                    if byte_position < len(binary_data):
                        byte_value = binary_data[byte_position]
                        
                        # Convert to percentage (different methods for different sensors)
                        if sensor_id == "water_tank_level":
                            # Special handling for water tank - try different scaling
                            percentage = min(100, int((byte_value * 100) / 255))
                        else:
                            # For other accessories, assume direct percentage
                            percentage = min(100, max(0, byte_value))
                        
                        return percentage
                    else:
                        return None
                        
                except Exception as e:
                    self._debug_log(f"⚠️ Failed to decode {sensor_id} data: {e}", "warning")
                    return None
            
            # Handle direct integer values
            elif isinstance(raw_value, (int, float)):
                return min(100, max(0, int(raw_value)))
            
            return None
            
        except Exception as e:
            self._debug_log(f"❌ Error extracting {sensor_id}: {e}", "error")
            return None

    def _extract_battery(self) -> Optional[int]:
        """Extract battery from Key 163 - KEPT AS WORKING."""
        if "163" in self.raw_data:
            try:
                battery_value = int(self.raw_data["163"])
                if self._should_do_detailed_logging():
                    self._debug_log(f"🔋 Battery extracted: {battery_value}% from key 163")
                return battery_value
            except (ValueError, TypeError) as e:
                self._debug_log(f"⚠️ Failed to parse battery from key 163: {e}", "warning", force=True)
        return None

    def _extract_clean_speed(self) -> Optional[str]:
        """Extract clean speed from Key 158 - KEPT AS WORKING."""
        if "158" in self.raw_data:
            try:
                raw_value = self.raw_data["158"]
                
                # Handle both integer and base64 encoded values
                if isinstance(raw_value, str):
                    try:
                        import base64
                        binary_data = base64.b64decode(raw_value)
                        if len(binary_data) > 0:
                            speed_code = binary_data[0]
                        else:
                            return None
                    except:
                        speed_code = int(raw_value)
                else:
                    speed_code = int(raw_value)
                
                from .const import CLEAN_SPEED_NAMES
                if 0 <= speed_code < len(CLEAN_SPEED_NAMES):
                    speed_name = CLEAN_SPEED_NAMES[speed_code]
                    if self._should_do_detailed_logging():
                        self._debug_log(f"⚡ Clean speed extracted: {speed_name} from key 158")
                    return speed_name
                    
            except (ValueError, TypeError, IndexError) as e:
                self._debug_log(f"⚠️ Failed to parse clean speed from key 158: {e}", "warning", force=True)
        return None

    async def update_accessory_life(self, accessory_id: str, new_percentage: int, notes: str = None) -> bool:
        """Update accessory life percentage in the JSON configuration."""
        try:
            success = await self.accessory_manager.update_accessory_life(
                accessory_id, new_percentage, notes
            )
            
            if success:
                # Reload sensors to reflect changes
                self.accessory_sensors = await self.accessory_manager.get_enabled_sensors()
                self._debug_log(f"✅ Updated {accessory_id} to {new_percentage}%", "info", force=True)
            
            return success
            
        except Exception as e:
            self._debug_log(f"❌ Failed to update {accessory_id}: {e}", "error", force=True)
            return False

    async def get_accessory_config_path(self) -> str:
        """Get the path to the accessory configuration file."""
        return self.accessory_manager.get_config_file_path()

    async def validate_accessory_config(self) -> Dict[str, Any]:
        """Validate the current accessory configuration."""
        return await self.accessory_manager.validate_config()

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        self._debug_log("🛑 Coordinator shutdown", "info", force=True)
        
        # Save final accessory data if any changes detected
        if self.previous_accessory_data:
            try:
                self._debug_log("💾 Saving final accessory state...", "info", force=True)
                # Could implement auto-save of detected changes here
            except Exception as e:
                self._debug_log(f"⚠️ Failed to save final accessory state: {e}", "warning", force=True)
        
        if self._eufy_login and hasattr(self._eufy_login, 'eufyApi'):
            try:
                if hasattr(self._eufy_login.eufyApi, 'close'):
                    await self._eufy_login.eufyApi.close()
                self._debug_log("✅ Eufy API connection closed", "info", force=True)
            except Exception as e:
                self._debug_log(f"❌ Error closing Eufy API: {e}", "error", force=True)
        
        self._debug_log(f"📊 Final statistics: {self.update_count} updates processed", "info", force=True)
        if self._last_successful_update:
            self._debug_log(f"✅ Last successful update: {time.ctime(self._last_successful_update)}", "info", force=True)
        
        accessories_tracked = len(self.accessory_sensors)
        self._debug_log(f"🔧 Accessory sensors tracked: {accessories_tracked}", "info", force=True)
        
        # Stop the async debug logger
        if self.debug_logger:
            await self.debug_logger.stop()
        
        self._debug_log("🏁 Coordinator shutdown complete", "info", force=True)