"""Sensor platform for Eufy Robovac Data Logger integration - DPS Only Edition."""
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
    """Set up Eufy Robovac Debug sensors with DPS-only data fetching."""
    coordinator: EufyX10DebugCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Core sensors (working and reliable) - DPS Only
    entities = [
        EufyRobovacDebugBatterySensor(coordinator),           # ✅ Key 163 - Working
        EufyRobovacDebugCleanSpeedSensor(coordinator),        # ✅ Key 158 - Working
        EufyRobovacDebugRawDataSensor(coordinator),           # ✅ Debug tool - Useful
        EufyRobovacDebugMonitoringSensor(coordinator),        # ✅ Monitoring - Useful
        EufyRobovacDebugAccessoryManagerSensor(coordinator),  # 🆕 Accessory config manager
    ]
    
    # Add Investigation Status Sensor if investigation mode enabled
    if coordinator.investigation_mode:
        entities.append(EufyRobovacInvestigationStatusSensor(coordinator))
        _LOGGER.info("🔍 Investigation Status Sensor added - Investigation Mode active")
    
    # Add dynamic accessory sensors from JSON configuration
    try:
        accessory_sensors = await coordinator.accessory_manager.get_enabled_sensors()
        
        for sensor_id, sensor_config in accessory_sensors.items():
            if sensor_config.get('enabled', False):
                entities.append(EufyRobovacDynamicAccessorySensor(coordinator, sensor_id, sensor_config))
                _LOGGER.debug("🔧 Added dynamic accessory sensor: %s", sensor_config.get('name'))
        
        investigation_status = " + Investigation Mode" if coordinator.investigation_mode else ""
        _LOGGER.info("🏭 Setting up %d total sensors (%d core + %d accessories)%s with DPS-only for device %s", 
                    len(entities), 5 + (1 if coordinator.investigation_mode else 0), len(accessory_sensors), investigation_status, coordinator.device_id)
    
    except Exception as e:
        _LOGGER.error("❌ Failed to load accessory sensors: %s", e)
        _LOGGER.info("🏭 Setting up %d core sensors only with DPS-only for device %s", len(entities), coordinator.device_id)
    
    async_add_entities(entities)


class EufyRobovacDebugBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Eufy Robovac Data Logger - DPS Only."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, sensor_type: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self.device_id = coordinator.device_id
        
        self._attr_unique_id = f"{self.device_id}_{sensor_type}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            name=f"Eufy Robovac Debug {self.device_id}",
            manufacturer="Eufy",
            model="Robovac (DPS Only + Investigation)",
            sw_version="Debug v3.0.0 - DPS Only + Accessory Config + Investigation Mode",
        )
        
        _LOGGER.debug("🔧 Initialized %s sensor for device %s with DPS-only", sensor_type, self.device_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class EufyRobovacInvestigationStatusSensor(EufyRobovacDebugBaseSensor):
    """Investigation Mode Status and Control Sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the investigation status sensor."""
        super().__init__(coordinator, "investigation_status")
        self._attr_name = f"Eufy Robovac Investigation Status"
        self._attr_icon = "mdi:magnify"

    @property
    def native_value(self) -> str:
        """Return investigation status."""
        if not self.coordinator.investigation_mode:
            return "Disabled"
        
        status = self.coordinator.get_investigation_status()
        
        if status.get("baseline_captured", False):
            return "Baseline Captured"
        elif status.get("available_keys"):
            return "Monitoring"
        else:
            return "Waiting for Data"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return investigation status and controls."""
        if not self.coordinator.investigation_mode:
            return {"status": "Investigation mode not enabled"}
        
        status = self.coordinator.get_investigation_status()
        
        attrs = {
            "version": status.get("version", "4.0_multi_key"),
            "session_id": status.get("session_id"),
            "baseline_captured": status.get("baseline_captured", False),
            "current_mode": status.get("current_mode", "monitoring"),
            "total_updates": status.get("total_updates", 0),
            "meaningful_logs": status.get("meaningful_logs", 0),
            "efficiency_percentage": status.get("efficiency_percentage", 0),
            "monitored_keys_count": status.get("monitored_keys_count", 0),
            "available_keys": status.get("available_keys", []),
            "missing_keys": status.get("missing_keys", []),
            "data_source": "🔍 DPS Only - Enhanced Key 180 + Multi-Key Analysis",
        }
        
        # Add Key 180 specific information
        if "180" in attrs["available_keys"]:
            attrs["key180_status"] = "✅ Available for analysis"
            attrs["position_15_status"] = "97% = Brush Guard (CONFIRMED)"
        else:
            attrs["key180_status"] = "❌ Not available"
            attrs["position_15_status"] = "Waiting for Key 180 data"
        
        # Workflow guidance
        attrs["workflow_steps"] = [
            "1. Capture baseline before cleaning",
            "2. Run a room cleaning cycle", 
            "3. Capture post-cleaning data after docking",
            "4. Check investigation files for byte changes",
            "5. Generate session summary for analysis"
        ]
        
        # Manual capture service info
        attrs["available_services"] = [
            "eufy_robovac_data_logger.capture_investigation_baseline",
            "eufy_robovac_data_logger.capture_investigation_post_cleaning",
            "eufy_robovac_data_logger.generate_investigation_summary"
        ]
        
        # File info
        investigation_dir = status.get("investigation_directory")
        if investigation_dir:
            attrs["files_location"] = investigation_dir
            attrs["file_pattern"] = "key180_*.json"
            attrs["session_files"] = f"Files with session ID: {status.get('session_id')}"
        
        return attrs


class EufyRobovacDebugBatterySensor(EufyRobovacDebugBaseSensor):
    """Battery sensor for debugging Key 163 - WORKING."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, "battery")
        self._attr_name = f"Eufy Robovac Debug Battery"
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
        data_source = self.coordinator.data.get("data_source", "Unknown")
        raw_data_count = self.coordinator.data.get("raw_data_count", 0)
        
        attrs = {
            "data_source": data_source,
            "connection_mode": "📱 DPS Only (Basic Login)",
            "key_used": "163",
            "confirmed_working": True,
            "accuracy": "100% confirmed from Android app",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
            "raw_keys_available": raw_data_count,
        }
        
        # Add investigation mode connection
        if self.coordinator.investigation_mode:
            attrs["investigation_note"] = "🔍 Key 163 is confirmed working and monitored in investigation mode"
        
        # Add DPS-only benefit indicator
        attrs["dps_benefits"] = "🎯 Direct access to robovac data without REST API interference"
        attrs["performance"] = "⚡ Fast, reliable DPS data extraction"
        
        return attrs


class EufyRobovacDebugCleanSpeedSensor(EufyRobovacDebugBaseSensor):
    """Clean speed sensor for debugging Key 158 - WORKING."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the clean speed sensor."""
        super().__init__(coordinator, "clean_speed")
        self._attr_name = f"Eufy Robovac Debug Clean Speed"
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> Optional[str]:
        """Return the cleaning speed."""
        speed = self.coordinator.data.get("clean_speed")
        if speed:
            _LOGGER.debug("🌪️ Clean speed sensor value: %s", speed)
        return speed

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        data_source = self.coordinator.data.get("data_source", "Unknown")
        raw_data_count = self.coordinator.data.get("raw_data_count", 0)
        
        attrs = {
            "data_source": data_source,
            "connection_mode": "📱 DPS Only (Basic Login)",
            "key_used": "158",
            "confirmed_working": True,
            "possible_values": "Standard, Medium, High",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
            "raw_keys_available": raw_data_count,
        }
        
        # Add investigation mode connection
        if self.coordinator.investigation_mode:
            attrs["investigation_note"] = "🔍 Key 158 is confirmed working and monitored in investigation mode"
        
        # Add DPS-only benefit indicator
        attrs["dps_benefits"] = "🎯 Direct access to robovac data without REST API interference"
        attrs["performance"] = "⚡ Fast, reliable DPS data extraction"
        
        return attrs


class EufyRobovacDebugRawDataSensor(EufyRobovacDebugBaseSensor):
    """Raw data sensor for debugging - shows key count."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the raw data sensor."""
        super().__init__(coordinator, "raw_data")
        self._attr_name = f"Eufy Robovac Debug Raw Data"
        self._attr_icon = "mdi:database"

    @property
    def native_value(self) -> int:
        """Return the number of raw data keys."""
        raw_count = self.coordinator.data.get("raw_data_count", 0)
        _LOGGER.debug("📊 Raw data sensor value: %d keys", raw_count)
        return raw_count

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return raw data details."""
        data_source = self.coordinator.data.get("data_source", "Unknown")
        raw_data_count = self.coordinator.data.get("raw_data_count", 0)
        
        # Get monitored keys status
        found_keys = self.coordinator.data.get("monitored_keys_found", [])
        monitored_total = len(MONITORED_KEYS)
        
        attrs = {
            "data_source": data_source,
            "connection_mode": "📱 DPS Only (Basic Login)",
            "total_raw_keys": raw_data_count,
            "monitored_keys_found": len(found_keys),
            "monitored_keys_total": monitored_total,
            "monitoring_coverage": f"{len(found_keys)}/{monitored_total}",
            "found_keys": found_keys,
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
        }
        
        # Add Key 180 specific status
        if "180" in found_keys:
            attrs["key180_status"] = "✅ Available - Ready for accessory analysis"
        else:
            attrs["key180_status"] = "❌ Not available"
        
        # Add investigation mode details
        if self.coordinator.investigation_mode:
            attrs["investigation_mode"] = "🔍 Enhanced Smart Multi-Key Investigation v4.0"
            attrs["investigation_note"] = f"Monitoring {monitored_total} keys for comprehensive analysis"
        
        # Performance indicators
        if raw_data_count > 0:
            attrs["status"] = "🟢 Receiving data"
            attrs["performance"] = "⚡ DPS connection working"
        else:
            attrs["status"] = "🔴 No data"
            attrs["performance"] = "❌ Check DPS connection"
        
        # Add DPS-only benefits
        attrs["dps_benefits"] = "🎯 Direct robovac access - no REST API blocking"
        
        return attrs


class EufyRobovacDebugMonitoringSensor(EufyRobovacDebugBaseSensor):
    """Monitoring sensor for tracking key coverage."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the monitoring sensor."""
        super().__init__(coordinator, "monitoring")
        self._attr_name = f"Eufy Robovac Debug Monitoring"
        self._attr_icon = "mdi:monitor-dashboard"

    @property
    def native_value(self) -> str:
        """Return monitoring status."""
        found_keys = self.coordinator.data.get("monitored_keys_found", [])
        total_keys = len(MONITORED_KEYS)
        return f"{len(found_keys)}/{total_keys}"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return monitoring details."""
        data_source = self.coordinator.data.get("data_source", "Unknown")
        found_keys = self.coordinator.data.get("monitored_keys_found", [])
        total_keys = len(MONITORED_KEYS)
        
        # Calculate coverage percentage
        coverage = (len(found_keys) / total_keys * 100) if total_keys > 0 else 0
        
        attrs = {
            "data_source": data_source,
            "connection_mode": "📱 DPS Only (Basic Login)",
            "monitored_keys_found": len(found_keys),
            "monitored_keys_total": total_keys,
            "coverage_percentage": round(coverage, 1),
            "found_keys": found_keys,
            "missing_keys": [key for key in MONITORED_KEYS if key not in found_keys],
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
        }
        
        # Priority key status
        priority_keys = {"163": "Battery", "158": "Clean Speed", "180": "Accessories"}
        for key, name in priority_keys.items():
            attrs[f"key_{key}_status"] = "✅ Found" if key in found_keys else "❌ Missing"
            attrs[f"key_{key}_name"] = name
        
        # Investigation mode status
        if self.coordinator.investigation_mode:
            attrs["investigation_mode"] = "🔍 Enhanced Smart Multi-Key Investigation v4.0"
            attrs["investigation_coverage"] = f"Monitoring {total_keys} keys for analysis"
        
        # Performance status
        if coverage >= 80:
            attrs["status"] = "🟢 Excellent coverage"
            attrs["performance"] = "🚀 Most keys available"
        elif coverage >= 50:
            attrs["status"] = "🟡 Good coverage"
            attrs["performance"] = "⚡ Key data flowing"
        else:
            attrs["status"] = "🔴 Poor coverage"
            attrs["performance"] = "❌ Check DPS connection"
        
        # Add DPS-only benefits
        attrs["dps_benefits"] = "🎯 Direct access to all robovac keys without REST blocking"
        
        return attrs


class EufyRobovacDebugAccessoryManagerSensor(EufyRobovacDebugBaseSensor):
    """Accessory configuration manager sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the accessory manager sensor."""
        super().__init__(coordinator, "accessory_manager")
        self._attr_name = f"Eufy Robovac Accessory Config Manager"
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
        data_source = self.coordinator.data.get("data_source", "Unknown")
        
        # Calculate status
        enabled_count = len([a for a in accessory_sensors.values() if a.get("enabled")])
        low_life_count = len([a for a in accessory_sensors.values() 
                             if a.get("configured_life", 100) <= a.get("threshold", 10)])
        
        attrs = {
            "data_source": data_source,
            "connection_mode": "📱 DPS Only (Basic Login)",
            "total_accessories": len(accessory_sensors),
            "enabled_accessories": enabled_count,
            "low_life_accessories": low_life_count,
            "config_file": "sensors.json",
            "config_location": "/config/custom_components/Eufy-Robovac-Data-Logger/accessories/",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
            "purpose": "🔧 Manage accessory sensors from JSON config",
        }
        
        # Add investigation mode connection
        if self.coordinator.investigation_mode:
            attrs["investigation_connection"] = "🔍 Key 180 analysis helps find correct byte positions for accessories"
        
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
        
        # Add DPS-only benefits
        attrs["dps_benefits"] = "🎯 Direct accessory data extraction from DPS keys"
        
        return attrs


class EufyRobovacDynamicAccessorySensor(EufyRobovacDebugBaseSensor):
    """Dynamic accessory sensor created from JSON configuration."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, accessory_id: str, sensor_config: Dict[str, Any]) -> None:
        """Initialize the dynamic accessory sensor."""
        super().__init__(coordinator, f"accessory_{accessory_id}")
        self.accessory_id = accessory_id
        self.sensor_config = sensor_config
        
        self._attr_name = f"Eufy Robovac {sensor_config.get('name', accessory_id)}"
        self._attr_device_class = SensorDeviceClass.BATTERY if 'battery' in sensor_config.get('name', '').lower() else None
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = sensor_config.get('icon', 'mdi:wrench')

    @property
    def native_value(self) -> Optional[int]:
        """Return the accessory life percentage."""
        accessory_data = self.coordinator.data.get("accessory_sensors", {}).get(self.accessory_id, {})
        configured_life = accessory_data.get("configured_life", 100)
        
        # Use detected value if available and accurate, otherwise configured
        detected_value = accessory_data.get("detected_value")
        if detected_value is not None:
            accuracy = accessory_data.get("detection_accuracy", 0)
            if accuracy and accuracy >= 80:  # Use detected if highly accurate
                return detected_value
        
        return configured_life

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return accessory details."""
        accessory_data = self.coordinator.data.get("accessory_sensors", {}).get(self.accessory_id, {})
        data_source = self.coordinator.data.get("data_source", "Unknown")
        
        attrs = {
            "accessory_name": self.sensor_config.get('name'),
            "description": self.sensor_config.get('description', ''),
            "data_source": data_source,
            "connection_mode": "📱 DPS Only (Basic Login)",
            "configured_life": accessory_data.get("configured_life", 100),
            "detected_value": accessory_data.get("detected_value"),
            "hours_remaining": accessory_data.get("hours_remaining", 0),
            "max_hours": accessory_data.get("max_hours", 0),
            "replacement_threshold": accessory_data.get("threshold", 10),
            "data_key": f"Key {accessory_data.get('key')}, Byte {accessory_data.get('byte_position')}",
            "enabled": accessory_data.get("enabled", True),
            "notes": accessory_data.get("notes", ""),
            "last_updated": accessory_data.get("last_updated"),
        }
        
        # Add investigation mode connection
        if self.coordinator.investigation_mode:
            attrs["investigation_help"] = "🔍 Use investigation mode files to verify this accessory's byte position"
        
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
        
        # Add DPS-only benefits
        attrs["dps_benefits"] = "🎯 Direct accessory data from DPS keys without REST interference"
        
        return attrs
