async def updateDevice(self, force_update: bool = False):
        """
        Production device data update from multiple REST API sources.
        Combines traditional DPS data with new accessory/consumable data from REST endpoints.
        REDUCED LOGGING: Only log REST attempts during detailed logging periods.
        """
        try:
            if not self.is_connected and not force_update:
                # Only log this during detailed periods
                if self.debug_logger and hasattr(self.debug_logger, '_should_log_detailed'):
                    self._log_warning("⚠️ Not connected, skipping update")
                return
            
            self.update_count += 1
            
            # Only log REST API attempts during detailed logging (every 10 minutes)
            detailed_logging = self._should_log_detailed()
            
            if detailed_logging:
                self._log_info(f"🔄 UPDATE #{self.update_count} STARTING")
            
            # STEP 1: Get traditional device data (DPS-style)
            device_data = await self._fetch_device_data(detailed_logging)
            
            # STEP 2-4: Only try REST endpoints during detailed logging
            accessory_data = None
            consumable_data = None  
            runtime_data = None
            
            if detailed_logging:
                # Get enhanced accessory data from REST endpoints
                accessory_data = await self._fetch_accessory_data()
                # Get consumable/wear data from new REST endpoints  
                consumable_data = await self._fetch_consumable_data()
                # Get runtime/usage data
                runtime_data = await self._fetch_runtime_data()
            
            # STEP 5: Combine all data sources
            combined_data = await self._combine_data_sources(
                device_data, accessory_data, consumable_data, runtime_data, detailed_logging
            )
            
            if combined_data:
                self.raw_data = combined_data
                self.last_update = time.time()
                
                if detailed_logging:
                    self._log_debug_data()
                    self._log_info(f"✅ Update #{self.update_count} completed - {len(self.raw_data)} total keys")
            else:
                if detailed_logging:
                    self._log_warning("⚠️ No data received from any source")
                # Clear raw data if no valid data received
                self.raw_data = {}
                
        except Exception as e:
            # Always log errors
            self._log_error(f"❌ Update #{self.update_count} failed: {e}")
            # Clear raw data on update failure
            self.raw_data = {}
            # Don't raise exception, just log it to keep integration running

    def _should_log_detailed(self) -> bool:
        """Check if we should do detailed logging (every 10 minutes)."""
        # This will be set by the coordinator
        if hasattr(self, '_detailed_logging_enabled'):
            return self._detailed_logging_enabled
        return False

    async def _fetch_device_data(self, detailed_logging: bool = False) -> Optional[Dict]:
        """Fetch traditional device data (DPS-style) from REST API endpoint."""
        try:
            if not self.session:
                await self._create_session()
            
            # Prepare request data for Clean/Home API
            request_data = {
                "device_id": self.device_id,
                "time_zone": 0,
                "transaction": str(int(time.time() * 1000))
            }
            
            if detailed_logging:
                self._log_debug("📡 Making device data REST API call")
                self._log_debug(f"🌐 URL: {self.device_data_url}")
            
            async with self.session.post(self.device_data_url, json=request_data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if detailed_logging:
                        self._log_debug("✅ Device data REST API call successful")
                    return response_data
                else:
                    # Try alternative endpoint
                    return await self._fetch_device_data_alternative(detailed_logging)
                    
        except Exception as e:
            if detailed_logging:
                self._log_error(f"❌ Device data REST API request failed: {e}")
            return None

    async def _fetch_device_data_alternative(self, detailed_logging: bool = False) -> Optional[Dict]:
        """Fetch device data from alternative Clean API endpoint."""
        try:
            request_data = {
                "device_sn": self.device_id,
                "attribute": 3,
                "timestamp": int(time.time() * 1000)
            }
            
            if detailed_logging:
                self._log_debug("📡 Trying alternative Clean API endpoint")
                self._log_debug(f"🌐 URL: {self.clean_device_info_url}")
            
            async with self.session.post(self.clean_device_info_url, json=request_data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if detailed_logging:
                        self._log_debug("✅ Alternative device data API call successful")
                    return response_data
                else:
                    if detailed_logging:
                        error_text = await response.text()
                        self._log_debug(f"⚠️ Alternative API call failed: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            if detailed_logging:
                self._log_error(f"❌ Alternative device data request failed: {e}")
            return None

    async def _fetch_accessory_data(self) -> Optional[Dict]:
        """Fetch accessory/consumable data from new REST endpoints (moved from MQTT)."""
        try:
            self._log_debug("🔧 Fetching accessory data from REST endpoint")
            
            request_data = {
                "device_id": self.device_id,
                "data_type": "accessory_status",
                "include_wear_data": True,
                "timestamp": int(time.time() * 1000)
            }
            
            async with self.session.post(self.accessory_data_url, json=request_data) as response:
                if response.status == 200:
                    accessory_data = await response.json()
                    self._log_debug("✅ Accessory data retrieved from REST endpoint")
                    return accessory_data
                else:
                    # Try alternative Clean API endpoint for accessory data
                    return await self._fetch_accessory_data_alternative()
                    
        except Exception as e:
            self._log_debug(f"⚠️ Accessory data REST request failed: {e}")
            return None

    async def _fetch_accessory_data_alternative(self) -> Optional[Dict]:
        """Fetch accessory data from Clean API endpoint."""
        try:
            request_data = {
                "device_sn": self.device_id,
                "accessory_types": ["brush", "filter", "mop", "sensor"],
                "include_usage": True
            }
            
            self._log_debug("🔧 Trying alternative Clean API for accessory data")
            
            async with self.session.post(self.clean_accessory_url, json=request_data) as response:
                if response.status == 200:
                    accessory_data = await response.json()
                    self._log_debug("✅ Alternative accessory data retrieved")
                    return accessory_data
                else:
                    self._log_debug(f"⚠️ Alternative accessory API failed: {response.status}")
                    return None
                    
        except Exception as e:
            self._log_debug(f"⚠️ Alternative accessory request failed: {e}")
            return None

    async def _fetch_consumable_data(self) -> Optional[Dict]:
        """Fetch consumable/wear level data from REST endpoints."""
        try:
            self._log_debug("🧽 Fetching consumable wear data from REST endpoint")
            
            request_data = {
                "device_id": self.device_id,
                "consumable_types": ["all"],
                "usage_data": True,
                "wear_levels": True
            }
            
            async with self.session.post(self.consumable_data_url, json=request_data) as response:
                if response.status == 200:
                    consumable_data = await response.json()
                    self._log_debug("✅ Consumable wear data retrieved from REST endpoint")
                    return consumable_data
                else:
                    self._log_debug(f"⚠️ Consumable data API call failed: {response.status}")
                    return None
                    
        except Exception as e:
            self._log_debug(f"⚠️ Consumable data request failed: {e}")
            return None

    async def _fetch_runtime_data(self) -> Optional[Dict]:
        """Fetch runtime/usage statistics from REST endpoints."""
        try:
            self._log_debug("⏱️ Fetching runtime data from REST endpoint")
            
            request_data = {
                "device_id": self.device_id,
                "runtime_types": ["cleaning", "accessories", "maintenance"],
                "period": "all"
            }
            
            async with self.session.post(self.runtime_data_url, json=request_data) as response:
                if response.status == 200:
                    runtime_data = await response.json()
                    self._log_debug("✅ Runtime data retrieved from REST endpoint")
                    return runtime_data
                else:
                    self._log_debug(f"⚠️ Runtime data API call failed: {response.status}")
                    return None
                    
        except Exception as e:
            self._log_debug(f"⚠️ Runtime data request failed: {e}")
            return None

    async def _combine_data_sources(self, device_data: Optional[Dict], 
                                   accessory_data: Optional[Dict],
                                   consumable_data: Optional[Dict], 
                                   runtime_data: Optional[Dict],
                                   detailed_logging: bool = False) -> Optional[Dict]:
        """Combine data from multiple REST API sources into unified DPS-like format."""
        try:
            combined_data = {}
            
            # STEP 1: Extract traditional DPS data
            if device_data:
                dps_data = self._extract_dps_data(device_data)
                if dps_data:
                    combined_data.update(dps_data)
                    if detailed_logging:
                        self._log_debug(f"📊 Traditional DPS data: {len(dps_data)} keys")
            
            # STEP 2-4: Only process REST data if we have it (detailed logging periods)
            if accessory_data:
                accessory_dps = self._convert_accessory_to_dps(accessory_data)
                combined_data.update(accessory_dps)
                if detailed_logging:
                    self._log_debug(f"🔧 Accessory data converted: {len(accessory_dps)} keys")
            
            if consumable_data:
                consumable_dps = self._convert_consumable_to_dps(consumable_data)
                combined_data.update(consumable_dps)
                if detailed_logging:
                    self._log_debug(f"🧽 Consumable data converted: {len(consumable_dps)} keys")
            
            if runtime_data:
                runtime_dps = self._convert_runtime_to_dps(runtime_data)
                combined_data.update(runtime_dps)
                if detailed_logging:
                    self._log_debug(f"⏱️ Runtime data converted: {len(runtime_dps)} keys")
            
            # Return combined data (may be empty if no sources provided data)
            if combined_data:
                if detailed_logging:
                    self._log_info(f"🔗 Combined data sources: {len(combined_data)} total keys")
            else:
                if detailed_logging:
                    self._log_warning("⚠️ No real data from any REST API source")
            
            return combined_data if combined_data else None
            
        except Exception as e:
            if detailed_logging:
                self._log_error(f"❌ Error combining data sources: {e}")
            return None