# Eufy Robovac API Data Logger - Investigation Edition

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger)
[![GitHub Release](https://img.shields.io/github/release/CBDesignS/Eufy-Robovac-Data-Logger.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/releases)

A Home Assistant custom component for comprehensive Eufy Robovac API debugging with **Enhanced Smart Investigation Mode v4.0** for accessory wear detection research.

## 🎯 What This Integration Does

This integration is specifically designed for **debugging and research** of Eufy robovac API data, with advanced features for discovering accessory sensor byte positions:

### 🔍 Enhanced Smart Investigation Mode v4.0
- **Complete Multi-Key Analysis**: Comprehensive analysis of all monitored keys with smart change detection
- **Self-Contained Files**: Every analysis file includes complete Android app reference data
- **Smart Change Detection**: Only logs meaningful changes, reducing file bloat by 80-90%
- **Position Discovery**: Automated analysis to find correct accessory sensor byte positions
- **Before/After Cleaning**: Capture baseline and post-cleaning data for wear detection

### 📊 Proven Data Sources (DPS-Only Architecture)
- **Key 163**: Battery level (100% accuracy confirmed)
- **Key 158**: Clean speed (confirmed working)
- **Key 180**: Complete accessory wear data with smart investigation
- **Keys 152-190**: All monitored keys analyzed for comprehensive debugging
- **Template System**: Smart sensors.json inheritance with real Android app data

## 🚀 Quick Start

### [📥 Installation Guide →](INSTALLATION.md)
Complete installation guide for HACS and manual setup

### [⚙️ Configuration Guide →](CONFIGURATION.md)
Setup instructions, Investigation Mode, and sensors configuration

### [🎛️ Dashboard Guide →](DASHBOARD.md)
Ready-to-use dashboard cards and auto-generation feature

## 🔬 Investigation Mode Discoveries

### ✅ Confirmed Findings
Through Enhanced Smart Investigation Mode v4.0, we've achieved:

- **Position 15 = Brush Guard (97%)**: Exact match confirmed through investigation files
- **Multi-Key Analysis**: Comprehensive monitoring of 22+ keys simultaneously
- **Self-Contained Analysis**: Complete Android app percentages included in every log file
- **Smart Efficiency**: 80-90% reduction in duplicate files while capturing all meaningful changes
- **Template System**: Clean sensors.json inheritance with real Android app data

### 🎯 Current Investigation Status
```json
{
  "investigation_mode": "Enhanced Smart v4.0 Multi-Key",
  "baseline_captured": true,
  "position_15_analysis": "97% = Brush Guard (EXACT MATCH)",
  "monitored_keys": 22,
  "available_keys": 22,
  "next_step": "Run cleaning cycle to verify Position 15 decreases",
  "efficiency": "80-90% file reduction with complete data"
}
```

### 📁 Investigation Files
All files are saved to: `/config/eufy_investigation/DEVICE_ID/`
- `multi_key_baseline_TIMESTAMP.json` - Pre-cleaning baseline with sensors config
- `multi_key_post_cleaning_TIMESTAMP.json` - Post-cleaning analysis  
- `multi_key_monitoring_TIMESTAMP.json` - Smart change detection logs
- `enhanced_multi_key_session_summary_SESSION_ID.json` - Complete session analysis

## 🧠 Smart Features

### Enhanced Investigation Workflow
1. **Baseline Capture**: Record all monitored keys before cleaning with complete sensors reference
2. **Cleaning Cycle**: Run 5-10 minute cleaning cycle
3. **Post-Cleaning Analysis**: Capture data after docking with change detection
4. **Multi-Key Position Discovery**: Automated analysis finds correct accessory positions across all keys
5. **Confirmation Testing**: Verify positions decrease logically after cleaning

### Self-Contained Analysis Files
Every investigation file now includes:
- ✅ Complete Android app percentages for comparison
- ✅ Current sensors configuration for reference
- ✅ Multi-key position analysis with confidence scoring
- ✅ Investigation workflow instructions
- ✅ Complete audit trail with metadata
- ✅ Cross-key analysis and correlation data

## 📊 Current Sensors & Accuracy

Example of a real world test setup and logging:
 
| Sensor | Android App | Investigation Status | Accuracy |
|--------|-------------|---------------------|----------|
| Battery (Key 163) | N/A | ✅ Confirmed | 100% |
| Clean Speed (Key 158) | N/A | ✅ Confirmed | 100% |
| Brush Guard | 97% | 🎯 Position 15 (EXACT MATCH) | Pending cleaning test |
| Rolling Brush | 99% | 🔍 Multiple candidates found | Under investigation |
| Side Brush | 98% | 🔍 Multiple candidates found | Under investigation |
| Dust Filter | 99% | 🔍 Multiple candidates found | Under investigation |
| Water Tank | 76% | 🔍 Key 167 candidates found | Under investigation |

## 🛠️ Available Services

Investigation Mode provides these manual control services:

### Investigation Services
```yaml
# Capture baseline before cleaning
eufy_robovac_data_logger.capture_investigation_baseline

# Capture data after cleaning cycle
eufy_robovac_data_logger.capture_investigation_post_cleaning

# Generate comprehensive session summary
eufy_robovac_data_logger.generate_investigation_summary
```

### Configuration Services
```yaml
# Reload sensors configuration
eufy_robovac_data_logger.reload_accessory_config

# Update accessory life percentage
eufy_robovac_data_logger.update_accessory_life

# Debug specific API keys
eufy_robovac_data_logger.debug_key_analysis
```

### Dashboard Generation
The integration includes an **auto-generate dashboard** feature:
- Go to **Settings** → **Devices & Services** → **Configure**
- Enable **"Generate Dashboard"**
- Copy the generated YAML with your device ID pre-filled
- Paste into your Home Assistant dashboard

See the [Dashboard Guide →](DASHBOARD.md) for complete dashboard examples and customization options.

## 🏆 Key Achievements

### Enhanced Smart Investigation v4.0
- **Multi-Key Support**: Simultaneous analysis of all monitored keys (22+ keys)
- **Template Inheritance**: Perfect sensors.json → sensors_DEVICEID.json system
- **Position Discovery**: Automated Android app percentage matching across all keys
- **Smart Logging**: Only meaningful changes logged with complete reference data
- **Self-Contained Files**: No cross-referencing needed for analysis

### DPS-Only Architecture
- **Reliable Connection**: Direct DPS access without REST API complications
- **Full Key Access**: Complete access to all device keys
- **Stable Performance**: Consistent data collection without external dependencies
- **Proven Accuracy**: 100% confirmed battery and speed sensors

### Configuration Management
- **Accessory Config Manager**: Smart JSON-based configuration system
- **Template Inheritance**: Seamless config updates with user preservation
- **Auto-Discovery**: Automated sensor creation from configuration
- **Manual Control**: Complete manual override capabilities

## 🎛️ Dashboard Integration

The integration provides multiple dashboard options:

### Auto-Generated Dashboards
- **One-Click Generation**: Built-in dashboard generator with device ID pre-filled
- **Copy-Paste Ready**: Perfect YAML formatting for immediate use
- **Service Integration**: All investigation services included as buttons

### Ready-Made Cards
- **Complete Investigation Center**: Full monitoring and control dashboard
- **Individual Sensor Cards**: Modular cards for custom layouts
- **Service Button Cards**: One-click investigation controls
- **Status Overview Cards**: Real-time monitoring displays

[See Dashboard Guide →](DASHBOARD.md) for complete examples and customization options.

## 🔧 Architecture Overview

### DPS-Only Data Collection
```
Eufy Account → DPS Login → Device Discovery → Key Extraction → Sensor Creation
```

### Investigation Mode Flow
```
Raw Data → Smart Analysis → Change Detection → File Generation → Position Discovery
```

### Configuration System
```
sensors.json (Template) → sensors_DEVICEID.json (Device Config) → Dynamic Sensors
```

## 🙏 Acknowledgments

This integration builds upon outstanding work from the Eufy community:

- **[jeppesens](https://github.com/jeppesens/eufy-clean)** - For cleaning up Login, Authentication, and Device ID handling. His refined codebase provided the solid foundation for this implementation.

- **[Martijnpoppen](https://github.com/martijnpoppen/eufy-clean)** - For the original reverse engineering work that made all this possible. Without his initial research, none of this would exist.

This Enhanced Smart Investigation Edition represents the culmination of community research with advanced debugging capabilities for accessory wear detection.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Contributing

- [GitHub Issues](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/issues)
- [GitHub Discussions](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/discussions)

## ⚠️ Important Notes

- **Research Purpose**: This integration is designed for debugging and research
- **Investigation Mode**: Creates detailed analysis files - monitor disk space usage
- **DPS-Only**: Reliable direct device access without REST API dependencies
- **Compatibility**: Designed for Eufy robovac devices, tested with X10 Pro Omni
- **Configuration**: Uses smart template inheritance system for accessory management

---

📊 **Enhanced Smart Investigation v4.0**: Multi-key analysis with 80-90% efficiency improvement

🎛️ **Dashboard Ready**: Auto-generated cards with copy-paste YAML

🔍 **Position Discovery**: Automated accessory sensor byte position detection across all monitored keys
