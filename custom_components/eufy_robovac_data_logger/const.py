"""Constants for Eufy Robovac Data Logger integration."""

# Integration constants - MUST STAY EXACTLY AS IS
DOMAIN = "eufy-robovac-data-logger"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEBUG_MODE = "debug_mode"

# Update interval in seconds
UPDATE_INTERVAL = 10

# DPS keys to log (150-180)
DPS_KEYS_TO_LOG = list(range(150, 181))

# Log directory
LOG_DIR = "eufy_dps_logs"

# Data keys we want to monitor - FOR LOGGING 150-180
MONITORED_KEYS = [str(i) for i in range(150, 181)]

# Clean speed mappings (for Key 158) - USED BY STATE.PY
CLEAN_SPEED_NAMES = ["quiet", "standard", "turbo", "max"]

# Work status mappings (for Key 153) - USED BY STATE.PY
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

# Eufy X10 device models - NEEDED FOR DEVICE IDENTIFICATION
EUFY_X10_MODELS = {
    'T2351': 'X10 Pro Omni',
    'T2320': 'X10 Pro',
    'T2262': 'X8',
    'T2261': 'X8 Hybrid',
    'T2266': 'X8 Pro',
    'T2276': 'X8 Pro SES',
}

# Key descriptions for debugging
KEY_DESCRIPTIONS = {str(i): f"Key {i}" for i in range(150, 181)}