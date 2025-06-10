"""Sensor platform for Eufy Robovac Data Logger integration."""
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
    """Set up Eufy X10 Debug sensors."""
    coordinator: EufyX10DebugCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        EufyX10DebugBatterySensor(coordinator),
        EufyX10DebugWaterTankSensor(coordinator),
        EufyX10DebugCleanSpeedSensor(coordinator),
        EufyX10DebugWorkStatusSensor(coordinator),
        EufyX10DebugRawDataSensor(coordinator),
        EufyX10DebugMonitoringSensor(coordinator),
    ]
    
    _LOGGER.info("🏭 Setting up %d debug sensors for device %s", len(entities), coordinator.device_id)
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
            sw_version="Debug v1.0.0",
        )
        
        _LOGGER.debug("🔧 Initialized %s sensor for device %s", sensor_type, self.device_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success


class EufyX10DebugBatterySensor(EufyX10DebugBaseSensor):
    """Battery sensor for debugging Key 163."""

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
            "data_source": "Key 163",
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


class EufyX10DebugWaterTankSensor(EufyX10DebugBaseSensor):
    """Water tank sensor for debugging Key 167."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the water tank sensor."""
        super().__init__(coordinator, "water_tank")
        self._attr_name = f"Eufy X10 Debug Water Tank"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:water-percent"

    @property
    def native_value(self) -> Optional[int]:
        """Return the water tank level."""
        water = self.coordinator.data.get("water_tank")
        if water is not None:
            _LOGGER.debug("💧 Water tank sensor value: %d%%", water)
        return water

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        raw_167 = self.coordinator.raw_data.get("167")
        raw_177 = self.coordinator.raw_data.get("177")
        
        # Decode byte 4 if available
        byte_4_info = "N/A"
        byte_4_hex = "N/A"
        if raw_167 and isinstance(raw_167, str):
            try:
                import base64
                binary_data = base64.b64decode(raw_167)
                if len(binary_data) > 4:
                    byte_4_info = f"{binary_data[4]}"
                    byte_4_hex = f"0x{binary_data[4]:02x}"
            except Exception as e:
                _LOGGER.debug("⚠️ Failed to decode water tank data: %s", e)
        
        attrs = {
            "raw_key_167": raw_167,
            "raw_key_177": raw_177,
            "byte_4_decimal": byte_4_info,
            "byte_4_hex": byte_4_hex,
            "data_source": "Key 167 Byte 4",
            "calculation_method": "Scale 255->100",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
        }
        
        # Add tank status with emoji indicators
        water = self.coordinator.data.get("water_tank")
        if water is not None:
            if water <= 10:
                attrs["tank_status"] = "🔴 Empty"
                attrs["tank_emoji"] = "🪣"
            elif water <= 30:
                attrs["tank_status"] = "🟠 Low"
                attrs["tank_emoji"] = "💧"
            elif water <= 70:
                attrs["tank_status"] = "🟡 Medium"
                attrs["tank_emoji"] = "💧"
            else:
                attrs["tank_status"] = "🟢 Full"
                attrs["tank_emoji"] = "💧"
        
        return attrs


class EufyX10DebugCleanSpeedSensor(EufyX10DebugBaseSensor):
    """Clean speed sensor for debugging Key 158."""

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
            "data_source": "Key 158",
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


class EufyX10DebugWorkStatusSensor(EufyX10DebugBaseSensor):
    """Work status sensor for debugging Key 153."""

    def __init__(self, coordinator: EufyX10DebugCoordinator) -> None:
        """Initialize the work status sensor."""
        super().__init__(coordinator, "work_status")
        self._attr_name = f"Eufy X10 Debug Work Status"
        self._attr_icon = "mdi:robot-vacuum"

    @property
    def native_value(self) -> Optional[str]:
        """Return the work status."""
        status = self.coordinator.data.get("work_status")
        if status is not None:
            _LOGGER.debug("🤖 Work status sensor value: %s", status)
        return status

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        raw_153 = self.coordinator.raw_data.get("153")
        play_pause = self.coordinator.data.get("play_pause")
        from .const import WORK_STATUS_MAP
        
        attrs = {
            "raw_key_153": raw_153,
            "raw_key_152_play_pause": self.coordinator.raw_data.get("152"),
            "play_pause_state": "Playing" if play_pause else "Paused" if play_pause is not None else "Unknown",
            "status_mapping": WORK_STATUS_MAP,
            "data_source": "Key 153 (Work Status), Key 152 (Play/Pause)",
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
        }
        
        # Add status emoji indicators
        status = self.coordinator.data.get("work_status")
        if status == "standby":
            attrs["status_emoji"] = "⏸️"
        elif status == "cleaning":
            attrs["status_emoji"] = "🧹"
        elif status == "charging":
            attrs["status_emoji"] = "🔌"
        elif status == "go_home":
            attrs["status_emoji"] = "🏠"
        elif status == "fault":
            attrs["status_emoji"] = "⚠️"
        else:
            attrs["status_emoji"] = "🤖"
        
        return attrs


class EufyX10DebugRawDataSensor(EufyX10DebugBaseSensor):
    """Raw data sensor for complete debugging."""

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
        }
        
        # Add first 15 characters of each raw value for debugging (prevent overflow)
        for key, value in list(self.coordinator.raw_data.items())[:20]:  # Limit to prevent overflow
            if isinstance(value, str) and len(value) > 20:
                attrs[f"raw_{key}_preview"] = f"{value[:15]}..."
            else:
                attrs[f"raw_{key}"] = value
        
        return attrs


class EufyX10DebugMonitoringSensor(EufyX10DebugBaseSensor):
    """Monitoring sensor showing which keys are found/missing."""

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
        coverage_pct = round((len(found_keys) / len(MONITORED_KEYS)) * 100, 1)
        
        attrs = {
            "monitored_keys_total": len(MONITORED_KEYS),
            "monitored_keys_found_count": len(found_keys),
            "monitored_keys_missing_count": len(missing_keys),
            "monitored_keys_found": found_keys,
            "monitored_keys_missing": missing_keys,
            "coverage_percentage": coverage_pct,
            "last_update": self.coordinator.data.get("last_update"),
            "update_count": self.coordinator.data.get("update_count"),
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
            
            # Add description for important keys
            key_descriptions = {
                "163": "🔋 Battery Level",
                "167": "💧 Water Tank Level (Byte 4)",
                "177": "🌊 Alternative Water Tank Source",
                "178": "⚡ Real-time Data",
                "168": "🔧 Accessories Status",
                "153": "🤖 Work Status/Mode",
                "152": "⏯️ Play/Pause Commands",
                "158": "⚡ Clean Speed Settings",
            }
            if key in key_descriptions:
                attrs[f"key_{key}_description"] = key_descriptions[key]
        
        return attrs