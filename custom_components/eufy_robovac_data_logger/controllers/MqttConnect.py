# v7 - Move Logging from H.A main log over to /config/logs/eufy_mqtt_traffic.log
# v6 - Added comprehensive MQTT message logging and multiple wake-up command attempts without reconnection logic
# v5 - Added detailed MQTT message logging with JSON structure inspection and hex dumps
# v4 - Implemented comprehensive wake-up attempts with 11 different find_robot value formats
# v3 - Enhanced wake-up sequence with additional status request methods (battery, error, work status)
# v2 - Added multiple find_robot value attempts (boolean, integer, string) for wake-up testing
# v1 - Fixed ModeCtrlRequest 'action' field error by removing incorrect find_robot protobuf usage
import asyncio
import json
import logging
import time
from functools import partial
from os import path
from threading import Thread
from datetime import datetime

from google.protobuf.message import Message
from paho.mqtt import client as mqtt

from ..controllers.Login import EufyLogin
from ..utils import sleep
from .SharedConnect import SharedConnect

_LOGGER = logging.getLogger(__name__)

# Set up file logging for MQTT traffic
import os
from logging.handlers import TimedRotatingFileHandler

# Create a separate logger for MQTT traffic
mqtt_logger = logging.getLogger('eufy_mqtt_traffic')
mqtt_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
log_dir = "/config/logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create a log filename with date
from datetime import datetime
date_str = datetime.now().strftime("%Y%m%d")
log_file = os.path.join(log_dir, f"eufy_mqtt_log_{date_str}.log")

