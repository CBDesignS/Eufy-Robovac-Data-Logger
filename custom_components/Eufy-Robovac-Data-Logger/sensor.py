"""Sensor platform for Eufy Robovac Data Logger integration - CLEANED UP VERSION."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MONITORED_KEYS
from .coordinator import EufyX10DebugCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eufy X10 Debug sensors - CLEANED UP."""
    coordinator: EufyX10DebugCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Core sensors (working and reliable)
    entities = [
        EufyX10DebugBatterySensor(coordinator),           # ✅ Key 163 - Working
        EufyX10DebugCleanSpeedSensor(coordinator),        # ✅ Key 158 - Working
        EufyX10DebugRawDataSensor(coordinator),           # ✅ Debug tool - Useful
        EufyX10DebugMonitoringSensor(coordinator),        # ✅ Monitoring - Useful
        EufyX10DebugAccessoryManagerSensor(coordinator),  # 🆕 Accessory config manager
    ]
    
    # Add dynamic accessory sensors from JSON configuration
    try:
        accessory_sensors = await coordinator.accessory_manager.get_enabled_sensors()
        
        for sensor_id, sensor_config in accessory_sensors.items():
            if sensor_config.get('enabled', False):
                entities.append(EufyX10DynamicAccessorySensor(coordinator, sensor_id, sensor_config))
                _LOGGER.debug("🔧 Added dynamic accessory sensor: %s", sensor_config.get('name'))
        
        _LOGGER.info("🏭 Setting up %d total sensors (%d core + %d accessories) for device %s", 
                    len(entities), 5, len(accessory_sensors), coordinator.device_id)
    
    except Exception as e:
        _LOGGER.error("❌ Failed to load accessory sensors: %s", e)
        _LOGGER.info("🏭 Setting up %d core sensors only for device %s", len(entities), coordinator.device_id)
    
    async_add_entities(entities)


