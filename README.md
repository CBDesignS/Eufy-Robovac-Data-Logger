# Eufy Robovac API Data Logger Integration

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger)
[![GitHub Release](https://img.shields.io/github/release/CBDesignS/Eufy-Robovac-Data-Logger.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/releases)

A Home Assistant custom component for debugging Eufy X10 Pro Omni REST API data. This integration is specifically designed to help developers understand the data structure and API responses from the NEW Android app.

## 🎯 Purpose

This integration focuses on debugging and logging the REST API data from my Eufy X10 Pro Omni devices (other devices may work if they use the NEW Eufy Clean Mobile App, but are untested), particularly the new data sources discovered:

- **Key 163**: Battery level (NEW Android App - 100% accuracy)
- **Key 167**: Water tank level
- **Key 178**: Real-time data source

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
   - **Device ID**: Your robot's device ID/serial number
   - **Debug Mode**: Enable verbose logging (recommended)

## 📊 Sensors Created

The integration creates 6 debug sensors:

### Battery Sensor (`sensor.eufy_x10_debug_battery`)
- **Source**: Key 163 (NEW Android App)
- **Accuracy**: 100% (Perfect match)
- Shows battery percentage with detailed debugging attributes

### Water Tank Sensor (`sensor.eufy_x10_debug_water_tank`)
- **Source**: Key 167, Byte 4 (NEW Android App)  
- **Accuracy**: 82% (Close to real 83%)
- Decodes base64 data and extracts water level from specific byte

### Clean Speed Sensor (`sensor.eufy_x10_debug_clean_speed`)
- **Source**: Key 158
- Shows current cleaning speed (quiet/standard/turbo/max)

### Work Status Sensor (`sensor.eufy_x10_debug_work_status`)
- **Source**: Key 153 + Key 152
- Shows robot status (standby/cleaning/charging/etc.) and play/pause state

### Raw Data Sensor (`sensor.eufy_x10_debug_raw_data`)
- Shows total number of API keys received
- Attributes contain all raw API data (truncated for safety)

### Monitoring Sensor (`sensor.eufy_x10_debug_monitoring`)
- Shows coverage: "X/Y" keys found
- Detailed status of all monitored keys (PRESENT/MISSING)
- Coverage percentage

## 🔍 Debugging Features

### Extensive Logging
When debug mode is enabled, the integration logs:

```
[custom_components.Eufy-Robovac-Data-Logger.coordinator] === EUFY X10 DEBUG UPDATE #1 ===
[custom_components.Eufy-Robovac-Data-Logger.coordinator] === EUFY X10 DEBUG: RAW API DATA ===
[custom_components.Eufy-Robovac-Data-Logger.coordinator] === BATTERY PROCESSING (NEW ANDROID APP) ===
[custom_components.Eufy-Robovac-Data-Logger.coordinator] === WATER TANK PROCESSING (NEW ANDROID APP) ===
[custom_components.Eufy-Robovac-Data-Logger.coordinator] === PROCESSING SUMMARY ===
```

### Rich Sensor Attributes
Each sensor includes detailed attributes showing:
- Raw API values
- Data sources
- Processing methods
- Accuracy information
- Update counts and timestamps

## 🛠️ For Developers

### Replacing Mock Data

The integration currently uses mock data in `coordinator.py`. To use with real API calls:

1. Replace the `_fetch_eufy_data()` method in `coordinator.py`
2. Implement actual Eufy API authentication and data fetching
3. The data processing logic is already complete

### Monitored Keys

The integration monitors these specific keys based on research:

```python
MONITORED_KEYS = [
    "163",  # Battery (NEW Android App - 100% accuracy)
    "167",  # Water tank data (Key 167, Byte 4 - 82% accuracy)  
    "177",  # Alternative water tank source
    "178",  # Real-time data source
    "168",  # Accessories status
    "153",  # Work status/mode
    "152",  # Play/pause commands
    "158",  # Clean speed settings
    # ... more keys
]
```

## 🐛 Enable Debug Logging

Add this to your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.Eufy-Robovac-Data-Logger: debug
```

Then restart Home Assistant to see detailed logs.

## 📋 Key Findings

Based on extensive protocol analysis:

- **NEW Android App**: Uses different data sources than old app, so the old mqtt protobuf data no longer exists
- **Key 163**: Perfect battery source (100% accuracy)
- **Key 167, Byte 4**: Best water tank source (82% accuracy)
- **REST API Mode**: New app appears to use REST API only, not MQTT

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is a debugging integration intended for development purposes. Use at your own risk. Not affiliated with Eufy/Anker.

## 🆘 Support

- [GitHub Issues](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/issues)
- [GitHub Discussions](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/discussions)


## to do list
rewrite the sensor search code so that found working sensors are no longer searched for.
add the ability to add and search for new sensors as Eufy includes them in the app (if any new sensors are released)
Auto add found tested working sensors to Home Assistant.

This is very early test code, contains lots of errors and bugs and may not be of much use if Eufy make big changes to their servers.
