import asyncio
import logging
from typing import Any, Callable

from homeassistant.components.vacuum import VacuumActivity

from ..constants.devices import EUFY_CLEAN_DEVICES
from ..constants.state import (EUFY_CLEAN_CLEAN_SPEED, EUFY_CLEAN_CONTROL,
                               EUFY_CLEAN_NOVEL_CLEAN_SPEED)
from ..proto.cloud.clean_param_pb2 import (CleanExtent, CleanParamRequest,
                                           CleanParamResponse, CleanType,
                                           MopMode)
from ..proto.cloud.control_pb2 import (ModeCtrlRequest, ModeCtrlResponse,
                                       SelectRoomsClean)
from ..proto.cloud.station_pb2 import (StationRequest, ManualActionCmd)
from ..proto.cloud.error_code_pb2 import ErrorCode
from ..proto.cloud.work_status_pb2 import WorkStatus
from ..utils import decode, encode, encode_message
from .Base import Base

_LOGGER = logging.getLogger(__name__)


class SharedConnect(Base):
    def __init__(self, config) -> None:
        super().__init__()
        self.debug_log = config.get('debug', False)
        self.device_id = config['deviceId']
        self.device_model = config.get('deviceModel', '')
        self.device_model_desc = EUFY_CLEAN_DEVICES.get(self.device_model, '') or self.device_model
        self.config = {}
        self._update_listeners = []

    _update_listeners: list[Callable[[], None]]

    async def _map_data(self, dps):
        # FIX: Store ALL DPS keys with their numeric keys
        for key, value in dps.items():
            # Store with numeric key
            self.robovac_data[key] = value
            
            # Also store with mapped name if it exists
            mapped_keys = [k for k, v in self.dps_map.items() if v == key]
            for mapped_key in mapped_keys:
                self.robovac_data[mapped_key] = value

        if self.debug_log:
            _LOGGER.debug('mappedData', self.robovac_data)

        await self.get_control_response()
        for listener in self._update_listeners:
            try:
                _LOGGER.debug(f'Calling listener {listener.__name__ if hasattr(listener, "__name__") else "anonymous"}')
                # Fixed: Handle both sync and async listeners
                if asyncio.iscoroutinefunction(listener):
                    await listener()
                else:
                    listener()
            except Exception as e:
                _LOGGER.error(f'Error calling listener: {e}')

    def add_listener(self, listener: Callable[[], None]):
        if listener not in self._update_listeners:
            self._update_listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]):
        if listener in self._update_listeners:
            self._update_listeners.remove(listener)

    async def room_clean(self, room_ids: list[int], map_id: int = 3):
        _LOGGER.debug(f'Room clean: {room_ids}, map_id: {map_id}')
        rooms_clean = SelectRoomsClean(
            rooms=[SelectRoomsClean.Room(id=id, order=i + 1) for i, id in enumerate(room_ids)],
            mode=SelectRoomsClean.Mode.DESCRIPTOR.values_by_name['MODE_NORMAL'].number,
            map_id=map_id,
        )
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.START_SELECT_ROOMS_CLEAN, 'select_rooms_clean': rooms_clean})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def zone_clean(self, zones: list[tuple[int, int, int, int]]):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.START_ZONE_CLEAN, 'zone_clean': {'zones': [{'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1} for x0, y0, x1, y1 in zones]}})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def quick_clean(self, room_ids: list[int]):
        quick_clean = SelectRoomsClean(rooms=[SelectRoomsClean.Room(id=id, order=i + 1) for i, id in enumerate(room_ids)])
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.START_QUICK_CLEAN, 'select_rooms_clean': quick_clean})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def scene_clean(self, id: int):
        increment = 3
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.START_SCENE_CLEAN, 'scene_clean': {'scene_id': id + increment}})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def play(self):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.RESUME_TASK})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def pause(self):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.PAUSE_TASK})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def stop(self):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.STOP_TASK})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def go_home(self):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.START_GOHOME})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def go_dry(self):
        value = encode(StationRequest, {'manual_cmd': {'go_dry': True}})
        return await self.send_command({self.dps_map['GO_HOME']: value})

    async def go_selfcleaning(self):
        value = encode(StationRequest, {'manual_cmd': {'go_selfcleaning': True}})
        return await self.send_command({self.dps_map['GO_HOME']: value})

    async def collect_dust(self):
        value = encode(StationRequest, {'manual_cmd': {'go_collect_dust': True}})
        return await self.send_command({self.dps_map['GO_HOME']: value})

    async def spot_clean(self):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.START_SPOT_CLEAN})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def set_map(self, map_id: int):
        value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.SELECT_MAP, 'select_map': {'map_id': map_id}})
        return await self.send_command({self.dps_map['PLAY_PAUSE']: value})

    async def set_clean_param(self, param):
        value = encode(CleanParamRequest, param)
        return await self.send_command({self.dps_map['CLEANING_PARAMETERS']: value})

    async def get_control_response(self):
        data = self.robovac_data.get('PLAY_PAUSE')
        if data:
            try:
                response = decode(ModeCtrlResponse, data)
                self.robovac_data['PLAY_PAUSE_RESPONSE'] = response
            except Exception as e:
                _LOGGER.debug('error in mapping to control response', e)

    async def get_work_status(self) -> VacuumActivity:
        data = self.robovac_data.get('WORK_STATUS')
        if data:
            try:
                response = decode(WorkStatus, data)
                state = response.work_mode
                if state == 0:
                    return 'standby'
                if state == 1:
                    return 'sleeping'
                if state == 2:
                    return 'error'
                if state == 3:
                    return 'recharging'
                if state == 4:
                    return 'fastmapping'
                if state == 5:
                    return 'cleaning'
                if state == 6:
                    return 'remote'
                if state == 7:
                    return 'recharge'
                if state == 8:
                    return 'pause'
                if state == 9:
                    return 'finished'
                if state == 10:
                    return 'locate'
                if state == 11:
                    return 'selectroom'
                if state == 12:
                    return 'station'
                if state == 13:
                    return 'cruise'
                if state == 14:
                    return 'breakpointrecharge'
                if state == 15:
                    return 'cruisepause'
                _LOGGER.info(f"Unknown work status: {state}")
                return state
            except Exception as e:
                _LOGGER.debug('error in mapping to work status', e)
        return 'standby'

    async def get_clean_params_response(self):
        data = self.robovac_data.get('CLEANING_PARAMETERS')
        if data:
            try:
                response = decode(CleanParamResponse, data)
                return response
            except Exception as e:
                _LOGGER.debug('error in mapping to params response', e)

    async def get_error_response(self):
        data = self.robovac_data.get('ERROR_CODE')
        if data:
            try:
                response = decode(ErrorCode, data)
                return response
            except Exception as e:
                _LOGGER.debug('error in mapping to error response', e)

    async def get_work_mode(self):
        work_status = await self.get_work_status()
        return work_status

    async def get_battery_level(self):
        data = self.robovac_data.get('BATTERY_LEVEL')
        return data

    async def get_clean_speed(self):
        params_res = await self.get_clean_params_response()
        if params_res and hasattr(params_res, 'clean_param') and hasattr(params_res.clean_param, 'clean_speed'):
            return EUFY_CLEAN_NOVEL_CLEAN_SPEED[params_res.clean_param.clean_speed]
        return None

    async def set_clean_speed(self, clean_speed: str):
        if clean_speed in EUFY_CLEAN_NOVEL_CLEAN_SPEED:
            clean_speed = EUFY_CLEAN_NOVEL_CLEAN_SPEED.index(clean_speed)
        else:
            clean_speed = 1
        # Get current params first
        params_res = await self.get_clean_params_response()
        if params_res and hasattr(params_res, 'clean_param'):
            # Use existing params and just update speed
            param = {
                'clean_type': params_res.clean_param.clean_type,
                'clean_speed': clean_speed,
                'clean_extent': params_res.clean_param.clean_extent,
                'mop_mode': params_res.clean_param.mop_mode
            }
        else:
            # Default params if can't get current
            param = {
                'clean_type': CleanType.BOTH_CLEAN,
                'clean_speed': clean_speed,
                'clean_extent': CleanExtent.DEFAULT,
                'mop_mode': MopMode.HIGH
            }
        return await self.set_clean_param(param)

    async def send_command(self, dps):
        raise NotImplementedError('Not implemented')