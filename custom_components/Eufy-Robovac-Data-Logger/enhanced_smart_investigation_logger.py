"""Enhanced Smart Investigation Logger v4.0 for multi-key Eufy robovac data analysis."""
import json
import hashlib
import asyncio
import aiofiles
from datetime import datetime
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


class EnhancedSmartMultiKeyInvestigationLogger:
    """Enhanced Smart Investigation Logger v4.0 with multi-key support and smart efficiency."""

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
        self.key_last_values = {}  # Track last value for each key
        self.key_change_counts = {key: 0 for key in self.monitored_keys}  # Track changes per key
        
        # Smart logging configuration
        self.min_log_interval_seconds = 30  # Don't log more frequently than every 30 seconds
        self.significant_change_threshold = 2  # Minimum change to be considered significant
        self.accessory_value_range = (0, 100)  # Expected range for accessory percentages
        
        # File management
        self.max_monitoring_files = 10  # Keep last 10 monitoring files per session
        
        _LOGGER.info("🔍 Enhanced Smart Multi-Key Investigation Logger v4.0 initialized")
        _LOGGER.info(f"📁 Investigation directory: {self.investigation_dir}")
        _LOGGER.info(f"🗂️ Monitoring {len(self.monitored_keys)} keys: {', '.join(self.monitored_keys)}")
        _LOGGER.info(f"🔬 Session ID: {self.session_id}")

    async def initialize(self) -> None:
        """Initialize the investigation logger - FIXED: Added missing method."""
        try:
            # Ensure investigation directory exists
            self.investigation_dir.mkdir(parents=True, exist_ok=True)
            
            # Load any existing session state
            await self._load_session_state()
            
            # Initialize sensors config
            await self._load_sensors_config()
            
            _LOGGER.info("✅ Enhanced Smart Multi-Key Investigation Logger v4.0 initialized successfully")
            _LOGGER.info(f"📂 Investigation directory ready: {self.investigation_dir}")
            _LOGGER.info(f"🔬 Session ID: {self.session_id}")
            _LOGGER.info(f"🗂️ Monitoring keys: {', '.join(self.monitored_keys)}")
            
        except Exception as e:
            _LOGGER.error(f"❌ Failed to initialize investigation logger: {e}")
            raise

    async def _load_session_state(self) -> None:
        """Load existing session state if available."""
        try:
            # Check for existing baseline files
            baseline_files = list(self.investigation_dir.glob("multi_key_baseline_*.json"))
            if baseline_files:
                self.baseline_captured = True
                self.current_mode = LoggingMode.SMART_MONITORING
                _LOGGER.info(f"📁 Found {len(baseline_files)} existing baseline files")
            
            # Check for existing monitoring files
            monitoring_files = list(self.investigation_dir.glob("multi_key_monitoring_*.json"))
            if monitoring_files:
                self.meaningful_logs_created = len(monitoring_files)
                _LOGGER.info(f"📊 Found {len(monitoring_files)} existing monitoring files")
                
        except Exception as e:
            _LOGGER.warning(f"⚠️ Could not load session state: {e}")

    async def process_multi_key_update(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Process multi-key update with enhanced smart logging v4.0."""
        try:
            self.total_updates_received += 1
            
            # Extract available monitored keys
            available_keys = {key: raw_data[key] for key in self.monitored_keys if key in raw_data and raw_data[key] is not None}
            
            if not available_keys:
                return None
            
            # Generate data hash for duplicate detection
            combined_data = json.dumps(available_keys, sort_keys=True)
            data_hash = hashlib.md5(combined_data.encode()).hexdigest()
            
            # Smart logging decision
            should_log, log_reason = await self._should_log_multi_key_update(available_keys, data_hash)
            
            if not should_log:
                if log_reason == "duplicate_data":
                    self.duplicates_skipped += 1
                return None
            
            # Determine logging mode and filename
            log_mode, filename = await self._determine_log_mode_and_filename(log_reason)
            
            # Load sensors config for enhanced analysis
            sensors_config = await self._load_sensors_config()
            
            # Create enhanced multi-key analysis
            analysis_data = await self._create_enhanced_multi_key_analysis(
                available_keys, raw_data, log_mode, log_reason, sensors_config
            )
            
            # Write to file
            filepath = self.investigation_dir / filename
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            
            # Update state
            await self._update_state_after_logging(available_keys, data_hash, log_mode, filepath)
            
            self.meaningful_logs_created += 1
            
            # Cleanup old files if needed
            await self._cleanup_old_files()
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error(f"❌ Multi-key processing error: {e}")
            return None

    async def _should_log_multi_key_update(self, available_keys: Dict[str, Any], data_hash: str) -> Tuple[bool, str]:
        """Determine if we should log this multi-key update."""
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
            return LoggingMode.BASELINE, f"multi_key_baseline_{timestamp}.json"
        elif "post_cleaning" in log_reason:
            return LoggingMode.POST_CLEANING, f"multi_key_post_cleaning_{timestamp}.json"
        else:
            return LoggingMode.SMART_MONITORING, f"multi_key_monitoring_{timestamp}.json"
    
    async def _create_enhanced_multi_key_analysis(
        self, 
        available_keys: Dict[str, Any], 
        full_raw_data: Dict[str, Any], 
        log_mode: LoggingMode, 
        log_reason: str,
        sensors_config: Optional[Dict[str, Any]]
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
                "smart_logger_version": "4.0_multi_key",
                "file_number": self.meaningful_logs_created + 1,
                "self_contained": True,
                "includes_sensors_config": sensors_config is not None,
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
        analysis_data["sensors_reference"] = await self._create_sensors_reference(sensors_config)
        
        # Add cross-key analysis for discoveries
        analysis_data["cross_key_analysis"] = await self._perform_cross_key_analysis(available_keys)
        analysis_data["search_results"] = await self._perform_targeted_searches(available_keys)
        
        return analysis_data
    
    async def _analyze_key_value(self, key: str, value: Any) -> Dict[str, Any]:
        """Analyze individual key value for patterns and potential meanings."""
        analysis = {}
        
        if isinstance(value, (int, float)):
            # Numeric analysis
            analysis["numeric"] = {
                "value": value,
                "is_percentage_range": 0 <= value <= 100,
                "potential_battery": value > 0 and key in ["163", "161"],
                "potential_water_tank": value > 0 and key in ["161", "167", "177"],
                "potential_accessory_wear": 0 <= value <= 100
            }
        
        elif isinstance(value, str):
            # String/Base64 analysis
            try:
                # Try to decode as base64
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
            "correlation_matrix": {},
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
                        if 90 <= byte_val <= 100:  # High wear values
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
        # This would search for specific percentage values we're looking for
        # Based on your Android app values
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
        
        # Find most likely candidates
        if search_results["water_tank_50_search"]:
            search_results["summary"]["most_likely_water_tank"] = search_results["water_tank_50_search"][0]["key"]
        
        return search_results
    
    async def _create_sensors_reference(self, sensors_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create sensors configuration reference for self-contained analysis."""
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"enhanced_multi_key_session_summary_{self.session_id}_{timestamp}.json"
        
        # Collect all investigation files for analysis
        baseline_files = list(self.investigation_dir.glob("multi_key_baseline_*.json"))
        monitoring_files = list(self.investigation_dir.glob("multi_key_monitoring_*.json"))
        post_cleaning_files = list(self.investigation_dir.glob("multi_key_post_cleaning_*.json"))
        
        summary_data = {
            "metadata": {
                "session_id": self.session_id,
                "device_id": self.device_id,
                "timestamp": datetime.now().isoformat(),
                "summary_version": "4.0_multi_key",
                "total_files_analyzed": len(baseline_files) + len(monitoring_files) + len(post_cleaning_files)
            },
            "session_statistics": {
                "total_updates_received": self.total_updates_received,
                "meaningful_logs_created": self.meaningful_logs_created,
                "duplicates_skipped": self.duplicates_skipped,
                "logging_efficiency": f"{(self.duplicates_skipped / max(1, self.total_updates_received) * 100):.1f}%",
                "baseline_files": len(baseline_files),
                "monitoring_files": len(monitoring_files),
                "post_cleaning_files": len(post_cleaning_files)
            },
            "key_change_summary": {
                "monitored_keys": self.monitored_keys,
                "key_change_counts": self.key_change_counts,
                "total_changes": sum(self.key_change_counts.values()),
                "most_active_keys": sorted(self.key_change_counts.items(), key=lambda x: x[1], reverse=True)[:5]
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
        """Get current smart logging status."""
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
            }
        }
    
    async def _load_sensors_config(self) -> Optional[Dict[str, Any]]:
        """Load sensors configuration for analysis reference."""
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
            