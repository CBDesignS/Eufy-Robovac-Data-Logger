"""
Accessory Configuration Manager for Eufy Robovac Data Logger integration.
FIXED VERSION: Properly implements template inheritance from sensors.json.
Preserves user template values (null byte positions, real percentages, disabled state).
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
    Manages accessory sensor configuration with PROPER template inheritance.
    FIXED: Now correctly reads sensors.json template and preserves all user values.
    """
    
    def __init__(self, integration_dir: str, device_id: str):
        """Initialize the accessory config manager."""
        self.device_id = device_id
        
        # Create accessories directory in integration folder
        self.accessories_dir = Path(integration_dir) / "accessories"
        self.accessories_dir.mkdir(exist_ok=True)
        
        # Template file (user-editable master template)
        self.template_file = self.accessories_dir / "sensors.json"
        
        # Device-specific config file
        self.config_file = self.accessories_dir / f"sensors_{device_id}.json"
        
        # Backup file for safety
        self.backup_file = self.accessories_dir / f"sensors_{device_id}_backup.json"
        
        # In-memory config cache
        self._config_cache: Optional[Dict] = None
        self._last_loaded: Optional[float] = None
        
        # File lock for thread safety
        self._file_lock = asyncio.Lock()
        
        _LOGGER.info("🔧 AccessoryConfigManager initialized for device: %s", device_id)
        _LOGGER.info("📂 Template file: %s", self.template_file)
        _LOGGER.info("📂 Device config file: %s", self.config_file)

    async def ensure_default_config(self) -> None:
        """
        FIXED: Smart template-based config generation with proper inheritance.
        """
        if not self.config_file.exists():
            _LOGGER.info("📝 Device config file missing, checking template and recovery options...")
            
            # OPTION 1: Try to restore from backup (preserves user work)
            if self.backup_file.exists():
                try:
                    _LOGGER.info("💾 Found backup file, restoring device configuration...")
                    
                    # Copy backup to main config file
                    async with aiofiles.open(self.backup_file, 'r', encoding='utf-8') as backup_f:
                        backup_content = await backup_f.read()
                        # Validate backup is valid JSON
                        backup_config = json.loads(backup_content)
                    
                    async with aiofiles.open(self.config_file, 'w', encoding='utf-8') as main_f:
                        await main_f.write(backup_content)
                    
                    _LOGGER.info("✅ Device configuration restored from backup successfully")
                    _LOGGER.info("📍 Restored file: %s", self.config_file)
                    return
                    
                except Exception as e:
                    _LOGGER.error("❌ Failed to restore from backup: %s", e)
                    _LOGGER.info("⚠️ Backup file corrupted, checking template")
            
            # OPTION 2: Generate from template (FIXED - proper template inheritance)
            if self.template_file.exists():
                try:
                    _LOGGER.info("📋 Found sensors.json template, generating device config from template...")
                    _LOGGER.info("🔄 Template inheritance: Preserving ALL user template values")
                    
                    device_config = await self._create_config_from_template()
                    await self.save_config(device_config, create_backup=False)
                    
                    _LOGGER.info("✅ Device configuration created from template successfully")
                    _LOGGER.info("📍 Template values preserved: null byte positions, real percentages, disabled state")
                    _LOGGER.info("🔧 Investigation Mode ready: All sensors start disabled for discovery")
                    return
                    
                except Exception as e:
                    _LOGGER.error("❌ Failed to create config from template: %s", e)
                    _LOGGER.info("⚠️ Template corrupted, falling back to hardcoded defaults")
            
            # OPTION 3: Create hardcoded defaults (fallback only)
            _LOGGER.info("📝 No template found, creating hardcoded default configuration")
            _LOGGER.info("⚠️ FALLBACK MODE: Using hardcoded defaults instead of template")
            
            default_config = await self._create_hardcoded_default_config()
            await self.save_config(default_config, create_backup=False)
            
            _LOGGER.info("✅ Hardcoded default configuration created")
            _LOGGER.info("💡 Create sensors.json template for better Investigation Mode support")
        else:
            _LOGGER.info("📁 Using existing device configuration (hands-off mode)")
            _LOGGER.info("🔒 File exists - integration will not modify user's settings")

    async def _create_config_from_template(self) -> Dict[str, Any]:
        """
        FIXED: Create device config from sensors.json template with proper inheritance.
        Preserves ALL template values - only updates device-specific metadata.
        """
        try:
            # Load the template file
            async with aiofiles.open(self.template_file, 'r', encoding='utf-8') as f:
                template_content = await f.read()
                template_config = json.loads(template_content)
            
            _LOGGER.info("📋 Template loaded successfully")
            _LOGGER.info(f"📊 Template contains {len(template_config.get('accessory_sensors', {}))} accessory sensors")
            
            # CRITICAL FIX: Use template as base, only update device-specific fields
            device_config = template_config.copy()  # Start with template
            
            # Update ONLY device-specific metadata (preserve all sensor configs)
            current_time = datetime.now().isoformat()
            
            device_config["device_info"] = {
                "device_id": self.device_id,  # Device-specific
                "created": current_time,      # Device-specific
                "last_updated": current_time, # Device-specific
                "config_version": template_config.get("device_info", {}).get("config_version", "2.0"),
                "auto_generated": True,       # Device-specific
                "template_file": False,       # Device-specific
                "inherited_from_template": True,  # NEW: Track inheritance
                "template_timestamp": template_config.get("device_info", {}).get("last_updated", "unknown")
            }
            
            # PRESERVE ALL TEMPLATE SENSOR CONFIGURATIONS (this was missing!)
            # The accessory_sensors section is kept exactly as-is from template
            
            # Log what we're preserving from template
            template_sensors = template_config.get("accessory_sensors", {})
            _LOGGER.info("🔄 PRESERVING template sensor configurations:")
            
            for sensor_id, sensor_config in template_sensors.items():
                byte_pos = sensor_config.get("byte_position")
                life_pct = sensor_config.get("current_life_remaining", 0)
                enabled = sensor_config.get("enabled", False)
                _LOGGER.info(f"   📍 {sensor_config.get('name', sensor_id)}: {life_pct}% life, byte_position={byte_pos}, enabled={enabled}")
            
            # PRESERVE discovery_settings and advanced_settings from template
            # (Keep template values, don't override)
            
            _LOGGER.info("✅ Device config created from template with proper inheritance")
            _LOGGER.info("🎯 Template values preserved: byte positions, percentages, enabled states")
            
            return device_config
            
        except Exception as e:
            _LOGGER.error("❌ Template inheritance failed: %s", e)
            raise

    async def _create_hardcoded_default_config(self) -> Dict[str, Any]:
        """Create hardcoded default configuration (FALLBACK ONLY when no template)."""
        _LOGGER.info("⚠️ CREATING HARDCODED DEFAULTS - Template not available")
        
        return {
            "device_info": {
                "device_id": self.device_id,
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "config_version": "2.0",
                "auto_generated": True,
                "template_file": False,
                "inherited_from_template": False,
                "fallback_mode": True
            },
            "accessory_sensors": {
                "rolling_brush": {
                    "name": "Rolling Brush",
                    "description": "Main cleaning brush - primary debris collection mechanism",
                    "key": "180",
                    "byte_position": None,  # Investigation mode: unknown position
                    "current_life_remaining": 100,  # Default fresh
                    "hours_remaining": 360,
                    "max_life_hours": 360,
                    "replacement_threshold": 10,
                    "enabled": False,  # Investigation mode: start disabled
                    "auto_update": False,
                    "last_updated": datetime.now().isoformat(),
                    "notes": "HARDCODED DEFAULT - Create sensors.json template for Investigation Mode"
                },
                "side_brush": {
                    "name": "Side Brush",
                    "description": "Edge cleaning brush - sweeps debris into main brush path",
                    "key": "180",
                    "byte_position": None,  # Investigation mode: unknown position
                    "current_life_remaining": 100,  # Default fresh
                    "hours_remaining": 180,
                    "max_life_hours": 180,
                    "replacement_threshold": 15,
                    "enabled": False,  # Investigation mode: start disabled
                    "auto_update": False,
                    "last_updated": datetime.now().isoformat(),
                    "notes": "HARDCODED DEFAULT - Create sensors.json template for Investigation Mode"
                },
                "dust_filter": {
                    "name": "Dust Filter",
                    "description": "Air filtration system - captures fine dust and allergens",
                    "key": "180",
                    "byte_position": None,  # Investigation mode: unknown position
                    "current_life_remaining": 100,  # Default fresh
                    "hours_remaining": 150,
                    "max_life_hours": 150,
                    "replacement_threshold": 20,
                    "enabled": False,  # Investigation mode: start disabled
                    "auto_update": False,
                    "last_updated": datetime.now().isoformat(),
                    "notes": "HARDCODED DEFAULT - Create sensors.json template for Investigation Mode"
                },
                "mop_cloth": {
                    "name": "Mop Cloth",
                    "description": "Mopping attachment - for wet cleaning hard floors",
                    "key": "180",
                    "byte_position": None,  # Investigation mode: unknown position
                    "current_life_remaining": 100,  # Default fresh
                    "hours_remaining": 50,
                    "max_life_hours": 50,
                    "replacement_threshold": 30,
                    "enabled": False,  # Investigation mode: start disabled
                    "auto_update": False,
                    "last_updated": datetime.now().isoformat(),
                    "notes": "HARDCODED DEFAULT - Create sensors.json template for Investigation Mode"
                }
            },
            "discovery_settings": {
                "enabled_for_discovery": ["181", "182", "183", "184", "185"],
                "auto_add_found_sensors": False,
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
                "=== HARDCODED DEFAULT CONFIGURATION ===",
                "",
                "⚠️ This was created without a sensors.json template",
                "🔧 For Investigation Mode, create sensors.json with real Android app data",
                "📝 Template should have null byte positions and real percentages",
                "🔄 Restart integration after creating template for proper inheritance"
            ]
        }

    async def load_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load accessory configuration from device-specific JSON file."""
        async with self._file_lock:
            current_time = datetime.now().timestamp()
            
            # Use cache if available and recent (unless forced)
            if (not force_reload and 
                self._config_cache is not None and 
                self._last_loaded is not None and 
                current_time - self._last_loaded < 30):  # 30 second cache
                return self._config_cache.copy()
            
            try:
                # Ensure device config exists (will use template if available)
                await self.ensure_default_config()
                
                # Load from device-specific file
                async with aiofiles.open(self.config_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    config = json.loads(content)
                
                # AUTO-BACKUP: Create backup if config file exists but no backup exists
                if self.config_file.exists() and not self.backup_file.exists():
                    try:
                        _LOGGER.info("💾 Creating initial backup of device configuration...")
                        async with aiofiles.open(self.backup_file, 'w', encoding='utf-8') as backup_f:
                            await backup_f.write(content)
                        _LOGGER.info("✅ Initial backup created: %s", self.backup_file.name)
                    except Exception as backup_error:
                        _LOGGER.warning("⚠️ Failed to create initial backup: %s", backup_error)
                
                # Update cache
                self._config_cache = config.copy()
                self._last_loaded = current_time
                
                # Log inheritance status
                device_info = config.get("device_info", {})
                if device_info.get("inherited_from_template"):
                    _LOGGER.debug("📖 Device config loaded (inherited from template)")
                elif device_info.get("fallback_mode"):
                    _LOGGER.debug("📖 Device config loaded (hardcoded fallback)")
                else:
                    _LOGGER.debug("📖 Device config loaded (user-created)")
                
                return config
                
            except FileNotFoundError:
                _LOGGER.error("❌ Device configuration file not found: %s", self.config_file)
                # Try to create default and reload
                await self.ensure_default_config()
                return await self.load_config(force_reload=True)
                
            except json.JSONDecodeError as e:
                _LOGGER.error("❌ Invalid JSON in device config file: %s", e)
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
                
                # Last resort: recreate from template or defaults
                _LOGGER.warning("⚠️ Creating new configuration due to corruption")
                # Remove corrupted file first
                if self.config_file.exists():
                    self.config_file.unlink()
                await self.ensure_default_config()
                return await self.load_config(force_reload=True)
                
            except Exception as e:
                _LOGGER.error("❌ Unexpected error loading config: %s", e)
                raise

    async def save_config(self, config: Dict[str, Any], create_backup: bool = True) -> bool:
        """Save accessory configuration to device-specific JSON file."""
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
                
                _LOGGER.debug("💾 Device configuration saved successfully")
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
                _LOGGER.warning("⚠️ Accessory '%s' not found in device configuration", accessory_id)
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
        """Get all enabled accessory sensors from device configuration."""
        try:
            config = await self.load_config()
            enabled_sensors = {}
            
            for sensor_id, sensor_config in config.get("accessory_sensors", {}).items():
                if sensor_config.get("enabled", False):
                    enabled_sensors[sensor_id] = sensor_config.copy()
            
            _LOGGER.debug("📋 Found %d enabled sensors in device config", len(enabled_sensors))
            
            # Log inheritance status
            device_info = config.get("device_info", {})
            if device_info.get("inherited_from_template"):
                _LOGGER.debug("🔄 Sensors inherited from template: sensors.json")
            elif device_info.get("fallback_mode"):
                _LOGGER.debug("⚠️ Sensors from hardcoded fallback (no template)")
            
            return enabled_sensors
            
        except Exception as e:
            _LOGGER.error("❌ Error getting enabled sensors: %s", e)
            return {}

    async def get_discovery_settings(self) -> Dict[str, Any]:
        """Get discovery settings from device configuration."""
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
        """Get the full path to the device configuration file for user reference."""
        return str(self.config_file.absolute())

    def get_template_file_path(self) -> str:
        """Get the full path to the template file for user reference."""
        return str(self.template_file.absolute())

    async def validate_config(self) -> Dict[str, Any]:
        """Validate the device configuration and return validation results."""
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
                required_fields = ["name", "key", "current_life_remaining"]
                for field in required_fields:
                    if field not in sensor_config:
                        issues.append(f"Sensor '{sensor_id}' missing required field: {field}")
                
                # Check value ranges
                life_remaining = sensor_config.get("current_life_remaining", 0)
                if not 0 <= life_remaining <= 100:
                    warnings.append(f"Sensor '{sensor_id}' has invalid life percentage: {life_remaining}")
            
            # Check inheritance status
            device_info = config.get("device_info", {})
            inheritance_status = "unknown"
            if device_info.get("inherited_from_template"):
                inheritance_status = "template_inherited"
            elif device_info.get("fallback_mode"):
                inheritance_status = "hardcoded_fallback"
            elif device_info.get("auto_generated"):
                inheritance_status = "auto_generated"
            else:
                inheritance_status = "user_created"
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "total_sensors": len(config.get("accessory_sensors", {})),
                "enabled_sensors": len([s for s in config.get("accessory_sensors", {}).values() 
                                      if s.get("enabled", False)]),
                "inheritance_status": inheritance_status,
                "template_available": self.template_file.exists(),
                "auto_generated": device_info.get("auto_generated", False),
                "template_inheritance_working": device_info.get("inherited_from_template", False)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "issues": [f"Configuration validation error: {e}"],
                "warnings": [],
                "total_sensors": 0,
                "enabled_sensors": 0,
                "inheritance_status": "error",
                "template_available": False,
                "auto_generated": False,
                "template_inheritance_working": False
            }