# Eufy Robovac Data Logger

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger)
[![GitHub Release](https://img.shields.io/github/release/CBDesignS/Eufy-Robovac-Data-Logger.svg)](https://github.com/CBDesignS/Eufy-Robovac-Data-Logger/releases)

## Shout out to the people behind the code that I used to make this work.

The integration would not be possible without the code and work by both
https://github.com/jeppesens/eufy-clean & https://github.com/martijnpoppen/eufy-clean.
Their code makes this integration work, Login, talk to the correct Eufy servers, Access the api server to get the current DPS data for this integration to log.
Without these people this would not be possible.
Thank you [martijnpoppen](https://github.com/martijnpoppen) & [jeppesens](https://github.com/jeppesens).
I just expanded upon their work to try and enhance the Eufy Robovac comminity and users.


A simple Home Assistant custom component that logs Eufy Robovac API data to JSON files for external analysis.

## 🎯 What This Integration Does

This integration connects to your Eufy Robovac via MQTT and dumps all protobuf data (keys 150-180) to JSON files every 60 seconds. Perfect for researchers and developers who want to analyze Eufy's data structure.

### Core Features
- **MQTT Data Collection**: Uses proven Eufy API to fetch device data
- **Automatic Data Dumping**: Saves keys 150-180 to JSON files every minute
- **Simple Sensors**: Shows battery level and clean speed in Home Assistant
- **Clean JSON Output**: Structured data ready for external protobuf analysis

## 📊 Data Collection

The integration dumps all data from keys 150-180, which includes:
- **Simple Values**: Battery (163), Clean Speed (158), etc.
- **Protobuf Data**: Base64 encoded data in keys like 152, 153, 154, 157, 162, 164, 165, 166, 167, 168, 169, and more

### Output Format
Files are saved to: `/config/eufy_robovac_dumps/YOUR_DEVICE_ID/`

Example JSON structure:
```json
{
  "timestamp": "2025-01-15T10:30:00",
  "device_id": "YOUR_DEVICE_ID",
  "device_name": "Your Robovac Name",
  "device_model": "T2351",
  "update_count": 1,
  "keys": {
    "150": null,
    "151": true,
    "152": "BAgYEGg=",
    "153": "DBADGgIQAXICIgB6AA==",
    "158": "3",
    "163": "100",
    "167": "base64_protobuf_data...",
    "168": "base64_protobuf_data...",
    "180": "base64_protobuf_data..."
  }
}
