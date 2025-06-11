"""
Accessory Configuration Manager for Eufy Robovac Data Logger integration.
Manages user-editable JSON configuration files for accessory sensors and discovery settings.
HANDS-OFF APPROACH: Write once on first setup, then never modify user's file.
"""

import asyncio
import aiofiles
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

_LOGGER = logging.getLogger(__name__)


class AccessoryConfigManager:
    """
    Manages accessory sensor configuration through user-editable JSON files.
    WRITE ONCE, READ MANY: Only creates defaults on first setup, then hands-off.
    """
    
    def __init__(self, integration_dir: str, device_id: str):
        """Initialize the accessory config manager."""
        self.device_id = device_id
        
        # Create accessories directory in integration folder
        self.accessories_dir = Path(integration_dir) / "accessories"
        self.accessories_dir.mkdir(exist_ok=True)
        
        # Main config file for this device
        self.config_file = self.accessories_dir / f"sensors_{device_id}.json"
        
        # Backup file for safety
        self.backup_file = self.accessories_dir / f"sensors_{device_id}_backup.json"
        
        # In-memory config cache
        self._config_cache: Optional[Dict] = None
        self._last_loaded: Optional[float] = None
        
        # File lock for thread safety
        self._file_lock = asyncio.Lock()
        
        _LOGGER.info("🔧 AccessoryConfigManager initialized for device: %s", device_id)
        _LOGGER.info("📂 Config file: %s", self.config_file)

    async def ensure_default_config(self) -> None:
        """Create default configuration ONLY if file doesn't exist (first time setup)."""
        if not self.config_file.exists():
            _LOGGER.info("📝 Creating default accessory configuration (FIRST TIME SETUP)")
            _LOGGER.info("🏠 This file will be hands-off after creation - user controls it completely")
            
            default_config = {
                "device_info": {
                    "device_id": self.device_id,
                    "created": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "config_version": "1.0"
                },
                "accessory_sensors": {
                    "rolling_brush": {
                        "name": "Rolling Brush",
                        "description": "Main cleaning brush - checks for hair tangles and wear",
                        "key": "180",
                        "byte_position": 146,
                        "current_life_remaining": 100,
                        "max_life_hours": 300,
                        "replacement_threshold": 10,
                        "enabled": True,
                        "auto_update": True,
                        "last_updated": datetime.now().isoformat(),
                        "notes": "Replace when tangled or worn down"
                    },
                    "side_brush": {
                        "name": "Side Brush",
                        "description": "Edge cleaning brush - sweeps debris into main brush path",
                        "key": "180",
                        "byte_position": 37,
                        "current_life_remaining": 100,
                        "max_life_hours": 200,
                        "replacement_threshold": 15,
                        "enabled": True,
                        "auto_update": True,
                        "last_updated": datetime.now().isoformat(),
                        "notes": "Replace when bent or missing bristles"
                    },
                    "dust_filter": {
                        "name": "Dust Filter",
                        "description": "Air filtration system - captures fine dust and allergens",
                        "key": "180",
                        "byte_position": 228,
                        "current_life_remaining": 100,
                        "max_life_hours": 150,
                        "replacement_threshold": 20,
                        "enabled": True,
                        "auto_update": True,
                        "last_updated": datetime.now().isoformat(),
                        "notes": "Replace when dirty or reduced suction"
                    },
                    "mop_cloth": {
                        "name": "Mop Cloth",
                        "description": "Mopping attachment - for wet cleaning hard floors",
                        "key": "180",
                        "byte_position": 5,
                        "current_life_remaining": 100,
                        "max_life_hours": 50,
                        "replacement_threshold": 30,
                        "enabled": True,
                        "auto_update": True,
                        "last_updated": datetime.now().isoformat(),
                        "notes": "Replace when frayed or no longer absorbs water"
                    },
                    "sensors": {
                        "name": "Cliff/Bump Sensors",
                        "description": "Navigation sensors - prevents falls and detects obstacles",
                        "key": "180",
                        "byte_position": 95,
                        "current_life_remaining": 100,
                        "max_life_hours": 1000,
                        "replacement_threshold": 5,
                        "enabled": True,
                        "auto_update": True,
                        "last_updated": datetime.now().isoformat(),
                        "notes": "Clean regularly, rarely need replacement"
                    }
                },
                "discovery_settings": {
                    "enabled_for_discovery": [
                        "181", "182", "183", "184", "185", "186", "187", "188", "189", "190"
                    ],
                    "auto_add_found_sensors": True,
                    "stop_searching_after_found": True,
                    "discovery_timeout_seconds": 300,
                    "min_updates_before_stop": 5,
                    "last_discovery_run": None
                },
                "advanced_settings": {
                    "backup_enabled": True,
                    "auto_backup_interval_hours": 24,
                    "log_accessory_changes": True,
                    "alert_on_low_life": True,
                    "maintenance_reminder_days": [7, 3, 1]
                },
                "user_notes": [
                    "=== HANDS-OFF USER CONFIGURATION ===",
                    "",
                    "🏠 This file is now YOURS to manage:",
                    "  • Edit accessory life percentages as they wear down",
                    "  • Add/remove accessories as needed",
                    "  • Modify thresholds and settings",
                    "  • The integration will NEVER overwrite your changes",
                    "",
                    "📝 EDITING INSTRUCTIONS:",
                    "  • Update 'current_life_remaining' percentages as accessories wear down",
                    "  • Set 'enabled': false to disable tracking for specific accessories",
                    "  • Adjust 'replacement_threshold' to change when low-life alerts trigger",
                    "  • Add notes about replacement dates or maintenance performed",
                    "",
                    "🔄 AFTER EDITING:",
                    "  • Restart the Home Assistant integration to load new values",
                    "  • Check the debug logs for accessory change detection",
                    "  • Monitor sensor entities for updated values",
                    "",
                    "⚠️ INTEGRATION UPDATES:",
                    "  • This file will NEVER be modified by integration updates",
                    "  • You have complete control - add/remove sensors as desired",
                    "  • New default sensors (if any) won't be auto-added",
                    "",
                    "💡 PRO TIPS:",
                    "  • Keep a maintenance log in the 'notes' field",
                    "  • Use realistic wear rates based on actual cleaning frequency",
                    "  • Set calendar reminders based on 'hours_remaining'",
                    "  • Compare multiple cleaning sessions to confirm sensor locations"
                ]
            }
            
            await self.save_config(default_config, create_backup=False)
            _LOGGER.info("✅ Default configuration created - now under user control")
        else:
            _LOGGER.info("📁 Using existing user configuration (hands-off mode)")
            _LOGGER.info("🔒 File exists - integration will not modify user's settings")

    async def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load accessory configuration from JSON file - HANDS-OFF approach."""
        async with self._file_lock:
            current_time = datetime.now().timestamp()
            
            # Use cache if available and recent (unless forced)
            if (not force_reload and 
                self._config_cache is not None and 
                self._last_loaded is not None and 
                current_time - self._last_loaded < 30):  # 30 second cache
                return self._config_cache.copy()
            
            try:
                # Ensure config exists (first time setup only)
                await self.ensure_default_config()
                
                # Load from file AS-IS (no modifications)
                async with aiofiles.open(self.config_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    config = json.loads(content)
                
                # Update cache
                self._config_cache = config.copy()
                self._last_loaded = current_time
                
                _LOGGER.debug("📖 User configuration loaded successfully (hands-off)")
                return config
                
            except FileNotFoundError:
                _LOGGER.error("❌ Configuration file not found: %s", self.config_file)
                # Try to create default and reload
                await self.ensure_default_config()
                return await self.load_config(force_reload=True)
                
            except json.JSONDecodeError as e:
                _LOGGER.error("❌ Invalid JSON in user config file: %s", e)
                # Try to restore from backup
                if self.backup_file.exists():
                    _LOGGER.info("🔄 Attempting to restore from backup")
                    try:
                        async with aiofiles.open(self.backup_file, 'r', encoding='utf-8') as f:
                            backup_content = await f.read()
                            backup_config = json.loads(backup_content)
                        
                        # Restore from backup
                        await self.save_config(backup_config, create_backup=False)
                        _LOGGER.info("✅ Configuration restored from backup")
                        return backup_config
                        
                    except Exception as backup_error:
                        _LOGGER.error("❌ Backup restore failed: %s", backup_error)
                
                # Last resort: create new default config
                _LOGGER.warning("⚠️ Creating new default configuration due to corruption")
                await self.ensure_default_config()
                return await self.load_config(force_reload=True)
                
            except Exception as e:
                _LOGGER.error("❌ Unexpected error loading config: %s", e)
                raise

    async def save_config(self, config: Dict[str, Any], create_backup: bool = True) -> bool:
        """Save accessory configuration to JSON file."""
        async with self._file_lock:
            try:
                # Update metadata (only touch metadata, not user data)
                if "device_info" in config:
                    config["device_info"]["last_updated"] = datetime.now().isoformat()
                
                # Create backup if enabled and requested
                if create_backup and self.config_file.exists():
                    try:
                        async with aiofiles.open(self.config_file, 'r', encoding='utf-8') as f:
                            backup_content = await f.read()
                        async with aiofiles.open(self.backup_file, 'w', encoding='utf-8') as f:
                            await f.write(backup_content)
                        _LOGGER.debug("💾 Backup created successfully")
                    except Exception as backup_error:
                        _LOGGER.warning("⚠️ Failed to create backup: %s", backup_error)
                
                # Write new config
                config_json = json.dumps(config, indent=2, ensure_ascii=False)
                async with aiofiles.open(self.config_file, 'w', encoding='utf-8') as f:
                    await f.write(config_json)
                
                # Update cache
                self._config_cache = config.copy()
                self._last_loaded = datetime.now().timestamp()
                
                _LOGGER.debug("💾 Configuration saved successfully")
                return True
                
            except Exception as e:
                _LOGGER.error("❌ Failed to save configuration: %s", e)
                return False

    async def update_accessory_life(self, accessory_id: str, new_percentage: int, 
                                   notes: Optional[str] = None) -> bool:
        """Update life remaining percentage for a specific accessory."""
        try:
            config = await self.load_config()
            
            if accessory_id not in config.get("accessory_sensors", {}):
                _LOGGER.warning("⚠️ Accessory '%s' not found in user configuration", accessory_id)
                return False
            
            # Update the accessory
            accessory = config["accessory_sensors"][accessory_id]
            old_percentage = accessory.get("current_life_remaining", 0)
            
            accessory["current_life_remaining"] = max(0, min(100, new_percentage))
            accessory["last_updated"] = datetime.now().isoformat()
            
            if notes:
                accessory["notes"] = notes
            
            # Save updated config
            success = await self.save_config(config)
            
            if success:
                _LOGGER.info("🔄 Updated %s life: %d%% → %d%%", 
                           accessory_id, old_percentage, new_percentage)
                return True
            else:
                _LOGGER.error("❌ Failed to save updated accessory life")
                return False
                
        except Exception as e:
            _LOGGER.error("❌ Error updating accessory life: %s", e)
            return False

    async def get_enabled_sensors(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled accessory sensors from user configuration."""
        try:
            config = await self.load_config()
            enabled_sensors = {}
            
            for sensor_id, sensor_config in config.get("accessory_sensors", {}).items():
                if sensor_config.get("enabled", False):
                    enabled_sensors[sensor_id] = sensor_config.copy()
            
            _LOGGER.debug("📋 Found %d enabled sensors in user config", len(enabled_sensors))
            return enabled_sensors
            
        except Exception as e:
            _LOGGER.error("❌ Error getting enabled sensors: %s", e)
            return {}

    async def get_discovery_settings(self) -> Dict[str, Any]:
        """Get discovery settings from user configuration."""
        try:
            config = await self.load_config()
            discovery_settings = config.get("discovery_settings", {})
            
            # Only set defaults if the section is completely missing
            if not discovery_settings:
                defaults = {
                    "enabled_for_discovery": ["181", "182", "183", "184", "185"],
                    "auto_add_found_sensors": False,  # Default to False for hands-off
                    "stop_searching_after_found": True,
                    "discovery_timeout_seconds": 300,
                    "min_updates_before_stop": 5
                }
                return defaults
            
            return discovery_settings
            
        except Exception as e:
            _LOGGER.error("❌ Error getting discovery settings: %s", e)
            return {}

    async def update_discovery_run(self) -> None:
        """Update the last discovery run timestamp."""
        try:
            config = await self.load_config()
            if "discovery_settings" not in config:
                config["discovery_settings"] = {}
            
            config["discovery_settings"]["last_discovery_run"] = datetime.now().isoformat()
            await self.save_config(config)
            
        except Exception as e:
            _LOGGER.error("❌ Error updating discovery run timestamp: %s", e)

    async def get_sensors_by_key(self, key: str) -> List[Dict[str, Any]]:
        """Get all sensors that monitor a specific key."""
        try:
            enabled_sensors = await self.get_enabled_sensors()
            matching_sensors = []
            
            for sensor_id, sensor_config in enabled_sensors.items():
                if sensor_config.get("key") == key:
                    sensor_config["sensor_id"] = sensor_id
                    matching_sensors.append(sensor_config)
            
            return matching_sensors
            
        except Exception as e:
            _LOGGER.error("❌ Error getting sensors by key: %s", e)
            return []

    async def get_low_life_accessories(self) -> List[Dict[str, Any]]:
        """Get accessories that are below their replacement threshold."""
        try:
            enabled_sensors = await self.get_enabled_sensors()
            low_life_accessories = []
            
            for sensor_id, sensor_config in enabled_sensors.items():
                current_life = sensor_config.get("current_life_remaining", 100)
                threshold = sensor_config.get("replacement_threshold", 10)
                
                if current_life <= threshold:
                    sensor_config["sensor_id"] = sensor_id
                    low_life_accessories.append(sensor_config)
            
            return low_life_accessories
            
        except Exception as e:
            _LOGGER.error("❌ Error getting low life accessories: %s", e)
            return []

    def get_config_file_path(self) -> str:
        """Get the full path to the configuration file for user reference."""
        return str(self.config_file.absolute())

    async def validate_config(self) -> Dict[str, Any]:
        """Validate the user configuration and return validation results."""
        try:
            config = await self.load_config()
            issues = []
            warnings = []
            
            # Check required sections
            required_sections = ["device_info", "accessory_sensors"]
            for section in required_sections:
                if section not in config:
                    issues.append(f"Missing required section: {section}")
            
            # Validate accessory sensors
            for sensor_id, sensor_config in config.get("accessory_sensors", {}).items():
                required_fields = ["name", "key", "byte_position", "current_life_remaining"]
                for field in required_fields:
                    if field not in sensor_config:
                        issues.append(f"Sensor '{sensor_id}' missing required field: {field}")
                
                # Check value ranges
                life_remaining = sensor_config.get("current_life_remaining", 0)
                if not 0 <= life_remaining <= 100:
                    warnings.append(f"Sensor '{sensor_id}' has invalid life percentage: {life_remaining}")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "total_sensors": len(config.get("accessory_sensors", {})),
                "enabled_sensors": len([s for s in config.get("accessory_sensors", {}).values() 
                                      if s.get("enabled", False)]),
                "user_controlled": True
            }
            
        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Configuration validation error: {e}"],
                "warnings": [],
                "total_sensors": 0,
                "enabled_sensors": 0,
                "user_controlled": False
            }