# Create timed rotating file handler (new file each day at midnight, keep 30 days)
file_handler = TimedRotatingFileHandler(
    log_file, 
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
file_handler.suffix = "%Y%m%d"
file_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger
mqtt_logger.addHandler(file_handler)


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

    async def connect(self):
        # Store the current event loop for later use
        self._loop = asyncio.get_running_loop()
        
        await self.eufyCleanApi.login({'mqtt': True})
        await self.connectMqtt(self.eufyCleanApi.mqtt_credentials)
        await self.updateDevice(True)
        await sleep(2000)

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
            mqtt_logger.info(f"=== NEW MQTT SESSION STARTED for {self.deviceId} ===")
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
        mqtt_logger.info(f"MQTT Connected - RC: {rc}, Subscribed to: cmd/eufy_home/{self.deviceModel}/{self.deviceId}/res")
        
        # Send wake-up nudge after connection
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self.send_find_robot_command(), 
                self._loop
            )

    async def send_find_robot_command(self):
        """Send find robot command to wake up the device."""
        try:
            _LOGGER.debug("Sending wake-up nudge - trying multiple approaches")
            mqtt_logger.info("=== WAKE-UP SEQUENCE STARTED ===")
            
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
                mqtt_logger.debug(f"Wake-up attempt {i+1}: DPS 160 = {value} (type: {type(value).__name__})")
                try:
                    await self.send_command({self.dps_map['FIND_ROBOT']: value})
                    await asyncio.sleep(1)  # Give it time to respond
                except Exception as e:
                    _LOGGER.debug(f"Attempt {i+1} failed: {e}")
                    mqtt_logger.error(f"Wake-up attempt {i+1} failed: {e}")
            
            # Also try some other wake-up approaches
            _LOGGER.debug("Trying alternative wake-up methods")
            mqtt_logger.info("=== TRYING ALTERNATIVE WAKE-UP METHODS ===")
            
            # Try requesting various status updates
            status_fields = ['WORK_STATUS', 'BATTERY_LEVEL', 'ERROR_CODE', 'WORK_MODE']
            for field in status_fields:
                if field in self.dps_map:
                    _LOGGER.debug(f"Requesting {field}")
                    mqtt_logger.debug(f"Status request: DPS {self.dps_map[field]} ({field})")
                    try:
                        await self.send_command({self.dps_map[field]: ""})
                        await asyncio.sleep(0.5)
                    except:
                        pass
            
            _LOGGER.debug("Wake-up nudge attempts completed")
            mqtt_logger.info("=== WAKE-UP SEQUENCE COMPLETED ===")
        except Exception as error:
            _LOGGER.error(f"Error sending wake-up nudge: {error}")
            mqtt_logger.error(f"Wake-up sequence error: {error}")

    def on_message(self, client, userdata, msg: Message):
        """Log everything for debugging and handle messages"""
        try:
            # Log to file instead of HA log
            mqtt_logger.info(f"=== MQTT MESSAGE RECEIVED ===")
            mqtt_logger.info(f"  Topic: {msg.topic}")
            mqtt_logger.info(f"  QoS: {msg.qos}")
            mqtt_logger.info(f"  Retain: {msg.retain}")
            mqtt_logger.info(f"  Payload length: {len(msg.payload)} bytes")
            mqtt_logger.debug(f"  Raw payload (first 200 chars): {str(msg.payload)[:200]}")
            
            # Try to decode as JSON
            try:
                messageParsed = json.loads(msg.payload.decode())
                mqtt_logger.info(f"  Decoded JSON: {json.dumps(messageParsed, indent=2)}")
            except json.JSONDecodeError:
                mqtt_logger.error(f"Failed to decode JSON, raw hex: {msg.payload.hex()}")
                messageParsed = {}
            
            # Track that we received data - still log to HA for basic status
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
                _LOGGER.info(f"DPS data received! Robot appears to be awake. Keys: {list(payload_data.keys())}")
                mqtt_logger.info(f"  DPS Keys found: {list(payload_data.keys())}")
                mqtt_logger.info(f"  DPS Data: {json.dumps(payload_data, indent=2)}")
                
                # Log hex dump of any binary data
                for key, value in payload_data.items():
                    if isinstance(value, (bytes, bytearray)):
                        mqtt_logger.debug(f"  DPS {key} (hex): {value.hex()}")
                    elif isinstance(value, str) and len(value) > 50:
                        mqtt_logger.debug(f"  DPS {key} (truncated): {value[:50]}...")
                
                # Schedule the async function to run in the event loop
                if self._loop and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(
                        self._map_data(payload_data), 
                        self._loop
                    )
                else:
                    _LOGGER.warning("Event loop not available for message processing")
            else:
                mqtt_logger.info("  No DPS data found in message")
                mqtt_logger.debug(f"  Message structure: {list(messageParsed.keys()) if isinstance(messageParsed, dict) else 'not a dict'}")
                
        except Exception as error:
            _LOGGER.error(f'Error processing message: {error}', exc_info=True)
            mqtt_logger.error(f'Error processing message: {error}', exc_info=True)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            _LOGGER.warning('Unexpected MQTT disconnection. Will auto-reconnect')
            mqtt_logger.warning(f'MQTT Disconnected - RC: {rc}')

    async def send_command(self, dataPayload) -> None:
        try:
            if not self.mqttCredentials:
                _LOGGER.error("No MQTT credentials available")
                return
            
            # Log to file
            mqtt_logger.info(f"=== SENDING MQTT COMMAND ===")
            mqtt_logger.info(f"  DPS Payload: {json.dumps(dataPayload, indent=2)}")
            
            # Check for any binary data in the payload
            for key, value in dataPayload.items():
                if isinstance(value, (bytes, bytearray)):
                    mqtt_logger.debug(f"  DPS {key} (hex): {value.hex()}")
                
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
            
            mqtt_logger.debug(f"  Full MQTT packet: {json.dumps(mqttVal, indent=2)}")
            
            topic = f"cmd/eufy_home/{self.deviceModel}/{self.deviceId}/req"
            mqtt_logger.info(f"  Publishing to topic: {topic}")
            
            if self.mqttClient and self.mqttClient.is_connected():
                result = self.mqttClient.publish(topic, json.dumps(mqttVal))
                mqtt_logger.info(f"  Publish result: {result.rc} (0=success)")
                _LOGGER.debug(f"Command sent successfully to {self.deviceId}")
            else:
                _LOGGER.error("MQTT client not connected")
                mqtt_logger.error("MQTT client not connected - command not sent")
        except Exception as error:
            _LOGGER.error(f"Error sending command: {error}", exc_info=True)
            mqtt_logger.error(f"Error sending command: {error}", exc_info=True)
    
    async def test_find_robot(self, value=None):
        """Test find robot command with a specific value - can be called from service"""
        try:
            mqtt_logger.info(f"=== MANUAL FIND ROBOT TEST ===")
            if value is None:
                # Try the most likely candidates
                test_values = [1, True, "1", 2]
                for v in test_values:
                    _LOGGER.info(f"Testing find_robot with value: {v}")
                    mqtt_logger.info(f"Testing find_robot with value: {v}")
                    await self.send_command({self.dps_map['FIND_ROBOT']: v})
                    await asyncio.sleep(3)  # Wait to hear beep
            else:
                _LOGGER.info(f"Testing find_robot with custom value: {value}")
                mqtt_logger.info(f"Testing find_robot with custom value: {value}")
                await self.send_command({self.dps_map['FIND_ROBOT']: value})
        except Exception as e:
            _LOGGER.error(f"Error testing find_robot: {e}")
            mqtt_logger.error(f"Error testing find_robot: {e}")