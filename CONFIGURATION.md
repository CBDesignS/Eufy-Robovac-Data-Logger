# Configuration Guide - Eufy Robovac Data Logger

Complete setup instructions for Enhanced Smart Investigation Mode v3.0 with sensors configuration.

## ⚙️ Initial Setup

### Step 1: Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **"Add Integration"** 
3. Search for **"Eufy Robovac Data Logger"**
4. Click on the integration

### Step 2: Enter Credentials

![Credentials Setup](images/setup-credentials.png) *(Screenshot placeholder)*

Enter your Eufy account details:

- **Username/Email**: Your Eufy account email
- **Password**: Your Eufy account password  
- **✅ Debug Mode**: Enable verbose logging (recommended)
- **🔍 Investigation Mode**: Enable Key 180 comprehensive analysis

### Step 3: Device Selection

If multiple devices are found, select your target robovac:

![Device Selection](images/device-selection.png) *(Screenshot placeholder)*

- Choose your target Eufy robovac device
- Integration will show device name and ID

### Step 4: Configuration Complete

![Setup Complete](images/setup-complete.png) *(Screenshot placeholder)*

- Integration status should show **"Configured"**
- Title will include **"(Investigation)"** if Investigation Mode enabled
- All sensors should be created automatically

## 🔍 Investigation Mode Configuration

Investigation Mode enables comprehensive Key 180 analysis for accessory discovery.

### What Investigation Mode Does

- **Captures Key 180 Data**: Complete byte-by-byte analysis of accessory payload
- **Smart Change Detection**: Only logs when meaningful changes occur
- **Self-Contained Files**: Each file includes complete Android app reference data  
- **Template System**: Clean sensors configuration with inheritance
- **Before/After Analysis**: Compare data before and after cleaning cycles

### Investigation Mode Files

Files are automatically created in:
```
/config/eufy_investigation/YOUR_DEVICE_ID/
├── key180_baseline_TIMESTAMP.json         ← Pre-cleaning baseline
├── key180_post_cleaning_TIMESTAMP.json    ← Post-cleaning analysis
├── key180_monitoring_TIMESTAMP.json       ← Change detection logs
└── enhanced_session_summary_SESSION_ID.json ← Complete session analysis
```

### Investigation Status Sensor

Monitor Investigation Mode via:
**`sensor.eufy_robovac_investigation_status`**

![Investigation Status](images/investigation-status.png) *(Screenshot placeholder)*

**Attributes show:**
- Session ID and file locations
- Baseline capture status  
- Available services for manual control
- Workflow instructions
- Current investigation focus (Position 15 = Brush Guard)

## 🔧 Sensors Configuration System

The integration uses a smart template system for sensor configuration.

### Configuration Files

```
/config/custom_components/eufy_robovac_data_logger/accessories/
├── sensors.json                    ← Master template (YOUR CONTROL)
└── sensors_YOUR_DEVICE_ID.json     ← Auto-generated device config
```

### Master Template: sensors.json

This is **YOUR FILE** - edit freely, never overwritten by updates.

**Complete Example Sensor Configuration:**

