# Installation Guide - Eufy Robovac Data Logger

This guide covers complete installation of the Eufy Robovac Data Logger integration with Enhanced Smart Investigation Mode v3.0.

## 📥 HACS Installation (Recommended)

### Prerequisites
- Home Assistant with HACS installed
- Eufy account credentials
- Compatible Eufy robovac device

### Step 1: Add Custom Repository

1. Open **HACS** in Home Assistant
2. Click on **"Integrations"**
3. Click the **three dots** in the top right corner
4. Select **"Custom repositories"**
5. Add this repository URL:
   ```
   https://github.com/CBDesignS/Eufy-Robovac-Data-Logger
   ```
6. Select **"Integration"** as the category
7. Click **"Add"**

### Step 2: Install Integration

1. Find **"Eufy Robovac Data Logger"** in HACS
2. Click **"Download"**
3. **Restart Home Assistant**

### Step 3: Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **"Add Integration"**
3. Search for **"Eufy Robovac Data Logger"**
4. Follow the configuration steps (see [Configuration Guide →](CONFIGURATION.md))

## 🛠️ Manual Installation

### Step 1: Download Files

1. Download the latest release from [GitHub Releases](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/releases)
2. Extract the ZIP file

### Step 2: Copy Files

1. Copy the `custom_components/eufy_robovac_data_logger` folder to your Home Assistant `custom_components` directory:
   ```
   /config/custom_components/eufy_robovac_data_logger/
   ```

2. Your directory structure should look like:
   ```
   /config/
   ├── custom_components/
   │   └── eufy_robovac_data_logger/
   │       ├── __init__.py
   │       ├── manifest.json
   │       ├── config_flow.py
   │       ├── coordinator.py
   │       ├── sensor.py
   │       ├── services.yaml
   │       ├── const.py
   │       ├── strings.json
   │       ├── enhanced_smart_investigation_logger.py
   │       ├── accessory_config_manager.py
   │       ├── async_debug_logger.py
   │       ├── controllers/
   │       │   ├── __init__.py
   │       │   ├── base.py
   │       │   ├── eufy_api.py
   │       │   ├── login.py
   │       │   └── rest_connect.py
   │       ├── accessories/
   │       │   └── sensors.json
   │       └── constants/
   │           ├── __init__.py
   │           ├── devices.py
   │           └── state.py
   ```

### Step 3: Restart and Configure

1. **Restart Home Assistant**
2. Go to **Settings** → **Devices & Services**
3. Click **"Add Integration"**
4. Search for **"Eufy Robovac Data Logger"**
5. Follow the configuration steps

## 🔧 Dependencies

The integration automatically installs these Python packages:

- `paho-mqtt>=1.6.1` - MQTT communication
- `protobuf>=3.20.0` - Protocol buffer support  
- `aiofiles>=23.1.0` - Async file operations for Investigation Mode

## ✅ Verification

After installation, verify everything is working:

### 1. Check Integration Status
- Go to **Settings** → **Devices & Services**
- Find **"Eufy Robovac Data Logger"** 
- Status should show **"Configured"**

### 2. Check Created Sensors
You should see these sensors created:
- `sensor.eufy_robovac_debug_battery` ✅ Working
- `sensor.eufy_robovac_debug_clean_speed` ✅ Working  
- `sensor.eufy_robovac_debug_raw_data` ✅ Working
- `sensor.eufy_robovac_debug_monitoring` ✅ Working
- `sensor.eufy_robovac_accessory_config_manager` 🔧 Config system
- `sensor.eufy_robovac_restconnect_status` 🌐 Connection status

### 3. Investigation Mode (if enabled)
- `sensor.eufy_robovac_investigation_status` 🔍 Investigation control
- Investigation files in `/config/eufy_investigation/DEVICE_ID/`

### 4. Check Services
Available services should include:
- `eufy_robovac_data_logger.capture_investigation_baseline`
- `eufy_robovac_data_logger.capture_investigation_post_cleaning` 
- `eufy_robovac_data_logger.generate_investigation_summary`
- `eufy_robovac_data_logger.reload_accessory_config`

## 🔍 Investigation Mode Setup

If you enabled Investigation Mode during setup:

### Automatic File Creation
The integration creates:
```
/config/eufy_investigation/YOUR_DEVICE_ID/
└── (Investigation files will appear here automatically)

/config/custom_components/eufy_robovac_data_logger/accessories/
├── sensors.json (Template with Android app percentages)
└── sensors_YOUR_DEVICE_ID.json (Generated device config)
```

### Template Inheritance System
- **sensors.json**: Master template with real Android app percentages
- **sensors_DEVICE_ID.json**: Auto-generated device config inheriting template values
- Perfect inheritance system preserves your template customizations

## 🚨 Troubleshooting Installation

### Integration Not Found
- Ensure you restarted Home Assistant after copying files
- Check file permissions (readable by `homeassistant` user)
- Verify directory structure matches exactly

### Login Issues
- Verify Eufy account credentials
- Check internet connectivity
- Try disabling 2FA temporarily during setup

### Missing Sensors
- Wait 1-2 minutes for initial data fetch
- Check **Developer Tools** → **States** for sensor entities
- Review logs: **Settings** → **System** → **Logs**

### Investigation Mode Issues
- Ensure Investigation Mode was enabled during setup
- Check `/config/eufy_investigation/` directory exists
- Verify sensors.json template is valid JSON

### RestConnect Issues
- RestConnect automatically falls back to basic login if endpoints fail
- Check `sensor.eufy_robovac_restconnect_status` for connection details
- Both RestConnect and basic login provide full functionality

## 📋 Debug Logging

To enable detailed logging for troubleshooting:

```yaml
# Add to configuration.yaml
logger:
  default: info
  logs:
    custom_components.eufy_robovac_data_logger: debug
```

**Restart Home Assistant** after adding logging configuration.

### Investigation Mode Logging
Investigation Mode creates separate log files:
- **Location**: `/config/logs/eufy_robovac_debug_DEVICEID_TIMESTAMP.log`
- **Content**: Detailed Key 180 analysis and discovery process
- **Purpose**: Avoid spamming main Home Assistant log

## 🎯 Next Steps

After successful installation:

1. **[Configure Your Integration →](CONFIGURATION.md)** - Setup Investigation Mode and sensors
2. **Test Basic Functionality** - Check battery and speed sensors work
3. **Enable Investigation Mode** - Start discovering accessory positions
4. **Run Cleaning Test** - Capture before/after data for analysis

## 🔄 Updating

### HACS Update
1. HACS will notify you of updates
2. Click **"Update"** 
3. **Restart Home Assistant**

### Manual Update
1. Download new release
2. Replace files in `custom_components/eufy_robovac_data_logger/`
3. **Restart Home Assistant**

⚠️ **Important**: Your sensors.json template and investigation files are never overwritten during updates.

---

## [← Back to README](README.md) | [Configuration Guide →](CONFIGURATION.md)

---

📊 **Installation Complete**: Ready for Enhanced Smart Investigation Mode v3.0

🌐 **RestConnect Ready**: Automatic fallback ensures reliable operation

🔍 **Investigation Mode**: Template system ready for accessory discovery
