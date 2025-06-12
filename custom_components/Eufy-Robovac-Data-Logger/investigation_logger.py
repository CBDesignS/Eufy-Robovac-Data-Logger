"""
Investigation Logger for Key 180 Accessory Wear Detection
Creates structured data files for offline analysis with complete byte dumps.
"""

import asyncio
import aiofiles
import json
import logging
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

_LOGGER = logging.getLogger(__name__)


class Key180InvestigationLogger:
    """
    Specialized logger for Key 180 investigation mode.
    Creates structured JSON files with complete byte analysis for offline processing.
    """
    
    def __init__(self, device_id: str, hass_config_dir: str):
        self.device_id = device_id
        
        # Create investigation directory
        self.investigation_dir = Path(hass_config_dir) / "eufy_investigation" / device_id
        self.investigation_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.baseline_captured = False
        self.last_key180_data = None
        self.update_counter = 0
        
        _LOGGER.info("🔍 Key 180 Investigation Logger initialized")
        _LOGGER.info("📂 Investigation directory: %s", self.investigation_dir)
    
    async def log_key180_data(self, raw_data: Dict[str, Any], phase: str = "monitoring") -> Optional[str]:
        """
        Log complete Key 180 data with comprehensive byte analysis.
        
        Args:
            raw_data: Complete raw API data
            phase: "baseline", "post_cleaning", "monitoring"
        
        Returns:
            Path to created file or None if no Key 180 data
        """
        try:
            if "180" not in raw_data:
                _LOGGER.debug("No Key 180 data in current update")
                return None
            
            key180_raw = raw_data["180"]
            self.update_counter += 1
            
            # Generate filename based on phase
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            
            if phase == "baseline":
                filename = f"key180_baseline_{timestamp}.json"
            elif phase == "post_cleaning":
                filename = f"key180_post_cleaning_{timestamp}.json"
            else:
                filename = f"key180_monitoring_{timestamp}.json"
            
            filepath = self.investigation_dir / filename
            
            # Create comprehensive analysis
            analysis_data = await self._create_comprehensive_analysis(
                key180_raw, raw_data, phase, timestamp
            )
            
            # Write to file
            async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(analysis_data, indent=2, ensure_ascii=False))
            
            _LOGGER.info("📊 Key 180 %s data logged: %s", phase, filename)
            
            # Update tracking
            self.last_key180_data = key180_raw
            if phase == "baseline":
                self.baseline_captured = True
            
            return str(filepath)
            
        except Exception as e:
            _LOGGER.error("❌ Failed to log Key 180 data: %s", e)
            return None
    
    async def _create_comprehensive_analysis(self, key180_raw: str, full_raw_data: Dict[str, Any], 
                                           phase: str, timestamp: str) -> Dict[str, Any]:
        """Create comprehensive analysis of Key 180 data."""
        analysis = {
            "metadata": {
                "device_id": self.device_id,
                "session_id": self.session_id,
                "timestamp": timestamp,
                "phase": phase,
                "update_counter": self.update_counter,
                "investigation_mode": True,
                "created_by": "Eufy Robovac Data Logger - Investigation Mode"
            },
            "key_180_data": {
                "raw_base64": key180_raw,
                "length": len(key180_raw),
                "data_type": "base64_encoded_binary"
            },
            "byte_analysis": {},
            "accessory_candidates": [],
            "context_data": {},
            "comparison": {}
        }
        
        # Decode and analyze bytes
        try:
            binary_data = base64.b64decode(key180_raw)
            hex_string = binary_data.hex()
            
            analysis["key_180_data"]["binary_length"] = len(binary_data)
            analysis["key_180_data"]["hex_dump"] = hex_string
            
            # Complete byte-by-byte analysis
            byte_analysis = {}
            accessory_candidates = []
            
            for i, byte_val in enumerate(binary_data):
                byte_info = {
                    "position": i,
                    "decimal": byte_val,
                    "hex": f"0x{byte_val:02x}",
                    "binary": f"0b{byte_val:08b}",
                    "is_percentage_candidate": 1 <= byte_val <= 100,
                    "is_status_flag": byte_val in [0, 255],
                    "is_zero": byte_val == 0,
                    "is_max": byte_val == 255
                }
                
                # Flag potential accessory wear percentages
                if 1 <= byte_val <= 100:
                    accessory_candidates.append({
                        "byte_position": i,
                        "value": byte_val,
                        "likely_accessory": self._guess_accessory_type(i, byte_val),
                        "confidence": self._calculate_confidence(i, byte_val)
                    })
                
                byte_analysis[f"byte_{i:03d}"] = byte_info
            
            analysis["byte_analysis"] = byte_analysis
            analysis["accessory_candidates"] = accessory_candidates
            
        except Exception as e:
            analysis["decode_error"] = str(e)
            _LOGGER.error("Failed to decode Key 180 data: %s", e)
        
        # Add context from other keys
        analysis["context_data"] = self._extract_context_data(full_raw_data)
        
        # Add comparison if we have previous data
        if self.last_key180_data and self.last_key180_data != key180_raw:
            analysis["comparison"] = await self._compare_with_previous(key180_raw, self.last_key180_data)
        
        return analysis
    
    def _guess_accessory_type(self, position: int, value: int) -> str:
        """Guess accessory type based on byte position and value patterns."""
        # Based on your existing research and common patterns
        position_guesses = {
            5: "mop_cloth",
            37: "side_brush", 
            75: "cleaning_tray",
            95: "sensors_or_status",
            125: "brush_guard",
            146: "rolling_brush",
            228: "filter"
        }
        
        # Check exact positions first
        if position in position_guesses:
            return position_guesses[position]
        
        # Check nearby positions (±5)
        for known_pos, accessory in position_guesses.items():
            if abs(position - known_pos) <= 5:
                return f"{accessory}_nearby"
        
        # General guesses based on value ranges
        if 80 <= value <= 100:
            return "new_accessory"
        elif 50 <= value <= 79:
            return "medium_wear_accessory"
        elif 20 <= value <= 49:
            return "high_wear_accessory"
        elif 1 <= value <= 19:
            return "replacement_needed_accessory"
        
        return "unknown_accessory"
    
    def _calculate_confidence(self, position: int, value: int) -> str:
        """Calculate confidence level for accessory detection."""
        known_positions = [5, 37, 75, 95, 125, 146, 228]
        
        if position in known_positions:
            return "high"
        elif any(abs(position - known) <= 2 for known in known_positions):
            return "medium"
        elif 1 <= value <= 100:
            return "low"
        else:
            return "very_low"
    
    def _extract_context_data(self, full_raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant context from other API keys."""
        context = {}
        
        # Add other relevant keys
        relevant_keys = ["163", "167", "168", "177", "158", "153"]
        
        for key in relevant_keys:
            if key in full_raw_data:
                context[f"key_{key}"] = full_raw_data[key]
        
        # Add summary
        context["total_keys_available"] = len(full_raw_data)
        context["all_keys"] = list(full_raw_data.keys())
        
        return context
    
    async def _compare_with_previous(self, current_data: str, previous_data: str) -> Dict[str, Any]:
        """Compare current Key 180 data with previous capture."""
        comparison = {
            "data_changed": current_data != previous_data,
            "changes": []
        }
        
        if current_data == previous_data:
            comparison["status"] = "no_changes"
            return comparison
        
        try:
            current_bytes = base64.b64decode(current_data)
            previous_bytes = base64.b64decode(previous_data)
            
            if len(current_bytes) != len(previous_bytes):
                comparison["length_changed"] = True
                comparison["previous_length"] = len(previous_bytes)
                comparison["current_length"] = len(current_bytes)
                return comparison
            
            # Find all changed bytes
            changes = []
            for i, (curr, prev) in enumerate(zip(current_bytes, previous_bytes)):
                if curr != prev:
                    change = {
                        "byte_position": i,
                        "previous_value": prev,
                        "current_value": curr,
                        "difference": curr - prev,
                        "change_type": self._classify_change(prev, curr)
                    }
                    changes.append(change)
            
            comparison["changes"] = changes
            comparison["total_changes"] = len(changes)
            comparison["status"] = "changes_detected"
            
            # Highlight significant changes (likely accessory wear)
            significant_changes = [
                c for c in changes 
                if abs(c["difference"]) in [1, 2, 3] and 1 <= min(c["previous_value"], c["current_value"]) <= 100
            ]
            comparison["significant_changes"] = significant_changes
            comparison["potential_wear_changes"] = len(significant_changes)
            
        except Exception as e:
            comparison["comparison_error"] = str(e)
        
        return comparison
    
    def _classify_change(self, previous: int, current: int) -> str:
        """Classify the type of change between two byte values."""
        diff = current - previous
        
        if diff == 0:
            return "no_change"
        elif diff == -1:
            return "decreased_by_1"  # Potential wear
        elif diff == -2:
            return "decreased_by_2"  # Potential wear
        elif diff == -3:
            return "decreased_by_3"  # Potential wear
        elif diff < -3:
            return "large_decrease"
        elif diff == 1:
            return "increased_by_1"
        elif diff == 2:
            return "increased_by_2"
        elif diff == 3:
            return "increased_by_3"
        elif diff > 3:
            return "large_increase"
        else:
            return "unchanged"
    
    async def capture_baseline(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Capture baseline Key 180 data before cleaning."""
        return await self.log_key180_data(raw_data, "baseline")
    
    async def capture_post_cleaning(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Capture Key 180 data after cleaning cycle."""
        return await self.log_key180_data(raw_data, "post_cleaning")
    
    async def generate_session_summary(self) -> str:
        """Generate a summary of the investigation session."""
        summary_file = self.investigation_dir / f"session_summary_{self.session_id}.json"
        
        # List all files created in this session
        session_files = [
            f for f in self.investigation_dir.glob("*.json") 
            if self.session_id in f.name
        ]
        
        summary = {
            "session_info": {
                "session_id": self.session_id,
                "device_id": self.device_id,
                "start_time": self.session_id,
                "end_time": datetime.now().isoformat(),
                "total_updates": self.update_counter,
                "baseline_captured": self.baseline_captured
            },
            "files_created": [f.name for f in session_files],
            "investigation_directory": str(self.investigation_dir),
            "analysis_recommendations": [
                "1. Compare baseline vs post_cleaning files for accessory wear detection",
                "2. Look for bytes that decreased by 1-3 in the 1-100 range",
                "3. Focus on known positions: 5, 37, 75, 125, 146, 228",
                "4. Use external tools to analyze patterns across multiple cleaning cycles",
                "5. Cross-reference with Eufy Android app accessory percentages"
            ]
        }
        
        try:
            async with aiofiles.open(summary_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary, indent=2, ensure_ascii=False))
            
            _LOGGER.info("📋 Investigation session summary created: %s", summary_file.name)
            return str(summary_file)
            
        except Exception as e:
            _LOGGER.error("❌ Failed to create session summary: %s", e)
            return ""
    
    def get_investigation_directory(self) -> str:
        """Get the path to the investigation directory."""
        return str(self.investigation_dir)
    
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id