```json
{
  "device_info": {
    "device_id": "TEMPLATE", 
    "created": "TEMPLATE_CREATED",
    "last_updated": "TEMPLATE_UPDATED",
    "config_version": "2.0",
    "auto_generated": false,
    "template_file": true
  },
  "accessory_sensors": {
    "rolling_brush": {
      "name": "Rolling Brush",                           // ← LEAVE ALONE: Display name
      "description": "Main cleaning brush",             // ← LEAVE ALONE: Description  
      "key": "180",                                     // ← LEAVE ALONE: Always Key 180
      "byte_position": null,                            // ← MODIFY: Set when position found
      "current_life_remaining": 99,                     // ← MODIFY: Real Android app %
      "hours_remaining": 357,                           // ← MODIFY: Calculated from %
      "max_life_hours": 360,                            // ← MODIFY: Total rated hours
      "replacement_threshold": 10,                      // ← MODIFY: Warning threshold %
      "enabled": false,                                 // ← MODIFY: Enable after confirming position
      "auto_update": false,                             // ← LEAVE ALONE: Manual control
      "last_updated": "2025-06-14T00:00:00.000000",    // ← AUTO: Updated automatically
      "notes": "INVESTIGATION MODE: Use files to find position", // ← MODIFY: Your notes
      "investigation_target": true,                     // ← MODIFY: Enable for discovery
      "search_strategy": "find_decreasing_percentage_bytes_after_cleaning" // ← LEAVE ALONE
    },
    
    "side_brush": {
      "name": "Side Brush",                             // ← LEAVE ALONE
      "description": "Edge cleaning brush",            // ← LEAVE ALONE
      "key": "180",                                    // ← LEAVE ALONE
      "byte_position": null,                           // ← MODIFY: Set to discovered position
      "current_life_remaining": 98,                    // ← MODIFY: Real Android app %
      "hours_remaining": 177,                          // ← MODIFY: Based on usage
      "max_life_hours": 180,                           // ← MODIFY: Rated life
      "replacement_threshold": 15,                     // ← MODIFY: Warning level
      "enabled": false,                                // ← MODIFY: Enable when confirmed
      "auto_update": false,                            // ← LEAVE ALONE
      "last_updated": "2025-06-14T00:00:00.000000",   // ← AUTO
      "notes": "Investigate Position 37 area",        // ← MODIFY: Your research notes
      "investigation_target": true,                    // ← MODIFY: Target for discovery
      "search_strategy": "find_decreasing_percentage_bytes_after_cleaning" // ← LEAVE ALONE
    },
    
    "dust_filter": {
      "name": "Dust Filter",                           // ← LEAVE ALONE
      "description": "Air filtration system",         // ← LEAVE ALONE  
      "key": "180",                                    // ← LEAVE ALONE
      "byte_position": null,                           // ← MODIFY: Set when found
      "current_life_remaining": 99,                    // ← MODIFY: Android app value
      "hours_remaining": 357,                          // ← MODIFY: Calculated
      "max_life_hours": 360,                           // ← MODIFY: Filter rated life
      "replacement_threshold": 20,                     // ← MODIFY: When to warn
      "enabled": false,                                // ← MODIFY: Enable after confirmation
      "auto_update": false,                            // ← LEAVE ALONE
      "last_updated": "2025-06-14T00:00:00.000000",   // ← AUTO
      "notes": "Check Position 228 area for matches", // ← MODIFY: Investigation notes
      "investigation_target": true,                    // ← MODIFY
      "search_strategy": "find_decreasing_percentage_bytes_after_cleaning" // ← LEAVE ALONE
    },
    
    "brush_guard": {
      "name": "Brush Guard",                           // ← LEAVE ALONE
      "description": "Protective guard for rolling brush", // ← LEAVE ALONE
      "key": "180",                                    // ← LEAVE ALONE
      "byte_position": 15,                             // ← MODIFY: ✅ CONFIRMED POSITION!
      "current_life_remaining": 97,                    // ← MODIFY: Exact Android app match
      "hours_remaining": 117,                          // ← MODIFY: Based on usage
      "max_life_hours": 120,                           // ← MODIFY: Estimated life
      "replacement_threshold": 10,                     // ← MODIFY: Warning level
      "enabled": true,                                 // ← MODIFY: ✅ ENABLE - Position confirmed!
      "auto_update": false,                            // ← LEAVE ALONE
      "last_updated": "2025-06-14T17:00:00.000000",   // ← AUTO
      "notes": "✅ CONFIRMED: Position 15 = 97% exact match with Android app", // ← MODIFY: Status
      "investigation_target": false,                   // ← MODIFY: Discovery complete
      "search_strategy": "confirmed_position"         // ← MODIFY: Mark as found
    }
  },
  
  "discovery_settings": {
    "enabled_for_discovery": ["181", "182", "183"],   // ← MODIFY: Additional keys to search
    "auto_add_found_sensors": false,                  // ← MODIFY: Manual vs auto sensor creation
    "stop_searching_after_found": true,               // ← LEAVE ALONE: Efficiency setting
    "discovery_timeout_seconds": 300,                 // ← LEAVE ALONE: Search timeout
    "min_updates_before_stop": 5,                     // ← LEAVE ALONE: Stability check
    "last_discovery_run": null                        // ← AUTO: Last discovery attempt
  },
  
  "advanced_settings": {
    "backup_enabled": true,                           // ← LEAVE ALONE: Auto-backup device config
    "auto_backup_interval_hours": 24,                // ← MODIFY: Backup frequency
    "log_accessory_changes": true,                   // ← LEAVE ALONE: Change detection
    "alert_on_low_life": true,                       // ← MODIFY: Enable low-life warnings
    "maintenance_reminder_days": [7, 3, 1],          // ← MODIFY: Warning schedule
    "investigation_mode_settings": {
      "auto_enable_after_position_found": true,      // ← MODIFY: Auto-enable confirmed sensors
      "confidence_threshold_to_enable": 85,          // ← MODIFY: Confidence % needed
      "require_manual_verification": true            // ← MODIFY: Manual vs auto confirmation
    }
  }
}
```

