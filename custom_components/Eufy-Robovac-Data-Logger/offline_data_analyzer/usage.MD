Key Features
🔍 Deep Analysis:

Analyzes ALL keys and bytes
Decodes base64 data and extracts percentage candidates (1-100 range)
Finds direct integer percentage values
Compares against your template sensor expectations

🎯 Template Matching:

Matches discovered percentages with your sensors.json template values
Provides confidence levels (EXACT_MATCH, CLOSE_MATCH, etc.)
Identifies both direct values and byte-position matches

📊 Change Detection:

Compares baseline vs post-cleaning files
Tracks value changes that indicate wear sensor activity
Calculates percentage changes

💡 Smart Recommendations:

Prioritizes findings by confidence level
Suggests specific key/byte positions to update in sensors.json
Provides actionable next steps

** Usage Destructions **
1. Save the file as eufy_analyzer.py
2. Run it with: python eufy_analyzer.py [input_directory] [output_file]
3. Just run it interactively with: python eufy_analyzer.py


📁 Offline Analyzer Output
Yes, the offline Python script generates comprehensive output files with the same (and more) detailed data:
Generated Files:

Primary Output: eufy_analysis_YYYYMMDD_HHMMSS.json
Console Summary: Real-time analysis results during execution

JSON Output Structure:
{
  "metadata": {
    "analysis_timestamp": "2025-06-16T...",
    "files_analyzed": 3,
    "template_sensors": {...}
  },
  "file_analyses": {
    "baseline_file.json": {...},
    "post_cleaning_file.json": {...}
  },
  "template_matches": {
    "exact_matches": [...],
    "close_matches": [...]
  },
  "cross_file_comparison": {
    "direct_value_changes": {...},
    "byte_changes": {...}
  },
  "recommendations": [
    {
      "priority": "HIGH",
      "type": "EXACT_MATCHES_FOUND", 
      "matches": {...}
    }
  ]
}

What You'll Get:
✅ All percentage candidates by key & byte position
✅ Template sensor matches with confidence levels
✅ Change detection between multiple log files
✅ Byte-level analysis of base64 decoded data
✅ Actionable recommendations for sensors.json updates
✅ Cross-session comparison capabilities
