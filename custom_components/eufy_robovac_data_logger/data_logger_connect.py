"""Data Logger extension of SharedConnect to capture raw DPS data."""
import logging
from typing import Any, Dict

from .controllers.SharedConnect import SharedConnect

_LOGGER = logging.getLogger(__name__)


class DataLoggerConnect(SharedConnect):
    """Extension of SharedConnect that captures raw DPS data for logging."""
    
    def __init__(self, config: Dict, openudid: str, eufyCleanApi):
        """Initialize with raw data storage."""
        super().__init__(config, openudid, eufyCleanApi)
        
        # Store raw DPS data separately for logging
        self.raw_dps_data: Dict[str, Any] = {}
        self._dps_update_count = 0
    
    async def _map_data(self, data: dict):
        """Override to capture raw DPS data before mapping."""
        # Store the raw DPS data first
        if data:
            self.raw_dps_data.update(data)
            self._dps_update_count += 1
            
            # Log what DPS keys we received
            keys_150_180 = [k for k in data.keys() if k.isdigit() and 150 <= int(k) <= 180]
            if keys_150_180:
                _LOGGER.info(f"DPS Update #{self._dps_update_count}: Received keys {keys_150_180}")
                _LOGGER.debug(f"Full DPS data (150-180): {{k: data[k] for k in keys_150_180}}")
        
        # Call parent to do the normal mapping
        await super()._map_data(data)
    
    def get_raw_dps_data(self) -> Dict[str, Any]:
        """Get the raw DPS data for logging."""
        return self.raw_dps_data.copy()
    
    def get_dps_keys_150_180(self) -> Dict[str, Any]:
        """Get only DPS keys 150-180."""
        filtered = {}
        for key in range(150, 181):
            str_key = str(key)
            if str_key in self.raw_dps_data:
                filtered[str_key] = self.raw_dps_data[str_key]
        return filtered