"""Constants for Eufy Robovac Data Logger integration with RestConnect and Investigation Mode support."""

# Integration constants
DOMAIN = "eufy-robovac-data-logger"
CONF_USERNAME = "username"
CONF_PASSWORD = "password" 
CONF_DEBUG_MODE = "debug_mode"
CONF_INVESTIGATION_MODE = "investigation_mode"  # NEW: For comprehensive multi-key deep analysis

# Update interval in seconds - REDUCED for better RestConnect performance
UPDATE_INTERVAL = 10

# Data keys we want to monitor based on REAL Android app data from live system
# Updated with actual key data that contains substantial information (Base64/Numeric)
MONITORED_KEYS = [
    "152",  # Base64 data - possible accessory info
    "153",  # Base64 data - possible work status
    "154",  # Large Base64 - possible cleaning parameters  
    "157",  # Base64 data - possible configuration
    "158",  # Numeric value (3) - likely speed/mode
    "161",  # Numeric value (50) - POSSIBLE WATER TANK!
    "162",  # Base64 data - possible runtime info
    "163",  # Numeric value (93) - POSSIBLE BATTERY!
    "164",  # Base64 data - possible accessory info
    "165",  # Large Base64 - room/location data?
    "166",  # Base64 data - possible settings
    "167",  # Base64 data - possible accessory wear
    "168",  # Large Base64 - comprehensive accessory data
    "169",  # Huge Base64 (260 chars) - device info/config
    "170",  # Base64 data - possible status
    "172",  # Base64 data - possible commands
    "173",  # Large Base64 - possible navigation/mapping
    "176",  # Base64 data (112 chars) - possible maintenance
    "177",  # Base64 data - alternative data source
    "178",  # Base64 data - real-time info
    "179",  # Base64 data - possible consumables
    "180",  # Accessory data (CONFIRMED working) - PRIMARY INVESTIGATION TARGET
]

# RestConnect specific keys (may be available via REST endpoints)
RESTCONNECT_ENHANCED_KEYS = [
    "181",  # Enhanced accessory data 1
    "182",  # Enhanced accessory data 2
    "183",  # Enhanced accessory data 3
    "184",  # Enhanced accessory data 4
    "185",  # Enhanced accessory data 5
    "186",  # Runtime statistics
    "187",  # Maintenance data
    "188",  # Consumable status
    "189",  # Water tank detailed
    "190",  # Sensor diagnostics
]

# Combined monitoring (traditional + RestConnect enhanced)
ALL_MONITORED_KEYS = MONITORED_KEYS + RESTCONNECT_ENHANCED_KEYS

# INVESTIGATION MODE CONSTANTS - UPDATED for multi-key analysis
INVESTIGATION_CONFIG = {
    "primary_target_key": "180",  # Keep 180 as primary since it's confirmed working
    "multi_key_targets": MONITORED_KEYS,  # All keys get same analysis treatment
    "capture_frequency": "every_update",  # Capture ALL monitored keys on every update
    "baseline_timeout_minutes": 30,  # Wait 30 min max for baseline
    "post_cleaning_detection_window_minutes": 10,  # Look for changes within 10 min after cleaning
    "significant_change_threshold": 3,  # Changes of 1-3 are significant for wear detection
    "accessory_value_range": (1, 100),  # Valid range for percentage values
    "water_tank_candidates": ["161", "167", "177", "179"],  # Keys likely to contain water tank data
    "battery_candidates": ["163", "162", "168"],  # Keys likely to contain battery data
    "accessory_candidates": ["164", "165", "168", "176", "179", "180"],  # Keys likely to contain accessory wear
}

# File patterns for investigation mode - UPDATED for multi-key
INVESTIGATION_FILE_PATTERNS = {
    "baseline": "multi_key_baseline_{timestamp}.json",
    "post_cleaning": "multi_key_post_cleaning_{timestamp}.json", 
    "monitoring": "multi_key_monitoring_{timestamp}.json",
    "summary": "multi_key_session_summary_{session_id}.json",
    "significant_change": "multi_key_significant_change_{timestamp}.json",
}

