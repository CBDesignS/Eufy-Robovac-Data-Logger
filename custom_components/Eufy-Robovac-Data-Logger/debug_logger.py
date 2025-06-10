"""
Debug logger utility for Eufy Robovac Data Logger integration.
This creates a separate log file to avoid spamming the main HA log.
Enhanced with accessory hunting capabilities.
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class EufyDebugLogger:
    """Separate logger for Eufy debugging to avoid spamming main HA log."""
    
    def __init__(self, device_id: str, hass_config_dir: str):
        self.device_id = device_id
        
        # Create logs directory if it doesn't exist
        log_dir = Path(hass_config_dir) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Create separate log file for this device with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"eufy_x10_debug_{device_id}_{timestamp}.log"
        
        # Set up the logger
        self.logger = logging.getLogger(f"eufy_x10_debug_{device_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create file handler with fresh log file
        file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')  # 'w' = new file
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.propagate = False  # Don't send to parent loggers (HA main log)
        
        # Log startup with session info
        self.logger.info("=" * 80)
        self.logger.info(f"EUFY ROBOVAC DATA LOGGING SESSION STARTED - Device: {device_id}")
        self.logger.info(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info("=" * 80)
        self.logger.info("🎯 DEBUGGING MISSION:")
        self.logger.info("  - Hunt for accessory sensor data bytes")
        self.logger.info("  - Match Android app usage levels")
        self.logger.info("  - Find: rolling brush, filter, side brush, mop cloth sensors")
        self.logger.info("  - Test: run room clean → dock → check accessory changes")
        self.logger.info("=" * 80)
    
    def info(self, message: str):
        """Log info level message."""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log debug level message."""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """Log warning level message."""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log error level message."""
        self.logger.error(message)
    
    def log_raw_data(self, data: dict):
        """Log raw API data with detailed breakdown."""
        self.logger.info("RAW API DATA RECEIVED:")
        self.logger.info("-" * 40)
        
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 100:
                self.logger.info(f"Key {key}: {value[:50]}... ({len(value)} chars)")
            else:
                self.logger.info(f"Key {key}: {value}")
        
        self.logger.info("-" * 40)
    
    def log_key_analysis(self, key: str, value: Any, analysis: dict):
        """Log detailed analysis of a specific key."""
        self.logger.info(f"KEY {key} ANALYSIS:")
        self.logger.info(f"  Raw Value: {value}")
        
        for analysis_key, analysis_value in analysis.items():
            self.logger.info(f"  {analysis_key}: {analysis_value}")
        
        self.logger.info("")
    
    def log_byte_analysis(self, key: str, base64_data: str):
        """Log detailed byte-by-byte analysis of base64 data."""
        try:
            import base64
            binary_data = base64.b64decode(base64_data)
            
            self.logger.info(f"BYTE ANALYSIS - Key {key}:")
            self.logger.info(f"  Base64: {base64_data}")
            self.logger.info(f"  Length: {len(binary_data)} bytes")
            self.logger.info(f"  Hex: {binary_data.hex()}")
            
            # Log first 20 bytes individually
            for i in range(min(20, len(binary_data))):
                byte_val = binary_data[i]
                self.logger.info(f"  Byte {i:2d}: {byte_val:3d} (0x{byte_val:02x})")
            
            if len(binary_data) > 20:
                self.logger.info(f"  ... and {len(binary_data) - 20} more bytes")
                
        except Exception as e:
            self.logger.error(f"Failed to decode base64 data for key {key}: {e}")
    
    def log_monitored_keys_status(self, found_keys: list, missing_keys: list):
        """Log status of all monitored keys."""
        self.logger.info("MONITORED KEYS STATUS:")
        self.logger.info(f"  Found: {len(found_keys)}/{len(found_keys) + len(missing_keys)}")
        
        if found_keys:
            self.logger.info("  ✅ PRESENT:")
            for key in found_keys:
                self.logger.info(f"    Key {key}")
        
        if missing_keys:
            self.logger.info("  ❌ MISSING:")
            for key in missing_keys:
                self.logger.info(f"    Key {key}")
        
        self.logger.info("")
    
    def log_accessory_hunt(self, phase: str, data: dict):
        """Log accessory hunting data with before/after comparison."""
        self.logger.info("=" * 60)
        self.logger.info(f"🔍 ACCESSORY HUNT - {phase.upper()}")
        self.logger.info("=" * 60)
        
        if phase == "BEFORE_CLEANING":
            self.logger.info("📝 BEFORE room cleaning - Record baseline accessory levels")
        elif phase == "AFTER_CLEANING": 
            self.logger.info("📝 AFTER room cleaning - Look for changed accessory levels")
        
        # Focus on keys likely to contain accessory data
        accessory_candidate_keys = ["180", "167", "168", "177", "164"]
        
        for key in accessory_candidate_keys:
            if key in data:
                value = data[key]
                self.logger.info(f"Key {key}: {value}")
                
                # Special analysis for base64 data
                if isinstance(value, str) and len(value) > 10:
                    try:
                        import base64
                        binary_data = base64.b64decode(value)
                        
                        # Look for percentage-like bytes (accessory wear levels)
                        percentage_bytes = []
                        for i, byte_val in enumerate(binary_data):
                            if 1 <= byte_val <= 100:  # Likely percentage
                                percentage_bytes.append(f"  Byte {i:3d}: {byte_val:3d}% (0x{byte_val:02x})")
                        
                        if percentage_bytes:
                            self.logger.info(f"  Key {key} percentage candidates:")
                            for pct_info in percentage_bytes[:15]:  # Limit to first 15
                                self.logger.info(pct_info)
                                
                    except Exception as e:
                        self.logger.info(f"  Key {key} decode error: {e}")
        
        self.logger.info("=" * 60)
        self.logger.info("")
    
    def log_comparison(self, before_data: dict, after_data: dict):
        """Compare before/after data to find accessory changes."""
        self.logger.info("=" * 80)
        self.logger.info("🔄 BEFORE vs AFTER COMPARISON - HUNTING FOR ACCESSORY CHANGES")
        self.logger.info("=" * 80)
        
        for key in before_data:
            if key in after_data:
                before_val = before_data[key]
                after_val = after_data[key]
                
                if before_val != after_val:
                    self.logger.info(f"🎯 KEY {key} CHANGED!")
                    self.logger.info(f"  Before: {before_val}")
                    self.logger.info(f"  After:  {after_val}")
                    
                    # If base64, compare bytes
                    if isinstance(before_val, str) and isinstance(after_val, str):
                        try:
                            import base64
                            before_bytes = base64.b64decode(before_val)
                            after_bytes = base64.b64decode(after_val)
                            
                            if len(before_bytes) == len(after_bytes):
                                self.logger.info(f"  Byte-by-byte changes:")
                                for i, (b_byte, a_byte) in enumerate(zip(before_bytes, after_bytes)):
                                    if b_byte != a_byte:
                                        self.logger.info(f"    Byte {i:3d}: {b_byte:3d} → {a_byte:3d} (diff: {a_byte-b_byte:+d})")
                                        
                                        # Flag potential accessory wear tracking
                                        if abs(a_byte - b_byte) == 1 and 1 <= min(a_byte, b_byte) <= 100:
                                            self.logger.info(f"    ⭐ POTENTIAL ACCESSORY WEAR: Byte {i} decreased by 1%")
                                            
                        except Exception as e:
                            self.logger.info(f"  Comparison error: {e}")
                    
                    self.logger.info("")
        
        self.logger.info("=" * 80)
