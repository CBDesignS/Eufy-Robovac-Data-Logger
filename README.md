# Eufy Robovac API Data Logger Integration - RestConnect + Investigation Edition

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger)
[![GitHub Release](https://img.shields.io/github/release/CBDesignS/Eufy-Robovac-Data-Logger.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/releases)

A Home Assistant custom component for debugging Eufy X10 Pro Omni REST API data with enhanced RestConnect support and **Investigation Mode** for comprehensive Key 180 accessory wear analysis.

## 🎯 Purpose

This integration focuses on debugging and logging the REST API data from Eufy X10 Pro Omni devices, with enhanced data collection through RestConnect and deep accessory analysis:

- **🌐 RestConnect**: Advanced REST API client with multiple endpoint support
- **📱 Fallback Mode**: Automatic fallback to basic login if RestConnect fails
- **🔍 Investigation Mode**: Complete Key 180 byte-by-byte analysis for accessory wear research
- **Key 163**: Battery level (NEW Android App - 100% accuracy)
- **Key 167**: Water tank level
- **Key 180**: Accessory wear data with enhanced byte-level analysis
- **Keys 181-190**: Enhanced data from RestConnect endpoints

## 🔍 Investigation Mode - NEW FEATURE

**Investigation Mode** provides comprehensive Key 180 analysis for accessory wear detection research.

### ⚙️ Enabling Investigation Mode

**During Initial Setup (Recommended):**
1. Settings → Devices & Services → Add Integration
2. Search "Eufy Robovac Data Logger"
3. Enter credentials
4. **✅ Check "Investigation Mode"** 
5. Complete setup

**On Existing Integration:**
1. Settings → Devices & Services → Find Integration → Configure
2. **✅ Enable "Investigation Mode"**
3. Save → **Restart Integration**

### 📁 Investigation Files Location

Files are automatically saved to:
```
/config/eufy_investigation/YOUR_DEVICE_ID/
├── key180_baseline_TIMESTAMP.json      ← Pre-cleaning baseline
├── key180_post_cleaning_TIMESTAMP.json ← Post-cleaning comparison  
├── key180_monitoring_TIMESTAMP.json    ← Continuous monitoring
└── session_summary_SESSION_ID.json     ← Analysis summaries
```

### 🎯 Investigation Workflow

1. **Enable Investigation Mode** (see above)
2. **Capture Baseline**: Before cleaning cycle
3. **Run Cleaning**: 5-10 minute room clean
4. **Capture Post-Cleaning**: After robot docks
5. **Analyze Files**: Compare JSON files for byte changes

### 🛠️ Investigation Services

Use these services in Developer Tools → Services:

```yaml
# Capture baseline before cleaning
service: eufy_robovac_data_logger.capture_investigation_baseline
data:
  device_id: "YOUR_DEVICE_ID"

# Capture data after cleaning  
service: eufy_robovac_data_logger.capture_investigation_post_cleaning
data:
  device_id: "YOUR_DEVICE_ID"

# Generate session summary
service: eufy_robovac_data_logger.generate_investigation_summary
data:
  device_id: "YOUR_DEVICE_ID"
```

### 📊 What Investigation Mode Captures

- **Complete byte-by-byte analysis** of Key 180 payload
- **Hex dumps** with position mapping
- **Before/after cleaning comparisons** 
- **Accessory wear change detection** (1-3 byte decreases)
- **Structured JSON** for external analysis tools

For detailed investigation analysis, see **[Investigation Mode Guide](INVESTIGATION.md)** *(coming soon)*

## 🙏 Acknowledgments

Special thanks to the developers who made this integration possible:

- **[jeppesens](https://github.com/jeppesens/eufy-clean)** - For his excellent work cleaning up the Login, Authentication, Device ID handling and removing unused code. His refined codebase provided the solid foundation for this RestConnect implementation.

- **[Martijnpoppen](https://github.com/martijnpoppen/eufy-clean)** - For the hard work in producing the original code to make all this happen. Without his initial research and reverse engineering of the Eufy API, none of this would have been possible.

This RestConnect + Investigation edition builds upon their outstanding contributions to bring enhanced debugging capabilities and comprehensive accessory wear analysis to the Eufy robovac community.

## 🆕 What's New in RestConnect + Investigation Edition

### Enhanced Data Collection
- **Multiple API Endpoints**: Access to device, accessory, consumable, and runtime data
- **Smart Fallback**: Automatically falls back to basic login if REST endpoints fail
- **Investigation Mode**: Complete Key 180 payload analysis for accessory research
- **Reduced Logging**: Detailed logs every 10 minutes to save space
- **Connection Status**: New sensor showing RestConnect vs Basic Login status

### Improved Accessory Tracking
- **Enhanced Byte Analysis**: Better debugging of accessory wear data
- **Multiple Data Sources**: Combines traditional DPS data with REST endpoint data
- **Real-time Detection**: Shows when RestConnect provides additional data
- **JSON Configuration**: User-editable accessory sensor configuration

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

1. Copy the `custom_components/eufy_robovac_data_logger` folder to your `custom_components` directory
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
   - **🔍 Investigation Mode**: Enable Key 180 comprehensive analysis

The integration will automatically:
- Initialize RestConnect for enhanced data collection
- Fall back to basic login if RestConnect fails
- Discover your devices and create appropriate sensors
- Start Investigation Mode logging if enabled

## 📊 Sensors Created

The integration creates 7-8 core sensors + dynamic accessory sensors:

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

#### RestConnect Status Sensor (`sensor.eufy_x10_restconnect_status`)
- **Connection Status**: Connected/Fallback Mode
- **API Endpoints**: Status of all REST endpoints
- **Authentication**: Token status indicators
- **Performance**: Enhanced vs Standard data collection

#### 🔍 Investigation Status Sensor (if Investigation Mode enabled)
- **Investigation Status**: Baseline captured/Monitoring/Waiting
- **Session Information**: Current investigation session details
- **File Locations**: Where investigation files are stored
- **Workflow Instructions**: Step-by-step investigation process

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

## 🔧 Services Available

Investigation Mode adds these services for manual control:

### Investigation Services
- `eufy_robovac_data_logger.capture_investigation_baseline`
- `eufy_robovac_data_logger.capture_investigation_post_cleaning`
- `eufy_robovac_data_logger.generate_investigation_summary`
- `eufy_robovac_data_logger.force_investigation_update`

### Configuration Services  
- `eufy_robovac_data_logger.reload_accessory_config`
- `eufy_robovac_data_logger.update_accessory_life`
- `eufy_robovac_data_logger.debug_key_analysis`

## 🔍 Debugging Features

### Investigation Mode Benefits
- **🔬 Complete Analysis**: Byte-by-byte Key 180 payload examination
- **📊 Structured Data**: JSON files perfect for external analysis
- **🎯 Change Detection**: Automatic before/after comparison
- **📁 Organized Storage**: Session-based file organization
- **🧮 Significance Scoring**: Identifies meaningful byte changes

### Enhanced Logging
- **Detailed Logs**: Every 10 minutes (reduced from 5 minutes)
- **First Update**: Only first update logged in detail
- **Brief Status**: Compact status updates between detailed logs
- **Smart Fallback**: Logs RestConnect failures and automatic fallback

### RestConnect Connection Monitoring
```
Update #5: 🌐 Battery=100%, Speed=max, Keys=14/14, Total=31, Accessories=5
```
- 🌐 = RestConnect active
- 📱 = Basic login fallback
- 🔍 = Investigation Mode active

## 🐛 Enable Debug Logging

Add this to your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.eufy_robovac_data_logger: debug
```

## 📋 Key Findings

Based on extensive protocol analysis:

- **Investigation Mode**: Complete Key 180 analysis for accessory wear research
- **RestConnect Benefits**: Access to additional API endpoints for enhanced data
- **Smart Fallback**: Automatic recovery if advanced endpoints fail
- **Key 163**: Perfect battery source (100% accuracy)
- **Key 180**: Enhanced accessory analysis with multiple data sources
- **Reduced Logging**: 50% less log overhead while maintaining debugging capability

## ⚠️ Important Notes

### Investigation Mode Requirements
- Requires Investigation Mode enabled during setup
- Creates detailed JSON files - monitor disk space usage
- Best used for research and debugging accessory wear patterns
- Files contain comprehensive data for external analysis

### RestConnect Requirements
- Requires stable internet connection for REST API access
- Falls back to basic login if endpoints are unavailable
- Some enhanced features may not be available in fallback mode

### Testing Recommendations
1. **Enable Investigation Mode** for comprehensive accessory analysis
2. **Monitor RestConnect Status** via the dedicated sensor
3. **Run Investigation Workflow** before/after cleaning cycles
4. **Verify Integration Status** through multiple sensor readings

## 📁 File Locations

**Investigation Files**: `/config/eufy_investigation/DEVICE_ID/`
**Accessory Config**: `/config/custom_components/eufy_robovac_data_logger/accessories/sensors_DEVICEID.json`
**Debug Logs**: `/config/logs/eufy_robovac_debug_DEVICEID_TIMESTAMP.log`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both RestConnect and Basic Login modes
5. Test Investigation Mode if adding accessory features
6. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is a debugging integration intended for development purposes. Investigation Mode creates detailed analysis files and may use additional disk space. RestConnect provides enhanced data collection but may have different stability characteristics than basic login. Use at your own risk.

## 🆘 Support

- [GitHub Issues](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/issues)
- [GitHub Discussions](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/discussions)

## 📝 Changelog

### v2.2.0 - Investigation Mode Edition
- ✅ Added Investigation Mode for complete Key 180 analysis
- ✅ Comprehensive byte-by-byte payload examination
- ✅ Before/after cleaning cycle comparison
- ✅ Structured JSON investigation files
- ✅ Manual investigation services for workflow control
- ✅ Session-based analysis and summaries
- ✅ Enhanced accessory wear detection research capabilities

### v2.1.0 - RestConnect Edition  
- ✅ Added RestConnect support with multiple REST API endpoints
- ✅ Smart fallback to basic login if RestConnect fails
- ✅ Reduced logging overhead (detailed logs every 10 minutes)
- ✅ New RestConnect status sensor
- ✅ Enhanced accessory byte analysis
- ✅ Improved connection status indicators
- ✅ Better error handling and recovery
