"""Constants for Eufy Robovac Data Logger integration with RestConnect and Investigation Mode support."""

# Integration constants
DOMAIN = "eufy_robovac_data_logger"
CONF_USERNAME = "username"
CONF_PASSWORD = "password" 
CONF_DEBUG_MODE = "debug_mode"
CONF_INVESTIGATION_MODE = "investigation_mode"  # NEW: For Key 180 deep analysis

# Update interval in seconds - REDUCED for better RestConnect performance
UPDATE_INTERVAL = 10

# Data keys we want to monitor based on NEW Android app research
MONITORED_KEYS = [
    "163",  # Battery (NEW Android App - 100% accuracy)
    "167",  # Water tank data (Key 167, Byte 4 - 82% accuracy)
    "177",  # Alternative water tank source
    "178",  # Real-time data source
    "168",  # Accessories status
    "153",  # Work status/mode
    "152",  # Play/pause commands
    "158",  # Clean speed settings
    "154",  # Cleaning parameters
    "155",  # Direction controls
    "160",  # Find robot
    "173",  # Go home commands
    "180",  # Accessory data (from existing research) - PRIMARY INVESTIGATION TARGET
    "164",  # Alternative water tank (from existing research)
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

# INVESTIGATION MODE CONSTANTS - NEW
INVESTIGATION_CONFIG = {
    "primary_target_key": "180",
    "capture_frequency": "every_update",  # Capture Key 180 on every update
    "baseline_timeout_minutes": 30,  # Wait 30 min max for baseline
    "post_cleaning_detection_window_minutes": 10,  # Look for changes within 10 min after cleaning
    "significant_change_threshold": 3,  # Changes of 1-3 are significant for wear detection
    "accessory_value_range": (1, 100),  # Valid range for accessory percentages
    "known_accessory_positions": [5, 37, 75, 95, 125, 146, 228],  # From existing research
    "investigation_file_retention_days": 30,  # Keep investigation files for 30 days
}

# INVESTIGATION MODE BYTE POSITIONS - Enhanced from your research
KEY_180_KNOWN_POSITIONS = {
    5: {
        "name": "Mopping Cloth",
        "description": "Mopping attachment for wet cleaning",
        "confidence": "medium",
        "current_detected": "24%",
        "notes": "Shows 24% but needs verification against app"
    },
    37: {
        "name": "Side Brush", 
        "description": "Edge cleaning brush",
        "confidence": "medium",
        "current_detected": "1%",
        "notes": "Shows 1% but needs verification - likely wrong"
    },
    75: {
        "name": "Cleaning Tray",
        "description": "Dust collection tray",
        "confidence": "low",
        "current_detected": "96%",
        "notes": "Shows 96% - verify if this is correct"
    },
    95: {
        "name": "Cliff/Bump Sensors",
        "description": "Navigation sensors",
        "confidence": "low",
        "current_detected": "255 (0xFF)",
        "notes": "Shows 255 - likely status flag, not percentage"
    },
    125: {
        "name": "Brush Guard",
        "description": "Protective guard for rolling brush",
        "confidence": "low", 
        "current_detected": "98%",
        "notes": "Shows 98% - needs verification"
    },
    146: {
        "name": "Rolling Brush",
        "description": "Main cleaning brush",
        "confidence": "medium",
        "current_detected": "32%",
        "notes": "Shows 32% but user expects 99% - likely wrong position"
    },
    228: {
        "name": "Dust Filter",
        "description": "Air filtration system", 
        "confidence": "medium",
        "current_detected": "12%",
        "notes": "Shows 12% but user expects 99% - likely wrong position"
    }
}

# Clean speed mappings (for Key 158)
CLEAN_SPEED_NAMES = ["quiet", "standard", "turbo", "max"]

# Work status mappings (for Key 153)
WORK_STATUS_MAP = {
    0: "standby",
    1: "sleep", 
    2: "fault",
    3: "charging",
    4: "fast_mapping",
    5: "cleaning",
    6: "remote_ctrl",
    7: "go_home",
    8: "cruising"
}

# Eufy X10 device models (focused on X10 series for debugging)
EUFY_X10_MODELS = {
    'T2351': 'X10 Pro Omni',
    'T2320': 'X10 Pro',
    'T2262': 'X8',
    'T2261': 'X8 Hybrid',
    'T2266': 'X8 Pro',
    'T2276': 'X8 Pro SES',
}

# Data source descriptions for debugging
KEY_DESCRIPTIONS = {
    "163": "Battery Level (NEW Android App - 100% accuracy)",
    "167": "Water Tank Level (NEW Android App - Key 167 Byte 4, 82% accuracy)",
    "177": "Alternative Water Tank Source",
    "178": "Real-time Data Source", 
    "168": "Accessories Status",
    "153": "Work Status/Mode",
    "152": "Play/Pause Commands",
    "158": "Clean Speed Settings",
    "154": "Cleaning Parameters",
    "155": "Direction Controls",
    "160": "Find Robot",
    "173": "Go Home Commands",
    "180": "Accessory Data (PRIMARY INVESTIGATION TARGET)",  # Enhanced description
    "164": "Alternative Water Tank (from existing research)",
    # RestConnect enhanced descriptions
    "181": "Enhanced Accessory Data 1 (RestConnect)",
    "182": "Enhanced Accessory Data 2 (RestConnect)",
    "183": "Enhanced Accessory Data 3 (RestConnect)",
    "184": "Enhanced Accessory Data 4 (RestConnect)",
    "185": "Enhanced Accessory Data 5 (RestConnect)",
    "186": "Runtime Statistics (RestConnect)",
    "187": "Maintenance Data (RestConnect)",
    "188": "Consumable Status (RestConnect)",
    "189": "Water Tank Detailed (RestConnect)",
    "190": "Sensor Diagnostics (RestConnect)",
}

# RestConnect API endpoints
RESTCONNECT_ENDPOINTS = {
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

# INVESTIGATION MODE BENEFITS - NEW
INVESTIGATION_BENEFITS = [
    "🔍 Complete byte-by-byte analysis of Key 180 payload",
    "📊 Structured JSON files for offline analysis",
    "🎯 Before/after cleaning cycle comparison",
    "🧮 Automatic change detection and significance scoring",
    "📁 Organized data files for external tool analysis",
    "🔬 Comprehensive metadata for research reproducibility",
]

# Logging configuration
DEBUG_LOG_INTERVALS = {
    "detailed_log_minutes": 10,  # Detailed log every 10 minutes (reduced from 5)
    "brief_log_updates": 1,      # Brief log for non-detailed updates
    "first_updates_detailed": 1, # Only first update in detail (reduced from 3)
}

# INVESTIGATION LOGGING - NEW
INVESTIGATION_LOG_CONFIG = {
    "log_every_update": True,  # Log Key 180 on every update in investigation mode
    "create_session_files": True,  # Create organized session files
    "include_hex_dump": True,  # Include complete hex dump in analysis
    "include_context_keys": ["163", "167", "168", "158", "153"],  # Other keys to include for context
    "auto_detect_cleaning_cycles": True,  # Try to detect when cleaning starts/stops
    "comparison_sensitivity": 1,  # Detect changes as small as 1 byte difference
}

# Connection status indicators
CONNECTION_STATUS_EMOJIS = {
    "restconnect": "🌐",
    "basic_login": "📱",
    "connected": "🟢",
    "disconnected": "🔴",
    "fallback": "🟡",
    "error": "❌",
    "investigation": "🔍",  # NEW: Investigation mode indicator
}
