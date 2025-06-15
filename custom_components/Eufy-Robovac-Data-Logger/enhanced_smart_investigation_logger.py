"""
Enhanced Smart Investigation Logger for Multi-Key Accessory Wear Detection
VERSION 4.0: Expanded from Key 180 only to ALL monitored keys with same analysis infrastructure.
Each key gets the same detailed logging, analysis, and tracking as Key 180.
GOAL: Find where water tank, battery, and accessory data moved in Eufy API updates.
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


class EnhancedSmartMultiKeyInvestigationLogger:
    """
    Enhanced Smart Investigation Logger with multi-key support.
    Replicates Key 180 analysis infrastructure for ALL monitored keys.
    Creates self-contained analysis files with complete reference data for each key.
    Reduces file bloat by only logging meaningful changes across all keys.
    """
    
    def __init__(self, device_id: str, hass_config_dir: str, integration_dir: Optional[str] = None, monitored_keys: Optional[List[str]] = None):
        self.device_id = device_id
        self.hass_config_dir = hass_config_dir
        
        # Multi-key support - default to comprehensive key list
        self.monitored_keys = monitored_keys or [
            "152", "153", "154", "157", "158", "161", "162", "163", "164", "165",
            "166", "167", "168", "169", "170", "172", "173", "176", "177", "178", 
            "179", "180"
        ]
        
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
        
        # Smart logging state - now tracks ALL keys
        self.current_mode = LoggingMode.BASELINE
        self.baseline_captured = False
        self.last_multi_key_hash = None
        self.last_logged_data = {}  # Store last data for each key
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
        
        # Multi-key tracking
        self.key_change_counts = {key: 0 for key in self.monitored_keys}
        self.key_last_values = {key: None for key in self.monitored_keys}
        
        # Sensors config cache
        self._sensors_config_cache = None
        self._device_config_cache = None
        self._config_load_time = None
        
        _LOGGER.info("🔍 Enhanced Smart Multi-Key Investigation Logger v4.0 initialized")
        _LOGGER.info("📂 Investigation directory: %s", self.investigation_dir)
        _LOGGER.info("🗂️ Monitoring %d keys: %s", len(self.monitored_keys), ", ".join(self.monitored_keys))
        _LOGGER.info("🔧 Sensors config: %s", self.sensors_config_file if self.sensors_config_file else "Not available")
        _LOGGER.info("🧠 Mode: %s", self.current_mode.value)
        _LOGGER.info("✨ NEW: Multi-key analysis with same infrastructure as Key 180")
    
    async def _load_sensors_config(self) -> Dict[str, Any]:
        """Load sensors.json configuration for reference data."""
        try:
            # Check cache first (5 minute cache)
            current_time = datetime.now()
            if (self._sensors_config_cache and self._config_load_time and 
                (current_time - self._config_load_time).total_seconds() < 300):
                return self._sensors_config_cache
            
            if not self.sensors_config_file or not self.sensors_config_file.exists():
                _LOGGER.warning("⚠️ Sensors config file not found: %s", self.sensors_config_file)
                return {}
            
            async with aiofiles.open(self.sensors_config_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                self._sensors_config_cache = json.loads(content)
                self._config_load_time = current_time
                _LOGGER.debug("📋 Loaded sensors config with %d accessories", 
                             len(self._sensors_config_cache.get('accessories', {})))
                return self._sensors_config_cache
        
        except Exception as e:
            _LOGGER.warning("⚠️ Failed to load sensors config: %s", e)
            return {}
    
    async def process_multi_key_update(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        Process multi-key update with same analysis as Key 180.
        
        Args:
            raw_data: Complete raw API data with all keys
        
        Returns:
            Path to created file or None if no logging needed
        """
        try:
            self.total_updates_received += 1
            
            # Extract monitored keys that have data
            available_keys = {key: raw_data[key] for key in self.monitored_keys if key in raw_data and raw_data[key] is not None}
            
            if not available_keys:
                _LOGGER.debug("🔍 No monitored keys available in update")
                return None
            
            # Calculate combined hash for change detection
            combined_data = json.dumps(available_keys, sort_keys=True)
            data_hash = hashlib.md5(combined_data.encode()).hexdigest()
            
            # Smart decision: Should we log this update?
            should_log, log_reason = await self._should_log_multi_key_update(available_keys, data_hash, raw_data)
            
            if not should_log:
                self.duplicates_skipped += 1
                return None
            
            # Determine appropriate logging mode and filename
            log_mode, filename = await self._determine_log_mode_and_filename(log_reason)
            
            # Load sensors config for enhanced analysis
            sensors_config = await self._load_sensors_config()
            
            # Create comprehensive multi-key analysis
            analysis_data = await self._create_enhanced_multi_key_analysis(
                available_keys, raw_data, log_mode, log_reason, sensors_config
            )
            
            # Write to file
            filepath = self.investigation_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            
            # Update state tracking
            await self._update_state_after_logging(available_keys, data_hash, log_mode, filepath)
            
            # Cleanup old files if needed
            if self.auto_cleanup_enabled:
                await self._cleanup_old_files()
            
            self.meaningful_logs_created += 1
            
            _LOGGER.info("📊 Enhanced multi-key log created: %s (Reason: %s, Keys: %d)", 
                        filename, log_reason, len(available_keys))
            _LOGGER.debug("📈 Stats: %d updates, %d logged, %d skipped", 
                         self.total_updates_received, self.meaningful_logs_created, self.duplicates_skipped)
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error("❌ Enhanced multi-key investigation processing failed: %s", e)
            return None
    
    async def _should_log_multi_key_update(self, available_keys: Dict[str, Any], data_hash: str, raw_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Intelligent decision on whether to log this multi-key update."""
        
        # Always log if no baseline captured
        if not self.baseline_captured:
            return True, "baseline_capture"
        
        # Don't log too frequently
        if (self.last_log_time and 
            (datetime.now() - self.last_log_time).total_seconds() < self.min_log_interval_seconds):
            return False, "too_frequent"
        
        # Check for duplicate data
        if self.last_multi_key_hash == data_hash:
            return False, "duplicate_data"
        
        # Check for significant changes in any key
        significant_changes = []
        for key, current_value in available_keys.items():
            last_value = self.key_last_values.get(key)
            if last_value is not None and last_value != current_value:
                # Analyze the change
                change_significance = await self._analyze_key_change_significance(key, last_value, current_value)
                if change_significance["significant"]:
                    significant_changes.append(f"Key {key}: {change_significance['description']}")
        
        if significant_changes:
            return True, f"significant_changes: {', '.join(significant_changes[:3])}"  # Limit to first 3
        
        # Check for potential cleaning activity (look for work status changes)
        if "153" in available_keys:  # Work status key
            work_status_change = await self._detect_cleaning_activity(available_keys["153"])
            if work_status_change:
                return True, f"cleaning_activity: {work_status_change}"
        
        # Log periodically even without changes (monitoring mode)
        if (self.last_log_time and 
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
                    # Not valid base64, treat as string change
                    return {
                        "significant": True,
                        "description": "String value changed",
                        "type": "string_change",
                        "magnitude": 1
                    }
        
        return {"significant": False, "description": "No significant change", "type": "unchanged", "magnitude": 0}
    
    async def _detect_cleaning_activity(self, work_status_value: Any) -> Optional[str]:
        """Detect cleaning activity from work status key."""
        # This is a placeholder - would need to decode the actual work status format
        # For now, just detect any change in work status
        last_work_status = self.key_last_values.get("153")
        if last_work_status and last_work_status != work_status_value:
            return f"work_status_change"
        return None
    
    async def _determine_log_mode_and_filename(self, log_reason: str) -> Tuple[LoggingMode, str]:
        """Determine logging mode and filename for multi-key logging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        if log_reason == "baseline_capture":
            mode = LoggingMode.BASELINE
            filename = f"multi_key_baseline_{timestamp}.json"
        elif "significant_changes" in log_reason:
            mode = LoggingMode.SMART_MONITORING
            filename = f"multi_key_significant_change_{timestamp}.json"
        elif "cleaning_activity" in log_reason:
            mode = LoggingMode.CLEANING_DETECTED
            filename = f"multi_key_cleaning_activity_{timestamp}.json"
        elif log_reason.startswith("manual_"):
            mode = LoggingMode.MANUAL_TRIGGER
            filename = f"multi_key_manual_{log_reason}_{timestamp}.json"
        else:
            mode = LoggingMode.SMART_MONITORING
            filename = f"multi_key_monitoring_{timestamp}.json"
        
        return mode, filename
    
    async def _create_enhanced_multi_key_analysis(self, available_keys: Dict[str, Any], full_raw_data: Dict[str, Any], 
                                                 log_mode: LoggingMode, log_reason: str, 
                                                 sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive multi-key analysis with same structure as Key 180."""
        
        analysis = {
            "metadata": {
                "device_id": self.device_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "log_mode": log_mode.value,
                "log_reason": log_reason,
                "update_number": self.total_updates_received,
                "smart_logger_version": "4.0_multi_key",
                "file_number": self.meaningful_logs_created + 1,
                "self_contained": True,
                "includes_sensors_config": True,
                "monitored_keys_count": len(self.monitored_keys),
                "available_keys_count": len(available_keys)
            },
            "smart_logging_info": {
                "total_updates_received": self.total_updates_received,
                "meaningful_logs_created": self.meaningful_logs_created,
                "duplicates_skipped": self.duplicates_skipped,
                "logging_efficiency": f"{(self.duplicates_skipped / max(1, self.total_updates_received) * 100):.1f}% duplicates avoided",
                "monitored_keys": self.monitored_keys,
                "available_keys": list(available_keys.keys()),
                "missing_keys": [key for key in self.monitored_keys if key not in available_keys]
            },
            "multi_key_data": {},  # Each key gets same analysis as Key 180
            "change_analysis": {},
            "context_data": self._extract_efficient_context(full_raw_data),
            "sensors_reference": await self._create_sensors_reference(sensors_config),
            "cross_key_analysis": await self._create_cross_key_analysis(available_keys, sensors_config),
            "search_results": await self._search_for_known_values(available_keys)
        }
        
        # Analyze each key with same infrastructure as Key 180
        for key, value in available_keys.items():
            analysis["multi_key_data"][f"key_{key}_data"] = await self._create_single_key_analysis(key, value, sensors_config)
        
        # Add change analysis if we have previous data
        if self.last_logged_data:
            analysis["change_analysis"] = await self._analyze_multi_key_changes(available_keys, self.last_logged_data)
        
        return analysis
    
    async def _create_single_key_analysis(self, key: str, value: Any, sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed analysis for a single key using same structure as Key 180."""
        
        key_analysis = {
            "raw_data": value,
            "data_type": type(value).__name__,
            "length": len(str(value)),
            "data_hash": hashlib.md5(str(value).encode()).hexdigest(),
            "analysis": {}
        }
        
        # Numeric analysis (potential percentages/battery/water tank)
        if isinstance(value, (int, float)):
            key_analysis["analysis"]["numeric"] = {
                "value": value,
                "is_percentage_range": self.accessory_value_range[0] <= value <= self.accessory_value_range[1],
                "potential_battery": key in ["163", "162", "168"] and 0 <= value <= 100,
                "potential_water_tank": key in ["161", "167", "177", "179"] and 0 <= value <= 100,
                "potential_accessory_wear": 0 <= value <= 100
            }
        
        # Base64 analysis (same as Key 180)
        elif isinstance(value, str) and len(value) > 4:
            try:
                decoded_data = base64.b64decode(value)
                key_analysis["analysis"]["base64"] = {
                    "is_valid_base64": True,
                    "decoded_length": len(decoded_data),
                    "decoded_hex": decoded_data.hex()[:100],  # First 50 bytes
                    "percentage_candidates": []
                }
                
                # Search for percentage-like bytes (same as Key 180)
                for i, byte_val in enumerate(decoded_data):
                    if self.accessory_value_range[0] <= byte_val <= self.accessory_value_range[1]:
                        key_analysis["analysis"]["base64"]["percentage_candidates"].append({
                            "position": i,
                            "value": byte_val,
                            "hex": f"0x{byte_val:02x}"
                        })
                
            except Exception as e:
                key_analysis["analysis"]["base64"] = {
                    "is_valid_base64": False,
                    "decode_error": str(e)
                }
        
        # Add previous value comparison
        last_value = self.key_last_values.get(key)
        if last_value is not None:
            change_analysis = await self._analyze_key_change_significance(key, last_value, value)
            key_analysis["change_from_last"] = change_analysis
        
        return key_analysis
    
    async def _create_cross_key_analysis(self, available_keys: Dict[str, Any], sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze relationships and patterns across all keys."""
        
        cross_analysis = {
            "water_tank_candidates": {},
            "battery_candidates": {},
            "accessory_wear_candidates": {},
            "correlation_matrix": {},
            "value_distribution": {}
        }
        
        # Search for water tank candidates (looking for ~50-53%)
        for key, value in available_keys.items():
            if isinstance(value, (int, float)) and 45 <= value <= 60:
                cross_analysis["water_tank_candidates"][key] = {
                    "value": value,
                    "confidence": "high" if 50 <= value <= 55 else "medium"
                }
        
        # Search for battery candidates (looking for ~93% from your data)
        for key, value in available_keys.items():
            if isinstance(value, (int, float)) and 80 <= value <= 100:
                cross_analysis["battery_candidates"][key] = {
                    "value": value,
                    "confidence": "high" if 90 <= value <= 95 else "medium"
                }
        
        # Search for accessory wear patterns in base64 data
        for key, value in available_keys.items():
            if isinstance(value, str):
                try:
                    decoded_data = base64.b64decode(value)
                    wear_candidates = []
                    for i, byte_val in enumerate(decoded_data):
                        if 90 <= byte_val <= 100:  # High wear percentages
                            wear_candidates.append({"position": i, "value": byte_val})
                    if wear_candidates:
                        cross_analysis["accessory_wear_candidates"][key] = wear_candidates
                except:
                    pass
        
        return cross_analysis
    
    async def _search_for_known_values(self, available_keys: Dict[str, Any]) -> Dict[str, Any]:
        """Search for known values like water tank (50), battery (93), etc."""
        
        search_results = {
            "water_tank_50_search": [],
            "battery_93_search": [],
            "speed_3_search": [],
            "percentage_values": [],
            "summary": {}
        }
        
        # Search for water tank value (50 from your data)
        for key, value in available_keys.items():
            if value == 50:
                search_results["water_tank_50_search"].append({
                    "key": key,
                    "value": value,
                    "type": type(value).__name__,
                    "confidence": "exact_match"
                })
        
        # Search for battery value (93 from your data)  
        for key, value in available_keys.items():
            if value == 93:
                search_results["battery_93_search"].append({
                    "key": key,
                    "value": value,
                    "type": type(value).__name__,
                    "confidence": "exact_match"
                })
        
        # Search for speed value (3 from your data)
        for key, value in available_keys.items():
            if value == 3:
                search_results["speed_3_search"].append({
                    "key": key,
                    "value": value,
                    "type": type(value).__name__,
                    "confidence": "exact_match"
                })
        
        # Collect all percentage-like values
        for key, value in available_keys.items():
            if isinstance(value, (int, float)) and 0 <= value <= 100:
                search_results["percentage_values"].append({
                    "key": key,
                    "value": value,
                    "potential_meaning": self._guess_percentage_meaning(key, value)
                })
        
        # Create search summary
        search_results["summary"] = {
            "water_tank_candidates": len(search_results["water_tank_50_search"]),
            "battery_candidates": len(search_results["battery_93_search"]), 
            "speed_candidates": len(search_results["speed_3_search"]),
            "total_percentage_values": len(search_results["percentage_values"]),
            "most_likely_water_tank": search_results["water_tank_50_search"][0]["key"] if search_results["water_tank_50_search"] else None,
            "most_likely_battery": search_results["battery_93_search"][0]["key"] if search_results["battery_93_search"] else None
        }
        
        return search_results
    
    def _guess_percentage_meaning(self, key: str, value: int) -> str:
        """Guess what a percentage value might represent based on key and value."""
        if key == "161" and 45 <= value <= 60:
            return "likely_water_tank"
        elif key == "163" and 80 <= value <= 100:
            return "likely_battery"
        elif key == "158" and 0 <= value <= 5:
            return "likely_speed_setting"
        elif 95 <= value <= 100:
            return "likely_accessory_wear"
        elif 80 <= value <= 100:
            return "possible_battery_or_wear"
        elif 40 <= value <= 70:
            return "possible_water_tank"
        else:
            return "unknown_percentage"
    
    async def _analyze_multi_key_changes(self, current_keys: Dict[str, Any], last_keys: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze changes across all keys since last logging."""
        
        changes = {
            "summary": {
                "total_keys_changed": 0,
                "significant_changes": 0,
                "new_keys": [],
                "removed_keys": [],
                "unchanged_keys": []
            },
            "key_changes": {}
        }
        
        # Find new and removed keys
        current_key_set = set(current_keys.keys())
        last_key_set = set(last_keys.keys())
        
        changes["summary"]["new_keys"] = list(current_key_set - last_key_set)
        changes["summary"]["removed_keys"] = list(last_key_set - current_key_set)
        
        # Analyze changes in common keys
        common_keys = current_key_set & last_key_set
        
        for key in common_keys:
            current_value = current_keys[key]
            last_value = last_keys[key]
            
            if current_value != last_value:
                change_analysis = await self._analyze_key_change_significance(key, last_value, current_value)
                changes["key_changes"][key] = change_analysis
                changes["summary"]["total_keys_changed"] += 1
                
                if change_analysis["significant"]:
                    changes["summary"]["significant_changes"] += 1
            else:
                changes["summary"]["unchanged_keys"].append(key)
        
        return changes
    
    async def _create_sensors_reference(self, sensors_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete sensors configuration reference for self-contained analysis."""
        if not sensors_config:
            return {"error": "No sensors configuration available"}
        
        reference = {
            "config_loaded": True,
            "config_timestamp": datetime.now().isoformat(),
            "accessories": sensors_config.get("accessories", {}),
            "discovery_settings": sensors_config.get("discovery_settings", {}),
            "template_info": {
                "purpose": "Android app percentages for comparison",
                "usage": "Compare detected values with these expected percentages",
                "note": "Values should decrease by 1-3% after cleaning cycles"
            }
        }
        
        return reference
    
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
        
        # Add first 5 characters of each monitored key for quick reference
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
            # Get all monitoring files
            monitoring_files = list(self.investigation_dir.glob("multi_key_monitoring_*.json"))
            
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
    
    # Manual trigger methods - updated for multi-key
    async def capture_baseline(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Manually capture baseline with multi-key support."""
        # Force baseline logging
        original_baseline_state = self.baseline_captured
        self.baseline_captured = False
        
        result = await self.process_multi_key_update(raw_data)
        
        if not result:
            self.baseline_captured = original_baseline_state
        
        return result
    
    async def capture_post_cleaning(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Manually capture post-cleaning data with multi-key analysis."""
        # Force post-cleaning log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"multi_key_post_cleaning_{timestamp}.json"
        
        # Extract available keys
        available_keys = {key: raw_data[key] for key in self.monitored_keys if key in raw_data and raw_data[key] is not None}
        
        if not available_keys:
            return None
        
        # Load sensors config for enhanced analysis
        sensors_config = await self._load_sensors_config()
        
        analysis_data = await self._create_enhanced_multi_key_analysis(
            available_keys, raw_data, LoggingMode.POST_CLEANING, "manual_post_cleaning", sensors_config
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
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_key_session_summary_{self.session_id}_{timestamp}.json"
            
            # Collect all investigation files from this session
            session_files = list(self.investigation_dir.glob(f"multi_key_*{self.session_id[:8]}*.json"))
            session_files.extend(list(self.investigation_dir.glob("multi_key_*.json")))
            
            # Load sensors config
            sensors_config = await self._load_sensors_config()
            
            summary = {
                "metadata": {
                    "session_id": self.session_id,
                    "device_id": self.device_id,
                    "generation_timestamp": datetime.now().isoformat(),
                    "summary_version": "4.0_multi_key",
                    "total_monitored_keys": len(self.monitored_keys),
                    "session_files_analyzed": len(session_files)
                },
                "session_statistics": {
                    "total_updates_received": self.total_updates_received,
                    "meaningful_logs_created": self.meaningful_logs_created,
                    "duplicates_skipped": self.duplicates_skipped,
                    "efficiency_percentage": round((self.duplicates_skipped / max(1, self.total_updates_received)) * 100, 1),
                    "key_change_counts": self.key_change_counts,
                    "most_active_keys": sorted(self.key_change_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                },
                "multi_key_summary": {
                    "monitored_keys": self.monitored_keys,
                    "last_known_values": self.key_last_values,
                    "baseline_captured": self.baseline_captured,
                    "current_mode": self.current_mode.value
                },
                "sensors_reference": await self._create_sensors_reference(sensors_config),
                "investigation_workflow": {
                    "next_steps": [
                        "1. Review water_tank_candidates for value ~50",
                        "2. Review battery_candidates for value ~93", 
                        "3. Run cleaning cycle and capture post_cleaning data",
                        "4. Compare before/after values to find wear patterns",
                        "5. Update sensors.json with discovered positions"
                    ],
                    "key_findings": {
                        "water_tank_candidates": [k for k, v in self.key_last_values.items() if isinstance(v, (int, float)) and 45 <= v <= 60],
                        "battery_candidates": [k for k, v in self.key_last_values.items() if isinstance(v, (int, float)) and 80 <= v <= 100],
                        "speed_candidates": [k for k, v in self.key_last_values.items() if v == 3]
                    }
                }
            }
            
            # Write summary file
            filepath = self.investigation_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            _LOGGER.info("📋 Multi-key session summary generated: %s", filename)
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error("❌ Session summary generation failed: %s", e)
            return f"Error generating summary: {e}"
    
    def get_smart_status(self) -> Dict[str, Any]:
        """Get current multi-key investigation status."""
        efficiency = round((self.duplicates_skipped / max(1, self.total_updates_received)) * 100, 1)
        
        return {
            "session_id": self.session_id,
            "version": "4.0_multi_key",
            "baseline_captured": self.baseline_captured,
            "current_mode": self.current_mode.value,
            "total_updates": self.total_updates_received,
            "meaningful_logs": self.meaningful_logs_created,
            "duplicates_skipped": self.duplicates_skipped,
            "efficiency_percentage": efficiency,
            "monitored_keys_count": len(self.monitored_keys),
            "investigation_directory": str(self.investigation_dir),
            "last_log_time": self.last_log_time.isoformat() if self.last_log_time else None,
            "key_change_summary": {
                "most_active": max(self.key_change_counts.items(), key=lambda x: x[1]) if self.key_change_counts else None,
                "total_changes": sum(self.key_change_counts.values())
            }
        }
        