class EufyX10DebugBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Eufy Robovac Data Logger."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, sensor_type: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self.device_id = coordinator.device_id
        
        self._attr_unique_id = f"{self.device_id}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=f"Eufy X10 Debug {self.device_id}",
            manufacturer="Eufy",
            model="X10 Pro Omni (Debug)",
            sw_version="Debug v2.0.0 - Accessory Config",
        )
        
        _LOGGER.debug("🔧 Initialized %s sensor for device %s", sensor_type, self.device_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class EufyX10DebugBatterySensor(EufyX10DebugBaseSensor):
    """Battery sensor for debugging Key 163 - KEPT AS WORKING."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, "battery")
        self._attr_name = f"Eufy X10 Debug Battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:battery"

    @property
    def native_value(self) -> Optional[int]:
        """Return the battery level."""
        battery = self.coordinator.data.get("battery")
        if battery is not None:
            _LOGGER.debug("🔋 Battery sensor value: %d%%", battery)
        return battery

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        raw_163 = self.coordinator.raw_data.get("163")
        attrs = {
            "raw_key_163": raw_163,
            "data_source": "Key 163 (Working)",
            "reliability": "✅ 100% Accurate",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
        }
        
        # Add battery status with emoji indicators
        battery = self.coordinator.data.get("battery")
        if battery is not None:
            if battery <= 10:
                attrs["battery_status"] = "🔴 Critical"
                attrs["battery_emoji"] = "🪫"
            elif battery <= 20:
                attrs["battery_status"] = "🟠 Low" 
                attrs["battery_emoji"] = "🔋"
            elif battery <= 50:
                attrs["battery_status"] = "🟡 Medium"
                attrs["battery_emoji"] = "🔋"
            else:
                attrs["battery_status"] = "🟢 High"
                attrs["battery_emoji"] = "🔋"
        
        return attrs


class EufyX10DebugCleanSpeedSensor(EufyX10DebugBaseSensor):
    """Clean speed sensor for debugging Key 158 - KEPT AS WORKING."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the clean speed sensor."""
        super().__init__(coordinator, "clean_speed")
        self._attr_name = f"Eufy X10 Debug Clean Speed"
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> Optional[str]:
        """Return the clean speed."""
        speed = self.coordinator.data.get("clean_speed")
        if speed is not None:
            _LOGGER.debug("⚡ Clean speed sensor value: %s", speed)
        return speed

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        raw_158 = self.coordinator.raw_data.get("158")
        from .const import CLEAN_SPEED_NAMES
        
        attrs = {
            "raw_key_158": raw_158,
            "available_speeds": CLEAN_SPEED_NAMES,
            "speed_mapping": {i: speed for i, speed in enumerate(CLEAN_SPEED_NAMES)},
            "data_source": "Key 158 (Working)",
            "reliability": "✅ Accurate",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
        }
        
        # Add speed emoji indicators
        speed = self.coordinator.data.get("clean_speed")
        if speed == "quiet":
            attrs["speed_emoji"] = "🐌"
        elif speed == "standard":
            attrs["speed_emoji"] = "🚶"
        elif speed == "turbo":
            attrs["speed_emoji"] = "🏃"
        elif speed == "max":
            attrs["speed_emoji"] = "🏃‍♂️💨"
        
        return attrs


class EufyX10DebugRawDataSensor(EufyX10DebugBaseSensor):
    """Raw data sensor for complete debugging - KEPT AS USEFUL."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the raw data sensor."""
        super().__init__(coordinator, "raw_data")
        self._attr_name = f"Eufy X10 Debug Raw Data"
        self._attr_icon = "mdi:code-json"

    @property
    def native_value(self) -> str:
        """Return the number of raw data keys."""
        count = len(self.coordinator.raw_data)
        _LOGGER.debug("📋 Raw data sensor: %d keys available", count)
        return str(count)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return all raw data as attributes."""
        attrs = {
            "total_keys": len(self.coordinator.raw_data),
            "raw_data_keys": list(self.coordinator.raw_data.keys()),
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
            "data_emoji": "📊",
            "purpose": "Complete API data for analysis",
        }
        
        # Add first 15 characters of each raw value for debugging (prevent overflow)
        for key, value in list(self.coordinator.raw_data.items())[:20]:  # Limit to prevent overflow
            if isinstance(value, str) and len(value) > 20:
                attrs[f"raw_{key}_preview"] = f"{value[:15]}..."
            else:
                attrs[f"raw_{key}"] = value
        
        return attrs


class EufyX10DebugMonitoringSensor(EufyX10DebugBaseSensor):
    """Monitoring sensor showing which keys are found/missing - KEPT AS USEFUL."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the monitoring sensor."""
        super().__init__(coordinator, "monitoring")
        self._attr_name = f"Eufy X10 Debug Monitoring"
        self._attr_icon = "mdi:monitor-eye"

    @property
    def native_value(self) -> str:
        """Return monitoring summary."""
        found = len(self.coordinator.data.get("monitored_keys_found", []))
        total = len(MONITORED_KEYS)
        coverage = f"{found}/{total}"
        _LOGGER.debug("👀 Monitoring sensor: %s keys coverage", coverage)
        return coverage

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return monitoring details."""
        found_keys = self.coordinator.data.get("monitored_keys_found", [])
        missing_keys = self.coordinator.data.get("monitored_keys_missing", [])
        coverage_pct = round((len(found_keys) / len(MONITORED_KEYS)) * 100, 1) if MONITORED_KEYS else 0
        
        attrs = {
            "monitored_keys_total": len(MONITORED_KEYS),
            "monitored_keys_found_count": len(found_keys),
            "monitored_keys_missing_count": len(missing_keys),
            "monitored_keys_found": found_keys,
            "monitored_keys_missing": missing_keys,
            "coverage_percentage": coverage_pct,
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
            "purpose": "Track hardcoded key discovery",
        }
        
        # Add coverage emoji
        if coverage_pct >= 90:
            attrs["coverage_emoji"] = "🟢"
        elif coverage_pct >= 70:
            attrs["coverage_emoji"] = "🟡"
        else:
            attrs["coverage_emoji"] = "🔴"
        
        # Add status for each monitored key with emoji indicators
        for key in MONITORED_KEYS:
            status = "✅ PRESENT" if key in found_keys else "❌ MISSING"
            attrs[f"key_{key}_status"] = status
        
        return attrs


class EufyX10DebugAccessoryManagerSensor(EufyX10DebugBaseSensor):
    """NEW: Accessory configuration manager sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the accessory manager sensor."""
        super().__init__(coordinator, "accessory_manager")
        self._attr_name = f"Eufy X10 Accessory Config Manager"
        self._attr_icon = "mdi:cog-outline"

    @property
    def native_value(self) -> str:
        """Return number of configured accessories."""
        accessory_count = len(self.coordinator.data.get("accessory_sensors", {}))
        return str(accessory_count)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return accessory manager status."""
        accessory_sensors = self.coordinator.data.get("accessory_sensors", {})
        
        # Calculate status
        enabled_count = len([a for a in accessory_sensors.values() if a.get("enabled")])
        low_life_count = len([a for a in accessory_sensors.values() 
                             if a.get("configured_life", 100) <= a.get("threshold", 10)])
        
        attrs = {
            "total_accessories": len(accessory_sensors),
            "enabled_accessories": enabled_count,
            "low_life_accessories": low_life_count,
            "config_file": "sensors.json",
            "config_location": "/config/custom_components/Eufy-Robovac-Data-Logger/accessories/",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
            "purpose": "🔧 Manage accessory sensors from JSON config",
        }
        
        # Add individual accessory status
        for sensor_id, sensor_data in accessory_sensors.items():
            attrs[f"{sensor_id}_life"] = f"{sensor_data.get('configured_life', 0)}%"
            attrs[f"{sensor_id}_detected"] = sensor_data.get('detected_value', 'N/A')
            attrs[f"{sensor_id}_enabled"] = sensor_data.get('enabled', False)
        
        # Status emoji
        if low_life_count > 0:
            attrs["status_emoji"] = "🔴"
            attrs["status"] = f"{low_life_count} accessories need replacement"
        elif enabled_count > 0:
            attrs["status_emoji"] = "🟢"
            attrs["status"] = "All accessories OK"
        else:
            attrs["status_emoji"] = "⚪"
            attrs["status"] = "No accessories configured"
        
        return attrs


class EufyX10DynamicAccessorySensor(EufyX10DebugBaseSensor):
    """NEW: Dynamic accessory sensor created from JSON configuration."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, sensor_id: str, sensor_config: Dict[str, Any]) -> None:
        """Initialize dynamic accessory sensor."""
        super().__init__(coordinator, f"accessory_{sensor_id}")
        
        self.accessory_id = sensor_id
        self.sensor_config = sensor_config
        
        self._attr_name = f"Eufy X10 {sensor_config.get('name', sensor_id)}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = self._get_accessory_icon(sensor_id)

    def _get_accessory_icon(self, sensor_id: str) -> str:
        """Get appropriate icon for accessory type."""
        icon_map = {
            "rolling_brush": "mdi:broom",
            "side_brush": "mdi:brush",
            "filter": "mdi:air-filter",
            "mopping_cloth": "mdi:water",
            "cleaning_tray": "mdi:tray",
            "robovac_sensors": "mdi:radar",
            "brush_guard": "mdi:shield-outline",
            "water_tank_level": "mdi:water-percent",
        }
        return icon_map.get(sensor_id, "mdi:cog")

    @property
    def native_value(self) -> Optional[int]:
        """Return the accessory life percentage."""
        accessory_data = self.coordinator.data.get("accessory_sensors", {}).get(self.accessory_id, {})
        
        # Use detected value if available, otherwise configured value
        detected = accessory_data.get("detected_value")
        configured = accessory_data.get("configured_life", 100)
        
        value = detected if detected is not None else configured
        
        if value is not None:
            _LOGGER.debug("🔧 %s sensor value: %d%%", self.sensor_config.get('name'), value)
        
        return value

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return accessory-specific attributes."""
        accessory_data = self.coordinator.data.get("accessory_sensors", {}).get(self.accessory_id, {})
        
        attrs = {
            "accessory_name": self.sensor_config.get('name'),
            "description": self.sensor_config.get('description', ''),
            "configured_life": accessory_data.get("configured_life", 100),
            "detected_value": accessory_data.get("detected_value"),
            "hours_remaining": accessory_data.get("hours_remaining", 0),
            "max_hours": accessory_data.get("max_hours", 0),
            "replacement_threshold": accessory_data.get("threshold", 10),
            "data_source": f"Key {accessory_data.get('key')}, Byte {accessory_data.get('byte_position')}",
            "enabled": accessory_data.get("enabled", True),
            "notes": accessory_data.get("notes", ""),
            "last_updated": accessory_data.get("last_updated"),
        }
        
        # Status indicators
        current_life = accessory_data.get("configured_life", 100)
        threshold = accessory_data.get("threshold", 10)
        
        if current_life <= threshold:
            attrs["status"] = "🔴 Replace Soon"
            attrs["urgency"] = "High"
        elif current_life <= threshold * 2:
            attrs["status"] = "🟡 Monitor"
            attrs["urgency"] = "Medium"
        else:
            attrs["status"] = "🟢 Good"
            attrs["urgency"] = "Low"
        
        # Detection accuracy
        detected = accessory_data.get("detected_value")
        configured = accessory_data.get("configured_life", 100)
        
        if detected is not None:
            difference = abs(detected - configured)
            if difference <= 2:
                attrs["detection_accuracy"] = "🟢 Excellent"
            elif difference <= 5:
                attrs["detection_accuracy"] = "🟡 Good"
            else:
                attrs["detection_accuracy"] = "🔴 Needs calibration"
            
            attrs["detection_difference"] = f"{difference}%"
        else:
            attrs["detection_accuracy"] = "⚪ Not detected"
            attrs["detection_difference"] = "N/A"
        
        return attrs