# Debug monitoring keys (used for status sensors and debugging)
DEBUG_MONITORING_KEYS = MONITORED_KEYS  # Same as monitored keys

# Clean speed settings (for sensor parsing)
CLEAN_SPEED_NAMES = {
    0: "Quiet",
    1: "Standard", 
    2: "Turbo",
    3: "Max",
}

# Work status mapping (for sensor parsing)
WORK_STATUS_MAP = {
    0: "Sleep",
    1: "Cleaning", 
    2: "Go Home",
    3: "Charging",
    4: "Pause",
    5: "Error",
    6: "Remote Control",
    7: "Sleeping",
    8: "Manual",
    9: "Zone Cleaning",
    10: "Spot Cleaning",
}

# API endpoints for RestConnect
API_ENDPOINTS = {
    "device_data": "https://api.eufylife.com/v1/device/info",
    "device_status": "https://api.eufylife.com/v1/device/status", 
    "accessory_data": "https://api.eufylife.com/v1/device/accessory_info",
    "consumable_data": "https://api.eufylife.com/v1/device/consumable_status",
    "runtime_data": "https://api.eufylife.com/v1/device/runtime_info",
    "clean_device_info": "https://aiot-clean-api-pr.eufylife.com/app/device/get_device_info",
    "clean_accessory": "https://aiot-clean-api-pr.eufylife.com/app/device/get_accessory_data",
}

# RestConnect benefits over basic login
RESTCONNECT_BENEFITS = [
    "🌐 Access to additional REST API endpoints",
    "🔧 Enhanced accessory wear data from dedicated endpoints",
    "🧽 Consumable status from REST consumable API",
    "⏱️ Runtime statistics from dedicated endpoint",
    "🚿 Detailed water tank data from Clean API",
    "📊 Better data accuracy through multiple data sources",
    "🎯 Fallback support to basic login if REST fails",
]

# INVESTIGATION MODE BENEFITS - UPDATED for multi-key
INVESTIGATION_BENEFITS = [
    "🔍 Complete byte-by-byte analysis of ALL monitored keys",
    "📊 Structured JSON files for offline analysis of each key",
    "🎯 Before/after cleaning cycle comparison across all keys",
    "🧮 Automatic change detection and significance scoring for each key",
    "📁 Organized multi-key data files for external tool analysis",
    "🔬 Comprehensive metadata for research reproducibility",
    "🔍 Water tank and battery location discovery across all keys",
    "📈 Cross-key correlation analysis for data relationships",
]

# Logging configuration
DEBUG_LOG_INTERVALS = {
    "detailed_log_minutes": 10,  # Detailed log every 10 minutes (reduced from 5)
    "brief_log_updates": 1,      # Brief log for non-detailed updates
    "first_updates_detailed": 1, # Only first update in detail (reduced from 3)
}

# INVESTIGATION LOGGING - UPDATED for multi-key
INVESTIGATION_LOG_CONFIG = {
    "log_every_update": True,  # Log ALL monitored keys on every update in investigation mode
    "create_session_files": True,  # Create organized session files
    "include_hex_dump": True,  # Include complete hex dump in analysis for each key
    "include_context_keys": MONITORED_KEYS,  # All monitored keys included for context
    "auto_detect_cleaning_cycles": True,  # Try to detect when cleaning starts/stops
    "comparison_sensitivity": 1,  # Detect changes as small as 1 byte difference
    "cross_key_analysis": True,  # NEW: Compare changes across all keys
    "percentage_search": True,  # NEW: Search for percentage values (1-100) in all keys
}

# Connection status indicators
CONNECTION_STATUS_EMOJIS = {
    "restconnect": "🌐",
    "basic_login": "📱",
    "connected": "🟢",
    "disconnected": "🔴",
    "fallback": "🟡",
    "error": "❌",
    "investigation": "🔍",  # Investigation mode indicator
    "multi_key": "🗂️",  # NEW: Multi-key analysis indicator
}