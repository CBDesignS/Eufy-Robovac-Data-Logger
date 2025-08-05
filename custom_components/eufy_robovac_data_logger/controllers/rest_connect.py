"""RestConnect controller for Eufy Robovac Data Logger integration."""
import asyncio
import logging
import time
import aiohttp
from typing import Any, Dict, Optional

from .base import Base

_LOGGER = logging.getLogger(__name__)


class RestConnect(Base):
    """RestConnect client with fallback to basic login when REST endpoints unavailable."""

    def __init__(self, config: Dict, openudid: str, eufyCleanApi):
        """Initialize RestConnect client."""
        super().__init__()
        
        self.device_id = config.get('deviceId')
        self.device_model = config.get('deviceModel', 'T8213')
        self.debug_mode = config.get('debug', False)
        self.openudid = openudid
        self.eufyCleanApi = eufyCleanApi
        
        # Connection state
        self.is_connected = False
        self.session = None
        self.raw_data = {}
        self.last_update = None
        self.update_count = 0
        
        # Debug logger reference (set by coordinator)
        self.debug_logger = None
        self._detailed_logging_enabled = False
        
        # REST API endpoints (may not be available)
        self.api_endpoints = {
            'device_data': 'https://api.eufylife.com/v1/device/info',
            'device_status': 'https://api.eufylife.com/v1/device/status',
            'accessory_data': 'https://api.eufylife.com/v1/device/accessory_info',
            'consumable_data': 'https://api.eufylife.com/v1/device/consumable_status',
            'runtime_data': 'https://api.eufylife.com/v1/device/runtime_info',
            'clean_device_info': 'https://aiot-clean-api-pr.eufylife.com/app/device/get_device_info',
            'clean_accessory': 'https://aiot-clean-api-pr.eufylife.com/app/device/get_accessory_data',
        }
        
        # Track which endpoints are working
        self.working_endpoints = set()
        self.failed_endpoints = set()

    async def connect(self):
        """Connect to REST API endpoints with fallback detection."""
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Test REST endpoint availability
            rest_available = await self._test_rest_endpoints()
            
            if rest_available:
                self.is_connected = True
                self._log_info("✅ RestConnect: Connected to REST API endpoints")
            else:
                self.is_connected = False
                self._log_warning("⚠️ RestConnect: REST endpoints not available, will use fallback")
                
        except Exception as e:
            self.is_connected = False
            self._log_error(f"❌ RestConnect connection failed: {e}")

    async def _test_rest_endpoints(self) -> bool:
        """Test if REST endpoints are available."""
        try:
            # Test a simple endpoint to see if REST is working
            test_url = self.api_endpoints.get('device_data')
            
            if not test_url:
                return False
            
            # Get auth headers
            headers = await self._get_auth_headers()
            if not headers:
                return False
            
            # Make a test request
            async with self.session.get(test_url, headers=headers, timeout=5) as response:
                if response.status in [200, 401, 403]:  # Any response means endpoint exists
                    self.working_endpoints.add('device_data')
                    self._log_debug("✅ REST endpoints responding")
                    return True
                else:
                    self.failed_endpoints.add('device_data')
                    return False
                    
        except Exception as e:
            self._log_debug(f"REST endpoint test failed: {e}")
            return False

    async def _get_auth_headers(self) -> Optional[Dict[str, str]]:
        """Get authentication headers for REST API calls."""
        try:
            if not self.eufyCleanApi or not hasattr(self.eufyCleanApi, 'eufyApi'):
                return None
            
            eufy_api = self.eufyCleanApi.eufyApi
            
            # Get tokens from the API
            if hasattr(eufy_api, 'session') and eufy_api.session:
                access_token = eufy_api.session.get('access_token')
            else:
                return None
            
            if hasattr(eufy_api, 'user_info') and eufy_api.user_info:
                user_center_token = eufy_api.user_info.get('user_center_token')
                gtoken = eufy_api.user_info.get('gtoken')
            else:
                return None
            
            if not all([access_token, user_center_token, gtoken]):
                return None
            
            # Return headers for REST API calls
            return {
                'user-agent': 'EufyHome-Android-3.1.3-753',
                'openudid': self.openudid,
                'os-version': 'Android',
                'model-type': 'PHONE',
                'app-name': 'eufy_home',
                'x-auth-token': user_center_token,
                'gtoken': gtoken,
                'content-type': 'application/json; charset=UTF-8',
                'token': access_token,
                'category': 'Home',
                'clienttype': '2',
            }
            
        except Exception as e:
            self._log_debug(f"Failed to get auth headers: {e}")
            return None

    async def updateDevice(self, force_update: bool = False):
        """
        Update device data - SIMPLIFIED VERSION with minimal logging.
        Only logs during detailed periods (every 10 minutes).
        """
        try:
            if not self.is_connected and not force_update:
                # Silently fail if not connected (no logging spam)
                return
            
            self.update_count += 1
            
            # Only log REST API attempts during detailed logging (every 10 minutes)
            detailed_logging = self._should_log_detailed()
            
            if detailed_logging:
                self._log_info(f"🔄 RestConnect UPDATE #{self.update_count} STARTING")
            
            # Try to fetch data from REST endpoints
            device_data = await self._fetch_device_data(detailed_logging)
            
            if device_data:
                # Extract DPS-like data from REST response
                combined_data = self._extract_dps_data(device_data)
                
                if combined_data:
                    self.raw_data = combined_data
                    self.last_update = time.time()
                    
                    if detailed_logging:
                        self._log_info(f"✅ RestConnect update #{self.update_count} completed - {len(self.raw_data)} keys")
                else:
                    if detailed_logging:
                        self._log_warning("⚠️ No DPS data extracted from REST response")
                    self.raw_data = {}
            else:
                if detailed_logging:
                    self._log_warning("⚠️ No data received from REST endpoints")
                self.raw_data = {}
                
        except Exception as e:
            # Only log errors during detailed periods or if critical
            if detailed_logging:
                self._log_error(f"❌ RestConnect update #{self.update_count} failed: {e}")
            # Clear raw data on update failure
            self.raw_data = {}

    def _should_log_detailed(self) -> bool:
        """Check if we should do detailed logging (controlled by coordinator)."""
        return getattr(self, '_detailed_logging_enabled', False)

    async def _fetch_device_data(self, detailed_logging: bool = False) -> Optional[Dict]:
        """Fetch device data from REST API endpoint."""
        try:
            if not self.session:
                return None
            
            headers = await self._get_auth_headers()
            if not headers:
                if detailed_logging:
                    self._log_debug("No auth headers available for REST call")
                return None
            
            # Try device data endpoint
            request_data = {
                "device_id": self.device_id,
                "time_zone": 0,
                "timestamp": int(time.time() * 1000)
            }
            
            if detailed_logging:
                self._log_debug("📡 Making REST API call to device endpoint")
            
            device_url = self.api_endpoints.get('device_data')
            if not device_url:
                return None
            
            async with self.session.post(device_url, json=request_data, headers=headers, timeout=10) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if detailed_logging:
                        self._log_debug("✅ REST API call successful")
                    return response_data
                else:
                    # Try alternative endpoint
                    return await self._fetch_device_data_alternative(detailed_logging)
                    
        except Exception as e:
            if detailed_logging:
                self._log_debug(f"REST API request failed: {e}")
            return None

    async def _fetch_device_data_alternative(self, detailed_logging: bool = False) -> Optional[Dict]:
        """Fetch device data from alternative Clean API endpoint."""
        try:
            headers = await self._get_auth_headers()
            if not headers:
                return None
            
            request_data = {
                "device_sn": self.device_id,
                "attribute": 3,
                "timestamp": int(time.time() * 1000)
            }
            
            if detailed_logging:
                self._log_debug("📡 Trying alternative Clean API endpoint")
            
            clean_url = self.api_endpoints.get('clean_device_info')
            if not clean_url:
                return None
            
            async with self.session.post(clean_url, json=request_data, headers=headers, timeout=10) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if detailed_logging:
                        self._log_debug("✅ Alternative REST API call successful")
                    return response_data
                else:
                    if detailed_logging:
                        self._log_debug(f"Alternative API call failed: {response.status}")
                    return None
                    
        except Exception as e:
            if detailed_logging:
                self._log_debug(f"Alternative REST request failed: {e}")
            return None

    def _extract_dps_data(self, response_data: Dict) -> Dict[str, Any]:
        """Extract DPS-like data from REST API response."""
        try:
            # Look for DPS data in various response formats
            dps_data = {}
            
            # Format 1: Direct DPS in response
            if 'dps' in response_data:
                dps_data.update(response_data['dps'])
            
            # Format 2: Device data with DPS
            if 'data' in response_data and isinstance(response_data['data'], dict):
                data_section = response_data['data']
                if 'dps' in data_section:
                    dps_data.update(data_section['dps'])
                
                # Also check for device in data
                if 'device' in data_section and 'dps' in data_section['device']:
                    dps_data.update(data_section['device']['dps'])
            
            # Format 3: Devices array
            if 'devices' in response_data and isinstance(response_data['devices'], list):
                for device in response_data['devices']:
                    if isinstance(device, dict) and device.get('device_sn') == self.device_id:
                        if 'dps' in device:
                            dps_data.update(device['dps'])
                        break
            
            return dps_data
            
        except Exception as e:
            self._log_debug(f"Error extracting DPS data: {e}")
            return {}

    def get_raw_data(self) -> Dict[str, Any]:
        """Get the current raw data."""
        return self.raw_data.copy()

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        return {
            'is_connected': self.is_connected,
            'last_update': self.last_update,
            'update_count': self.update_count,
            'keys_received': len(self.raw_data),
            'device_id': self.device_id,
            'device_model': self.device_model,
            'working_endpoints': list(self.working_endpoints),
            'failed_endpoints': list(self.failed_endpoints),
            'has_session': self.session is not None,
            'has_auth_token': hasattr(self.eufyCleanApi, 'eufyApi') and 
                             hasattr(self.eufyCleanApi.eufyApi, 'session') and
                             self.eufyCleanApi.eufyApi.session is not None,
            'has_user_center_token': hasattr(self.eufyCleanApi, 'eufyApi') and 
                                   hasattr(self.eufyCleanApi.eufyApi, 'user_info') and
                                   self.eufyCleanApi.eufyApi.user_info is not None,
            'has_gtoken': hasattr(self.eufyCleanApi, 'eufyApi') and 
                         hasattr(self.eufyCleanApi.eufyApi, 'user_info') and
                         self.eufyCleanApi.eufyApi.user_info is not None and
                         'gtoken' in self.eufyCleanApi.eufyApi.user_info,
            'api_endpoints_available': {endpoint: endpoint in self.working_endpoints 
                                      for endpoint in self.api_endpoints.keys()},
        }

    async def stop_polling(self):
        """Stop polling and cleanup."""
        try:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
            
            self.is_connected = False
            self._log_debug("RestConnect polling stopped")
            
        except Exception as e:
            self._log_error(f"Error stopping RestConnect polling: {e}")

    def _log_info(self, message: str):
        """Log info level message."""
        if self.debug_logger:
            self.debug_logger.info(message)
        elif self.debug_mode:
            _LOGGER.info("[RestConnect] %s", message)

    def _log_debug(self, message: str):
        """Log debug level message."""
        if self.debug_logger:
            self.debug_logger.debug(message)
        elif self.debug_mode:
            _LOGGER.debug("[RestConnect] %s", message)

    def _log_warning(self, message: str):
        """Log warning level message."""
        if self.debug_logger:
            self.debug_logger.warning(message)
        elif self.debug_mode:
            _LOGGER.warning("[RestConnect] %s", message)

    def _log_error(self, message: str):
        """Log error level message."""
        if self.debug_logger:
            self.debug_logger.error(message)
        else:
            _LOGGER.error("[RestConnect] %s", message)