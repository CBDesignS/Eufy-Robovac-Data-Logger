# rev 7 remove old logging and enable new mqtt logging.
# rev 6 add full as possible mqtt logging to try and find out whats going out and in thru mqtt.
# rev 5 full wakeup restart of mqtt to try and keep the connection from going stale
import asyncio
import json
import logging
import time
from functools import partial
from os import path
from threading import Thread

from google.protobuf.message import Message
from paho.mqtt import client as mqtt

from ..controllers.Login import EufyLogin
from ..utils import sleep
from .SharedConnect import SharedConnect

_LOGGER = logging.getLogger(__name__)


def get_blocking_mqtt_client(client_id: str, username: str, certificate_pem: str, private_key: str):
    client = mqtt.Client(
        client_id=client_id,
        transport='tcp',
    )
    client.username_pw_set(username)

    current_dir = path.dirname(path.abspath(__file__))
    ca_path = path.join(current_dir, 'ca.pem')
    key_path = path.join(current_dir, 'key.key')

    with open(ca_path, 'w') as f:
        f.write(certificate_pem)
    with open(key_path, 'w') as f:
        f.write(private_key)

    client.tls_set(
        certfile=path.abspath(ca_path),
        keyfile=path.abspath(key_path),
    )
    return client


class MqttConnect(SharedConnect):
    def __init__(self, config, openudid: str, eufyCleanApi: EufyLogin):
        super().__init__(config)
        self.deviceId = config['deviceId']
        self.deviceModel = config['deviceModel']
        self.config = config
        self.debugLog = config.get('debug', False)
        self.openudid = openudid
        self.eufyCleanApi = eufyCleanApi
        self.mqttClient = None
        self.mqttCredentials = None
        self._loop = None  # Store reference to the event loop
        self._polling_task = None  # Store reference to polling task
        self.last_data_received = None
        self.connection_time = None

    async def connect(self):
        # Store the current event loop for later use
        self._loop = asyncio.get_running_loop()
        
        await self.eufyCleanApi.login({'mqtt': True})
        await self.connectMqtt(self.eufyCleanApi.mqtt_credentials)
        await self.updateDevice(True)
        await sleep(2000)
        
        # Start periodic polling to keep robot awake
        self._polling_task = asyncio.create_task(self._periodic_polling())

    async def updateDevice(self, checkApiType=False):
        try:
            if not checkApiType:
                return
            device = await self.eufyCleanApi.getMqttDevice(self.deviceId)
            if device and device.get('dps'):
                await self._map_data(device.get('dps'))
        except Exception as error:
            _LOGGER.error(f"Error updating device: {error}")

    async def connectMqtt(self, mqttCredentials):
        if mqttCredentials:
            _LOGGER.debug('MQTT Credentials found')
            self.mqttCredentials = mqttCredentials
            username = self.mqttCredentials['thing_name']
            client_id = f"android-{self.mqttCredentials['app_name']}-eufy_android_{self.openudid}_{self.mqttCredentials['user_id']}-{int(time.time() * 1000)}"
            _LOGGER.debug('Setup MQTT Connection', {
                'clientId': client_id,
                'username': username,
            })
            if self.mqttClient:
                self.mqttClient.disconnect()
            # When calling a blocking function in your library code
            loop = asyncio.get_running_loop()
            self.mqttClient = await loop.run_in_executor(None, partial(
                get_blocking_mqtt_client,
                client_id=client_id,
                username=username,
                certificate_pem=self.mqttCredentials['certificate_pem'],
                private_key=self.mqttCredentials['private_key'],
            ))
            self.mqttClient.connect_timeout = 30

            self.setupListeners()
            self.mqttClient.connect_async(self.mqttCredentials['endpoint_addr'], port=8883)
            self.mqttClient.loop_start()

    def setupListeners(self):
        self.mqttClient.on_connect = self.on_connect
        self.mqttClient.on_message = self.on_message
        self.mqttClient.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        _LOGGER.debug('Connected to MQTT')
        _LOGGER.info(f"Subscribe to cmd/eufy_home/{self.deviceModel}/{self.deviceId}/res")
        self.mqttClient.subscribe(f"cmd/eufy_home/{self.deviceModel}/{self.deviceId}/res")
        
        # Mark when we connected
        self.last_data_received = None
        self.connection_time = time.time()
        
        # Don't send wake-up nudge on reconnect - let the robot naturally start sending data
        _LOGGER.debug("Connection established, waiting for data...")

    async def send_find_robot_command(self):
        """Send find robot command to wake up the device."""
        try:
            _LOGGER.debug("Sending wake-up nudge - trying multiple approaches")
            
            # Try different find_robot values
            find_robot_values = [
                True,           # Boolean true
                1,              # Integer 1
                "1",            # String "1"
                {"value": 1},   # Dict with value
                {"find": True}, # Dict with find
                2,              # Integer 2 (might be "start find")
                0,              # Integer 0 (might be "stop find")
                {"action": 1},  # Dict with action
                {"cmd": "find"},# Dict with cmd
                255,            # Max byte value
                {"enabled": True}, # Dict with enabled
            ]
            
            for i, value in enumerate(find_robot_values):
                _LOGGER.debug(f"Attempt {i+1}: Sending find_robot with value: {value} (type: {type(value).__name__})")
                try:
                    await self.send_command({self.dps_map['FIND_ROBOT']: value})
                    await asyncio.sleep(1)  # Give it time to respond
                except Exception as e:
                    _LOGGER.debug(f"Attempt {i+1} failed: {e}")
            
            # Also try some other wake-up approaches
            _LOGGER.debug("Trying alternative wake-up methods")
            
            # Try requesting various status updates
            status_fields = ['WORK_STATUS', 'BATTERY_LEVEL', 'ERROR_CODE', 'WORK_MODE']
            for field in status_fields:
                if field in self.dps_map:
                    _LOGGER.debug(f"Requesting {field}")
                    try:
                        await self.send_command({self.dps_map[field]: ""})
                        await asyncio.sleep(0.5)
                    except:
                        pass
            
            _LOGGER.debug("Wake-up nudge attempts completed")
        except Exception as error:
            _LOGGER.error(f"Error sending wake-up nudge: {error}")
    
    async def send_wake_up_sequence(self):
        """Try various methods to wake up the robot"""
        try:
            _LOGGER.info("Starting comprehensive wake-up sequence")
            start_time = time.time()
            
            # First try find_robot variations
            await self.send_find_robot_command()
            
            # Check if we got any data
            await asyncio.sleep(2)
            if self.last_data_received and self.last_data_received > start_time:
                _LOGGER.info("Wake-up successful! Robot is responding")
                return
            
            # Try more aggressive wake-up methods
            _LOGGER.info("No response yet, trying command-based wake-up")
            
            # Try sending a pause command (might wake it even if already paused)
            try:
                from ..proto.cloud.control_pb2 import ModeCtrlRequest
                from ..constants.state import EUFY_CLEAN_CONTROL
                from ..utils import encode
                
                value = encode(ModeCtrlRequest, {'method': EUFY_CLEAN_CONTROL.PAUSE_TASK})
                await self.send_command({self.dps_map['PLAY_PAUSE']: value})
                await asyncio.sleep(2)
            except Exception as e:
                _LOGGER.debug(f"Pause command failed: {e}")
            
            # Check again
            if self.last_data_received and self.last_data_received > start_time:
                _LOGGER.info("Wake-up successful via pause command!")
                return
            
            # Try requesting cleaning parameters
            try:
                await self.send_command({self.dps_map['CLEANING_PARAMETERS']: ""})
                await asyncio.sleep(2)
            except:
                pass
            
            # Final check
            if self.last_data_received and self.last_data_received > start_time:
                _LOGGER.info("Wake-up successful!")
            else:
                _LOGGER.warning("Robot did not respond to wake-up attempts. It may be in deep sleep.")
                
        except Exception as e:
            _LOGGER.error(f"Error in wake-up sequence: {e}")

    def on_message(self, client, userdata, msg: Message):
        """Log everything for debugging and handle messages"""
        try:
            # Log raw message details
            _LOGGER.debug(f"=== MQTT MESSAGE RECEIVED ===")
            _LOGGER.debug(f"  Topic: {msg.topic}")
            _LOGGER.debug(f"  QoS: {msg.qos}")
            _LOGGER.debug(f"  Retain: {msg.retain}")
            _LOGGER.debug(f"  Payload length: {len(msg.payload)} bytes")
            _LOGGER.debug(f"  Raw payload (first 200 chars): {str(msg.payload)[:200]}")
            
            # Try to decode as JSON
            try:
                messageParsed = json.loads(msg.payload.decode())
                _LOGGER.debug(f"  Decoded JSON: {json.dumps(messageParsed, indent=2)}")
            except json.JSONDecodeError:
                _LOGGER.error(f"Failed to decode JSON, raw hex: {msg.payload.hex()}")
                messageParsed = {}
            
            # Track that we received data
            self.last_data_received = time.time()
            
            # Get the payload data - try multiple paths
            payload_data = None
            if isinstance(messageParsed, dict):
                # Try different paths where data might be
                if 'payload' in messageParsed:
                    if isinstance(messageParsed['payload'], dict) and 'data' in messageParsed['payload']:
                        payload_data = messageParsed['payload']['data']
                    elif isinstance(messageParsed['payload'], str):
                        # Payload might be JSON string
                        try:
                            payload_decoded = json.loads(messageParsed['payload'])
                            if isinstance(payload_decoded, dict) and 'data' in payload_decoded:
                                payload_data = payload_decoded['data']
                        except:
                            pass
                elif 'data' in messageParsed:
                    payload_data = messageParsed['data']
            
            if payload_data:
                _LOGGER.info(f"DPS data received! Robot appears to be awake.")
                _LOGGER.debug(f"  DPS Keys: {list(payload_data.keys())}")
                _LOGGER.debug(f"  DPS Data: {json.dumps(payload_data, indent=2)}")
                
                # Log hex dump of any binary data
                for key, value in payload_data.items():
                    if isinstance(value, (bytes, bytearray)):
                        _LOGGER.debug(f"  DPS {key} (hex): {value.hex()}")
                    elif isinstance(value, str) and len(value) > 50:
                        _LOGGER.debug(f"  DPS {key} (truncated): {value[:50]}...")
                
                # Schedule the async function to run in the event loop
                if self._loop and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._map_data(payload_data), 
                        self._loop
                    )
                else:
                    _LOGGER.warning("Event loop not available for message processing")
            else:
                _LOGGER.debug("  No DPS data found in message")
                _LOGGER.debug(f"  Message structure: {list(messageParsed.keys()) if isinstance(messageParsed, dict) else 'not a dict'}")
                
        except Exception as error:
            _LOGGER.error(f'Error processing message: {error}', exc_info=True)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            _LOGGER.warning('Unexpected MQTT disconnection. Will auto-reconnect')
        
        # Cancel polling task on disconnect
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()

    async def send_command(self, dataPayload) -> None:
        try:
            if not self.mqttCredentials:
                _LOGGER.error("No MQTT credentials available")
                return
            
            # Log what we're sending
            _LOGGER.debug(f"=== SENDING MQTT COMMAND ===")
            _LOGGER.debug(f"  DPS Payload: {json.dumps(dataPayload, indent=2)}")
            
            # Check for any binary data in the payload
            for key, value in dataPayload.items():
                if isinstance(value, (bytes, bytearray)):
                    _LOGGER.debug(f"  DPS {key} (hex): {value.hex()}")
                
            payload = json.dumps({
                'account_id': self.mqttCredentials['user_id'],
                'data': dataPayload,
                'device_sn': self.deviceId,
                'protocol': 2,
                't': int(time.time()) * 1000,
            })
            
            mqttVal = {
                'head': {
                    'client_id': f"android-{self.mqttCredentials['app_name']}-eufy_android_{self.openudid}_{self.mqttCredentials['user_id']}",
                    'cmd': 65537,
                    'cmd_status': 2,
                    'msg_seq': 1,
                    'seed': '',
                    'sess_id': f"android-{self.mqttCredentials['app_name']}-eufy_android_{self.openudid}_{self.mqttCredentials['user_id']}",
                    'sign_code': 0,
                    'timestamp': int(time.time()) * 1000,
                    'version': '1.0.0.1'
                },
                'payload': payload,
            }
            
            _LOGGER.debug(f"  Full MQTT packet: {json.dumps(mqttVal, indent=2)}")
            
            topic = f"cmd/eufy_home/{self.deviceModel}/{self.deviceId}/req"
            _LOGGER.debug(f"  Publishing to topic: {topic}")
            
            if self.mqttClient and self.mqttClient.is_connected():
                result = self.mqttClient.publish(topic, json.dumps(mqttVal))
                _LOGGER.debug(f"  Publish result: {result.rc} (0=success)")
            else:
                _LOGGER.error("MQTT client not connected")
        except Exception as error:
            _LOGGER.error(f"Error sending command: {error}", exc_info=True)
    
    async def _periodic_polling(self):
        """Periodically check connection and reconnect if no data"""
        check_interval = 60  # Check every minute
        no_data_timeout = 300  # 5 minutes without data triggers reconnect
        
        while True:
            try:
                # Check if we have recent data
                if self.last_data_received:
                    time_since_last_data = time.time() - self.last_data_received
                    
                    if time_since_last_data > no_data_timeout:
                        _LOGGER.warning(f"No data for {time_since_last_data:.0f} seconds, triggering reconnection")
                        await self._reconnect()
                    elif time_since_last_data > 60:
                        _LOGGER.debug(f"No data for {time_since_last_data:.0f} seconds")
                else:
                    # No data ever received since connection
                    if self.connection_time and (time.time() - self.connection_time) > 60:
                        _LOGGER.warning("No data received since connection, triggering reconnection")
                        await self._reconnect()
                
                await asyncio.sleep(check_interval)
                    
            except asyncio.CancelledError:
                _LOGGER.info("Periodic polling cancelled")
                break
            except Exception as e:
                _LOGGER.error(f"Error in periodic polling: {e}")
                await asyncio.sleep(check_interval)
    
    async def _reconnect(self):
        """Disconnect and reconnect to wake up the robot"""
        try:
            _LOGGER.info("Starting reconnection process")
            
            # Cancel the polling task to avoid conflicts
            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect MQTT client
            if self.mqttClient:
                _LOGGER.debug("Disconnecting MQTT client")
                try:
                    self.mqttClient.loop_stop()
                    self.mqttClient.disconnect()
                except:
                    pass
                self.mqttClient = None
            
            # Wait a bit for clean disconnect
            await asyncio.sleep(2)
            
            # Reset connection tracking
            self.last_data_received = None
            self.connection_time = None
            
            # Re-login and reconnect
            _LOGGER.debug("Re-establishing connection")
            await self.eufyCleanApi.login({'mqtt': True})
            await self.connectMqtt(self.eufyCleanApi.mqtt_credentials)
            
            # Try to get initial device data
            await self.updateDevice(True)
            
            # Restart polling task
            self._polling_task = asyncio.create_task(self._periodic_polling())
            
            _LOGGER.info("Reconnection complete")
            
        except Exception as e:
            _LOGGER.error(f"Reconnection failed: {e}")
            # Schedule another reconnection attempt
            await asyncio.sleep(30)
            if self._loop and not self._loop.is_closed():
                asyncio.create_task(self._reconnect())
    
    async def force_wake_up(self):
        """Force wake-up attempt - can be called manually"""
        _LOGGER.info("Forcing wake-up attempt via reconnection")
        
        # Just trigger a reconnection
        await self._reconnect()
        
        # Wait for data
        await asyncio.sleep(10)
        
        # Report result
        if self.last_data_received:
            _LOGGER.info("Force wake-up successful!")
            return True
        else:
            _LOGGER.warning("Force wake-up failed - robot may be in deep sleep")
            return False
    
    async def disconnect(self):
        """Properly disconnect and cleanup"""
        try:
            # Cancel polling task
            if self._polling_task and not self._polling_task.done():
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect MQTT
            if self.mqttClient:
                self.mqttClient.loop_stop()
                self.mqttClient.disconnect()
                self.mqttClient = None
                
            _LOGGER.info("Disconnected from MQTT")
        except Exception as e:
            _LOGGER.error(f"Error during disconnect: {e}")