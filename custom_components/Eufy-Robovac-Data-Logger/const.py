"""Constants for Eufy Robovac Data Logger integration."""

# Integration constants
DOMAIN = "Eufy-Robovac-Data-Logger"
CONF_USERNAME = "username"
CONF_PASSWORD = "password" 
CONF_DEBUG_MODE = "debug_mode"

# Update interval in seconds
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
    "180",  # Accessory data (from existing research)
    "164",  # Alternative water tank (from existing research)
]

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
    "180": "Accessory Data (from existing research)",
    "164": "Alternative Water Tank (from existing research)",
}
