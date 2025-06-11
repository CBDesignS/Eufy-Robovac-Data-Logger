# Eufy Robovac API Data Logger Integration - RestConnect Edition

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger)
[![GitHub Release](https://img.shields.io/github/release/CBDesignS/Eufy-Robovac-Data-Logger.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/releases)

A Home Assistant custom component for debugging Eufy X10 Pro Omni REST API data with enhanced RestConnect support. This integration now includes advanced REST API endpoints for improved accessory tracking and debugging capabilities.

## 🎯 Purpose

This integration focuses on debugging and logging the REST API data from Eufy X10 Pro Omni devices, with enhanced data collection through RestConnect:

- **🌐 RestConnect**: Advanced REST API client with multiple endpoint support
- **📱 Fallback Mode**: Automatic fallback to basic login if RestConnect fails
- **Key 163**: Battery level (NEW Android App - 100% accuracy)
- **Key 167**: Water tank level
- **Key 180**: Accessory wear data with enhanced byte-level analysis
- **Keys 181-190**: Enhanced data from RestConnect endpoints

## 🙏 Acknowledgments

Special thanks to the developers who made this integration possible:

- **[jeppesens](https://github.com/jeppesens/eufy-clean)** - For his excellent work cleaning up the Login, Authentication, Device ID handling and removing unused code. His refined codebase provided the solid foundation for this RestConnect implementation.

- **[Martijnpoppen](https://github.com/martijnpoppen/eufy-clean)** - For the hard work in producing the original code to make all this happen. Without his initial research and reverse engineering of the Eufy API, none of this would have been possible.

This RestConnect edition builds upon their outstanding contributions to bring enhanced debugging capabilities and improved data collection to the Eufy robovac community.

## 🆕 What's New in RestConnect Edition

### Enhanced Data Collection
- **Multiple API Endpoints**: Access to device, accessory, consumable, and runtime data
- **Smart Fallback**: Automatically falls back to basic login if REST endpoints fail
- **Reduced Logging**: Detailed logs every 10 minutes to save space 1 full dps log and 1 full rest log
- **Connection Status**: New sensor showing RestConnect vs Basic Login status

### Improved Accessory Tracking
- **Enhanced Byte Analysis**: Better debugging of accessory wear data
- **Multiple Data Sources**: Combines traditional DPS data with REST endpoint data
- **Real-time Detection**: Shows when RestConnect provides additional data if and when it becomes active again !!

## 📥 Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/CBDesignS/Eufy-Robovac-Data-Logger`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Eufy Robovac Data Logger" in HACS and install it
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/Eufy-Robovac-Data-Logger` folder to your `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations > Add Integration > "Eufy Robovac Data Logger"

## ⚙️ Configuration

1. Go to Configuration > Integrations
2. Click "Add Integration"
3. Search for "Eufy Robovac Data Logger"
4. Enter your credentials:
   - **Username**: Your Eufy account username
   - **Password**: Your Eufy account password
   - **Debug Mode**: Enable verbose logging (recommended)

The integration will automatically:
- Initialize RestConnect for enhanced data collection
- Fall back to basic login if RestConnect fails
- Discover your devices and create appropriate sensors

## 📊 Sensors Created

The integration creates 7 core sensors + dynamic accessory sensors:

### Core Sensors

#### Battery Sensor (`sensor.eufy_x10_debug_battery`)
- **Source**: Key 163 (NEW Android App)
- **Accuracy**: 100% (Perfect match)
- **Data Source**: RestConnect or Basic Login

#### Clean Speed Sensor (`sensor.eufy_x10_debug_clean_speed`)
- **Source**: Key 158
- **Values**: quiet/standard/turbo/max
- **Data Source**: RestConnect or Basic Login

#### Raw Data Sensor (`sensor.eufy_x10_debug_raw_data`)
- Shows total number of API keys received
- Indicates data source (RestConnect vs Basic Login)
- Attributes contain raw API data (truncated for safety)

#### Monitoring Sensor (`sensor.eufy_x10_debug_monitoring`)
- Shows coverage: "X/Y" keys found
- Detailed status of all monitored keys
- Data source tracking

#### Accessory Manager Sensor (`sensor.eufy_x10_accessory_config_manager`)
- Shows number of configured accessories
- Status of JSON configuration system
- Low-life accessory alerts

#### 🆕 RestConnect Status Sensor (`sensor.eufy_x10_restconnect_status`)
- **Connection Status**: Connected/Fallback Mode
- **API Endpoints**: Status of all REST endpoints
- **Authentication**: Token status indicators
- **Performance**: Enhanced vs Standard data collection

### Dynamic Accessory Sensors
Automatically created from JSON configuration:
- Rolling Brush Life
- Side Brush Life  
- HEPA Filter Life
- Mop Cloth Life
- Sensor/Cliff Sensors Life
- Water Tank Level (testing)

## 🌐 RestConnect vs Basic Login

### RestConnect Mode (🌐)
- **Enhanced Data**: Access to additional REST API endpoints
- **Multiple Sources**: Device, accessory, consumable, and runtime APIs
- **Better Accuracy**: Combines multiple data sources for improved reliability
- **Future-Proof**: Ready for new Eufy API features

### Basic Login Fallback (📱)
- **Reliable**: Uses proven DPS data extraction
- **Compatible**: Works with all Eufy devices
- **Stable**: Automatic fallback if RestConnect fails

## 🔍 Debugging Features

### Reduced Logging Overhead
- **Detailed Logs**: Every 10 minutes (reduced from 5 minutes)
- **First Update**: Only first update logged in detail (reduced from 3)
- **Brief Status**: Compact status updates between detailed logs
- **Smart Fallback**: Logs RestConnect failures and automatic fallback

### Enhanced Byte Analysis
- **Accessory Detection**: Enhanced debugging of Key 180 byte positions
- **Water Tank**: Testing multiple byte positions for accurate detection
- **Change Detection**: Monitors for accessory wear changes between updates

### RestConnect Connection Monitoring
```
Update #5: 🌐 Battery=100%, Speed=max, Keys=14/14, Total=31, Accessories=5
```
- 🌐 = RestConnect active
- 📱 = Basic login fallback

## 🛠️ For Developers

### RestConnect Architecture
The integration uses a layered approach:

1. **RestConnect Client**: Primary data source with multiple REST endpoints
2. **EufyLogin**: Fallback authentication and basic DPS data
3. **Smart Coordinator**: Manages connection switching and data processing

### Key Code Changes
- `coordinator.py`: Now uses RestConnect with automatic fallback
- `sensor.py`: Added RestConnect status sensor
- `const.py`: Added RestConnect-specific constants
- Logging reduced to save disk space

### API Endpoints Used
```python
RESTCONNECT_ENDPOINTS = {
    "device_data": "https://api.eufylife.com/v1/device/info",
    "accessory_data": "https://api.eufylife.com/v1/device/accessory_info", 
    "consumable_data": "https://api.eufylife.com/v1/device/consumable_status",
    "runtime_data": "https://api.eufylife.com/v1/device/runtime_info",
    "clean_accessory": "https://aiot-clean-api-pr.eufylife.com/app/device/get_accessory_data"
}
```

## 📋 Testing the RestConnect Update

### Immediate Testing
1. **Install the Update**: Upload the new files and restart HA
2. **Check Sensor Status**: Look for "RestConnect Status" sensor
3. **Monitor Data Source**: Raw Data sensor shows "RestConnect" or "Basic Login"
4. **Verify Fallback**: If RestConnect fails, integration should continue with Basic Login

### Accessory Testing Workflow
1. **Check Current State**: Note accessory percentages in JSON config
2. **Run Cleaning Cycle**: 5-10 minute room clean
3. **Monitor for Changes**: Check logs for byte-level changes in Key 180
4. **Compare Before/After**: Look for 1-2% decreases in accessory wear

## 🐛 Enable Debug Logging

Add this to your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.Eufy-Robovac-Data-Logger: debug
```

## 📋 Key Findings

Based on extensive protocol analysis:

- **RestConnect Benefits**: Access to additional API endpoints for enhanced data
- **Smart Fallback**: Automatic recovery if advanced endpoints fail
- **Key 163**: Perfect battery source (100% accuracy)
- **Key 180**: Enhanced accessory analysis with multiple data sources
- **Reduced Logging**: 50% less log overhead while maintaining debugging capability

## ⚠️ Important Notes

### RestConnect Requirements
- Requires stable internet connection for REST API access
- Falls back to basic login if endpoints are unavailable
- Some enhanced features may not be available in fallback mode

### Testing Recommendations
1. **Monitor RestConnect Status**: Check the new sensor for connection health
2. **Compare Data Sources**: Note differences between RestConnect and Basic Login
3. **Test Fallback**: Verify integration continues working if RestConnect fails
4. **Accessory Tracking**: Run cleaning cycles to test wear detection

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both RestConnect and Basic Login modes
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is a debugging integration intended for development purposes. RestConnect provides enhanced data collection but may have different stability characteristics than basic login. Use at your own risk.

## 🆘 Support

- [GitHub Issues](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/issues)
- [GitHub Discussions](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/discussions)

## 🙏 Acknowledgments

## 🙏 Acknowledgments

Special thanks to the developers who made this integration possible:

- **[jeppesens](https://github.com/jeppesens/eufy-clean)** - For his excellent work cleaning up the Login, Authentication, Device ID handling and removing unused code. His refined codebase provided the solid foundation for this RestConnect implementation.

- **[Martijnpoppen](https://github.com/martijnpoppen/eufy-clean)** - For the hard work in producing the original code to make all this happen. Without his initial research and reverse engineering of the Eufy API, none of this would have been possible.

This RestConnect edition builds upon their outstanding contributions to bring enhanced debugging capabilities and improved data collection to the Eufy robovac community.

Based on research into the NEW Android Eufy app protocol and REST API data sources, with enhanced RestConnect support for improved debugging capabilities.

## 📝 Changelog

### v2.1.0 - RestConnect Edition
- ✅ Added RestConnect support with multiple REST API endpoints
- ✅ Smart fallback to basic login if RestConnect fails
- ✅ Reduced logging overhead (detailed logs every 10 minutes)
- ✅ New RestConnect status sensor
- ✅ Enhanced accessory byte analysis
- ✅ Improved connection status indicators
- ✅ Better error handling and recovery