### Field-by-Field Guide

| Field | Action | Description |
|-------|--------|-------------|
| `name` | **LEAVE ALONE** | Display name in Home Assistant |
| `description` | **LEAVE ALONE** | Sensor description |
| `key` | **LEAVE ALONE** | Always "180" for accessories |
| `byte_position` | **🔧 MODIFY** | Set to discovered position (null = unknown) |
| `current_life_remaining` | **🔧 MODIFY** | Real percentage from Android app |
| `hours_remaining` | **🔧 MODIFY** | Calculated from current life |
| `max_life_hours` | **🔧 MODIFY** | Total rated accessory life |
| `replacement_threshold` | **🔧 MODIFY** | Warning threshold percentage |
| `enabled` | **🔧 MODIFY** | Enable only after confirming position |
| `auto_update` | **LEAVE ALONE** | Keep false for manual control |
| `last_updated` | **AUTO** | System managed timestamp |
| `notes` | **🔧 MODIFY** | Your investigation notes |
| `investigation_target` | **🔧 MODIFY** | Include in discovery process |
| `search_strategy` | **LEAVE ALONE** | Algorithm for position finding |

## 🎯 Investigation Workflow

### Phase 1: Baseline Capture

1. **Ensure Investigation Mode Enabled**
   - Check `sensor.eufy_robovac_investigation_status`
   - Status should show "Monitoring" or "Waiting for Data"

2. **Capture Baseline** (before cleaning)
   ```yaml
   service: eufy_robovac_data_logger.capture_investigation_baseline
   data:
     device_id: "YOUR_DEVICE_ID"
   ```

3. **Verify Baseline File Created**
   - Check `/config/eufy_investigation/DEVICE_ID/`
   - Look for `key180_baseline_TIMESTAMP.json`

### Phase 2: Cleaning Cycle Test

1. **Start Cleaning Cycle**
   - Use Eufy app or voice command
   - Run 5-10 minute room cleaning
   - Let robot return to dock

2. **Capture Post-Cleaning Data**
   ```yaml
   service: eufy_robovac_data_logger.capture_investigation_post_cleaning  
   data:
     device_id: "YOUR_DEVICE_ID"
   ```

3. **Verify Post-Cleaning File**
   - New file: `key180_post_cleaning_TIMESTAMP.json`

### Phase 3: Analysis

1. **Generate Session Summary**
   ```yaml
   service: eufy_robovac_data_logger.generate_investigation_summary
   data:
     device_id: "YOUR_DEVICE_ID"
   ```

2. **Review Analysis Files**
   - Each file is self-contained with complete reference data
   - Look for `android_app_comparison` section
   - Check `position_15_focus` for Brush Guard analysis
   - Find exact matches between detected and expected percentages

### Phase 4: Position Confirmation

**When you find a confirmed position:**

1. **Edit sensors.json**:
   ```json
   "brush_guard": {
     "byte_position": 15,              // ← Set discovered position
     "current_life_remaining": 97,     // ← Real Android app value
     "enabled": true,                  // ← Enable the sensor
     "notes": "✅ CONFIRMED: Position 15 = 97% exact match",
     "investigation_target": false     // ← Discovery complete
   }
   ```

2. **Reload Configuration**:
   ```yaml
   service: eufy_robovac_data_logger.reload_accessory_config
   data:
     device_id: "YOUR_DEVICE_ID"
   ```

3. **Test Accuracy**:
   - Monitor sensor values over multiple cleaning cycles
   - Verify values decrease logically after cleaning
   - Compare with Android app regularly

## 📊 Sensor Management

### Accessory Config Manager

