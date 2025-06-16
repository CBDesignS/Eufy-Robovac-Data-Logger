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
        Get device list with DPS data - RESTORED WORKING VERSION with better error handling.
        This was the original working method that returns real DPS data from the cloud.
        """
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
                    json={'attribute': 3},
                    timeout=aiohttp.ClientTimeout(total=15)  # Better timeout handling
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        devices = data.get('data', {}).get('devices')
                        if not devices:
                            _LOGGER.warning('No devices found in response')
                            return []
                        
                        # Extract device array with DPS data (original working pattern)
                        device_array = []
                        for device_wrapper in devices:
                            if 'device' in device_wrapper:
                                device = device_wrapper['device']
                                device_array.append(device)
                        
                        # Filter by device_sn if specified
                        if device_sn:
                            found_device = next((device for device in device_array if device.get('device_sn') == device_sn), None)
                            if found_device:
                                _LOGGER.debug(f'Found device {device_sn} with {len(found_device.get("dps", {}))} DPS keys')
                                return found_device
                            else:
                                _LOGGER.warning(f'Device {device_sn} not found')
                                return None
                        
                        _LOGGER.debug(f'Found {len(device_array)} devices with DPS data')
                        return device_array
                    else:
                        _LOGGER.error(f'get_device_list failed with status {response.status}')
                        return []
                        
        except asyncio.TimeoutError:
            _LOGGER.error('get_device_list: Request timeout - network connectivity issue')
            return []
        except aiohttp.ClientError as e:
            _LOGGER.error(f'get_device_list: Network error - {e}')
            return []
        except Exception as e:
            _LOGGER.error(f'get_device_list error: {e}')
            return []

    # REMOVED: update_device_dps - not needed with restored working REST call

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
        self._cloud_devices.clear()
        _LOGGER.debug('Cleared EufyApi cache')