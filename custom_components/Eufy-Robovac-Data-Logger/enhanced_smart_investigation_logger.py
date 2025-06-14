"""
Enhanced Smart Investigation Logger for Key 180 Accessory Wear Detection
VERSION 3.0: Now includes sensors.json reference data for self-contained analysis.
Optimized with intelligent change detection and reduced file bloat.
Only logs when meaningful changes are detected.
FIXED: Complete file without syntax errors.
"""

import asyncio
import aiofiles
import json
import logging
import base64
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum

_LOGGER = logging.getLogger(__name__)


class LoggingMode(str, Enum):
    """Investigation logging modes."""
    BASELINE = "baseline"
    SMART_MONITORING = "smart_monitoring"
    CLEANING_DETECTED = "cleaning_detected"
    POST_CLEANING = "post_cleaning"
    MANUAL_TRIGGER = "manual_trigger"


class EnhancedSmartKey180InvestigationLogger:
    """
    Enhanced Smart Investigation Logger with sensors.json integration.
    Creates self-contained analysis files with complete reference data.
    Reduces file bloat by only logging meaningful changes.
    """
    
    def __init__(self, device_id: str, hass_config_dir: str, integration_dir: Optional[str] = None):
        self.device_id = device_id
        self.hass_config_dir = hass_config_dir
        
        # Create investigation directory
        self.investigation_dir = Path(hass_config_dir) / "eufy_investigation" / device_id
        self.investigation_dir.mkdir(parents=True, exist_ok=True)
        
        # Integration directory for accessing sensors.json
        if integration_dir:
            self.integration_dir = Path(integration_dir)
            self.sensors_config_file = self.integration_dir / "accessories" / "sensors.json"
            self.device_config_file = self.integration_dir / "accessories" / f"sensors_{device_id}.json"
        else:
            self.integration_dir = None
            self.sensors_config_file = None
            self.device_config_file = None
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Smart logging state
        self.current_mode = LoggingMode.BASELINE
        self.baseline_captured = False
        self.last_key180_hash = None
        self.last_logged_data = None
        self.last_log_time = None
        
        # Change detection settings
        self.min_log_interval_seconds = 30  # Don't log more than once per 30 seconds
        self.significant_change_threshold = 3  # Changes of 1-3 bytes are significant
        self.accessory_value_range = (1, 100)  # Valid accessory percentage range
        
        # File management
        self.max_monitoring_files = 10  # Keep max 10 monitoring files
        self.auto_cleanup_enabled = True
        
        # Statistics
        self.total_updates_received = 0
        self.meaningful_logs_created = 0
        self.duplicates_skipped = 0
        
        # NEW: Sensors config cache
        self._sensors_config_cache = None
        self._device_config_cache = None
        self._config_load_time = None
        
        _LOGGER.info("🔍 Enhanced Smart Investigation Logger v3.0 initialized with sensors config integration")
        _LOGGER.info("📂 Investigation directory: %s", self.investigation_dir)
        _LOGGER.info("🔧 Sensors config: %s", self.sensors_config_file if self.sensors_config_file else "Not available")
        _LOGGER.info("🧠 Mode: %s", self.current_mode.value)
        _LOGGER.info("✨ NEW: Self-contained analysis files with complete reference data")
    
    async def _load_sensors_config(self) -> Dict[str, Any]:
        """Load sensors.json configuration for reference data."""
        try:
            current_time = datetime.now().timestamp()
            
            # Use cache if recent (5 minute cache)
            if (self._sensors_config_cache and self._config_load_time and 
                current_time - self._config_load_time < 300):
                return self._sensors_config_cache
            
            sensors_config = {}
            device_config = {}
            
            # Load template sensors.json
            if self.sensors_config_file and self.sensors_config_file.exists():
                try:
                    async with aiofiles.open(self.sensors_config_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        sensors_config = json.loads(content)
                    _LOGGER.debug("✅ Loaded sensors.json template config")
                except Exception as e:
                    _LOGGER.warning("⚠️ Failed to load sensors.json template: %s", e)
            
            # Load device-specific sensors_DEVICEID.json
            if self.device_config_file and self.device_config_file.exists():
                try:
                    async with aiofiles.open(self.device_config_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        device_config = json.loads(content)
                    _LOGGER.debug("✅ Loaded device-specific sensor config")
                except Exception as e:
                    _LOGGER.warning("⚠️ Failed to load device sensor config: %s", e)
            
            # Cache the loaded configs
            self._sensors_config_cache = {
                "template_config": sensors_config,
                "device_config": device_config,
                "load_timestamp": datetime.now().isoformat(),
                "template_available": bool(sensors_config),
                "device_config_available": bool(device_config)
            }
            self._config_load_time = current_time
            
            return self._sensors_config_cache
            
        except Exception as e:
            _LOGGER.error("❌ Error loading sensors configuration: %s", e)
            return {
                "template_config": {},
                "device_config": {},
                "load_timestamp": datetime.now().isoformat(),
                "template_available": False,
                "device_config_available": False,
                "error": str(e)
            }
    
    async def process_key180_update(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        Enhanced smart processing of Key 180 data with sensors config integration.
        
        Args:
            raw_data: Complete raw API data
        
        Returns:
            Path to created file or None if no logging needed
        """
        try:
            self.total_updates_received += 1
            
            if "180" not in raw_data:
                return None
            
            key180_raw = raw_data["180"]
            
            # Calculate data hash for change detection
            data_hash = hashlib.md5(key180_raw.encode()).hexdigest()
            
            # Smart decision: Should we log this update?
            should_log, log_reason = await self._should_log_update(key180_raw, data_hash, raw_data)
            
            if not should_log:
                self.duplicates_skipped += 1
                return None
            
            # Determine appropriate logging mode and filename
            log_mode, filename = await self._determine_log_mode_and_filename(log_reason)
            
            # NEW: Load sensors config for enhanced analysis
            sensors_config = await self._load_sensors_config()
            
            # Create comprehensive analysis with sensors reference data
            analysis_data = await self._create_enhanced_analysis(
                key180_raw, raw_data, log_mode, log_reason, sensors_config
            )
            
            # Write to file
            filepath = self.investigation_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            
            # Update state tracking
            await self._update_state_after_logging(key180_raw, data_hash, log_mode, filepath)
            
            # Cleanup old files if needed
            if self.auto_cleanup_enabled:
                await self._cleanup_old_files()
            
            self.meaningful_logs_created += 1
            
            _LOGGER.info("📊 Enhanced log created: %s (Reason: %s)", filename, log_reason)
            _LOGGER.debug("📈 Stats: %d updates, %d logged, %d skipped", 
                         self.total_updates_received, self.meaningful_logs_created, self.duplicates_skipped)
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error("❌ Enhanced investigation processing failed: %s", e)
            return None
    
    async def _should_log_update(self, key180_raw: str, data_hash: str, raw_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Intelligent decision on whether to log this update."""
        
        # Always log baseline if not captured
        if not self.baseline_captured:
            return True, "baseline_capture"
        
        # Check if data actually changed
        if data_hash == self.last_key180_hash:
            return False, "no_change"
        
        # Check minimum time interval
        if self.last_log_time and (datetime.now() - self.last_log_time).total_seconds() < self.min_log_interval_seconds:
            return False, "too_frequent"
        
        # Detect significant byte changes
        if self.last_logged_data:
            change_significance = await self._analyze_change_significance(key180_raw, self.last_logged_data)
            
            if change_significance["has_significant_changes"]:
                return True, f"significant_change_{change_significance['change_count']}_bytes"
        
        # Detect cleaning cycle activity
        cleaning_activity = await self._detect_cleaning_activity(raw_data)
        if cleaning_activity["is_cleaning_related"]:
            return True, f"cleaning_activity_{cleaning_activity['activity_type']}"
        
        # If we made it here, it's a minor change - only log occasionally
        if self.total_updates_received % 20 == 0:  # Every 20th update for minor changes
            return True, "periodic_minor_change"
        
        return False, "minor_change_skipped"
    
    async def _analyze_change_significance(self, current_data: str, previous_data: str) -> Dict[str, Any]:
        """Enhanced analysis if changes are significant for accessory wear detection."""
        try:
            current_bytes = base64.b64decode(current_data)
            previous_bytes = base64.b64decode(previous_data)
            
            if len(current_bytes) != len(previous_bytes):
                return {"has_significant_changes": True, "change_count": "length_mismatch", "reason": "Data length changed"}
            
            significant_changes = []
            accessory_wear_changes = []
            
            # NEW: Load sensors config for enhanced position analysis
            sensors_config = await self._load_sensors_config()
            known_positions = self._extract_known_positions_from_config(sensors_config)
            
            for i, (curr, prev) in enumerate(zip(current_bytes, previous_bytes)):
                if curr != prev:
                    diff = curr - prev
                    
                    # Check if this looks like accessory wear (decrease in percentage range)
                    if (1 <= min(curr, prev) <= 100 and 
                        abs(diff) <= self.significant_change_threshold and 
                        diff < 0):  # Decrease indicates wear
                        
                        # Enhanced analysis with sensors config data
                        accessory_info = self._find_accessory_for_position(i, sensors_config)
                        
                        accessory_wear_changes.append({
                            "position": i,
                            "previous": prev,
                            "current": curr,
                            "decrease": abs(diff),
                            "likely_accessory": accessory_info.get("name", "unknown"),
                            "expected_percentage": accessory_info.get("expected_percentage"),
                            "config_match": accessory_info.get("config_match", False),
                            "confidence": self._calculate_position_confidence(i, curr, accessory_info)
                        })
                    
                    significant_changes.append({
                        "position": i,
                        "previous": prev,
                        "current": curr,
                        "difference": diff,
                        "in_known_positions": i in known_positions,
                        "accessory_candidate": 1 <= min(curr, prev) <= 100
                    })
            
            return {
                "has_significant_changes": len(accessory_wear_changes) > 0 or len(significant_changes) > 5,
                "change_count": len(significant_changes),
                "accessory_wear_changes": accessory_wear_changes,
                "total_changes": significant_changes,
                "known_position_changes": [c for c in significant_changes if c["in_known_positions"]],
                "reason": f"{len(accessory_wear_changes)} accessory wear changes, {len(significant_changes)} total changes"
            }
            
        except Exception as e:
            _LOGGER.error("❌ Enhanced change analysis failed: %s", e)
            return {"has_significant_changes": False, "change_count": 0, "reason": f"Analysis error: {e}"}
    
    def _extract_known_positions_from_config(self, sensors_config: Dict[str, Any]) -> List[int]:
        """Extract known byte positions from sensors configuration."""
        known_positions = []
        
        # From template config
        template_sensors = sensors_config.get("template_config", {}).get("accessory_sensors", {})
        for sensor_data in template_sensors.values():
            pos = sensor_data.get("byte_position")
            if isinstance(pos, int) and pos not in known_positions:
                known_positions.append(pos)
        
        # From device config
        device_sensors = sensors_config.get("device_config", {}).get("accessory_sensors", {})
        for sensor_data in device_sensors.values():
            pos = sensor_data.get("byte_position")
            if isinstance(pos, int) and pos not in known_positions:
                known_positions.append(pos)
        
        # Add known research positions
        research_positions = [5, 37, 75, 95, 125, 146, 228]
        for pos in research_positions:
            if pos not in known_positions:
                known_positions.append(pos)
        
        return sorted(known_positions)
    
    def _find_accessory_for_position(self, position: int, sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Find accessory information for a given byte position."""
        # Check device config first (most specific)
        device_sensors = sensors_config.get("device_config", {}).get("accessory_sensors", {})
        for sensor_id, sensor_data in device_sensors.items():
            if sensor_data.get("byte_position") == position:
                return {
                    "name": sensor_data.get("name", sensor_id),
                    "expected_percentage": sensor_data.get("current_life_remaining"),
                    "config_match": True,
                    "source": "device_config",
                    "sensor_id": sensor_id
                }
        
        # Check template config
        template_sensors = sensors_config.get("template_config", {}).get("accessory_sensors", {})
        for sensor_id, sensor_data in template_sensors.items():
            if sensor_data.get("byte_position") == position:
                return {
                    "name": sensor_data.get("name", sensor_id),
                    "expected_percentage": sensor_data.get("current_life_remaining"),
                    "config_match": True,
                    "source": "template_config",
                    "sensor_id": sensor_id
                }
        
        # Fallback to research-based guesses
        position_map = {
            5: {"name": "mop_cloth", "expected_percentage": None},
            37: {"name": "side_brush", "expected_percentage": None},
            75: {"name": "cleaning_tray", "expected_percentage": None},
            95: {"name": "sensors_status", "expected_percentage": None},
            125: {"name": "brush_guard", "expected_percentage": None},
            146: {"name": "rolling_brush", "expected_percentage": None},
            228: {"name": "dust_filter", "expected_percentage": None}
        }
        
        if position in position_map:
            return {
                "name": position_map[position]["name"],
                "expected_percentage": None,
                "config_match": False,
                "source": "research_guess",
                "sensor_id": None
            }
        
        return {
            "name": "unknown_accessory",
            "expected_percentage": None,
            "config_match": False,
            "source": "unknown",
            "sensor_id": None
        }
    
    def _calculate_position_confidence(self, position: int, detected_value: int, accessory_info: Dict[str, Any]) -> str:
        """Calculate confidence level for accessory position match."""
        if accessory_info.get("config_match"):
            expected = accessory_info.get("expected_percentage")
            if expected is not None:
                diff = abs(detected_value - expected)
                if diff <= 2:
                    return "very_high"
                elif diff <= 5:
                    return "high"
                else:
                    return "medium"
            else:
                return "medium"
        elif accessory_info.get("source") == "research_guess":
            return "low"
        else:
            return "very_low"
    
    async def _detect_cleaning_activity(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if current data indicates cleaning activity."""
        try:
            # Check work status (Key 153) for cleaning indicators
            work_status = raw_data.get("153")
            if work_status in [5, 6, 7]:  # cleaning, remote_ctrl, go_home
                return {"is_cleaning_related": True, "activity_type": f"work_status_{work_status}"}
            
            # Check if clean speed changed (Key 158) - indicates user interaction
            clean_speed = raw_data.get("158")
            if clean_speed is not None and self.last_logged_data:
                # If clean speed changed, it might indicate start of cleaning
                return {"is_cleaning_related": False, "activity_type": "speed_change_detected"}
            
            return {"is_cleaning_related": False, "activity_type": "idle"}
            
        except Exception as e:
            return {"is_cleaning_related": False, "activity_type": f"detection_error_{e}"}
    
    async def _determine_log_mode_and_filename(self, log_reason: str) -> Tuple[LoggingMode, str]:
        """Determine logging mode and generate appropriate filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        if log_reason == "baseline_capture":
            mode = LoggingMode.BASELINE
            filename = f"key180_baseline_{timestamp}.json"
        elif "significant_change" in log_reason:
            mode = LoggingMode.SMART_MONITORING
            filename = f"key180_significant_change_{timestamp}.json"
        elif "cleaning_activity" in log_reason:
            mode = LoggingMode.CLEANING_DETECTED
            filename = f"key180_cleaning_activity_{timestamp}.json"
        elif log_reason.startswith("manual_"):
            mode = LoggingMode.MANUAL_TRIGGER
            filename = f"key180_manual_{log_reason}_{timestamp}.json"
        else:
            mode = LoggingMode.SMART_MONITORING
            filename = f"key180_monitoring_{timestamp}.json"
        
        return mode, filename
    
    async def _create_enhanced_analysis(self, key180_raw: str, full_raw_data: Dict[str, Any], 
                                       log_mode: LoggingMode, log_reason: str, 
                                       sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive analysis with sensors config integration."""
        analysis = {
            "metadata": {
                "device_id": self.device_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "log_mode": log_mode.value,
                "log_reason": log_reason,
                "update_number": self.total_updates_received,
                "smart_logger_version": "3.0_enhanced",
                "file_number": self.meaningful_logs_created + 1,
                "self_contained": True,
                "includes_sensors_config": True
            },
            "smart_logging_info": {
                "total_updates_received": self.total_updates_received,
                "meaningful_logs_created": self.meaningful_logs_created,
                "duplicates_skipped": self.duplicates_skipped,
                "logging_efficiency": f"{(self.duplicates_skipped / max(1, self.total_updates_received) * 100):.1f}% duplicates avoided"
            },
            "key_180_data": {
                "raw_base64": key180_raw,
                "length": len(key180_raw),
                "data_hash": hashlib.md5(key180_raw.encode()).hexdigest()
            },
            "change_analysis": {},
            "context_data": self._extract_efficient_context(full_raw_data),
            # NEW: Complete sensors configuration reference
            "sensors_reference": await self._create_sensors_reference(sensors_config),
            # NEW: Enhanced accessory analysis with config comparison
            "accessory_analysis": await self._create_enhanced_accessory_analysis(key180_raw, sensors_config)
        }
        
        # Add detailed byte analysis only for baseline and significant changes
        if log_mode in [LoggingMode.BASELINE, LoggingMode.CLEANING_DETECTED] or "significant_change" in log_reason:
            analysis["detailed_byte_analysis"] = await self._create_detailed_byte_analysis(key180_raw, sensors_config)
        
        # Add comparison if we have previous data
        if self.last_logged_data and self.last_logged_data != key180_raw:
            analysis["change_analysis"] = await self._analyze_change_significance(key180_raw, self.last_logged_data)
        
        return analysis
    
    async def _create_sensors_reference(self, sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete sensors configuration reference for self-contained analysis."""
        try:
            template_config = sensors_config.get("template_config", {})
            device_config = sensors_config.get("device_config", {})
            
            reference = {
                "config_availability": {
                    "template_available": sensors_config.get("template_available", False),
                    "device_config_available": sensors_config.get("device_config_available", False),
                    "load_timestamp": sensors_config.get("load_timestamp")
                },
                "android_app_percentages": {},
                "investigation_targets": {},
                "known_byte_positions": {},
                "template_inheritance_status": device_config.get("device_info", {}).get("inherited_from_template", False)
            }
            
            # Extract Android app percentages from template
            template_sensors = template_config.get("accessory_sensors", {})
            for sensor_id, sensor_data in template_sensors.items():
                reference["android_app_percentages"][sensor_id] = {
                    "name": sensor_data.get("name"),
                    "percentage": sensor_data.get("current_life_remaining"),
                    "byte_position": sensor_data.get("byte_position"),
                    "enabled": sensor_data.get("enabled", False),
                    "investigation_target": sensor_data.get("investigation_target", False)
                }
                
                if sensor_data.get("investigation_target"):
                    reference["investigation_targets"][sensor_id] = {
                        "name": sensor_data.get("name"),
                        "expected_percentage": sensor_data.get("current_life_remaining"),
                        "search_strategy": sensor_data.get("search_strategy"),
                        "notes": sensor_data.get("notes")
                    }
                
                # Track known positions
                pos = sensor_data.get("byte_position")
                if isinstance(pos, int):
                    reference["known_byte_positions"][str(pos)] = {
                        "accessory": sensor_data.get("name"),
                        "expected_percentage": sensor_data.get("current_life_remaining"),
                        "source": "template"
                    }
            
            # Extract current device config
            device_sensors = device_config.get("accessory_sensors", {})
            reference["current_device_config"] = {}
            for sensor_id, sensor_data in device_sensors.items():
                reference["current_device_config"][sensor_id] = {
                    "name": sensor_data.get("name"),
                    "percentage": sensor_data.get("current_life_remaining"),
                    "byte_position": sensor_data.get("byte_position"),
                    "enabled": sensor_data.get("enabled", False),
                    "last_updated": sensor_data.get("last_updated")
                }
                
                # Override known positions with device config if available
                pos = sensor_data.get("byte_position")
                if isinstance(pos, int):
                    reference["known_byte_positions"][str(pos)] = {
                        "accessory": sensor_data.get("name"),
                        "expected_percentage": sensor_data.get("current_life_remaining"),
                        "source": "device_config"
                    }
            
            # Investigation workflow instructions
            reference["investigation_workflow"] = [
                "1. Compare detected bytes with android_app_percentages",
                "2. Look for exact matches (Position 15: 97% = Brush Guard 97%)",
                "3. Run cleaning cycle and check for 1-3% decreases",
                "4. Update byte_position in sensors config when confirmed",
                "5. Enable sensor and test accuracy over multiple cycles"
            ]
            
            # Current investigation status
            reference["current_investigation_focus"] = {
                "suspected_position": 15,
                "detected_percentage": "TBD - check detailed_byte_analysis",
                "expected_accessory": "Brush Guard",
                "expected_percentage": 97,
                "match_confidence": "TBD - exact match pending cleaning test",
                "next_step": "Run cleaning cycle, capture post-cleaning, verify decrease"
            }
            
            return reference
            
        except Exception as e:
            return {
                "error": f"Failed to create sensors reference: {e}",
                "config_availability": {
                    "template_available": False,
                    "device_config_available": False,
                    "error": str(e)
                }
            }
    
    async def _create_enhanced_accessory_analysis(self, key180_raw: str, sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced accessory analysis with config comparison."""
        try:
            binary_data = base64.b64decode(key180_raw)
            
            # Get known positions from config
            known_positions = self._extract_known_positions_from_config(sensors_config)
            
            analysis = {
                "total_bytes": len(binary_data),
                "hex_dump": binary_data.hex(),
                "known_positions_analysis": {},
                "percentage_candidates": [],
                "position_confidence_map": {}
            }
            
            # Analyze known positions with enhanced confidence
            for pos in known_positions:
                if pos < len(binary_data):
                    byte_val = binary_data[pos]
                    accessory_info = self._find_accessory_for_position(pos, sensors_config)
                    
                    analysis["known_positions_analysis"][str(pos)] = {
                        "position": pos,
                        "byte_value": byte_val,
                        "hex": f"0x{byte_val:02x}",
                        "accessory_info": accessory_info,
                        "confidence": self._calculate_position_confidence(pos, byte_val, accessory_info),
                        "is_percentage": 1 <= byte_val <= 100
                    }
            
            # Enhanced percentage candidates analysis
            for i, byte_val in enumerate(binary_data):
                if 1 <= byte_val <= 100:
                    accessory_info = self._find_accessory_for_position(i, sensors_config)
                    
                    analysis["percentage_candidates"].append({
                        "position": i,
                        "value": byte_val,
                        "hex": f"0x{byte_val:02x}",
                        "accessory_candidate": accessory_info.get("name", "unknown"),
                        "config_match": accessory_info.get("config_match", False),
                        "confidence": self._calculate_position_confidence(i, byte_val, accessory_info)
                    })
            
            return analysis
            
        except Exception as e:
            return {"error": f"Enhanced accessory analysis failed: {e}"}
    
    async def _create_detailed_byte_analysis(self, key180_raw: str, sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed byte analysis enhanced with sensors config data."""
        try:
            binary_data = base64.b64decode(key180_raw)
            
            # Get known positions from config
            known_positions = self._extract_known_positions_from_config(sensors_config)
            
            analysis = {
                "total_bytes": len(binary_data),
                "percentage_candidates": [],
                "config_position_analysis": {},
                "android_app_comparison": {},
                "position_15_focus": {}
            }
            
            # Find all percentage candidates (1-100 range)
            for i, byte_val in enumerate(binary_data):
                if 1 <= byte_val <= 100:
                    analysis["percentage_candidates"].append({
                        "position": i,
                        "value": byte_val,
                        "hex": f"0x{byte_val:02x}"
                    })
            
            # Analyze known positions from config
            template_sensors = sensors_config.get("template_config", {}).get("accessory_sensors", {})
            for sensor_id, sensor_data in template_sensors.items():
                pos = sensor_data.get("byte_position")
                expected_pct = sensor_data.get("current_life_remaining")
                
                if isinstance(pos, int) and pos < len(binary_data):
                    detected_val = binary_data[pos]
                    
                    analysis["config_position_analysis"][sensor_id] = {
                        "position": pos,
                        "expected_percentage": expected_pct,
                        "detected_value": detected_val,
                        "match": detected_val == expected_pct if expected_pct else False,
                        "difference": abs(detected_val - expected_pct) if expected_pct else None,
                        "accessory_name": sensor_data.get("name"),
                        "enabled": sensor_data.get("enabled", False)
                    }
            
            # Android app comparison for all percentage candidates
            for candidate in analysis["percentage_candidates"]:
                pos = candidate["position"]
                val = candidate["value"]
                
                # Find matching Android app percentages
                matches = []
                for sensor_id, sensor_data in template_sensors.items():
                    expected = sensor_data.get("current_life_remaining")
                    if expected and abs(val - expected) <= 2:  # Within 2% tolerance
                        matches.append({
                            "sensor_id": sensor_id,
                            "accessory_name": sensor_data.get("name"),
                            "expected_percentage": expected,
                            "difference": abs(val - expected),
                            "exact_match": val == expected
                        })
                
                if matches:
                    analysis["android_app_comparison"][str(pos)] = {
                        "position": pos,
                        "detected_value": val,
                        "matches": matches,
                        "best_match": min(matches, key=lambda x: x["difference"])
                    }
            
            # Special focus on Position 15 (suspected Brush Guard)
            if 15 < len(binary_data):
                pos_15_value = binary_data[15]
                analysis["position_15_focus"] = {
                    "position": 15,
                    "detected_value": pos_15_value,
                    "suspected_accessory": "Brush Guard",
                    "expected_percentage": 97,  # From Android app
                    "exact_match": pos_15_value == 97,
                    "difference": abs(pos_15_value - 97),
                    "confidence": "very_high" if pos_15_value == 97 else "medium",
                    "testing_recommendation": "Run cleaning cycle and verify this position decreases by 1-3%",
                    "confirmation_status": "pending_cleaning_test"
                }
            
            return analysis
            
        except Exception as e:
            return {"error": f"Enhanced detailed byte analysis failed: {e}"}
    
    def _extract_efficient_context(self, full_raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only essential context data to keep files smaller."""
        relevant_keys = ["163", "167", "168", "158", "153"]
        context = {}
        
        for key in relevant_keys:
            if key in full_raw_data:
                context[f"key_{key}"] = full_raw_data[key]
        
        context["total_keys_available"] = len(full_raw_data)
        return context
    
    async def _update_state_after_logging(self, key180_raw: str, data_hash: str, 
                                        log_mode: LoggingMode, filepath: Path) -> None:
        """Update internal state after successful logging."""
        self.last_key180_hash = data_hash
        self.last_logged_data = key180_raw
        self.last_log_time = datetime.now()
        
        if log_mode == LoggingMode.BASELINE:
            self.baseline_captured = True
            self.current_mode = LoggingMode.SMART_MONITORING
            _LOGGER.info("🎯 Enhanced baseline captured with sensors config, switching to smart monitoring mode")
    
    async def _cleanup_old_files(self) -> None:
        """Cleanup old monitoring files to prevent bloat."""
        try:
            # Get all monitoring files
            monitoring_files = list(self.investigation_dir.glob("key180_monitoring_*.json"))
            
            if len(monitoring_files) > self.max_monitoring_files:
                # Sort by modification time and remove oldest
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
        """Manually capture baseline with enhanced sensors config."""
        if "180" not in raw_data:
            return None
        
        # Force baseline logging
        original_baseline_state = self.baseline_captured
        self.baseline_captured = False
        
        result = await self.process_key180_update(raw_data)
        
        if not result:
            self.baseline_captured = original_baseline_state
        
        return result
    
    async def capture_post_cleaning(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Manually capture post-cleaning data with enhanced analysis."""
        if "180" not in raw_data:
            return None
        
        # Force post-cleaning log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"key180_post_cleaning_{timestamp}.json"
        
        # Load sensors config for enhanced analysis
        sensors_config = await self._load_sensors_config()
        
        analysis_data = await self._create_enhanced_analysis(
            raw_data["180"], raw_data, LoggingMode.POST_CLEANING, "manual_post_cleaning", sensors_config
        )
        
        filepath = self.investigation_dir / filename
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
        
        await self._update_state_after_logging(raw_data["180"], 
                                             hashlib.md5(raw_data["180"].encode()).hexdigest(),
                                             LoggingMode.POST_CLEANING, filepath)
        
        self.meaningful_logs_created += 1
        return str(filepath)
    
    async def generate_session_summary(self) -> str:
        """Generate enhanced session summary with sensors config analysis."""
        summary_file = self.investigation_dir / f"enhanced_session_summary_{self.session_id}.json"
        
        # Analyze all files in this session
        session_files = [f for f in self.investigation_dir.glob("*.json") if self.session_id in f.name]
        
        # Load sensors config for summary
        sensors_config = await self._load_sensors_config()
        
        summary = {
            "session_info": {
                "session_id": self.session_id,
                "device_id": self.device_id,
                "start_time": self.session_id,
                "end_time": datetime.now().isoformat(),
                "enhanced_logger_version": "3.0",
                "sensors_config_integration": True
            },
            "efficiency_stats": {
                "total_updates_received": self.total_updates_received,
                "meaningful_logs_created": self.meaningful_logs_created,
                "duplicates_skipped": self.duplicates_skipped,
                "logging_efficiency": f"{(self.duplicates_skipped / max(1, self.total_updates_received) * 100):.1f}%",
                "file_reduction": f"Reduced from {self.total_updates_received} to {self.meaningful_logs_created} files"
            },
            "files_created": [f.name for f in session_files],
            "investigation_directory": str(self.investigation_dir),
            "sensors_config_summary": await self._create_sensors_reference(sensors_config),
            "enhanced_features": [
                "✅ Self-contained analysis files with complete reference data",
                "✅ Android app percentages included for comparison",
                "✅ Position 15 (97%) focus for Brush Guard confirmation", 
                "✅ Enhanced change detection with config validation",
                "✅ Complete audit trail with sensors configuration"
            ],
            "analysis_recommendations": [
                "1. Check Position 15 analysis in baseline file for Brush Guard match",
                "2. Run cleaning cycle and capture post-cleaning data",
                "3. Compare Position 15 before/after for 1-3% decrease",
                "4. If confirmed, update sensors config with Position 15 = Brush Guard",
                "5. Repeat process for other accessories using Android app percentages"
            ]
        }
        
        try:
            async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            _LOGGER.info("📋 Enhanced session summary created: %s", summary_file.name)
            _LOGGER.info("📊 Enhanced efficiency: %d updates → %d self-contained files", 
                        self.total_updates_received, self.meaningful_logs_created)
            
            return str(summary_file)
            
        except Exception as e:
            _LOGGER.error("❌ Failed to create enhanced session summary: %s", e)
            return ""
    
    def get_smart_status(self) -> Dict[str, Any]:
        """Get current enhanced smart logging status."""
        return {
            "mode": self.current_mode.value,
            "baseline_captured": self.baseline_captured,
            "session_id": self.session_id,
            "total_updates": self.total_updates_received,
            "meaningful_logs": self.meaningful_logs_created,
            "duplicates_skipped": self.duplicates_skipped,
            "efficiency_percentage": (self.duplicates_skipped / max(1, self.total_updates_received)) * 100,
            "last_log_time": self.last_log_time.isoformat() if self.last_log_time else None,
            "investigation_directory": str(self.investigation_dir),
            "enhanced_features": True,
            "sensors_config_integration": self.sensors_config_file is not None,
            "version": "3.0_enhanced"
        }
    
    def get_investigation_directory(self) -> str:
        """Get investigation directory path."""
        return str(self.investigation_dir)
    
    def get_session_id(self) -> str:
        """Get current session ID."""
        return self.session_id