"""API polling client for Eufy Robovac Data Logger integration."""
import logging
import time
from typing import Any, Dict

from .base import Base

_LOGGER = logging.getLogger(__name__)


class RestConnect(Base):
    """API polling client that uses EufyLogin's getMqttDevice method."""

    def __init__(self, config: Dict, openudid: str, eufyCleanApi):
        """Initialize API polling client."""
        super().__init__()
        
        self.device_id = config.get('deviceId')
        self.device_model = config.get('deviceModel', 'T8213')
        self.debug_mode = config.get('debug', False)
        self.openudid = openudid
        self.eufyCleanApi = eufyCleanApi
        
        # Data storage (like MqttConnect but without MQTT)
        self.is_connected = False
        self.raw_data = {}
        self.last_update = None
        self.update_count = 0

    async def connect(self):
        """Initialize connection - just verify we have login."""
        try:
            # Unlike MqttConnect, we don't need MQTT credentials or certificates
            # We just need to ensure eufyCleanApi is logged in
            if self.eufyCleanApi:
                self.is_connected = True
                _LOGGER.info("API polling initialized for device %s", self.device_id)
            else:
                raise Exception("No eufyCleanApi provided")
        except Exception as e:
            self.is_connected = False
            _LOGGER.error("Failed to initialize: %s", e)
            raise

    async def updateDevice(self, force_update: bool = False):
        """Update device data using API polling (similar to MqttConnect but without MQTT)."""
        try:
            # This is the same call that MqttConnect makes in its updateDevice
            device_data = await self.eufyCleanApi.getMqttDevice(self.device_id)
            
            if device_data:
                # Handle the response format (can be list or dict)
                if isinstance(device_data, list) and len(device_data) > 0:
                    device = device_data[0]
                else:
                    device = device_data
                
                # Extract DPS data (same as MqttConnect does)
                if isinstance(device, dict) and 'dps' in device:
                    self.raw_data = device['dps']
                    self.last_update = time.time()
                    self.update_count += 1
                    
                    # If base class has _map_data (like SharedConnect), call it
                    if hasattr(self, '_map_data'):
                        await self._map_data(device['dps'])
                    
                    if self.debug_mode:
                        _LOGGER.debug("Update #%d: %d keys received", 
                                     self.update_count, len(self.raw_data))
                else:
                    if self.debug_mode:
                        _LOGGER.debug("No DPS data in response")
                        
        except Exception as e:
            _LOGGER.error("Failed to update device: %s", e)

    def get_raw_data(self) -> Dict[str, Any]:
        """Get the raw DPS data."""
        return self.raw_data.copy()

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            'is_connected': self.is_connected,
            'connection_mode': 'API Polling (No MQTT)',
            'last_update': self.last_update,
            'update_count': self.update_count,
            'keys_received': len(self.raw_data),
            'device_id': self.device_id,
            'device_model': self.device_model,
            'data_source': 'EufyLogin.getMqttDevice()'
        }

    async def stop_polling(self):
        """Stop polling - no cleanup needed unlike MQTT."""
        self.is_connected = False
        _LOGGER.info("API polling stopped for device %s", self.device_id)

    async def send_command(self, data_payload: Dict[str, Any]):
        """Send command - NOT IMPLEMENTED for API polling."""
        _LOGGER.warning("send_command not supported in API polling mode")
        # MqttConnect uses MQTT publish, but we can't do that without MQTT
        # This would need a different API endpoint to send commands
