# Dashboard Guide - Eufy Robovac Data Logger

Complete dashboard setup with ready-to-use YAML cards for monitoring and controlling your Eufy robovac investigation.

## 🎛️ Auto-Generated Dashboard

The integration includes an **auto-generate dashboard** feature that creates device-specific YAML with your exact device ID pre-filled.

### How to Use Auto-Generate

1. **Go to Settings** → **Devices & Services**
2. **Find your integration** → Click **"Configure"**
3. **Enable "Generate Dashboard"** → Click **Submit**
4. **Copy the generated YAML** from the result page
5. **Paste into your dashboard** → Save

![Auto-Generate Dashboard](images/auto-generate-dashboard.png) *(Screenshot placeholder)*

## 📋 Complete Investigation Dashboard

Copy and paste this complete dashboard YAML (replace `YOUR_DEVICE_ID` with your actual device ID):

```yaml
type: vertical-stack
title: "🔍 Eufy Robovac Investigation Center"
cards:
  # Status Overview Card
  - type: entities
    title: "📊 Device Status Overview"
    entities:
      - entity: sensor.eufy_robovac_debug_battery
        name: "🔋 Battery Level"
        icon: mdi:battery
      - entity: sensor.eufy_robovac_debug_clean_speed
        name: "🌪️ Clean Speed"
        icon: mdi:speedometer
      - entity: sensor.eufy_robovac_debug_monitoring
        name: "📡 Key Monitoring"
        icon: mdi:monitor-dashboard
      - entity: sensor.eufy_robovac_debug_raw_data
        name: "🗃️ Raw Data Keys"
        icon: mdi:database
      - entity: sensor.eufy_robovac_investigation_status
        name: "🔍 Investigation Mode"
        icon: mdi:magnify
      - entity: sensor.eufy_robovac_restconnect_status
        name: "🌐 RestConnect"
        icon: mdi:api
      - entity: sensor.eufy_robovac_accessory_config_manager
        name: "🔧 Accessory Manager"
        icon: mdi:cog-outline
    show_header_toggle: false
    state_color: true

  # Investigation Services Card
  - type: horizontal-stack
    cards:
      - type: button
        name: "🎯 Capture Baseline"
        icon: mdi:target
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.capture_investigation_baseline
          service_data:
            device_id: "YOUR_DEVICE_ID"
        show_name: true
        show_icon: true
        show_state: false
        
      - type: button
        name: "📊 Post-Cleaning"
        icon: mdi:clipboard-check
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.capture_investigation_post_cleaning
          service_data:
            device_id: "YOUR_DEVICE_ID"
        show_name: true
        show_icon: true
        show_state: false

      - type: button
        name: "📋 Generate Summary"
        icon: mdi:file-document-outline
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.generate_investigation_summary
          service_data:
            device_id: "YOUR_DEVICE_ID"
        show_name: true
        show_icon: true
        show_state: false

  # Configuration Services Card
  - type: horizontal-stack
    cards:
      - type: button
        name: "🔄 Force Update"
        icon: mdi:refresh
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.force_investigation_update
          service_data:
            device_id: "YOUR_DEVICE_ID"
            phase: "monitoring"
        show_name: true
        show_icon: true
        show_state: false

      - type: button
        name: "⚙️ Reload Config"
        icon: mdi:reload
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.reload_accessory_config
          service_data:
            device_id: "YOUR_DEVICE_ID"
        show_name: true
        show_icon: true
        show_state: false

      - type: button
        name: "🔍 Debug Key 180"
        icon: mdi:bug
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.debug_key_analysis
          service_data:
            device_id: "YOUR_DEVICE_ID"
            key: "180"
            analysis_type: "complete"
        show_name: true
        show_icon: true
        show_state: false

  # Investigation Workflow Card
  - type: markdown
    content: |
      ## 🔬 Investigation Workflow
      
      **Step 1:** 🎯 Capture baseline before cleaning  
      **Step 2:** 🤖 Run room cleaning cycle (5-10 minutes)  
      **Step 3:** 📊 Capture post-cleaning data after docking  
      **Step 4:** 📋 Generate summary to analyze changes  
      **Step 5:** 📁 Check `/config/eufy_investigation/DEVICE_ID/` for files
      
      **Current Focus:** Position 15 = Brush Guard (97%)
```

