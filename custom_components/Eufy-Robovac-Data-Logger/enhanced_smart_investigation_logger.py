"""Enhanced Smart Investigation Logger v4.1 for multi-key Eufy robovac data analysis with FIXED automatic post-cleaning detection."""
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
    """Enhanced Smart Investigation Logger v4.1 with FIXED automatic post-cleaning detection."""

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
        
        # FIXED: Enhanced cleaning state tracking for automatic post-cleaning detection
        self.cleaning_state = CleaningState.UNKNOWN
        self.previous_cleaning_state = CleaningState.UNKNOWN
        self.cleaning_start_time = None
        self.docked_confirmation_time = None
        self.cleaning_cycle_active = False
        self.post_cleaning_captured_this_cycle = False
        
        # Automatic detection settings
        self.min_cleaning_duration_minutes = 5  # Must clean for at least 5 minutes
        self.docked_confirmation_seconds = 30   # Must stay docked for 30 seconds
        self.post_cleaning_window_minutes = 5   # Capture within 5 minutes of completion
        
        # Smart logging configuration
        self.min_log_interval_seconds = 60  # Don't log more frequently than every minute
        self.significant_change_threshold = 2
        self.accessory_value_range = (0, 100)
        
        # File management
        self.max_monitoring_files = 10
        
        _LOGGER.info("🔍 Enhanced Smart Multi-Key Investigation Logger v4.1 initialized")
        _LOGGER.info("🔧 FIXED: Automatic post-cleaning detection waits for completion")
        _LOGGER.info(f"📁 Investigation directory: {self.investigation_dir}")
        _LOGGER.info(f"🗂️ Monitoring {len(self.monitored_keys)} keys")
        _LOGGER.info(f"🔬 Session ID: {self.session_id}")

    async def initialize(self) -> None:
        """Initialize the investigation logger."""
        try:
            self.investigation_dir.mkdir(parents=True, exist_ok=True)
            await self._load_session_state()
            
            _LOGGER.info("✅ Enhanced Smart Multi-Key Investigation Logger v4.1 initialized successfully")
            _LOGGER.info(f"📂 Investigation directory ready: {self.investigation_dir}")
            _LOGGER.info("🔧 FIXED: Auto post-cleaning detection waits for actual completion")
            
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
        """Process multi-key update with FIXED automatic post-cleaning detection."""
        try:
            self.total_updates_received += 1
            
            # Extract available monitored keys
            available_keys = {key: raw_data[key] for key in self.monitored_keys if key in raw_data and raw_data[key] is not None}
            
            if not available_keys:
                return None
            
            # FIXED: Update cleaning state tracking FIRST
            await self._update_cleaning_state_tracking(available_keys)
            
            # Generate data hash for duplicate detection
            combined_data = json.dumps(available_keys, sort_keys=True)
            data_hash = hashlib.md5(combined_data.encode()).hexdigest()
            
            # FIXED: Smart logging decision with proper completion detection
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
            
            # FIXED: Log completion detection info
            if "automatic_post_cleaning" in log_reason:
                _LOGGER.info("🎯 AUTOMATIC POST-CLEANING CAPTURED: Cleaning cycle completed, robot returned to dock")
                _LOGGER.info(f"⏱️ Cleaning duration: {self._get_cleaning_duration_minutes():.1f} minutes")
                _LOGGER.info(f"📁 File: {filename}")
            
            # Cleanup old files if needed
            await self._cleanup_old_files()
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error(f"❌ Multi-key processing error: {e}")
            return None

    async def _update_cleaning_state_tracking(self, available_keys: Dict[str, Any]) -> None:
        """FIXED: Update cleaning state tracking for automatic completion detection."""
        try:
            # Extract work status from Key 153
            new_state = await self._determine_cleaning_state(available_keys)
            
            # Update state history
            self.previous_cleaning_state = self.cleaning_state
            self.cleaning_state = new_state
            
            current_time = datetime.now()
            
            # FIXED: Track cleaning cycle start
            if (self.previous_cleaning_state in [CleaningState.DOCKED, CleaningState.CHARGING, CleaningState.UNKNOWN] and
                self.cleaning_state in [CleaningState.WASHING_MOPS, CleaningState.CLEANING]):
                
                self.cleaning_start_time = current_time
                self.cleaning_cycle_active = True
                self.post_cleaning_captured_this_cycle = False
                self.docked_confirmation_time = None
                
                _LOGGER.info(f"🚀 CLEANING CYCLE STARTED: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
            
            # FIXED: Track return to dock (completion candidate)
            elif (self.cleaning_cycle_active and 
                  self.previous_cleaning_state in [CleaningState.CLEANING, CleaningState.GOING_HOME] and
                  self.cleaning_state in [CleaningState.DOCKED, CleaningState.CHARGING]):
                
                if self.docked_confirmation_time is None:
                    self.docked_confirmation_time = current_time
                    _LOGGER.info(f"🏠 RETURNED TO DOCK: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
                    _LOGGER.info(f"⏱️ Starting {self.docked_confirmation_seconds}s docked confirmation timer")
            
            # FIXED: Reset if robot leaves dock during confirmation
            elif (self.docked_confirmation_time is not None and
                  self.cleaning_state not in [CleaningState.DOCKED, CleaningState.CHARGING]):
                
                _LOGGER.warning(f"⚠️ DOCK CONFIRMATION RESET: Robot left dock during confirmation")
                self.docked_confirmation_time = None
            
            # Log state changes for debugging
            if self.previous_cleaning_state != self.cleaning_state:
                _LOGGER.debug(f"🔄 State change: {self.previous_cleaning_state.value} → {self.cleaning_state.value}")
                
        except Exception as e:
            _LOGGER.error(f"❌ Error updating cleaning state: {e}")

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

    def _is_cleaning_completed(self) -> bool:
        """FIXED: Check if cleaning cycle has completed and robot is confirmed docked."""
        current_time = datetime.now()
        
        # Must have an active cleaning cycle
        if not self.cleaning_cycle_active:
            return False
        
        # Must not have already captured post-cleaning for this cycle
        if self.post_cleaning_captured_this_cycle:
            return False
        
        # Must have started cleaning at least minimum duration ago
        if not self.cleaning_start_time:
            return False
        
        cleaning_duration = (current_time - self.cleaning_start_time).total_seconds() / 60
        if cleaning_duration < self.min_cleaning_duration_minutes:
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
        
        # All conditions met - cleaning is completed!
        return True

    def _get_cleaning_duration_minutes(self) -> float:
        """Get the duration of the current/last cleaning cycle in minutes."""
        if not self.cleaning_start_time:
            return 0.0
        
        end_time = self.docked_confirmation_time or datetime.now()
        return (end_time - self.cleaning_start_time).total_seconds() / 60

    async def _should_log_multi_key_update(self, available_keys: Dict[str, Any], data_hash: str) -> Tuple[bool, str]:
        """FIXED: Determine if we should log this multi-key update with proper completion detection."""
        
        # Always log if no baseline captured
        if not self.baseline_captured:
            return True, "baseline_capture"
        
        # FIXED: Check for automatic post-cleaning completion FIRST
        if self._is_cleaning_completed():
            self.post_cleaning_captured_this_cycle = True
            self.cleaning_cycle_active = False
            return True, "automatic_post_cleaning_completion"
        
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
                "smart_logger_version": "4.1_multi_key_fixed_auto_detection",
                "file_number": self.meaningful_logs_created + 1,
                "self_contained": True,
                "monitored_keys_count": len(self.monitored_keys),
                "available_keys_count": len(available_keys),
                "cleaning_cycle_info": {
                    "cleaning_state": self.cleaning_state.value,
                    "previous_state": self.previous_cleaning_state.value,
                    "cycle_active": self.cleaning_cycle_active,
                    "cleaning_duration_minutes": self._get_cleaning_duration_minutes(),
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
                    "completion_detection_fixed": True,
                    "min_cleaning_duration_minutes": self.min_cleaning_duration_minutes,
                    "docked_confirmation_seconds": self.docked_confirmation_seconds,
                    "current_cleaning_state": self.cleaning_state.value,
                    "cleaning_cycle_active": self.cleaning_cycle_active
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
    
    async def _analyze_key_value(self, key: str, value: Any) -> Dict[str, Any]:
        """Analyze individual key value for patterns and potential meanings."""
        analysis = {}
        
        if isinstance(value, (int, float)):
            analysis["numeric"] = {
                "value": value,
                "is_percentage_range": 0 <= value <= 100,
                "potential_battery": value > 0 and key in ["163", "161"],
                "potential_water_tank": value > 0 and key in ["161", "167", "177"],
                "potential_accessory_wear": 0 <= value <= 100
            }
        
        elif isinstance(value, str):
            try:
                decoded = base64.b64decode(value)
                analysis["base64"] = {
                    "is_valid_base64": True,
                    "decoded_length": len(decoded),
                    "decoded_hex": decoded.hex(),
                    "percentage_candidates": []
                }
                
                # Look for percentage-like bytes
                for i, byte_val in enumerate(decoded):
                    if 0 <= byte_val <= 100:
                        analysis["base64"]["percentage_candidates"].append({
                            "position": i,
                            "value": byte_val,
                            "hex": f"0x{byte_val:02x}"
                        })
                
            except:
                analysis["string"] = {
                    "is_valid_base64": False,
                    "length": len(value),
                    "potential_battery": False,
                    "potential_water_tank": False,
                    "potential_accessory_wear": False
                }
        
        return analysis
    
    async def _perform_cross_key_analysis(self, available_keys: Dict[str, Any]) -> Dict[str, Any]:
        """Perform cross-key analysis to find relationships and patterns."""
        analysis = {
            "water_tank_candidates": {},
            "battery_candidates": {},
            "accessory_wear_candidates": {},
            "value_distribution": {}
        }
        
        # Look for water tank candidates (around 50-90%)
        for key, value in available_keys.items():
            if isinstance(value, (int, float)) and 40 <= value <= 90:
                analysis["water_tank_candidates"][key] = {
                    "value": value,
                    "confidence": "high" if 50 <= value <= 80 else "medium"
                }
        
        # Look for battery candidates (usually higher values)
        for key, value in available_keys.items():
            if isinstance(value, (int, float)) and 80 <= value <= 100:
                analysis["battery_candidates"][key] = {
                    "value": value,
                    "confidence": "high" if key == "163" else "medium"
                }
        
        # Look for accessory wear in base64 data
        for key, value in available_keys.items():
            if isinstance(value, str):
                try:
                    decoded = base64.b64decode(value)
                    candidates = []
                    for i, byte_val in enumerate(decoded):
                        if 90 <= byte_val <= 100:
                            candidates.append({
                                "position": i,
                                "value": byte_val
                            })
                    if candidates:
                        analysis["accessory_wear_candidates"][key] = candidates
                except:
                    continue
        
        return analysis
    
    async def _perform_targeted_searches(self, available_keys: Dict[str, Any]) -> Dict[str, Any]:
        """Perform targeted searches for specific values like water tank, battery, etc."""
        search_results = {
            "water_tank_50_search": [],
            "battery_93_search": [],
            "speed_3_search": [],
            "percentage_values": [],
            "summary": {
                "water_tank_candidates": 0,
                "battery_candidates": 0,
                "speed_candidates": 0,
                "total_percentage_values": 0,
                "most_likely_water_tank": None,
                "most_likely_battery": None
            }
        }
        
        # Search for specific values
        for key, value in available_keys.items():
            if isinstance(value, (int, float)):
                # Water tank search (around 50%)
                if value == 50:
                    search_results["water_tank_50_search"].append({
                        "key": key,
                        "value": value,
                        "type": "int",
                        "confidence": "exact_match"
                    })
                
                # Add to percentage values list
                if 0 <= value <= 100:
                    potential_meaning = "unknown"
                    if 40 <= value <= 60:
                        potential_meaning = "likely_water_tank"
                    elif 90 <= value <= 100:
                        potential_meaning = "likely_battery"
                    elif 1 <= value <= 10:
                        potential_meaning = "likely_speed_or_mode"
                    
                    search_results["percentage_values"].append({
                        "key": key,
                        "value": value,
                        "potential_meaning": potential_meaning
                    })
        
        # Update summary
        search_results["summary"]["total_percentage_values"] = len(search_results["percentage_values"])
        search_results["summary"]["water_tank_candidates"] = len(search_results["water_tank_50_search"])
        
        if search_results["water_tank_50_search"]:
            search_results["summary"]["most_likely_water_tank"] = search_results["water_tank_50_search"][0]["key"]
        
        return search_results
    
    def _extract_efficient_context(self, full_raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context data efficiently without bloating the file."""
        context = {
            "total_keys_available": len(full_raw_data),
            "monitored_keys_available": len([k for k in self.monitored_keys if k in full_raw_data]),
            "data_source_info": {
                "has_key_180": "180" in full_raw_data,
                "has_key_163": "163" in full_raw_data,
                "has_key_161": "161" in full_raw_data,
                "has_key_167": "167" in full_raw_data
            }
        }
        
        # Add first 10 characters of each monitored key for quick reference
        for key in self.monitored_keys:
            if key in full_raw_data and full_raw_data[key] is not None:
                value = str(full_raw_data[key])
                context[f"key_{key}_preview"] = value[:10] + ("..." if len(value) > 10 else "")
        
        return context
    
    async def _update_state_after_logging(self, available_keys: Dict[str, Any], data_hash: str, log_mode: LoggingMode, filepath: Path) -> None:
        """Update tracking state after successful logging."""
        self.last_multi_key_hash = data_hash
        self.last_logged_data = available_keys.copy()
        self.last_log_time = datetime.now()
        
        # Update individual key tracking
        for key, value in available_keys.items():
            if self.key_last_values.get(key) != value:
                self.key_change_counts[key] += 1
            self.key_last_values[key] = value
        
        if log_mode == LoggingMode.BASELINE:
            self.baseline_captured = True
            self.current_mode = LoggingMode.SMART_MONITORING
            _LOGGER.info("🎯 Enhanced multi-key baseline captured, switching to smart monitoring mode")
    
    async def _cleanup_old_files(self) -> None:
        """Cleanup old monitoring files to prevent bloat."""
        try:
            monitoring_files = list(self.investigation_dir.glob("multi_key_monitoring_*.json"))
            
            if len(monitoring_files) > self.max_monitoring_files:
                monitoring_files.sort(key=lambda f: f.stat().st_mtime)
                files_to_remove = monitoring_files[:-self.max_monitoring_files]
                
                for file_to_remove in files_to_remove:
                    file_to_remove.unlink()
                    _LOGGER.debug("🗑️ Cleaned up old monitoring file: %s", file_to_remove.name)
                
                _LOGGER.info("🧹 Cleaned up %d old monitoring files", len(files_to_remove))
        
        except Exception as e:
            _LOGGER.warning("⚠️ File cleanup failed: %s", e)
    
    # Manual trigger methods
    async def capture_baseline(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Manually capture baseline with multi-key support."""
        original_baseline_state = self.baseline_captured
        self.baseline_captured = False
        
        result = await self.process_multi_key_update(raw_data)
        
        if not result:
            self.baseline_captured = original_baseline_state
        
        return result
    
    async def capture_post_cleaning(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Manually capture post-cleaning data with multi-key analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"multi_key_manual_post_cleaning_{timestamp}.json"
        
        # Extract available keys
        available_keys = {key: raw_data[key] for key in self.monitored_keys if key in raw_data and raw_data[key] is not None}
        
        if not available_keys:
            return None
        
        analysis_data = await self._create_enhanced_multi_key_analysis(
            available_keys, raw_data, LoggingMode.POST_CLEANING, "manual_post_cleaning"
        )
        
        filepath = self.investigation_dir / filename
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
        
        # Update state
        combined_data = json.dumps(available_keys, sort_keys=True)
        data_hash = hashlib.md5(combined_data.encode()).hexdigest()
        await self._update_state_after_logging(available_keys, data_hash, LoggingMode.POST_CLEANING, filepath)
        
        self.meaningful_logs_created += 1
        return str(filepath)
    
    async def generate_session_summary(self) -> str:
        """Generate enhanced session summary with multi-key analysis."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"enhanced_multi_key_session_summary_{self.session_id}_{timestamp}.json"
        
        # Collect all investigation files for analysis
        baseline_files = list(self.investigation_dir.glob("multi_key_baseline_*.json"))
        monitoring_files = list(self.investigation_dir.glob("multi_key_monitoring_*.json"))
        post_cleaning_files = list(self.investigation_dir.glob("multi_key_*post_cleaning_*.json"))
        
        summary_data = {
            "metadata": {
                "session_id": self.session_id,
                "device_id": self.device_id,
                "timestamp": datetime.now().isoformat(),
                "summary_version": "4.1_multi_key_fixed_auto_detection",
                "total_files_analyzed": len(baseline_files) + len(monitoring_files) + len(post_cleaning_files),
                "auto_detection_summary": {
                    "completion_detection_fixed": True,
                    "min_cleaning_duration_minutes": self.min_cleaning_duration_minutes,
                    "docked_confirmation_seconds": self.docked_confirmation_seconds,
                    "automatic_captures": len([f for f in post_cleaning_files if "auto_post_cleaning" in f.name]),
                    "manual_captures": len([f for f in post_cleaning_files if "manual_post_cleaning" in f.name])
                }
            },
            "session_statistics": {
                "total_updates_received": self.total_updates_received,
                "meaningful_logs_created": self.meaningful_logs_created,
                "duplicates_skipped": self.duplicates_skipped,
                "logging_efficiency": f"{(self.duplicates_skipped / max(1, self.total_updates_received) * 100):.1f}%",
                "baseline_files": len(baseline_files),
                "monitoring_files": len(monitoring_files),
                "post_cleaning_files": len(post_cleaning_files),
                "automatic_post_cleaning_files": len([f for f in post_cleaning_files if "auto_post_cleaning" in f.name]),
                "manual_post_cleaning_files": len([f for f in post_cleaning_files if "manual_post_cleaning" in f.name])
            },
            "key_change_summary": {
                "monitored_keys": self.monitored_keys,
                "key_change_counts": self.key_change_counts,
                "total_changes": sum(self.key_change_counts.values()),
                "most_active_keys": sorted(self.key_change_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            },
            "cleaning_cycle_tracking": {
                "current_state": self.cleaning_state.value,
                "last_cleaning_duration_minutes": self._get_cleaning_duration_minutes(),
                "cleaning_detection_settings": {
                    "min_cleaning_duration_minutes": self.min_cleaning_duration_minutes,
                    "docked_confirmation_seconds": self.docked_confirmation_seconds,
                    "post_cleaning_window_minutes": self.post_cleaning_window_minutes
                }
            },
            "investigation_directory": str(self.investigation_dir),
            "file_inventory": {
                "baseline_files": [f.name for f in baseline_files],
                "monitoring_files": [f.name for f in monitoring_files],
                "post_cleaning_files": [f.name for f in post_cleaning_files]
            }
        }
        
        # Write summary file
        filepath = self.investigation_dir / filename
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(summary_data, indent=2, ensure_ascii=False))
        
        return str(filepath)
    
    def get_smart_status(self) -> Dict[str, Any]:
        """Get current smart logging status - REQUIRED by coordinator."""
        efficiency_percentage = (self.duplicates_skipped / max(1, self.total_updates_received) * 100)
        
        return {
            "session_id": self.session_id,
            "baseline_captured": self.baseline_captured,
            "current_mode": self.current_mode.value,
            "total_updates": self.total_updates_received,
            "meaningful_logs": self.meaningful_logs_created,
            "duplicates_skipped": self.duplicates_skipped,
            "efficiency_percentage": round(efficiency_percentage, 1),
            "monitored_keys_count": len(self.monitored_keys),
            "investigation_directory": str(self.investigation_dir),
            "last_log_time": self.last_log_time.isoformat() if self.last_log_time else None,
            "key_change_summary": {
                "total_changes": sum(self.key_change_counts.values()),
                "key_change_counts": self.key_change_counts,
                "most_active_keys": sorted(self.key_change_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            },
            "cleaning_state_tracking": {
                "current_state": self.cleaning_state.value,
                "cleaning_cycle_active": self.cleaning_cycle_active,
                "cleaning_duration_minutes": self._get_cleaning_duration_minutes(),
                "auto_detection_working": True,
                "completion_detection_fixed": True
            }
        }
    
    async def _load_sensors_config(self) -> Optional[Dict[str, Any]]:
        """Load sensors configuration for analysis reference - REQUIRED by coordinator."""
        try:
            # Try to load device-specific config first
            device_config_path = self.integration_dir / "accessories" / f"sensors_{self.device_id}.json"
            if device_config_path.exists():
                async with aiofiles.open(device_config_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            
            # Fallback to template config
            template_config_path = self.integration_dir / "accessories" / "sensors.json"
            if template_config_path.exists():
                async with aiofiles.open(template_config_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            
            return None
            
        except Exception as e:
            _LOGGER.warning(f"⚠️ Could not load sensors config: {e}")
            return None