Monitor the configuration system via:
**`sensor.eufy_robovac_accessory_config_manager`**

![Accessory Manager](images/accessory-manager.png) *(Screenshot placeholder)*

**Shows:**
- Total accessories configured
- Number of enabled sensors
- Low-life accessory alerts
- Configuration file status
- Template inheritance status

### Manual Life Updates

Update accessory life when you perform maintenance:

```yaml
service: eufy_robovac_data_logger.update_accessory_life
data:
  device_id: "YOUR_DEVICE_ID"
  accessory_id: "rolling_brush"     # sensor ID from config
  life_percentage: 85               # new percentage after maintenance
  notes: "Cleaned rolling brush, removed hair tangles"
```

### Configuration Reload

After editing sensors.json:

```yaml
service: eufy_robovac_data_logger.reload_accessory_config
data:
  device_id: "YOUR_DEVICE_ID"
```

This reloads the template and regenerates the device configuration.

## 🌐 RestConnect Configuration

RestConnect provides enhanced data collection with automatic fallback.

### RestConnect Status

Monitor connection via:
**`sensor.eufy_robovac_restconnect_status`**

![RestConnect Status](images/restconnect-status.png) *(Screenshot placeholder)*

**Connection Modes:**
- **🌐 RestConnect**: Using advanced REST API endpoints
- **📱 Basic Login**: Fallback mode (still fully functional)

**Status Indicators:**
- `is_connected`: RestConnect operational status
- `api_endpoints_available`: Which REST endpoints are working
- `has_auth_token`: Authentication status
- `performance`: Enhanced vs Standard data collection

### RestConnect Benefits

When RestConnect is active:
- **Enhanced Data Sources**: Access to device, accessory, consumable APIs
- **Multiple Endpoints**: Combines data from various Eufy services
- **Better Accuracy**: Cross-validation between data sources
- **Investigation Enhancement**: More comprehensive Key 180 analysis

### Automatic Fallback

If RestConnect fails:
- **Seamless Switch**: Automatic fallback to basic login
- **No Data Loss**: All sensors continue working
- **Background Recovery**: RestConnect retries periodically
- **User Notification**: Status sensor shows current mode

## 🔍 Debug and Troubleshooting

### Debug Logging

Enable detailed logging in `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.eufy_robovac_data_logger: debug
```

### Investigation Mode Debug Files

Investigation Mode creates separate detailed logs:

**Location**: `/config/logs/eufy_robovac_debug_DEVICEID_TIMESTAMP.log`

**Contents**:
- Complete Key 180 analysis process
- Byte-by-byte change detection
- Android app comparison results
- Position discovery attempts
- Template inheritance status

### Common Issues

#### Investigation Files Not Created
1. **Check Investigation Mode**: Verify enabled in integration options
2. **Check Key 180 Data**: Sensor must receive Key 180 from device
3. **Check Permissions**: Ensure HA can write to `/config/eufy_investigation/`
4. **Check Disk Space**: Investigation files need storage space

#### Sensors Not Appearing
1. **Check Template**: Verify `sensors.json` has valid JSON syntax
2. **Check Inheritance**: Look for `sensors_DEVICEID.json` file creation
3. **Check Enable Status**: Sensors start disabled - enable after position confirmation
4. **Reload Config**: Use reload service after template changes

#### Position Discovery Issues
1. **Android App Sync**: Ensure your percentages in template match app exactly
2. **Cleaning Cycle**: Must run actual cleaning for wear detection
3. **Timing**: Capture post-cleaning data immediately after docking
4. **Multiple Tests**: Run several cleaning cycles to confirm patterns

### Sensor Validation

Check sensor accuracy by comparing with Android app:

**`sensor.eufy_robovac_debug_monitoring`** shows:
- Key coverage percentage
- Found vs missing keys
- Data source (RestConnect vs Basic Login)

**Individual accessory sensors** show:
- `detected_value`: What integration found in byte data
- `configured_life`: What you set in sensors.json
- `detection_accuracy`: How well they match

## 🎯 Advanced Configuration

### Multiple Device Support

Each device gets its own configuration:
```
/config/custom_components/eufy_robovac_data_logger/accessories/
├── sensors.json                    ← Master template
├── sensors_DEVICE1_ID.json         ← Device 1 config  
├── sensors_DEVICE2_ID.json         ← Device 2 config
└── sensors_DEVICE3_ID.json         ← Device 3 config
```

