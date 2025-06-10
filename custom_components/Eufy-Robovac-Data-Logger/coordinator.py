"""Data update coordinator for Eufy Robovac Data Logger integration."""
import asyncio
import logging
import time
from datetime import timedelta
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, MONITORED_KEYS, CONF_DEBUG_MODE

_LOGGER = logging.getLogger(__name__)


class EufyX10DebugCoordinator(DataUpdateCoordinator):
    """Eufy X10 Debugging data coordinator."""

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
        
        # Initialize async debug logger
        self.debug_logger = None
        if self.debug_mode:
            try:
                # Import the async logger
                from .async_debug_logger import AsyncEufyDebugLogger
                self.debug_logger = AsyncEufyDebugLogger(self.device_id, hass.config.config_dir)
                _LOGGER.info("🚀 DEBUG MODE: Coordinator initialized with 5-minute interval logging for device: %s", self.device_id)
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
            water_tank = self.parsed_data.get('water_tank', 'N/A')
            work_status = self.parsed_data.get('work_status', 'N/A')
            keys_found = len(self.parsed_data.get('monitored_keys_found', []))
            total_keys = len(self.raw_data)
            
            brief_msg = (f"Update #{self.update_count}: Battery={battery}%, "
                        f"Water={water_tank}%, Status={work_status}, "
                        f"Keys={keys_found}/{len(MONITORED_KEYS)}, Total={total_keys}")
            
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
            
            # Get device data
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
                        self.raw_data.update(dps_data)
                        
                        # Log raw data to separate file (only during detailed logging)
                        if do_detailed and self.debug_logger:
                            self.debug_logger.log_raw_data(dps_data)
                    else:
                        self._debug_log("⚠️ No DPS data found for device", "warning", force=True)
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
            raise

    async def _process_sensor_data(self):
        """Process raw data into sensor values."""
        do_detailed = self._should_do_detailed_logging()
        
        if do_detailed:
            self._debug_log("🔧 Processing sensor data...", "info")
        
        # Process the data
        self.parsed_data = {
            "device_id": self.device_id,
            "battery": self._extract_battery(),
            "water_tank": self._extract_water_tank(),
            "clean_speed": self._extract_clean_speed(),
            "work_status": self._extract_work_status(),
            "play_pause": self._extract_play_pause(),
            "raw_keys": list(self.raw_data.keys()),
            "monitored_keys_found": [k for k in MONITORED_KEYS if k in self.raw_data],
            "monitored_keys_missing": [k for k in MONITORED_KEYS if k not in self.raw_data],
            "last_update": time.time(),
            "update_count": self.update_count,
            "consecutive_failures": self._consecutive_failures,
        }
        
        # Detailed processing summary (only during detailed logging)
        if do_detailed:
            self._debug_log("📊 DETAILED DATA PROCESSED:", "info")
            self._debug_log(f"   🔋 Battery: {self.parsed_data['battery']}", "info")
            self._debug_log(f"   💧 Water Tank: {self.parsed_data['water_tank']}", "info")
            self._debug_log(f"   🤖 Work Status: {self.parsed_data['work_status']}", "info")
            self._debug_log(f"   ⚡ Clean Speed: {self.parsed_data['clean_speed']}", "info")
            self._debug_log(f"   ⏯️ Play/Pause: {self.parsed_data['play_pause']}", "info")
            self._debug_log(f"   🔑 Keys Found: {self.parsed_data['monitored_keys_found']}", "info")
            self._debug_log(f"   ❌ Keys Missing: {self.parsed_data['monitored_keys_missing']}", "info")
            self._debug_log(f"   📊 Total Raw Keys: {len(self.parsed_data['raw_keys'])}", "info")
            
            # Log monitoring status to separate file
            if self.debug_logger:
                self.debug_logger.log_monitored_keys_status(
                    self.parsed_data['monitored_keys_found'],
                    self.parsed_data['monitored_keys_missing']
                )

    def _extract_battery(self) -> Optional[int]:
        """Extract battery from Key 163."""
        if "163" in self.raw_data:
            try:
                battery_value = int(self.raw_data["163"])
                if self._should_do_detailed_logging():
                    self._debug_log(f"🔋 Battery extracted: {battery_value}% from key 163")
                return battery_value
            except (ValueError, TypeError) as e:
                self._debug_log(f"⚠️ Failed to parse battery from key 163: {e}", "warning", force=True)
        return None

    def _extract_water_tank(self) -> Optional[int]:
        """Extract water tank from Key 167."""
        if "167" in self.raw_data:
            try:
                import base64
                base64_data = self.raw_data["167"]
                if isinstance(base64_data, str):
                    binary_data = base64.b64decode(base64_data)
                    if len(binary_data) > 4:
                        raw_value = binary_data[4]
                        water_level = min(100, int((raw_value * 100) / 255))
                        
                        if self._should_do_detailed_logging():
                            self._debug_log(f"💧 Water tank extracted: {water_level}% from key 167 byte 4")
                            
                            # Log detailed byte analysis to separate file
                            if self.debug_logger:
                                self.debug_logger.log_byte_analysis("167", base64_data)
                        
                        return water_level
            except Exception as e:
                self._debug_log(f"⚠️ Failed to parse water tank from key 167: {e}", "warning", force=True)
        return None

    def _extract_clean_speed(self) -> Optional[str]:
        """Extract clean speed from Key 158."""
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

    def _extract_work_status(self) -> Optional[str]:
        """Extract work status from Key 153 - handles base64 data."""
        if "153" in self.raw_data:
            try:
                raw_value = self.raw_data["153"]
                
                if isinstance(raw_value, str):
                    try:
                        import base64
                        binary_data = base64.b64decode(raw_value)
                        if len(binary_data) > 0:
                            status_code = binary_data[0]
                            
                            # Log detailed analysis to separate file (only during detailed logging)
                            if self._should_do_detailed_logging() and self.debug_logger:
                                self.debug_logger.log_byte_analysis("153", raw_value)
                        else:
                            return None
                    except:
                        status_code = int(raw_value)
                else:
                    status_code = int(raw_value)
                
                from .const import WORK_STATUS_MAP
                status_name = WORK_STATUS_MAP.get(status_code)
                if status_name:
                    if self._should_do_detailed_logging():
                        self._debug_log(f"🤖 Work status extracted: {status_name} from key 153")
                else:
                    # Always log unknown status codes as they're important
                    self._debug_log(f"🤖 Unknown work status code: {status_code} from key 153", "warning", force=True)
                return status_name
                
            except (ValueError, TypeError) as e:
                # Only log parsing errors during detailed logging to reduce spam
                if self._should_do_detailed_logging():
                    self._debug_log(f"⚠️ Failed to parse work status from key 153: {e}", "warning")
        return None

    def _extract_play_pause(self) -> Optional[bool]:
        """Extract play/pause from Key 152 - handles base64 data."""
        if "152" in self.raw_data:
            try:
                raw_value = self.raw_data["152"]
                
                if isinstance(raw_value, str):
                    try:
                        import base64
                        binary_data = base64.b64decode(raw_value)
                        if len(binary_data) > 0:
                            play_pause_state = bool(binary_data[0])
                        else:
                            return None
                    except:
                        play_pause_state = raw_value.lower() in ('true', '1', 'yes', 'on')
                else:
                    play_pause_state = bool(raw_value)
                
                if self._should_do_detailed_logging():
                    self._debug_log(f"⏯️ Play/pause extracted: {play_pause_state} from key 152")
                return play_pause_state
                
            except (ValueError, TypeError) as e:
                self._debug_log(f"⚠️ Failed to parse play/pause from key 152: {e}", "warning", force=True)
        return None

    async def async_shutdown(self):
        """Shutdown the coordinator."""
        self._debug_log("🛑 Coordinator shutdown", "info", force=True)
        
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
        
        # Stop the async debug logger
        if self.debug_logger:
            await self.debug_logger.stop()
        
        self._debug_log("🏁 Coordinator shutdown complete", "info", force=True)