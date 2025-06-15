"""Sensor platform for Eufy Robovac Data Logger integration - Debug Version."""
import logging
from typing import Any, Dict, Optional

# CRITICAL DEBUG: Add logging immediately at module level
_LOGGER = logging.getLogger(__name__)
_LOGGER.error("🚨 DEBUG: sensor.py module loading started")

try:
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
    _LOGGER.error("✅ DEBUG: HomeAssistant sensor imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: HomeAssistant sensor import failed: {e}")
    raise

try:
    from .const import DOMAIN, MONITORED_KEYS
    _LOGGER.error("✅ DEBUG: const.py sensor imports successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: const.py sensor import failed: {e}")
    raise

try:
    from .coordinator import EufyX10DebugCoordinator
    _LOGGER.error("✅ DEBUG: coordinator.py sensor import successful")
except ImportError as e:
    _LOGGER.error(f"❌ DEBUG: coordinator.py sensor import failed: {e}")
    raise

_LOGGER.error("🎯 DEBUG: sensor.py all imports completed successfully")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eufy Robovac Debug sensors with Investigation Mode."""
    _LOGGER.error("🚨 DEBUG: async_setup_entry called in sensor.py")
    
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        _LOGGER.error("✅ DEBUG: Coordinator retrieved successfully")
    except KeyError as e:
        _LOGGER.error(f"❌ DEBUG: Failed to retrieve coordinator: {e}")
        return
    
    try:
        sensors = []
        
        # Create basic sensors
        sensors.extend([
            EufyRobovacBatterySensor(coordinator, entry),
            EufyRobovacCleanSpeedSensor(coordinator, entry),
            EufyRobovacRawDataSensor(coordinator, entry),
            EufyRobovacMonitoringSensor(coordinator, entry),
        ])
        
        _LOGGER.error(f"✅ DEBUG: Created {len(sensors)} basic sensors")
        
        # Add investigation sensor if enabled
        if coordinator.investigation_mode:
            sensors.append(EufyRobovacInvestigationSensor(coordinator, entry))
            _LOGGER.error("✅ DEBUG: Added investigation sensor")
        
        async_add_entities(sensors, update_before_add=True)
        _LOGGER.error(f"✅ DEBUG: Added {len(sensors)} sensors total")
        
    except Exception as e:
        _LOGGER.error(f"❌ DEBUG: Failed to setup sensors: {e}")
        raise


class EufyRobovacSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Eufy Robovac sensors."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name=coordinator.device_name,
            manufacturer="Eufy",
            model=coordinator.device_model,
            sw_version="Debug v3.0",
        )


class EufyRobovacBatterySensor(EufyRobovacSensorBase):
    """Battery level sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, entry: ConfigEntry) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.device_id}_battery"
        self._attr_name = f"{coordinator.device_name} Battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[int]:
        """Return the battery level."""
        return self.coordinator.parsed_data.get("battery")


class EufyRobovacCleanSpeedSensor(EufyRobovacSensorBase):
    """Clean speed sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, entry: ConfigEntry) -> None:
        """Initialize the clean speed sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.device_id}_clean_speed"
        self._attr_name = f"{coordinator.device_name} Clean Speed"

    @property
    def native_value(self) -> Optional[str]:
        """Return the clean speed."""
        speed_value = self.coordinator.parsed_data.get("clean_speed")
        return f"Speed {speed_value}" if speed_value is not None else None


class EufyRobovacRawDataSensor(EufyRobovacSensorBase):
    """Raw data sensor for debugging."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, entry: ConfigEntry) -> None:
        """Initialize the raw data sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.device_id}_raw_data"
        self._attr_name = f"{coordinator.device_name} Raw Data"

    @property
    def native_value(self) -> str:
        """Return raw data status."""
        return f"Debug Data Available ({len(self.coordinator.raw_data)} keys)"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return raw data attributes."""
        return {
            "raw_data_keys": list(self.coordinator.raw_data.keys()),
            "parsed_data": self.coordinator.parsed_data,
            "update_count": self.coordinator.update_count,
            "last_update": self.coordinator.last_update,
        }


class EufyRobovacMonitoringSensor(EufyRobovacSensorBase):
    """Monitoring status sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, entry: ConfigEntry) -> None:
        """Initialize the monitoring sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.device_id}_monitoring"
        self._attr_name = f"{coordinator.device_name} Monitoring"

    @property
    def native_value(self) -> str:
        """Return monitoring status."""
        return "Active" if self.coordinator.last_update else "Inactive"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return monitoring attributes."""
        return {
            "debug_mode": self.coordinator.debug_mode,
            "investigation_mode": self.coordinator.investigation_mode,
            "monitored_keys": len(MONITORED_KEYS),
            "consecutive_failures": self.coordinator._consecutive_failures,
        }


class EufyRobovacInvestigationSensor(EufyRobovacSensorBase):
    """Investigation mode sensor."""

    def __init__(self, coordinator: EufyX10DebugCoordinator, entry: ConfigEntry) -> None:
        """Initialize the investigation sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.device_id}_investigation_status"
        self._attr_name = f"{coordinator.device_name} Investigation Status"

    @property
    def native_value(self) -> str:
        """Return investigation status."""
        if not self.coordinator.investigation_mode:
            return "Disabled"
        
        if self.coordinator.smart_investigation_logger:
            return "Enhanced Smart v4.0 Active"
        else:
            return "Investigation Mode Error"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return investigation attributes."""
        attrs = {
            "investigation_enabled": self.coordinator.investigation_mode,
            "monitored_keys_count": len(MONITORED_KEYS),
        }
        
        if self.coordinator.smart_investigation_logger:
            try:
                smart_status = self.coordinator.smart_investigation_logger.get_smart_status()
                attrs.update({
                    "session_id": self.coordinator.smart_investigation_logger.session_id,
                    "investigation_directory": str(self.coordinator.smart_investigation_logger.investigation_dir),
                    "smart_status": smart_status,
                })
            except Exception as e:
                attrs["smart_status_error"] = str(e)
        
        return attrs