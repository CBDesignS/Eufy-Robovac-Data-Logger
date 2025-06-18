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
Or run interactively with: python eufy_analyzer.py