## 🔧 Individual Sensor Cards

### Battery and Speed Monitoring
```yaml
type: entities
title: "⚡ Core Sensors"
entities:
  - entity: sensor.eufy_robovac_debug_battery
    name: "🔋 Battery"
    icon: mdi:battery
  - entity: sensor.eufy_robovac_debug_clean_speed
    name: "🌪️ Speed"
    icon: mdi:speedometer
show_header_toggle: false
state_color: true
```

### Investigation Status Card
```yaml
type: entities
title: "🔍 Investigation Status"
entities:
  - entity: sensor.eufy_robovac_investigation_status
    name: "Investigation Mode"
    icon: mdi:magnify
  - entity: sensor.eufy_robovac_debug_monitoring
    name: "Key Coverage"
    icon: mdi:monitor-dashboard
  - entity: sensor.eufy_robovac_debug_raw_data
    name: "Raw Data Keys"
    icon: mdi:database
show_header_toggle: false
state_color: true
```

### RestConnect & Config Status
```yaml
type: entities
title: "🌐 Connection & Config"
entities:
  - entity: sensor.eufy_robovac_restconnect_status
    name: "RestConnect Status"
    icon: mdi:api
  - entity: sensor.eufy_robovac_accessory_config_manager
    name: "Accessory Config"
    icon: mdi:cog-outline
show_header_toggle: false
state_color: true
```

## 🎯 Service Button Cards

### Investigation Service Buttons
```yaml
type: horizontal-stack
cards:
  - type: button
    name: "🎯 Baseline"
    icon: mdi:target
    tap_action:
      action: call-service
      service: eufy_robovac_data_logger.capture_investigation_baseline
      service_data:
        device_id: "YOUR_DEVICE_ID"
    show_name: true
    show_icon: true
    
  - type: button
    name: "📊 Post-Clean"
    icon: mdi:clipboard-check
    tap_action:
      action: call-service
      service: eufy_robovac_data_logger.capture_investigation_post_cleaning
      service_data:
        device_id: "YOUR_DEVICE_ID"
    show_name: true
    show_icon: true

  - type: button
    name: "📋 Summary"
    icon: mdi:file-document-outline
    tap_action:
      action: call-service
      service: eufy_robovac_data_logger.generate_investigation_summary
      service_data:
        device_id: "YOUR_DEVICE_ID"
    show_name: true
    show_icon: true
```

### Configuration Service Buttons
```yaml
type: horizontal-stack
cards:
  - type: button
    name: "🔄 Force Update"
    icon: mdi:refresh
    tap_action:
      action: call-service
      service: eufy_robovac_data_logger.force_investigation_update
      service_data:
        device_id: "YOUR_DEVICE_ID"
        phase: "monitoring"
    show_name: true
    show_icon: true

  - type: button
    name: "⚙️ Reload Config"
    icon: mdi:reload
    tap_action:
      action: call-service
      service: eufy_robovac_data_logger.reload_accessory_config
      service_data:
        device_id: "YOUR_DEVICE_ID"
    show_name: true
    show_icon: true
```

## 🔍 Accessory Maintenance Card

```yaml
type: entities
title: "🔧 Accessory Maintenance"
entities:
  - entity: sensor.eufy_robovac_rolling_brush
    name: "🪣 Rolling Brush"
    icon: mdi:brush
  - entity: sensor.eufy_robovac_side_brush
    name: "🖌️ Side Brush"
    icon: mdi:brush-variant
  - entity: sensor.eufy_robovac_dust_filter
    name: "🌪️ Dust Filter"
    icon: mdi:air-filter
  - entity: sensor.eufy_robovac_brush_guard
    name: "🛡️ Brush Guard"
    icon: mdi:shield-outline
show_header_toggle: false
state_color: true
footer:
  type: buttons
  entities:
    - entity: script.update_rolling_brush_life
      name: "Update Brush"
      icon: mdi:wrench
    - entity: script.reset_all_accessories
      name: "Reset All"
      icon: mdi:restore
```

## 📱 Mini Investigation Card

Perfect for smaller dashboards:

