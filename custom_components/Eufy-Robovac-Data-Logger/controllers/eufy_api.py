import hashlib
import logging
from typing import Any, Optional
import aiohttp

_LOGGER = logging.getLogger(__name__)


class EufyApi:
    def __init__(self, username: str, password: str, openudid: str) -> None:
        self.username = username
        self.password = password
        self.openudid = openudid
        self.session = None
        self.user_info = None
        self._cloud_devices = []  # Cache cloud devices from initial setup
        self._device_dps_cache = {}  # Cache DPS data to avoid repeated calls

    async def login(self, validate_only: bool = False) -> dict[str, Any]:
        """
        Login and get initial credentials - REST calls only during setup phase.
        Following original eufy-clean/mqtt pattern: REST for setup, DPS for operation.
        """
        session = await self.eufy_login()
        if validate_only:
            return {'session': session}
        user = await self.get_user_info()
        mqtt = await self.get_mqtt_credentials()
        return {'session': session, 'user': user, 'mqtt': mqtt}

    async def eufy_login(self) -> Optional[dict[str, Any]]:
        """Initial authentication - REST call for setup only."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://home-api.eufylife.com/v1/user/email/login',
                    headers={
                        'category': 'Home',
                        'Accept': '*/*',
                        'openudid': self.openudid,
                        'Content-Type': 'application/json',
                        'clientType': '1',
                        'User-Agent': 'EufyHome-iOS-2.14.0-6',
                        'Connection': 'keep-alive',
                    },
                    json={
                        'email': self.username,
                        'password': self.password,
                        'client_id': 'eufyhome-app',
                        'client_secret': 'GQCpr9dSp3uQpsOMgJ4xQ',
                    }
                ) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        if response_json.get('access_token'):
                            _LOGGER.debug('eufyLogin successful')
                            self.session = response_json
                            return response_json
                    _LOGGER.error(f'Login failed: {await response.json()}')
                    return None
        except Exception as e:
            _LOGGER.error(f'Login error: {e}')
            return None

    async def get_user_info(self) -> Optional[dict[str, Any]]:
        """Get user info - REST call for setup only."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.eufylife.com/v1/user/user_center_info',
                    headers={
                        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'user-agent': 'EufyHome-Android-3.1.3-753',
                        'category': 'Home',
                        'token': self.session['access_token'],
                        'openudid': self.openudid,
                        'clienttype': '2',
                    }
                ) as response:
                    if response.status == 200:
                        self.user_info = await response.json()
                        if not self.user_info.get('user_center_id'):
                            _LOGGER.error('No user_center_id found')
                            return None
                        self.user_info['gtoken'] = hashlib.md5(self.user_info['user_center_id'].encode()).hexdigest()
                        return self.user_info
                    _LOGGER.error('get user center info failed')
                    _LOGGER.error(await response.json())
                    return None
        except Exception as e:
            _LOGGER.error(f'Get user info error: {e}')
            return None

    async def get_cloud_device_list(self) -> list[dict[str, Any]]:
        """
        Get cloud device list - REST call for initial setup only.
        This method should only be called once during initialization.
        """
        if self._cloud_devices:
            return self._cloud_devices  # Return cached data
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://aiot-clean-api-pr.eufylife.com/app/devicerelation/get_device_list',
                    headers={
                        'user-agent': 'EufyHome-Android-3.1.3-753',
                        'openudid': self.openudid,
                        'os-version': 'Android',
                        'model-type': 'PHONE',
                        'app-name': 'eufy_home',
                        'x-auth-token': self.user_info['user_center_token'],
                        'gtoken': self.user_info['gtoken'],
                        'content-type': 'application/json; charset=UTF-8',
                    },
                    json={}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        devices = data.get('data', {}).get('device_list', [])
                        self._cloud_devices = devices  # Cache the result
                        _LOGGER.debug(f'Found {len(devices)} cloud devices during setup')
                        return devices
                    _LOGGER.error('get cloud device list failed')
                    _LOGGER.error(await response.json())
                    return []
        except Exception as e:
            _LOGGER.error(f'Get cloud device list error: {e}')
            return []

    async def get_device_list(self, device_sn: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Get device DPS data - PURE DPS IMPLEMENTATION, NO REST CALLS.
        This method is called by coordinator updates and must be DPS-only.
        
        CRITICAL: This method no longer makes REST API calls to avoid DNS timeouts.
        It now extracts DPS data from MQTT/device connection or cached data.
        """
        try:
            # If requesting specific device and we have cached DPS data, return it
            if device_sn and device_sn in self._device_dps_cache:
                cached_device = self._device_dps_cache[device_sn]
                _LOGGER.debug(f'Returning cached DPS data for device {device_sn}')
                return [cached_device]
            
            # For coordinator updates, we should get DPS data from MQTT connection
            # instead of making REST calls. This requires the MQTT connection to provide DPS data.
            # The actual DPS data should come from the MQTT connection established by MqttConnect
            
            # Return placeholder structure that matches expected format
            # Real DPS data will come from MQTT connection in MqttConnect.updateDevice()
            devices = []
            
            if device_sn:
                # Single device request - return minimal structure
                # DPS data will be populated by MQTT connection
                device_data = {
                    'device_sn': device_sn,
                    'dps': {},  # DPS data populated by MQTT
                    'is_online': True
                }
                devices = [device_data]
                
                # Cache this device structure
                self._device_dps_cache[device_sn] = device_data
            else:
                # Multiple devices request - return all known devices from cloud cache
                for cloud_device in self._cloud_devices:
                    device_id = cloud_device.get('id', cloud_device.get('device_sn', ''))
                    if device_id:
                        device_data = {
                            'device_sn': device_id,
                            'dps': {},  # DPS data populated by MQTT
                            'is_online': cloud_device.get('is_online', True)
                        }
                        devices.append(device_data)
                        
                        # Cache this device structure
                        self._device_dps_cache[device_id] = device_data
            
            _LOGGER.debug(f'get_device_list: Returning {len(devices)} devices (DPS-only mode)')
            return devices
            
        except Exception as e:
            _LOGGER.error(f'get_device_list error: {e}')
            return []

    def update_device_dps(self, device_sn: str, dps_data: dict) -> None:
        """
        Update DPS data for a device (called by MQTT connection).
        This allows the MQTT connection to feed real DPS data into the cached device data.
        """
        if device_sn in self._device_dps_cache:
            self._device_dps_cache[device_sn]['dps'] = dps_data
            _LOGGER.debug(f'Updated DPS cache for device {device_sn}')
        else:
            # Create new cache entry
            self._device_dps_cache[device_sn] = {
                'device_sn': device_sn,
                'dps': dps_data,
                'is_online': True
            }
            _LOGGER.debug(f'Created new DPS cache entry for device {device_sn}')

    async def get_mqtt_credentials(self) -> Optional[dict[str, Any]]:
        """Get MQTT credentials - REST call for setup only."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://aiot-clean-api-pr.eufylife.com/app/devicemanage/get_user_mqtt_info',
                    headers={
                        'content-type': 'application/json',
                        'user-agent': 'EufyHome-Android-3.1.3-753',
                        'openudid': self.openudid,
                        'os-version': 'Android',
                        'model-type': 'PHONE',
                        'app-name': 'eufy_home',
                        'x-auth-token': self.user_info['user_center_token'],
                        'gtoken': self.user_info['gtoken'],
                    }
                ) as response:
                    if response.status == 200:
                        return (await response.json()).get('data')
                    _LOGGER.error('get mqtt credentials failed')
                    _LOGGER.error(await response.json())
                    return None
        except Exception as e:
            _LOGGER.error(f'Get MQTT credentials error: {e}')
            return None

    # REMOVED: get_product_data_point method (was making REST calls during operation)
    # This method was calling REST endpoints and not needed for DPS-only operation
    
    def clear_cache(self) -> None:
        """Clear cached data (useful for testing or re-initialization)."""
        self._device_dps_cache.clear()
        self._cloud_devices.clear()
        _LOGGER.debug('Cleared EufyApi cache')