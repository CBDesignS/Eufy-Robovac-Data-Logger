"""Constants for the Eufy Robovac Data Logger integration."""
import logging

# CRITICAL DEBUG: Add logging immediately at module level
_LOGGER = logging.getLogger(__name__)
_LOGGER.error("🚨 DEBUG: const.py module loading started")

# Domain
DOMAIN = "eufy_robovac_data_logger"
_LOGGER.error(f"✅ DEBUG: DOMAIN set to: {DOMAIN}")

# Update interval in seconds
UPDATE_INTERVAL = 30
_LOGGER.error(f"✅ DEBUG: UPDATE_INTERVAL set to: {UPDATE_INTERVAL}")

# Configuration keys
CONF_DEBUG_MODE = "debug_mode"
CONF_INVESTIGATION_MODE = "investigation_mode"
_LOGGER.error("✅ DEBUG: Configuration keys defined")

# MULTI-KEY MONITORING - Enhanced Smart Investigation Mode v4.0
MONITORED_KEYS = [
    "163",  # Battery (confirmed - shows 35%)
    "167",  # Water tank data (Key 167, Byte 4 - 82% accuracy)
    "177",  # Alternative water tank source
    "178",  # Real-time data source
    "168",  # Accessories status
    "153",  # Work status/mode
    "152",  # Play/pause commands
    "158",  # Clean speed settings
    "154",  # Cleaning parameters
    "161",  # Potential water tank level
    "164",  # Alternative water tank
    "180",  # Current investigation target (keep)
]
_LOGGER.error(f"✅ DEBUG: MONITORED_KEYS defined with {len(MONITORED_KEYS)} keys")

# RestConnect Enhanced Keys
RESTCONNECT_ENHANCED_KEYS = [
    "181", "182", "183", "184", "185",  # Enhanced accessory data
    "186", "187", "188", "189", "190"   # Runtime, maintenance, consumables
]
_LOGGER.error(f"✅ DEBUG: RESTCONNECT_ENHANCED_KEYS defined with {len(RESTCONNECT_ENHANCED_KEYS)} keys")

# Combine all monitored keys
ALL_MONITORED_KEYS = MONITORED_KEYS + RESTCONNECT_ENHANCED_KEYS
_LOGGER.error(f"✅ DEBUG: ALL_MONITORED_KEYS combined: {len(ALL_MONITORED_KEYS)} total keys")

# Clean speed names
CLEAN_SPEED_NAMES = {
    0: "Auto",
    1: "No Suction",
    2: "Standard",
    3: "Boost IQ",
    4: "Max"
}
_LOGGER.error("✅ DEBUG: CLEAN_SPEED_NAMES defined")

# Work status mapping
WORK_STATUS_MAP = {
    0: "Standby",
    1: "Cleaning", 
    2: "Going Home",
    3: "Charging",
    4: "Go Charging",
    5: "Mopping",
    6: "Drying",
    7: "Manual Paused",
    8: "Sleeping",
    9: "Error",
    10: "Remote Control Cleaning",
    11: "Sleeping",
    12: "Manual Mode",
    13: "Zone Cleaning",
    14: "Spot Cleaning",
    15: "Fast Mapping"
}
_LOGGER.error("✅ DEBUG: WORK_STATUS_MAP defined")

# API endpoints
API_BASE = "https://mysecurity.eufylife.com/api/v1"
LOGIN_ENDPOINT = f"{API_BASE}/passport/login"
DEVICE_LIST_ENDPOINT = f"{API_BASE}/app/get_devs_list"
DEVICE_PROPS_ENDPOINT = f"{API_BASE}/app/get_device_upgrade_status"
_LOGGER.error("✅ DEBUG: API endpoints defined")

# RestConnect endpoints
RESTCONNECT_BASE = "https://openapi.api.eufylife.com/v1"
RESTCONNECT_ENDPOINTS = {
    "device_info": f"{RESTCONNECT_BASE}/device/info",
    "device_status": f"{RESTCONNECT_BASE}/device/status", 
    "accessory_info": f"{RESTCONNECT_BASE}/device/accessory",
    "consumable_info": f"{RESTCONNECT_BASE}/device/consumable",
    "runtime_info": f"{RESTCONNECT_BASE}/device/runtime"
}
_LOGGER.error("✅ DEBUG: RESTCONNECT_ENDPOINTS defined")

# Default values
DEFAULT_OPENUDID = "eufy_ha_integration"
DEFAULT_DEVICE_MODEL = "T8213"
DEFAULT_UPDATE_INTERVAL = 30
_LOGGER.error("✅ DEBUG: Default values defined")

# Investigation mode settings
INVESTIGATION_DIR_NAME = "eufy_investigation"
ACCESSORY_CONFIG_DIR = "accessories"
SENSORS_TEMPLATE_FILE = "sensors.json"
_LOGGER.error("✅ DEBUG: Investigation mode settings defined")

# Sensor entity IDs
SENSOR_BATTERY = "battery"
SENSOR_CLEAN_SPEED = "clean_speed"
SENSOR_RAW_DATA = "raw_data"
SENSOR_MONITORING = "monitoring"
SENSOR_ACCESSORY_CONFIG = "accessory_config_manager"
SENSOR_RESTCONNECT_STATUS = "restconnect_status"
SENSOR_INVESTIGATION_STATUS = "investigation_status"
_LOGGER.error("✅ DEBUG: Sensor entity IDs defined")

# Error messages
ERROR_LOGIN_FAILED = "Login to Eufy account failed"
ERROR_DEVICE_NOT_FOUND = "Device not found in account"
ERROR_DATA_FETCH_FAILED = "Failed to fetch device data"
ERROR_INVESTIGATION_INIT_FAILED = "Failed to initialize investigation mode"
_LOGGER.error("✅ DEBUG: Error messages defined")

_LOGGER.error("🎯 DEBUG: const.py module loading completed successfully")