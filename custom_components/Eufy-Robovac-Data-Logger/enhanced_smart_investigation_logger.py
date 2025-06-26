"""Enhanced Smart Investigation Logger v4.1 for multi-key Eufy robovac data analysis with FIXED room cleaning completion detection."""
import json
import hashlib
import asyncio
import aiofiles
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import logging
import base64

_LOGGER = logging.getLogger(__name__)


class LoggingMode(Enum):
    """Logging modes for enhanced smart investigation."""
    BASELINE = "baseline"
    SMART_MONITORING = "smart_monitoring"
    POST_CLEANING = "post_cleaning"
    SESSION_SUMMARY = "session_summary"


class CleaningState(Enum):
    """Cleaning states for automatic completion detection."""
    UNKNOWN = "unknown"
    DOCKED = "docked"
    WASHING_MOPS = "washing_mops"
    CLEANING = "cleaning"
    GOING_HOME = "going_home"
    CHARGING = "charging"


class EnhancedSmartMultiKeyInvestigationLogger:
    """Enhanced Smart Investigation Logger v4.1 with FIXED room cleaning completion detection."""

    def __init__(self, device_id: str, hass_config_dir: str, integration_dir: str, monitored_keys: List[str]):
        """Initialize the enhanced smart multi-key investigation logger."""
        self.device_id = device_id
        self.hass_config_dir = Path(hass_config_dir)
        self.integration_dir = Path(integration_dir)
        self.monitored_keys = monitored_keys
        
        # Investigation directory setup
        self.investigation_dir = self.hass_config_dir / "eufy_investigation" / self.device_id
        self.investigation_dir.mkdir(parents=True, exist_ok=True)
        
        # Session management
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Smart logging state tracking
        self.baseline_captured = False
        self.current_mode = LoggingMode.SMART_MONITORING
        self.total_updates_received = 0
        self.meaningful_logs_created = 0
        self.duplicates_skipped = 0
        
        # Multi-key change tracking
        self.last_multi_key_hash = None
        self.last_logged_data = {}
        self.last_log_time = None
        self.key_last_values = {}
        self.key_change_counts = {key: 0 for key in self.monitored_keys}
        
        # FIXED: Enhanced cleaning state tracking for ROOM CLEANING completion detection
        self.cleaning_state = CleaningState.UNKNOWN
        self.previous_cleaning_state = CleaningState.UNKNOWN
        self.cleaning_start_time = None
        self.room_cleaning_end_time = None  # NEW: Track when room cleaning specifically ends
        self.docked_confirmation_time = None
        self.cleaning_cycle_active = False
        self.room_cleaning_completed = False  # NEW: Track room cleaning vs full cycle
        self.post_cleaning_captured_this_cycle = False
        
        # FIXED: Detection settings for room cleaning completion
        self.min_room_cleaning_duration_minutes = 5   # Room clean must be at least 5 minutes
        self.max_reasonable_room_clean_minutes = 90   # Room clean shouldn't exceed 90 minutes
        self.docked_confirmation_seconds = 30         # Must stay docked for 30 seconds
        self.post_cleaning_window_minutes = 5         # Capture within 5 minutes
        
        # Smart logging configuration
        self.min_log_interval_seconds = 60
        self.significant_change_threshold = 2
        self.accessory_value_range = (0, 100)
        
        # File management
        self.max_monitoring_files = 10
        
        _LOGGER.info("🔍 Enhanced Smart Multi-Key Investigation Logger v4.1 initialized")
        _LOGGER.info("🔧 FIXED: Room cleaning completion detection (ignores mop wash/dry)")
        _LOGGER.info(f"📁 Investigation directory: {self.investigation_dir}")
        _LOGGER.info(f"🗂️ Monitoring {len(self.monitored_keys)} keys")
        _LOGGER.info(f"🔬 Session ID: {self.session_id}")
        _LOGGER.info(f"⏱️ Room clean detection: {self.min_room_cleaning_duration_minutes}-{self.max_reasonable_room_clean_minutes} minutes + {self.docked_confirmation_seconds}s dock confirm")

    async def initialize(self) -> None:
        """Initialize the investigation logger."""
        try:
            self.investigation_dir.mkdir(parents=True, exist_ok=True)
            await self._load_session_state()
            
            _LOGGER.info("✅ Enhanced Smart Multi-Key Investigation Logger v4.1 initialized successfully")
            _LOGGER.info(f"📂 Investigation directory ready: {self.investigation_dir}")
            _LOGGER.info("🔧 FIXED: Room cleaning completion detection (ignores mop maintenance)")
            
        except Exception as e:
            _LOGGER.error(f"❌ Failed to initialize investigation logger: {e}")
            raise

    async def _load_session_state(self) -> None:
        """Load existing session state if available."""
        try:
            baseline_files = list(self.investigation_dir.glob("multi_key_baseline_*.json"))
            if baseline_files:
                self.baseline_captured = True
                self.current_mode = LoggingMode.SMART_MONITORING
                _LOGGER.info(f"📁 Found {len(baseline_files)} existing baseline files")
            
            monitoring_files = list(self.investigation_dir.glob("multi_key_monitoring_*.json"))
            if monitoring_files:
                self.meaningful_logs_created = len(monitoring_files)
                _LOGGER.info(f"📊 Found {len(monitoring_files)} existing monitoring files")
                
        except Exception as e:
            _LOGGER.warning(f"⚠️ Could not load session state: {e}")

    async def process_multi_key_update(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Process multi-key update with FIXED room cleaning completion detection."""
        try:
            self.total_updates_received += 1
            
            # Extract available monitored keys
            available_keys = {key: raw_data[key] for key in self.monitored_keys if key in raw_data and raw_data[key] is not None}
            
            if not available_keys:
                return None
            
            # FIXED: Update cleaning state tracking FIRST
            await self._update_room_cleaning_state_tracking(available_keys)
            
            # Generate data hash for duplicate detection
            combined_data = json.dumps(available_keys, sort_keys=True)
            data_hash = hashlib.md5(combined_data.encode()).hexdigest()
            
            # FIXED: Smart logging decision with room cleaning completion detection
            should_log, log_reason = await self._should_log_multi_key_update(available_keys, data_hash)
            
            if not should_log:
                if log_reason == "duplicate_data":
                    self.duplicates_skipped += 1
                return None
            
            # Determine logging mode and filename
            log_mode, filename = await self._determine_log_mode_and_filename(log_reason)
            
            # Create enhanced multi-key analysis
            analysis_data = await self._create_enhanced_multi_key_analysis(
                available_keys, raw_data, log_mode, log_reason
            )
            
            # Write to file
            filepath = self.investigation_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            
            # Update state
            await self._update_state_after_logging(available_keys, data_hash, log_mode, filepath)
            
            self.meaningful_logs_created += 1
            
            # FIXED: Log room cleaning completion detection info
            if "automatic_post_cleaning" in log_reason:
                _LOGGER.info("🎯 AUTOMATIC POST-CLEANING CAPTURED: Room cleaning completed, robot returned to dock")
                _LOGGER.info(f"⏱️ Room cleaning duration: {self._get_room_cleaning_duration_minutes():.1f} minutes")
                _LOGGER.info(f"📁 File: {filename}")
                _LOGGER.info("ℹ️ Note: Mop washing/drying may continue but post-cleaning data captured")
            
            # Cleanup old files if needed
            await self._cleanup_old_files()
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error(f"❌ Multi-key processing error: {e}")
            return None

    async def _update_room_cleaning_state_tracking(self, available_keys: Dict[str, Any]) -> None:
        """FIXED: Update room cleaning state tracking for completion detection (ignores mop maintenance)."""
        try:
            # Extract work status from Key 153
            new_state = await self._determine_cleaning_state(available_keys)
            
            # Update state history
            self.previous_cleaning_state = self.cleaning_state
            self.cleaning_state = new_state
            
            current_time = datetime.now()
            
            # FIXED: Track ROOM cleaning cycle start (not just any cleaning)
            if (self.previous_cleaning_state in [CleaningState.DOCKED, CleaningState.CHARGING, CleaningState.UNKNOWN] and
                self.cleaning_state in [CleaningState.CLEANING]):  # Only actual cleaning, not mop washing
                
                self.cleaning_start_time = current_time
                self.cleaning_cycle_active = True
                self.room_cleaning_completed = False
                self.room_cleaning_end_time = None
                self.post_cleaning_captured_this_cycle = False
                self.docked_confirmation_time = None
                
                _LOGGER.info(f"🚀 ROOM CLEANING STARTED: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
            
            # FIXED: Track room cleaning END (when robot starts returning home or goes to dock)
            elif (self.cleaning_cycle_active and not self.room_cleaning_completed and
                  self.previous_cleaning_state == CleaningState.CLEANING and
                  self.cleaning_state in [CleaningState.GOING_HOME, CleaningState.DOCKED, CleaningState.CHARGING, CleaningState.WASHING_MOPS]):
                
                self.room_cleaning_end_time = current_time
                self.room_cleaning_completed = True
                
                room_duration = self._get_room_cleaning_duration_minutes()
                _LOGGER.info(f"🏁 ROOM CLEANING ENDED: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
                _LOGGER.info(f"⏱️ Room cleaning duration: {room_duration:.1f} minutes")
                
                # If reasonable room cleaning duration, start dock confirmation immediately
                if self.min_room_cleaning_duration_minutes <= room_duration <= self.max_reasonable_room_clean_minutes:
                    if self.cleaning_state in [CleaningState.DOCKED, CleaningState.CHARGING]:
                        self.docked_confirmation_time = current_time
                        _LOGGER.info(f"🏠 ROOM CLEAN COMPLETE - ROBOT DOCKED: Starting {self.docked_confirmation_seconds}s confirmation")
                    else:
                        _LOGGER.info(f"🏠 ROOM CLEAN COMPLETE - ROBOT GOING HOME: Waiting for dock")
            
            # FIXED: Track final docking after room cleaning is complete
            elif (self.room_cleaning_completed and not self.post_cleaning_captured_this_cycle and
                  self.cleaning_state in [CleaningState.DOCKED, CleaningState.CHARGING] and
                  self.docked_confirmation_time is None):
                
                self.docked_confirmation_time = current_time
                _LOGGER.info(f"🏠 ROBOT DOCKED AFTER ROOM CLEAN: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
                _LOGGER.info(f"⏱️ Starting {self.docked_confirmation_seconds}s docked confirmation timer")
            
            # FIXED: Reset if robot leaves dock during confirmation (unusual but possible)
            elif (self.docked_confirmation_time is not None and
                  self.cleaning_state not in [CleaningState.DOCKED, CleaningState.CHARGING]):
                
                # Only reset if robot actually leaves for more cleaning (not just mop maintenance)
                if self.cleaning_state == CleaningState.CLEANING:
                    _LOGGER.warning(f"⚠️ DOCK CONFIRMATION RESET: Robot left dock to continue cleaning")
                    self.docked_confirmation_time = None
                    self.room_cleaning_completed = False
                    self.room_cleaning_end_time = None
            
            # Log state changes for debugging
            if self.previous_cleaning_state != self.cleaning_state:
                _LOGGER.debug(f"🔄 State change: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
                
        except Exception as e:
            _LOGGER.error(f"❌ Error updating room cleaning state: {e}")

    async def _determine_cleaning_state(self, available_keys: Dict[str, Any]) -> CleaningState:
        """FIXED: Determine current cleaning state from work status data."""
        try:
            # Try Key 153 (work status)
            if "153" in available_keys:
                work_status_value = available_keys["153"]
                
                # Try to decode if base64
                if isinstance(work_status_value, str):
                    try:
                        decoded = base64.b64decode(work_status_value)
                        # Look for status bytes in known ranges
                        for byte_val in decoded:
                            state = self._map_byte_to_cleaning_state(byte_val)
                            if state != CleaningState.UNKNOWN:
                                return state
                    except:
                        pass
                
                # Try direct numeric value
                elif isinstance(work_status_value, (int, float)):
                    return self._map_byte_to_cleaning_state(int(work_status_value))
            
            # Fallback: try other status keys
            for key in ["152", "154", "157", "162", "177"]:
                if key in available_keys:
                    try:
                        value = available_keys[key]
                        if isinstance(value, (int, float)):
                            state = self._map_byte_to_cleaning_state(int(value))
                            if state != CleaningState.UNKNOWN:
                                return state
                    except:
                        continue
            
            return CleaningState.UNKNOWN
            
        except Exception as e:
            _LOGGER.debug(f"Error determining cleaning state: {e}")
            return CleaningState.UNKNOWN

    def _map_byte_to_cleaning_state(self, byte_value: int) -> CleaningState:
        """FIXED: Map byte values to cleaning states based on known patterns."""
        # Common work status mappings from Eufy protocol
        if byte_value == 0:
            return CleaningState.DOCKED
        elif byte_value == 1:
            return CleaningState.WASHING_MOPS
        elif byte_value == 2:
            return CleaningState.CHARGING
        elif byte_value == 3:
            return CleaningState.CHARGING
        elif byte_value == 4:
            return CleaningState.CLEANING
        elif byte_value == 5:
            return CleaningState.CLEANING
        elif byte_value == 6:
            return CleaningState.CLEANING
        elif byte_value == 7:
            return CleaningState.GOING_HOME
        elif byte_value == 8:
            return CleaningState.CLEANING
        else:
            return CleaningState.UNKNOWN

    def _is_room_cleaning_completed(self) -> bool:
        """FIXED: Check if ROOM cleaning has completed and robot is confirmed docked."""
        current_time = datetime.now()
        
        # Must have an active cleaning cycle
        if not self.cleaning_cycle_active:
            return False
        
        # Must have completed room cleaning phase
        if not self.room_cleaning_completed:
            return False
        
        # Must not have already captured post-cleaning for this cycle
        if self.post_cleaning_captured_this_cycle:
            return False
        
        # Must have room cleaning end time
        if not self.room_cleaning_end_time:
            return False
        
        # Check room cleaning duration was reasonable
        room_duration = self._get_room_cleaning_duration_minutes()
        if not (self.min_room_cleaning_duration_minutes <= room_duration <= self.max_reasonable_room_clean_minutes):
            return False
        
        # Must be currently docked/charging
        if self.cleaning_state not in [CleaningState.DOCKED, CleaningState.CHARGING]:
            return False
        
        # Must have been docked for confirmation period
        if not self.docked_confirmation_time:
            return False
        
        docked_duration = (current_time - self.docked_confirmation_time).total_seconds()
        if docked_duration < self.docked_confirmation_seconds:
            return False
        
        # All conditions met - room cleaning is completed and robot is docked!
        return True

    def _get_room_cleaning_duration_minutes(self) -> float:
        """Get the duration of the room cleaning phase in minutes."""
        if not self.cleaning_start_time:
            return 0.0
        
        end_time = self.room_cleaning_end_time or datetime.now()
        return (end_time - self.cleaning_start_time).total_seconds() / 60

    async def _should_log_multi_key_update(self, available_keys: Dict[str, Any], data_hash: str) -> Tuple[bool, str]:
        """FIXED: Determine if we should log with room cleaning completion detection."""
        
        # Always log if no baseline captured
        if not self.baseline_captured:
            return True, "baseline_capture"
        
        # FIXED: Check for room cleaning completion FIRST
        if self._is_room_cleaning_completed():
            self.post_cleaning_captured_this_cycle = True
            self.cleaning_cycle_active = False
            return True, "automatic_post_cleaning_room_completion"
        
        # Don't log too frequently
        if (self.last_log_time and 
            (datetime.now() - self.last_log_time).total_seconds() < self.min_log_interval_seconds):
            return False, "too_frequent"
        
        # Check for duplicate data
        if self.last_multi_key_hash == data_hash:
            return False, "duplicate_data"
        
        # Check for significant changes in any key (but NOT during active cleaning)
        if not self.cleaning_cycle_active:
            significant_changes = []
            for key, current_value in available_keys.items():
                last_value = self.key_last_values.get(key)
                if last_value is not None and last_value != current_value:
                    change_significance = await self._analyze_key_change_significance(key, last_value, current_value)
                    if change_significance["significant"]:
                        significant_changes.append(f"Key {key}: {change_significance['description']}")
            
            if significant_changes:
                return True, f"significant_changes: {', '.join(significant_changes[:3])}"
        
        # Log periodically even without changes (monitoring mode) - but not during cleaning
        if (not self.cleaning_cycle_active and 
            self.last_log_time and 
            (datetime.now() - self.last_log_time).total_seconds() > 300):  # 5 minutes
            return True, "periodic_monitoring"
        
        return False, "no_significant_change"

    async def _analyze_key_change_significance(self, key: str, old_value: Any, new_value: Any) -> Dict[str, Any]:
        """Analyze the significance of a change in a specific key."""
        # For numeric values (potential percentages)
        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            difference = abs(new_value - old_value)
            if self.accessory_value_range[0] <= new_value <= self.accessory_value_range[1]:
                if difference >= self.significant_change_threshold:
                    return {
                        "significant": True,
                        "description": f"{old_value}% → {new_value}% (Δ{difference}%)",
                        "type": "percentage_change",
                        "magnitude": difference
                    }
        
        # For base64 data changes
        if isinstance(old_value, str) and isinstance(new_value, str):
            if old_value != new_value:
                try:
                    old_decoded = base64.b64decode(old_value)
                    new_decoded = base64.b64decode(new_value)
                    
                    # Check for byte-level differences
                    if len(old_decoded) == len(new_decoded):
                        diff_count = sum(1 for a, b in zip(old_decoded, new_decoded) if a != b)
                        if diff_count > 0:
                            return {
                                "significant": True,
                                "description": f"Base64 change ({diff_count} bytes different)",
                                "type": "base64_change",
                                "magnitude": diff_count
                            }
                except:
                    return {
                        "significant": True,
                        "description": "String value changed",
                        "type": "string_change",
                        "magnitude": 1
                    }
        
        return {"significant": False, "description": "No significant change", "type": "unchanged", "magnitude": 0}
    
    async def _determine_log_mode_and_filename(self, log_reason: str) -> Tuple[LoggingMode, str]:
        """Determine logging mode and filename for multi-key logging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        if log_reason == "baseline_capture":
            return LoggingMode.BASELINE, f"multi_key_baseline_{timestamp}.json"
        elif "automatic_post_cleaning" in log_reason:
            return LoggingMode.POST_CLEANING, f"multi_key_auto_post_cleaning_{timestamp}.json"
        elif "post_cleaning" in log_reason:
            return LoggingMode.POST_CLEANING, f"multi_key_post_cleaning_{timestamp}.json"
        else:
            return LoggingMode.SMART_MONITORING, f"multi_key_monitoring_{timestamp}.json"
    
    async def _create_enhanced_multi_key_analysis(
        self, 
        available_keys: Dict[str, Any], 
        full_raw_data: Dict[str, Any], 
        log_mode: LoggingMode, 
        log_reason: str
    ) -> Dict[str, Any]:
        """Create comprehensive multi-key analysis with enhanced features."""
        
        analysis_data = {
            "metadata": {
                "device_id": self.device_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "log_mode": log_mode.value,
                "log_reason": log_reason,
                "update_number": self.total_updates_received,
                "smart_logger_version": "4.1_multi_key_fixed_room_completion",
                "file_number": self.meaningful_logs_created + 1,
                "self_contained": True,
                "monitored_keys_count": len(self.monitored_keys),
                "available_keys_count": len(available_keys),
                "cleaning_cycle_info": {
                    "cleaning_state": self.cleaning_state.value,
                    "previous_state": self.previous_cleaning_state.value,
                    "cycle_active": self.cleaning_cycle_active,
                    "room_cleaning_completed": self.room_cleaning_completed,
                    "room_cleaning_duration_minutes": self._get_room_cleaning_duration_minutes(),
                    "auto_completion_detected": "automatic_post_cleaning" in log_reason
                }
            },
            "smart_logging_info": {
                "total_updates_received": self.total_updates_received,
                "meaningful_logs_created": self.meaningful_logs_created,
                "duplicates_skipped": self.duplicates_skipped,
                "logging_efficiency": f"{(self.duplicates_skipped / max(1, self.total_updates_received) * 100):.1f}% duplicates avoided",
                "monitored_keys": self.monitored_keys,
                "available_keys": list(available_keys.keys()),
                "missing_keys": [key for key in self.monitored_keys if key not in available_keys],
                "auto_detection_info": {
                    "room_completion_detection_fixed": True,
                    "min_room_cleaning_duration_minutes": self.min_room_cleaning_duration_minutes,
                    "max_reasonable_room_clean_minutes": self.max_reasonable_room_clean_minutes,
                    "docked_confirmation_seconds": self.docked_confirmation_seconds,
                    "current_cleaning_state": self.cleaning_state.value,
                    "room_cleaning_completed": self.room_cleaning_completed
                }
            },
            "multi_key_data": {}
        }
        
        # Add individual key analysis
        for key, value in available_keys.items():
            key_data = {
                "raw_data": value,
                "data_type": type(value).__name__,
                "length": len(str(value)),
                "data_hash": hashlib.md5(str(value).encode()).hexdigest(),
                "analysis": await self._analyze_key_value(key, value)
            }
            
            # Add change detection if we have previous data
            if key in self.key_last_values:
                last_value = self.key_last_values[key]
                change_analysis = await self._analyze_key_change_significance(key, last_value, value)
                key_data["change_from_last"] = change_analysis
            
            analysis_data["multi_key_data"][f"key_{key}_data"] = key_data
        
        # Add context and reference data
        analysis_data["context"] = self._extract_efficient_context(full_raw_data)
        analysis_data["cross_key_analysis"] = await self._perform_cross_key_analysis(available_keys)
        analysis_data["search_results"] = await self._perform_targeted_searches(available_keys)
        
        return analysis_data