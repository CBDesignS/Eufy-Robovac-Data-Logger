"""
Async debug logger utility for Eufy Robovac Data Logger integration.
This creates a separate log file without blocking the event loop.
"""

import asyncio
import aiofiles
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class AsyncEufyDebugLogger:
    """Non-blocking async logger for Eufy debugging."""
    
    def __init__(self, device_id: str, hass_config_dir: str):
        self.device_id = device_id
        self.log_queue = asyncio.Queue()
        self.log_task = None
        self.is_running = False
        
        # Create logs directory if it doesn't exist
        self.log_dir = Path(hass_config_dir) / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Create log file path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"eufy_x10_debug_{device_id}_{timestamp}.log"
        
        # Start the async logging task
        self.start_logging()
    
    def start_logging(self):
        """Start the async logging task."""
        if not self.is_running:
            self.is_running = True
            self.log_task = asyncio.create_task(self._log_worker())
    
    async def _log_writer(self, message: str):
        """Write message to file asynchronously."""
        try:
            async with aiofiles.open(self.log_file, mode='a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                await f.write(f"{timestamp} - {message}\n")
        except Exception as e:
            # Fallback to standard logger if file writing fails
            logging.getLogger(__name__).error(f"Failed to write to debug log: {e}")
    
    async def _log_worker(self):
        """Background worker that processes log messages."""
        # Write initial header
        header_messages = [
            "=" * 80,
            f"EUFY X10 DEBUG SESSION STARTED - Device: {self.device_id}",
            f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Log file: {self.log_file}",
            "=" * 80,
            "🎯 DEBUGGING MISSION:",
            "  - Hunt for accessory sensor data bytes",
            "  - Match Android app usage levels",
            "  - Find: rolling brush, filter, side brush, mop cloth sensors",
            "  - Test: run room clean → dock → check accessory changes",
            "=" * 80
        ]
        
        for msg in header_messages:
            await self._log_writer(msg)
        
        # Process queued log messages
        while self.is_running:
            try:
                # Wait for a message with timeout
                message = await asyncio.wait_for(self.log_queue.get(), timeout=1.0)
                await self._log_writer(message)
                self.log_queue.task_done()
            except asyncio.TimeoutError:
                # No message received, continue loop
                continue
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in log worker: {e}")
                break
    
    def info(self, message: str):
        """Log info level message (non-blocking)."""
        if self.is_running:
            try:
                self.log_queue.put_nowait(f"INFO - {message}")
            except asyncio.QueueFull:
                pass  # Silently drop if queue is full
    
    def debug(self, message: str):
        """Log debug level message (non-blocking)."""
        if self.is_running:
            try:
                self.log_queue.put_nowait(f"DEBUG - {message}")
            except asyncio.QueueFull:
                pass
    
    def warning(self, message: str):
        """Log warning level message (non-blocking)."""
        if self.is_running:
            try:
                self.log_queue.put_nowait(f"WARNING - {message}")
            except asyncio.QueueFull:
                pass
    
    def error(self, message: str):
        """Log error level message (non-blocking)."""
        if self.is_running:
            try:
                self.log_queue.put_nowait(f"ERROR - {message}")
            except asyncio.QueueFull:
                pass
    
    def log_raw_data(self, data: dict):
        """Log raw API data with detailed breakdown (non-blocking)."""
        messages = [
            "RAW API DATA RECEIVED:",
            "-" * 40
        ]
        
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 100:
                messages.append(f"Key {key}: {value[:50]}... ({len(value)} chars)")
            else:
                messages.append(f"Key {key}: {value}")
        
        messages.append("-" * 40)
        
        for msg in messages:
            self.info(msg)
    
    def log_key_analysis(self, key: str, value: Any, analysis: dict):
        """Log detailed analysis of a specific key (non-blocking)."""
        messages = [
            f"KEY {key} ANALYSIS:",
            f"  Raw Value: {value}"
        ]
        
        for analysis_key, analysis_value in analysis.items():
            messages.append(f"  {analysis_key}: {analysis_value}")
        
        messages.append("")
        
        for msg in messages:
            self.info(msg)
    
    def log_byte_analysis(self, key: str, base64_data: str):
        """Log detailed byte-by-byte analysis of base64 data (non-blocking)."""
        try:
            import base64
            binary_data = base64.b64decode(base64_data)
            
            messages = [
                f"BYTE ANALYSIS - Key {key}:",
                f"  Base64: {base64_data}",
                f"  Length: {len(binary_data)} bytes",
                f"  Hex: {binary_data.hex()}"
            ]
            
            # Log first 20 bytes individually
            for i in range(min(20, len(binary_data))):
                byte_val = binary_data[i]
                messages.append(f"  Byte {i:2d}: {byte_val:3d} (0x{byte_val:02x})")
            
            if len(binary_data) > 20:
                messages.append(f"  ... and {len(binary_data) - 20} more bytes")
            
            for msg in messages:
                self.info(msg)
                
        except Exception as e:
            self.error(f"Failed to decode base64 data for key {key}: {e}")
    
    def log_monitored_keys_status(self, found_keys: list, missing_keys: list):
        """Log status of all monitored keys (non-blocking)."""
        messages = [
            "MONITORED KEYS STATUS:",
            f"  Found: {len(found_keys)}/{len(found_keys) + len(missing_keys)}"
        ]
        
        if found_keys:
            messages.append("  ✅ PRESENT:")
            for key in found_keys:
                messages.append(f"    Key {key}")
        
        if missing_keys:
            messages.append("  ❌ MISSING:")
            for key in missing_keys:
                messages.append(f"    Key {key}")
        
        messages.append("")
        
        for msg in messages:
            self.info(msg)
    
    def log_accessory_hunt(self, phase: str, data: dict):
        """Log accessory hunting data with before/after comparison (non-blocking)."""
        messages = [
            "=" * 60,
            f"🔍 ACCESSORY HUNT - {phase.upper()}",
            "=" * 60
        ]
        
        if phase == "BEFORE_CLEANING":
            messages.append("📝 BEFORE room cleaning - Record baseline accessory levels")
        elif phase == "AFTER_CLEANING": 
            messages.append("📝 AFTER room cleaning - Look for changed accessory levels")
        
        # Focus on keys likely to contain accessory data
        accessory_candidate_keys = ["180", "167", "168", "177", "164"]
        
        for key in accessory_candidate_keys:
            if key in data:
                value = data[key]
                messages.append(f"Key {key}: {value}")
                
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
                            messages.append(f"  Key {key} percentage candidates:")
                            for pct_info in percentage_bytes[:15]:  # Limit to first 15
                                messages.append(pct_info)
                                
                    except Exception as e:
                        messages.append(f"  Key {key} decode error: {e}")
        
        messages.extend(["=" * 60, ""])
        
        for msg in messages:
            self.info(msg)
    
    async def stop(self):
        """Stop the async logging task."""
        if self.is_running:
            self.is_running = False
            
            # Write final message
            await self._log_writer("=" * 80)
            await self._log_writer("EUFY X10 DEBUG SESSION ENDED")
            await self._log_writer("=" * 80)
            
            # Wait for queue to be processed
            if not self.log_queue.empty():
                await self.log_queue.join()
            
            # Cancel the logging task
            if self.log_task and not self.log_task.done():
                self.log_task.cancel()
                try:
                    await self.log_task
                except asyncio.CancelledError:
                    pass