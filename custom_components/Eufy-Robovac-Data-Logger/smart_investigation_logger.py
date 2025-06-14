"""
Smart Investigation Logger for Key 180 Accessory Wear Detection
Optimized version with intelligent change detection and reduced file bloat.
Only logs when meaningful changes are detected.
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


class SmartKey180InvestigationLogger:
    """
    Smart Investigation Logger with intelligent change detection.
    Reduces file bloat by only logging meaningful changes.
    """
    
    def __init__(self, device_id: str, hass_config_dir: str):
        self.device_id = device_id
        
        # Create investigation directory
        self.investigation_dir = Path(hass_config_dir) / "eufy_investigation" / device_id
        self.investigation_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        _LOGGER.info("🔍 Smart Investigation Logger initialized with change detection")
        _LOGGER.info("📂 Investigation directory: %s", self.investigation_dir)
        _LOGGER.info("🧠 Mode: %s", self.current_mode.value)
    
    async def process_key180_update(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """
        Smart processing of Key 180 data with intelligent change detection.
        
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
            
            # Create comprehensive analysis
            analysis_data = await self._create_smart_analysis(
                key180_raw, raw_data, log_mode, log_reason
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
            
            _LOGGER.info("📊 Smart log created: %s (Reason: %s)", filename, log_reason)
            _LOGGER.debug("📈 Stats: %d updates, %d logged, %d skipped", 
                         self.total_updates_received, self.meaningful_logs_created, self.duplicates_skipped)
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error("❌ Smart investigation processing failed: %s", e)
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
        """Analyze if changes are significant for accessory wear detection."""
        try:
            current_bytes = base64.b64decode(current_data)
            previous_bytes = base64.b64decode(previous_data)
            
            if len(current_bytes) != len(previous_bytes):
                return {"has_significant_changes": True, "change_count": "length_mismatch", "reason": "Data length changed"}
            
            significant_changes = []
            accessory_wear_changes = []
            
            for i, (curr, prev) in enumerate(zip(current_bytes, previous_bytes)):
                if curr != prev:
                    diff = curr - prev
                    
                    # Check if this looks like accessory wear (decrease in percentage range)
                    if (1 <= min(curr, prev) <= 100 and 
                        abs(diff) <= self.significant_change_threshold and 
                        diff < 0):  # Decrease indicates wear
                        
                        accessory_wear_changes.append({
                            "position": i,
                            "previous": prev,
                            "current": curr,
                            "decrease": abs(diff),
                            "likely_accessory": self._guess_accessory_type(i)
                        })
                    
                    significant_changes.append({
                        "position": i,
                        "previous": prev,
                        "current": curr,
                        "difference": diff
                    })
            
            return {
                "has_significant_changes": len(accessory_wear_changes) > 0 or len(significant_changes) > 5,
                "change_count": len(significant_changes),
                "accessory_wear_changes": accessory_wear_changes,
                "total_changes": significant_changes,
                "reason": f"{len(accessory_wear_changes)} accessory wear changes, {len(significant_changes)} total changes"
            }
            
        except Exception as e:
            _LOGGER.error("❌ Change analysis failed: %s", e)
            return {"has_significant_changes": False, "change_count": 0, "reason": f"Analysis error: {e}"}
    
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
    
    async def _create_smart_analysis(self, key180_raw: str, full_raw_data: Dict[str, Any], 
                                   log_mode: LoggingMode, log_reason: str) -> Dict[str, Any]:
        """Create comprehensive but efficient analysis."""
        analysis = {
            "metadata": {
                "device_id": self.device_id,
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "log_mode": log_mode.value,
                "log_reason": log_reason,
                "update_number": self.total_updates_received,
                "smart_logger_version": "2.0",
                "file_number": self.meaningful_logs_created + 1
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
            "context_data": self._extract_efficient_context(full_raw_data)
        }
        
        # Add detailed byte analysis only for baseline and significant changes
        if log_mode in [LoggingMode.BASELINE, LoggingMode.CLEANING_DETECTED] or "significant_change" in log_reason:
            analysis["detailed_byte_analysis"] = await self._create_detailed_byte_analysis(key180_raw)
        
        # Add comparison if we have previous data
        if self.last_logged_data and self.last_logged_data != key180_raw:
            analysis["change_analysis"] = await self._analyze_change_significance(key180_raw, self.last_logged_data)
        
        return analysis
    
    async def _create_detailed_byte_analysis(self, key180_raw: str) -> Dict[str, Any]:
        """Create detailed byte analysis for important logs."""
        try:
            binary_data = base64.b64decode(key180_raw)
            
            # Focus on known accessory positions
            known_positions = [5, 37, 75, 95, 125, 146, 228]
            accessory_analysis = {}
            
            for pos in known_positions:
                if pos < len(binary_data):
                    byte_val = binary_data[pos]
                    accessory_analysis[f"position_{pos}"] = {
                        "byte_value": byte_val,
                        "hex": f"0x{byte_val:02x}",
                        "is_percentage": 1 <= byte_val <= 100,
                        "likely_accessory": self._guess_accessory_type(pos),
                        "confidence": self._calculate_confidence(pos, byte_val)
                    }
            
            return {
                "total_bytes": len(binary_data),
                "hex_dump": binary_data.hex(),
                "known_accessory_positions": accessory_analysis,
                "percentage_candidates": [
                    {"position": i, "value": byte_val}
                    for i, byte_val in enumerate(binary_data)
                    if 1 <= byte_val <= 100
                ][:20]  # Limit to first 20 candidates
            }
            
        except Exception as e:
            return {"error": f"Byte analysis failed: {e}"}
    
    def _extract_efficient_context(self, full_raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only essential context data to keep files smaller."""
        relevant_keys = ["163", "167", "168", "158", "153"]
        context = {}
        
        for key in relevant_keys:
            if key in full_raw_data:
                context[f"key_{key}"] = full_raw_data[key]
        
        context["total_keys_available"] = len(full_raw_data)
        return context
    
    def _guess_accessory_type(self, position: int) -> str:
        """Guess accessory type based on known positions."""
        position_map = {
            5: "mop_cloth",
            37: "side_brush",
            75: "cleaning_tray", 
            95: "sensors_status",
            125: "brush_guard",
            146: "rolling_brush",
            228: "dust_filter"
        }
        return position_map.get(position, "unknown_accessory")
    
    def _calculate_confidence(self, position: int, value: int) -> str:
        """Calculate confidence for accessory detection."""
        known_positions = [5, 37, 75, 95, 125, 146, 228]
        
        if position in known_positions and 1 <= value <= 100:
            return "high"
        elif position in known_positions:
            return "medium"
        elif 1 <= value <= 100:
            return "low"
        else:
            return "very_low"
    
    async def _update_state_after_logging(self, key180_raw: str, data_hash: str, 
                                        log_mode: LoggingMode, filepath: Path) -> None:
        """Update internal state after successful logging."""
        self.last_key180_hash = data_hash
        self.last_logged_data = key180_raw
        self.last_log_time = datetime.now()
        
        if log_mode == LoggingMode.BASELINE:
            self.baseline_captured = True
            self.current_mode = LoggingMode.SMART_MONITORING
            _LOGGER.info("🎯 Baseline captured, switching to smart monitoring mode")
    
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
        """Manually capture baseline."""
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
        """Manually capture post-cleaning data."""
        if "180" not in raw_data:
            return None
        
        # Force post-cleaning log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"key180_post_cleaning_{timestamp}.json"
        
        analysis_data = await self._create_smart_analysis(
            raw_data["180"], raw_data, LoggingMode.POST_CLEANING, "manual_post_cleaning"
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
        """Generate smart session summary."""
        summary_file = self.investigation_dir / f"smart_session_summary_{self.session_id}.json"
        
        # Analyze all files in this session
        session_files = [f for f in self.investigation_dir.glob("*.json") if self.session_id in f.name]
        
        summary = {
            "session_info": {
                "session_id": self.session_id,
                "device_id": self.device_id,
                "start_time": self.session_id,
                "end_time": datetime.now().isoformat(),
                "smart_logger_version": "2.0"
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
            "analysis_recommendations": [
                "1. Focus on files with 'significant_change' in the name for wear detection",
                "2. Compare baseline vs post_cleaning files for comprehensive analysis",
                "3. Look for byte decreases in positions 5, 37, 75, 125, 146, 228",
                "4. Files with 'cleaning_activity' show data during actual cleaning cycles",
                "5. Smart logger has eliminated duplicate monitoring - only meaningful changes logged"
            ],
            "smart_features": [
                "✅ Duplicate detection prevents file bloat",
                "✅ Change significance analysis focuses on accessory wear",
                "✅ Automatic cleanup maintains manageable file count",
                "✅ Intelligent mode switching optimizes logging strategy",
                "✅ Cleaning activity detection captures relevant moments"
            ]
        }
        
        try:
            async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            _LOGGER.info("📋 Smart session summary created: %s", summary_file.name)
            _LOGGER.info("📊 Efficiency: %d updates → %d files (%d%% reduction)", 
                        self.total_updates_received, self.meaningful_logs_created,
                        int((self.duplicates_skipped / max(1, self.total_updates_received)) * 100))
            
            return str(summary_file)
            
        except Exception as e:
            _LOGGER.error("❌ Failed to create smart session summary: %s", e)
            return ""
    
    def get_smart_status(self) -> Dict[str, Any]:
        """Get current smart logging status."""
        return {
            "mode": self.current_mode.value,
            "baseline_captured": self.baseline_captured,
            "session_id": self.session_id,
            "total_updates": self.total_updates_received,
            "meaningful_logs": self.meaningful_logs_created,
            "duplicates_skipped": self.duplicates_skipped,
            "efficiency_percentage": (self.duplicates_skipped / max(1, self.total_updates_received)) * 100,
            "last_log_time": self.last_log_time.isoformat() if self.last_log_time else None,
            "investigation_directory": str(self.investigation_dir)
        }
    
    def get_investigation_directory(self) -> str:
        """Get investigation directory path."""
        return str(self.investigation_dir)
    
    def get_session_id(self) -> str:
        """Get current session ID."""
        return self.session_id