Each inherits from the same `sensors.json` template but maintains separate:
- Byte positions (may differ between models)
- Current life percentages
- Last updated timestamps
- Discovery status

### Custom Discovery Keys

Add additional keys to search in `sensors.json`:

```json
"discovery_settings": {
  "enabled_for_discovery": [
    "181", "182", "183", "184", "185",  // Standard enhanced keys
    "190", "191", "192"                 // Custom additional keys
  ],
  "auto_add_found_sensors": false,      // Manual control recommended
  "discovery_timeout_seconds": 600      // Longer search time
}
```

### Advanced Investigation Settings

Fine-tune investigation behavior:

```json
"advanced_settings": {
  "investigation_mode_settings": {
    "auto_enable_after_position_found": false,  // Manual enable only
    "confidence_threshold_to_enable": 95,       // Higher confidence required
    "require_manual_verification": true,        // Always require manual check
    "max_position_candidates": 10,              // Limit search scope
    "significant_change_threshold": 2           // Sensitivity for change detection
  }
}
```

## 📋 Integration Options

### Modifying Integration Settings

1. **Go to Settings** → **Devices & Services**
2. **Find your integration** → Click **"Configure"**
3. **Modify options**:

![Integration Options](images/integration-options.png) *(Screenshot placeholder)*

**Available Options:**
- **🐛 Debug Mode**: Enable/disable detailed logging
- **🔍 Investigation Mode**: Enable/disable Key 180 analysis

4. **Save changes** → Integration automatically reloads

### Investigation Mode Toggle

**Enabling Investigation Mode**:
- Creates investigation directory structure
- Starts Key 180 data capture
- Enables enhanced smart logging
- Creates investigation status sensor

**Disabling Investigation Mode**:
- Stops Key 180 analysis (keeps existing files)
- Removes investigation status sensor
- Reduces system resource usage
- Basic sensors continue working normally

## 🔄 Maintenance Tasks

### Regular Maintenance

**Weekly:**
- Check sensor accuracy vs Android app
- Update accessory life percentages after cleaning
- Review investigation files for new discoveries

**Monthly:**
- Update `current_life_remaining` in sensors.json with real values
- Clean up old investigation files (auto-cleanup enabled by default)
- Verify template inheritance working correctly

**After Accessory Replacement:**
1. Update sensors.json with new 100% values
2. Reset `hours_remaining` to `max_life_hours`
3. Update `last_updated` timestamp
4. Reload configuration

### File Management

**Investigation Files**: Auto-cleanup keeps last 10 monitoring files per session

**Manual Cleanup**:
```bash
# Keep only last 30 days of investigation files
find /config/eufy_investigation -name "*.json" -mtime +30 -delete
```

**Backup Important Files**:
- Always backup your customized `sensors.json`
- Investigation baseline files are valuable for research
- Session summaries contain comprehensive analysis

## 🎉 Success Criteria

### Position Discovery Success

You've successfully discovered an accessory position when:

1. **Exact Match**: Detected value matches Android app exactly
2. **Logical Decrease**: Value decreases by 1-3% after cleaning cycles  
3. **Consistency**: Multiple cleaning cycles show same pattern
4. **Stability**: Value doesn't change randomly between cleanings

### Integration Health

Your integration is healthy when:

1. **All Core Sensors Working**: Battery, speed, monitoring sensors active
2. **RestConnect or Fallback**: Either mode working reliably
3. **Template Inheritance**: Device config properly inherits from template
4. **Investigation Files**: Regular capture without errors (if enabled)

### Accessory Tracking Accuracy

Your accessory tracking is accurate when:

1. **App Synchronization**: Sensor values match Android app within 2%
2. **Wear Detection**: Values decrease logically after usage
3. **Threshold Alerts**: Low-life warnings trigger appropriately
4. **Maintenance Tracking**: Manual updates reflect real maintenance

---

## [← Back to README](README.md) | [Installation Guide ←](INSTALLATION.md)

---

🔧 **Configuration Complete**: Enhanced Smart Investigation Mode v3.0 ready

📊 **Sensors Configured**: Template inheritance system operational  

🎯 **Discovery Ready**: Position discovery workflow prepared for testing
