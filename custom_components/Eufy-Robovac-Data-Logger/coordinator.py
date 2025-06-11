async def _fetch_eufy_data_with_rest(self):
        """Fetch data using RestConnect client with fallback to basic login."""
        try:
            do_detailed = self._should_do_detailed_logging()
            
            if do_detailed:
                self._debug_log("🔄 Fetching data using RestConnect...", "info")
            
            # Try RestConnect first
            if self._rest_client and self._rest_client.is_connected:
                try:
                    # Pass detailed logging flag to RestConnect
                    self._rest_client._detailed_logging_enabled = do_detailed
                    
                    await self._rest_client.updateDevice()
                    rest_data = self._rest_client.get_raw_data()
                    
                    if rest_data:
                        if do_detailed:
                            self._debug_log(f"✅ RestConnect data fetch successful - {len(rest_data)} keys", "info")
                            self._debug_log(f"📊 RestConnect DPS keys: {list(rest_data.keys())}", "info")
                        
                        self.raw_data = rest_data
                        
                        # Log raw data to separate file (only during detailed logging)
                        if do_detailed and self.debug_logger:
                            self.debug_logger.log_raw_data(rest_data)
                        
                        return  # Success with RestConnect
                    else:
                        if do_detailed:
                            self._debug_log("⚠️ RestConnect returned no data, falling back to basic login", "warning", force=True)
                        
                except Exception as rest_error:
                    if do_detailed:
                        self._debug_log(f"⚠️ RestConnect failed: {rest_error}, falling back to basic login", "warning", force=True)
            
            # Fallback to basic login method
            if do_detailed:
                self._debug_log("🔄 Using fallback basic login method...", "info")
            
            # Ensure basic login is available
            if not self._eufy_login:
                from .controllers.login import EufyLogin
                self._eufy_login = EufyLogin(
                    username=self.username,
                    password=self.password,
                    openudid=self.openudid
                )
            
            # Get device data from basic API
            devices = await self._eufy_login.init()
            
            if devices:
                if do_detailed:
                    self._debug_log(f"✅ Fallback API data fetch successful - {len(devices)} devices found", "info")
                
                # Find our specific device
                target_device = None
                for device in devices:
                    if device.get('deviceId') == self.device_id:
                        target_device = device
                        break
                
                if target_device:
                    # Get DPS data from our device
                    dps_data = target_device.get('dps', {})
                    if dps_data:
                        if do_detailed:
                            self._debug_log(f"📊 Fallback DPS data keys found: {list(dps_data.keys())}", "info")
                        self.raw_data = dps_data
                        
                        # Log raw data to separate file (only during detailed logging)
                        if do_detailed and self.debug_logger:
                            self.debug_logger.log_raw_data(dps_data)
                    else:
                        self._debug_log("⚠️ No DPS data found for device", "warning", force=True)
                        self.raw_data = {}
                else:
                    error_msg = f"Target device {self.device_id} not found in device list"
                    self._debug_log(f"❌ {error_msg}", "error", force=True)
                    raise UpdateFailed(error_msg)
            else:
                error_msg = "No devices returned from fallback API"
                self._debug_log(f"❌ {error_msg}", "error", force=True)
                raise UpdateFailed(error_msg)
                
        except Exception as e:
            self._debug_log(f"❌ Failed to fetch Eufy data with RestConnect: {e}", "error", force=True)
            # Clear raw data on API failure
            self.raw_data = {}
            raise