```yaml
type: vertical-stack
cards:
  - type: glance
    title: "🔍 Eufy Investigation"
    entities:
      - entity: sensor.eufy_robovac_debug_battery
        name: "Battery"
      - entity: sensor.eufy_robovac_investigation_status
        name: "Investigation"
      - entity: sensor.eufy_robovac_debug_monitoring
        name: "Keys"
    show_name: true
    show_icon: true
    show_state: true
    
  - type: horizontal-stack
    cards:
      - type: button
        icon: mdi:target
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.capture_investigation_baseline
          service_data:
            device_id: "YOUR_DEVICE_ID"
        show_name: false
        show_icon: true
        
      - type: button
        icon: mdi:clipboard-check
        tap_action:
          action: call-service
          service: eufy_robovac_data_logger.capture_investigation_post_cleaning
          service_data:
            device_id: "YOUR_DEVICE_ID"
        show_name: false
        show_icon: true
```

## 🎨 Advanced Card Examples

### Investigation Progress Tracker
```yaml
type: markdown
content: |
  ## 🔬 Investigation Progress
  
  ### ✅ Confirmed Positions
  - **Position 15**: Brush Guard (97%) - EXACT MATCH
  
  ### 🔍 Under Investigation
  - **Rolling Brush**: 99% - Multiple candidates
  - **Side Brush**: 98% - Byte analysis ongoing
  - **Dust Filter**: 99% - Position discovery active
  - **Water Tank**: 76% - Key 167 analysis
  
  ### 📊 Session Statistics
  - **Files Created**: {{states('sensor.eufy_robovac_investigation_status')}}
  - **Key Coverage**: {{states('sensor.eufy_robovac_debug_monitoring')}}
  - **Raw Data**: {{states('sensor.eufy_robovac_debug_raw_data')}} keys
  
  **Next Action**: Run cleaning cycle to test Position 15 decrease
title: Investigation Status
```

### Service Call with Confirmations
```yaml
type: button
name: "🎯 Capture Baseline with Confirmation"
icon: mdi:target
tap_action:
  action: call-service
  service: eufy_robovac_data_logger.capture_investigation_baseline
  service_data:
    device_id: "YOUR_DEVICE_ID"
confirmation:
  text: "Capture baseline before cleaning cycle? Make sure robot is docked and not currently cleaning."
show_name: true
show_icon: true
```

## 🚀 Dashboard Automation

### Auto-Update Accessory Life Script Example
```yaml
# Add to scripts.yaml
update_accessory_after_cleaning:
  alias: "Update Accessory Life After Cleaning"
  sequence:
    - service: eufy_robovac_data_logger.capture_investigation_post_cleaning
      data:
        device_id: "YOUR_DEVICE_ID"
    - delay: "00:00:05"
    - service: eufy_robovac_data_logger.update_accessory_life
      data:
        device_id: "YOUR_DEVICE_ID"
        accessory_id: "rolling_brush"
        life_percentage: "{{ states('sensor.eufy_robovac_rolling_brush') | int - 1 }}"
        notes: "Auto-updated after cleaning cycle"
```

## 💡 Pro Tips

### Finding Your Device ID
Your device ID is shown in:
- Integration title in Settings → Devices & Services
- Any sensor's attributes under `device_id`
- Investigation Status sensor attributes

### Custom Icons
Replace `mdi:` icons with your preferences:
- `mdi:robot-vacuum` - Robot vacuum
- `mdi:battery-charging` - Charging battery
- `mdi:home-automation` - Smart home
- `mdi:wrench-outline` - Maintenance
- `mdi:chart-line` - Analytics

### Color Customization
Add custom colors to buttons:
```yaml
type: button
name: "🎯 Baseline"
icon: mdi:target
tap_action: # ... service call
style: |
  ha-card {
    --card-background-color: rgba(0, 150, 0, 0.1);
    border: 2px solid var(--green-color);
  }
```

---

## [← Back to README](README.md) | [Configuration Guide ←](CONFIGURATION.md)

---

🎛️ **Dashboard Ready**: Copy-paste YAML for instant investigation control

📊 **Auto-Generated**: Use integration's dashboard generator for device-specific cards

🔍 **Investigation Optimized**: Perfect workflow for accessory position discovery
