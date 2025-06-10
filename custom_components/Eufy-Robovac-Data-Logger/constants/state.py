"""State constants for Eufy Robovac Data Logger integration - Simplified for debugging focus."""

from enum import Enum

# Work status mappings (Key 153)
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

# Clean speed names (Key 158)
CLEAN_SPEED_NAMES = ["quiet", "standard", "turbo", "max"]

# Basic vacuum states for Home Assistant compatibility
class VACUUM_STATE(str, Enum):
    STOPPED = 'stopped'
    CLEANING = 'cleaning'
    DOCKED = 'docked'
    CHARGING = 'charging'
    RETURNING = 'returning'
    ERROR = 'error'

# Clean speed enum for debugging
class CLEAN_SPEED(str, Enum):
    QUIET = 'quiet'
    STANDARD = 'standard'
    TURBO = 'turbo'
    MAX = 'max'

# Work mode enum for debugging
class WORK_MODE(str, Enum):
    AUTO = 'auto'
    ROOM = 'room'
    ZONE = 'zone'
    SPOT = 'spot'
    EDGE = 'edge'

# Error codes (common ones for debugging)
COMMON_ERROR_CODES = {
    0: 'NONE',
    1: 'CRASH_BUFFER_STUCK',
    2: 'WHEEL_STUCK',
    3: 'SIDE_BRUSH_STUCK',
    4: 'ROLLING_BRUSH_STUCK',
    5: 'HOST_TRAPPED_CLEAR_OBST',
    6: 'MACHINE_TRAPPED_MOVE',
    7: 'WHEEL_OVERHANGING',
    8: 'POWER_LOW_SHUTDOWN',
    13: 'HOST_TILTED',
    14: 'NO_DUST_BOX',
    21: 'DOCK_FAILED',
    72: 'ROBOVAC_LOW_WATER',
    73: 'DIRTY_TANK_FULL',
    74: 'CLEAN_WATER_LOW',
    75: 'WATER_TANK_ABSENT',
}

def get_work_status_name(status_code: int) -> str:
    """Get human-readable work status from code."""
    return WORK_STATUS_MAP.get(status_code, f"unknown_{status_code}")

def get_clean_speed_name(speed_code: int) -> str:
    """Get human-readable clean speed from code."""
    if 0 <= speed_code < len(CLEAN_SPEED_NAMES):
        return CLEAN_SPEED_NAMES[speed_code]
    return f"unknown_{speed_code}"

def get_error_description(error_code: int) -> str:
    """Get human-readable error description from code."""
    return COMMON_ERROR_CODES.get(error_code, f"UNKNOWN_ERROR_{error_code}")
