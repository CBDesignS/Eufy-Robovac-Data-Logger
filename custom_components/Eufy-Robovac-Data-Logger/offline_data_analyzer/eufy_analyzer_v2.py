#!/usr/bin/env python3
"""
Eufy Robovac DPS Log Analyzer v2
Enhanced tool for analyzing base64-encoded DPS logs to find accessory wear sensors,
with added functionality for tracking historical changes and identifying infrequent updates.

Usage:
    python eufy_analyzer_v2.py [input_directory] [output_file]

If no arguments provided, will prompt for file selection.
"""

import json
import base64
import os
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import argparse
from collections import defaultdict

class EufyDPSAnalyzer:
    def __init__(self):
        # Template sensors with expected percentages
        self.template_sensors = {
            "rolling_brush": {"name": "Rolling Brush", "expected_percentage": 99},
            "side_brush": {"name": "Side Brush", "expected_percentage": 98},
            "dust_filter": {"name": "Dust Filter", "expected_percentage": 99},
            "mop_cloth": {"name": "Mop Cloth", "expected_percentage": 98},
            "cliff_bump_sensors": {"name": "Cliff/Bump Sensors", "expected_percentage": 91},
            "brush_guard": {"name": "Brush Guard", "expected_percentage": 97},
            "cleaning_tray": {"name": "Cleaning Tray", "expected_percentage": 93},
            "water_tank_level": {"name": "Water Tank Level", "expected_percentage": 53}
        }

        # Initialize analysis results structure
        self.analysis_results = {
            "metadata": {},
            "file_analyses": {}, # Detailed analysis for each individual file
            "cross_file_comparison": {}, # Comparison between baseline and post-cleaning (if applicable)
            "template_matches": {}, # Matches against known sensor templates for each file
            "historical_change_analysis": { # New section for tracking changes over time
                "direct_values": {},
                "byte_values": {},
                "infrequently_changing_values": [],
                "frequently_changing_values": []
            },
            "recommendations": [] # Overall recommendations
        }

        # New: Data structures to store historical values across all logs
        # { 'key_id': { 'timestamp': value, ... } }
        self.historical_direct_values = defaultdict(dict)
        # { 'key_id': { 'byte_position': { 'timestamp': value, ... }, ... } }
        self.historical_byte_values = defaultdict(lambda: defaultdict(dict))

        # Configuration for infrequent change detection
        self.INFREQUENT_CHANGE_THRESHOLD = 0.20 # If changes occur in <= 20% of logs (excluding first)
        self.MIN_LOGS_FOR_FREQUENCY_ANALYSIS = 3 # Minimum logs to perform frequency analysis

    def decode_base64_safely(self, data: str) -> Tuple[bool, bytes, str]:
        """Safely decode base64 data and return success, bytes, and hex"""
        try:
            decoded = base64.b64decode(data)
            hex_string = decoded.hex()
            return True, decoded, hex_string
        except Exception as e:
            # print(f"Error decoding base64: {e}") # Debugging
            return False, b'', f"Error: {str(e)}"

    def extract_percentage_candidates(self, hex_data: str) -> List[Dict]:
        """Extract potential percentage values (1-100) from hex data"""
        candidates = []
        # Ensure hex_data length is even for proper byte extraction
        if len(hex_data) % 2 != 0:
            hex_data = "0" + hex_data # Pad with a leading zero if odd length

        hex_bytes = [hex_data[i:i+2] for i in range(0, len(hex_data), 2)]

        for i, hex_byte in enumerate(hex_bytes):
            try:
                decimal_value = int(hex_byte, 16)
                if 1 <= decimal_value <= 100:  # Valid percentage range
                    candidates.append({
                        "position": i,
                        "hex": f"0x{hex_byte}",
                        "decimal": decimal_value,
                        "confidence": self.calculate_confidence(decimal_value)
                    })
            except ValueError:
                continue # Skip if not a valid hex byte

        return candidates

    def calculate_confidence(self, value: int) -> str:
        """Calculate confidence level for percentage match against template sensors"""
        for v in self.template_sensors.values():
            if value == v["expected_percentage"]:
                return "EXACT_MATCH"
            elif abs(value - v["expected_percentage"]) <= 2:
                return "CLOSE_MATCH"
        if 80 <= value <= 100:
            return "HIGH_RANGE"
        elif 50 <= value <= 79:
            return "MEDIUM_RANGE"
        elif 1 <= value <= 49:
            return "LOW_RANGE"
        else:
            return "OUT_OF_RANGE"

    def analyze_json_file(self, file_path: str) -> Dict:
        """Analyze a single JSON log file and return its extracted data"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            file_analysis = {
                "file_path": file_path,
                "timestamp": data.get("metadata", {}).get("timestamp", "unknown"),
                "log_mode": data.get("metadata", {}).get("log_mode", "unknown"),
                "keys_analyzed": [],
                "percentage_candidates": {}, # Contains detailed candidates (position, hex, decimal)
                "direct_percentage_values": {}, # Simplified for direct int values (key: value)
                "total_candidates_found": 0
            }

            multi_key_data = data.get("multi_key_data", {})

            for key, key_data in multi_key_data.items():
                key_analysis = {
                    "raw_data": key_data.get("raw_data"),
                    "data_type": key_data.get("data_type"),
                    "data_hash": key_data.get("data_hash"),
                    "percentage_candidates": [],
                    "direct_values": [] # List for direct int values, if any
                }

                # Handle direct integer/percentage values
                if key_data.get("data_type") == "int":
                    value = key_data.get("raw_data")
                    if isinstance(value, int) and 1 <= value <= 100:
                        key_analysis["direct_values"].append({
                            "value": value,
                            "confidence": self.calculate_confidence(value),
                            "type": "direct_integer"
                        })
                        file_analysis["direct_percentage_values"][key] = value

                # Handle base64 encoded data
                elif key_data.get("data_type") == "str" and key_data.get("raw_data"):
                    raw_data = key_data.get("raw_data")
                    success, decoded_bytes, hex_string = self.decode_base64_safely(raw_data)

                    if success:
                        candidates = self.extract_percentage_candidates(hex_string)
                        key_analysis["percentage_candidates"] = candidates
                        key_analysis["hex_data"] = hex_string
                        key_analysis["decoded_length"] = len(decoded_bytes)

                file_analysis["keys_analyzed"].append(key)
                file_analysis["percentage_candidates"][key] = key_analysis # Store detailed analysis
                file_analysis["total_candidates_found"] += len(key_analysis["percentage_candidates"])

            return file_analysis

        except Exception as e:
            return {"error": f"Failed to analyze {file_path}: {str(e)}"}

    def find_template_matches(self, file_analysis: Dict) -> Dict:
        """Find matches between discovered percentages and template sensor values for a single file"""
        matches = {}

        # Check direct percentage values
        for key, value in file_analysis.get("direct_percentage_values", {}).items():
            for sensor_id, sensor_info in self.template_sensors.items():
                expected = sensor_info["expected_percentage"]
                if value == expected:
                    # Using a unique ID for each match
                    match_id = f"direct_key_{key}_sensor_{sensor_id}"
                    matches[match_id] = {
                        "key": key,
                        "sensor": sensor_id,
                        "sensor_name": sensor_info["name"],
                        "found_value": value,
                        "expected_value": expected,
                        "match_type": "EXACT_DIRECT",
                        "confidence": "HIGH"
                    }
                elif abs(value - expected) <= 2:
                    match_id = f"direct_key_{key}_sensor_{sensor_id}_close"
                    matches[match_id] = {
                        "key": key,
                        "sensor": sensor_id,
                        "sensor_name": sensor_info["name"],
                        "found_value": value,
                        "expected_value": expected,
                        "match_type": "CLOSE_DIRECT",
                        "confidence": "MEDIUM"
                    }

        # Check base64 decoded percentage candidates
        for key, key_data in file_analysis.get("percentage_candidates", {}).items():
            for candidate in key_data.get("percentage_candidates", []):
                value = candidate["decimal"]
                position = candidate["position"]

                for sensor_id, sensor_info in self.template_sensors.items():
                    expected = sensor_info["expected_percentage"]
                    if value == expected:
                        match_id = f"byte_key_{key}_pos{position}_sensor_{sensor_id}"
                        matches[match_id] = {
                            "key": key,
                            "byte_position": position,
                            "sensor": sensor_id,
                            "sensor_name": sensor_info["name"],
                            "found_value": value,
                            "expected_value": expected,
                            "match_type": "EXACT_BYTE",
                            "confidence": "HIGH",
                            "hex": candidate["hex"]
                        }
                    elif abs(value - expected) <= 2:
                        match_id = f"byte_key_{key}_pos{position}_sensor_{sensor_id}_close"
                        matches[match_id] = {
                            "key": key,
                            "byte_position": position,
                            "sensor": sensor_id,
                            "sensor_name": sensor_info["name"],
                            "found_value": value,
                            "expected_value": expected,
                            "match_type": "CLOSE_BYTE",
                            "confidence": "MEDIUM",
                            "hex": candidate["hex"]
                        }

        return matches

    def compare_files(self, baseline_analysis: Dict, post_cleaning_analysis: Dict) -> Dict:
        """Compare baseline and post-cleaning files to find changes in a simplified manner"""
        changes = {
            "direct_value_changes": {},
            "byte_changes": {},
            "summary": {
                "total_direct_changes": 0,
                "total_byte_changes": 0,
                "keys_with_changes": []
            }
        }

        # Compare direct percentage values
        baseline_direct = baseline_analysis.get("direct_percentage_values", {})
        post_direct = post_cleaning_analysis.get("direct_percentage_values", {})

        for key in set(baseline_direct.keys()) | set(post_direct.keys()):
            baseline_val = baseline_direct.get(key)
            post_val = post_direct.get(key)

            if baseline_val != post_val:
                changes["direct_value_changes"][key] = {
                    "baseline": baseline_val,
                    "post_cleaning": post_val,
                    "change": (post_val or 0) - (baseline_val or 0),
                    # Avoid division by zero for percentage change
                    "percentage_change": ((post_val or 0) - (baseline_val or 0)) / (baseline_val or 1) * 100 if baseline_val else 0
                }
                changes["summary"]["total_direct_changes"] += 1
                if key not in changes["summary"]["keys_with_changes"]:
                    changes["summary"]["keys_with_changes"].append(key)

        # Compare byte-level percentage candidates
        baseline_candidates = baseline_analysis.get("percentage_candidates", {})
        post_candidates = post_cleaning_analysis.get("percentage_candidates", {})

        for key in set(baseline_candidates.keys()) | set(post_candidates.keys()):
            baseline_key_data = baseline_candidates.get(key, {})
            post_key_data = post_candidates.get(key, {})

            # Map position to decimal value for easier comparison
            baseline_bytes = {c["position"]: c["decimal"] for c in baseline_key_data.get("percentage_candidates", [])}
            post_bytes = {c["position"]: c["decimal"] for c in post_key_data.get("percentage_candidates", [])}

            key_changes = {}
            for pos in set(baseline_bytes.keys()) | set(post_bytes.keys()):
                baseline_val = baseline_bytes.get(pos)
                post_val = post_bytes.get(pos)

                if baseline_val != post_val:
                    key_changes[pos] = {
                        "baseline": baseline_val,
                        "post_cleaning": post_val,
                        "change": (post_val or 0) - (baseline_val or 0)
                    }

            if key_changes:
                changes["byte_changes"][key] = key_changes
                changes["summary"]["total_byte_changes"] += len(key_changes)
                if key not in changes["summary"]["keys_with_changes"]:
                    changes["summary"]["keys_with_changes"].append(key)

        return changes

    def _calculate_change_frequency(self, history: Dict[str, Any], total_logs: int) -> Tuple[int, float]:
        """
        Helper to calculate change count and frequency from a time-series history.
        Frequency is calculated as (number of changes) / (total_logs - 1),
        as a value can only change from the second log onwards.
        Returns (change_count, change_frequency).
        """
        if total_logs < self.MIN_LOGS_FOR_FREQUENCY_ANALYSIS:
            return 0, 0.0 # Not enough logs for meaningful frequency analysis

        sorted_timestamps = sorted(history.keys())
        change_count = 0
        if len(sorted_timestamps) > 1:
            previous_value = history[sorted_timestamps[0]]
            for i in range(1, len(sorted_timestamps)):
                current_value = history[sorted_timestamps[i]]
                if current_value != previous_value:
                    change_count += 1
                previous_value = current_value

        # total_comparisons is total_logs - 1 because we compare each log to the previous one
        total_comparisons = total_logs - 1
        if total_comparisons > 0:
            frequency = change_count / total_comparisons
        else:
            frequency = 0.0 # Only one log or no logs

        return change_count, frequency

    def analyze_historical_changes(self, total_logs: int) -> Dict:
        """
        Analyzes historical data to identify infrequently and frequently changing values.
        Populates self.analysis_results["historical_change_analysis"].
        """
        historical_analysis = {
            "direct_values": {},
            "byte_values": {},
            "infrequently_changing_values": [],
            "frequently_changing_values": [],
            "total_logs_for_frequency_analysis": total_logs
        }

        # Analyze historical direct values
        for key, history in self.historical_direct_values.items():
            change_count, frequency = self._calculate_change_frequency(history, total_logs)
            historical_analysis["direct_values"][key] = {
                "change_count": change_count,
                "frequency": frequency,
                "history": history # Include history for detailed inspection
            }
            if total_logs >= self.MIN_LOGS_FOR_FREQUENCY_ANALYSIS:
                if frequency <= self.INFREQUENT_CHANGE_THRESHOLD and change_count > 0: # Must change at least once
                    historical_analysis["infrequently_changing_values"].append({
                        "type": "direct_value",
                        "key": key,
                        "change_count": change_count,
                        "frequency": frequency,
                        "last_known_value": history[sorted(history.keys())[-1]] if history else None
                    })
                elif frequency > self.INFREQUENT_CHANGE_THRESHOLD:
                    historical_analysis["frequently_changing_values"].append({
                        "type": "direct_value",
                        "key": key,
                        "change_count": change_count,
                        "frequency": frequency,
                        "last_known_value": history[sorted(history.keys())[-1]] if history else None
                    })


        # Analyze historical byte values
        for key, positions_history in self.historical_byte_values.items():
            historical_analysis["byte_values"][key] = {}
            for pos, history in positions_history.items():
                change_count, frequency = self._calculate_change_frequency(history, total_logs)
                historical_analysis["byte_values"][key][pos] = {
                    "change_count": change_count,
                    "frequency": frequency,
                    "history": history
                }
                if total_logs >= self.MIN_LOGS_FOR_FREQUENCY_ANALYSIS:
                    if frequency <= self.INFREQUENT_CHANGE_THRESHOLD and change_count > 0: # Must change at least once
                        historical_analysis["infrequently_changing_values"].append({
                            "type": "byte_value",
                            "key": key,
                            "byte_position": pos,
                            "change_count": change_count,
                            "frequency": frequency,
                            "last_known_value": history[sorted(history.keys())[-1]] if history else None
                        })
                    elif frequency > self.INFREQUENT_CHANGE_THRESHOLD:
                         historical_analysis["frequently_changing_values"].append({
                            "type": "byte_value",
                            "key": key,
                            "byte_position": pos,
                            "change_count": change_count,
                            "frequency": frequency,
                            "last_known_value": history[sorted(history.keys())[-1]] if history else None
                        })

        self.analysis_results["historical_change_analysis"] = historical_analysis

    def generate_recommendations(self, all_matches: Dict, changes_summary: Dict, historical_analysis: Dict) -> List[Dict]:
        """Generate recommendations based on all analysis findings"""
        recommendations = []

        # High confidence template matches
        high_confidence_matches = {k: v for k, v in all_matches.items() if v["confidence"] == "HIGH"}
        if high_confidence_matches:
            recommendations.append({
                "priority": "HIGH",
                "type": "EXACT_TEMPLATE_MATCHES_FOUND",
                "description": f"Found {len(high_confidence_matches)} exact matches with template sensors (may indicate wear sensors)",
                "action": "Investigate these key/byte positions. Consider updating 'sensors.json' with these mappings.",
                "matches": high_confidence_matches
            })

        # Medium confidence template matches
        medium_confidence_matches = {k: v for k, v in all_matches.items() if v["confidence"] == "MEDIUM"}
        if medium_confidence_matches:
            recommendations.append({
                "priority": "MEDIUM",
                "type": "CLOSE_TEMPLATE_MATCHES_FOUND",
                "description": f"Found {len(medium_confidence_matches)} close matches (±2%) with template sensors",
                "action": "Investigate these positions further - they may be correct sensors with slight value drift.",
                "matches": medium_confidence_matches
            })

        # Changes detected between baseline and post-cleaning
        if changes_summary["summary"]["total_direct_changes"] > 0 or changes_summary["summary"]["total_byte_changes"] > 0:
            recommendations.append({
                "priority": "HIGH",
                "type": "CHANGES_DETECTED_BETWEEN_SPECIFIC_LOGS",
                "description": (f"Detected changes: {changes_summary['summary']['total_direct_changes']} direct value changes and "
                                f"{changes_summary['summary']['total_byte_changes']} byte changes between 'baseline' and 'post-cleaning' logs."),
                "action": "These keys are actively changing. Focus on them for sensor identification.",
                "changes_summary": changes_summary["summary"]
            })
        elif historical_analysis.get("total_logs_for_frequency_analysis", 0) >= 2: # Only if more than 1 log was analyzed
             recommendations.append({
                "priority": "LOW",
                "type": "NO_MAJOR_CHANGES_DETECTED",
                "description": "No significant changes were detected between the designated 'baseline' and 'post-cleaning' logs.",
                "action": "This might be expected or indicates that these two specific logs didn't capture the sensor's update cycle. Review historical change analysis for broader trends."
            })


        # Infrequently changing values (new recommendation)
        infrequent_values = historical_analysis.get("infrequently_changing_values", [])
        if infrequent_values:
            recommendations.append({
                "priority": "CRITICAL", # High priority as this is what user is looking for
                "type": "INFREQUENTLY_CHANGING_VALUES",
                "description": (f"Identified {len(infrequent_values)} values that change infrequently "
                                f"(frequency <= {self.INFREQUENT_CHANGE_THRESHOLD * 100:.0f}% of logs). "
                                "These are strong candidates for accessory wear sensors."),
                "action": "Prioritize investigation of these keys/byte positions. Their infrequent changes align with wear sensor behavior.",
                "values": infrequent_values
            })
        elif historical_analysis.get("total_logs_for_frequency_analysis", 0) >= self.MIN_LOGS_FOR_FREQUENCY_ANALYSIS:
            recommendations.append({
                "priority": "LOW",
                "type": "NO_INFREQUENT_CHANGES_FOUND",
                "description": "No values were found to change infrequently across the analyzed logs based on the defined threshold.",
                "action": "Consider adjusting the 'INFREQUENT_CHANGE_THRESHOLD' or collecting more logs over a longer period. Also, check 'frequently_changing_values' if unexpected."
            })

        # Frequently changing values (informational recommendation)
        frequent_values = historical_analysis.get("frequently_changing_values", [])
        if frequent_values:
            recommendations.append({
                "priority": "INFO",
                "type": "FREQUENTLY_CHANGING_VALUES",
                "description": (f"Identified {len(frequent_values)} values that change frequently "
                                f"(frequency > {self.INFREQUENT_CHANGE_THRESHOLD * 100:.0f}% of logs)."),
                "action": "These values are likely volatile or real-time measurements, less likely to be wear sensors. May still be useful for other monitoring.",
                "values": frequent_values
            })

        return recommendations


    def analyze_directory(self, input_dir: str) -> Dict:
        """Analyze all JSON files in a directory and collect historical data"""
        input_path = Path(input_dir)
        # Sort files by name to ensure chronological processing if timestamps are in name
        json_files = sorted(list(input_path.glob("*.json")))

        if not json_files:
            raise ValueError(f"No JSON files found in {input_dir}")

        self.analysis_results["metadata"] = {
            "analysis_timestamp": datetime.now().isoformat(),
            "input_directory": str(input_path),
            "files_analyzed": len(json_files),
            "template_sensors": self.template_sensors,
            "infrequent_change_threshold": self.INFREQUENT_CHANGE_THRESHOLD,
            "min_logs_for_frequency_analysis": self.MIN_LOGS_FOR_FREQUENCY_ANALYSIS
        }

        baseline_analysis = None
        post_cleaning_analysis = None
        all_template_matches = {} # To collect matches from all files for recommendations

        for json_file in json_files:
            print(f"Analyzing {json_file.name}...")
            file_analysis = self.analyze_json_file(str(json_file))

            if "error" not in file_analysis:
                file_timestamp_str = file_analysis.get("timestamp", json_file.name) # Use filename as fallback
                try:
                    # Attempt to parse timestamp for consistent sorting in history
                    file_timestamp = datetime.fromisoformat(file_timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    file_timestamp = datetime.fromtimestamp(os.path.getmtime(json_file)) # Fallback to file modified time

                self.analysis_results["file_analyses"][json_file.name] = file_analysis

                # Collect historical direct values
                for key, value in file_analysis.get("direct_percentage_values", {}).items():
                    self.historical_direct_values[key][file_timestamp.isoformat()] = value

                # Collect historical byte values
                for key, key_data in file_analysis.get("percentage_candidates", {}).items():
                    for candidate in key_data.get("percentage_candidates", []):
                        pos = candidate["position"]
                        value = candidate["decimal"]
                        self.historical_byte_values[key][pos][file_timestamp.isoformat()] = value

                # Find template matches for this file
                matches = self.find_template_matches(file_analysis)
                if matches:
                    self.analysis_results["template_matches"][json_file.name] = matches
                    all_template_matches.update(matches) # Aggregate for overall recommendations

                # Track baseline and post-cleaning files for specific comparison
                log_mode = file_analysis.get("log_mode", "").lower()
                if "baseline" in log_mode:
                    baseline_analysis = file_analysis
                elif "post" in log_mode or "cleaning" in log_mode:
                    post_cleaning_analysis = file_analysis
            else:
                print(f"Error analyzing {json_file.name}: {file_analysis['error']}")

        total_logs_analyzed = len(self.analysis_results["file_analyses"])

        # Perform cross-file comparison if both baseline and post-cleaning logs are found
        changes_summary = {
            "summary": {
                "total_direct_changes": 0,
                "total_byte_changes": 0,
                "keys_with_changes": []
            }
        }
        if baseline_analysis and post_cleaning_analysis:
            print("Comparing baseline vs post-cleaning...")
            changes_summary = self.compare_files(baseline_analysis, post_cleaning_analysis)
            self.analysis_results["cross_file_comparison"] = changes_summary

        # Perform historical change analysis
        if total_logs_analyzed > 0:
            print("Analyzing historical changes across all logs...")
            self.analyze_historical_changes(total_logs_analyzed)

        # Generate overall recommendations
        self.analysis_results["recommendations"] = self.generate_recommendations(
            all_template_matches,
            changes_summary, # Pass the baseline/post-cleaning comparison summary
            self.analysis_results["historical_change_analysis"] # Pass the full historical analysis
        )

        return self.analysis_results

    def save_results(self, results: Dict, output_file: str):
        """Save analysis results to a JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\nAnalysis complete! Results saved to: {output_path}")

        # Print summary to console
        self.print_summary(results)

    def print_summary(self, results: Dict):
        """Print a summary of analysis results to console"""
        print("\n" + "="*80)
        print("EUFY DPS LOG ANALYSIS SUMMARY (v2)")
        print("="*80)

        metadata = results.get("metadata", {})
        print(f"Files analyzed: {metadata.get('files_analyzed', 0)}")
        print(f"Analysis timestamp: {metadata.get('analysis_timestamp', 'unknown')}")
        print(f"Infrequent Change Threshold: <= {metadata.get('infrequent_change_threshold', 0.0) * 100:.0f}% change frequency")
        print(f"Min Logs for Frequency Analysis: {metadata.get('min_logs_for_frequency_analysis', 0)}")


        # Template matches summary (from all files combined)
        # Re-aggregate all_template_matches from the results, as it's not stored directly as a top-level key
        all_matches_aggregated = {}
        for file_matches in results.get("template_matches", {}).values():
            all_matches_aggregated.update(file_matches)

        if all_matches_aggregated:
            print(f"\n--- TEMPLATE MATCHES FOUND: {len(all_matches_aggregated)} ---")
            for match_id, match_data in all_matches_aggregated.items():
                match_source = "Direct" if "direct_key" in match_id else "Byte"
                pos_info = f" Pos {match_data['byte_position']}" if "byte_position" in match_data else ""
                print(f"• {match_data['sensor_name']} ({match_source}): Key {match_data['key']}{pos_info}")
                print(f"  Found Value: {match_data['found_value']}% (Expected: {match_data['expected_value']}%)")
                print(f"  Confidence: {match_data['confidence']}")
        else:
            print("\n--- NO TEMPLATE MATCHES FOUND ---")

        # Changes between specific baseline/post-cleaning files
        changes = results.get("cross_file_comparison", {})
        if changes and changes["summary"]["total_direct_changes"] > 0 or changes["summary"]["total_byte_changes"] > 0:
            summary = changes.get("summary", {})
            print(f"\n--- CHANGES DETECTED (Baseline vs. Post-Cleaning): {summary.get('total_direct_changes', 0)} direct + {summary.get('total_byte_changes', 0)} byte changes ---")

            if summary.get("keys_with_changes"):
                print("Keys with changes:", ", ".join(summary["keys_with_changes"]))
        else:
             print("\n--- NO MAJOR CHANGES DETECTED BETWEEN BASELINE AND POST-CLEANING LOGS ---")

        # Historical Change Analysis Summary (new section)
        historical_analysis = results.get("historical_change_analysis", {})
        total_logs_for_freq_analysis = historical_analysis.get('total_logs_for_frequency_analysis', 0)

        if total_logs_for_freq_analysis >= metadata.get('min_logs_for_frequency_analysis', 0):
            infrequent_values = historical_analysis.get("infrequently_changing_values", [])
            if infrequent_values:
                print(f"\n--- INFREQUENTLY CHANGING VALUES ({len(infrequent_values)} found) ---")
                print(f"Threshold: <= {metadata.get('infrequent_change_threshold', 0.0) * 100:.0f}% change frequency")
                for val_info in infrequent_values:
                    source_type = "Direct" if val_info["type"] == "direct_value" else "Byte"
                    pos_info = f", Pos {val_info['byte_position']}" if "byte_position" in val_info else ""
                    print(f"• {source_type} Key {val_info['key']}{pos_info}:")
                    print(f"  Changes: {val_info['change_count']}, Frequency: {val_info['frequency']:.2f}, Last Value: {val_info['last_known_value']}")
            else:
                print("\n--- NO INFREQUENTLY CHANGING VALUES FOUND ---")
                print(f"Consider adjusting the threshold ({metadata.get('infrequent_change_threshold', 0.0) * 100:.0f}%) or providing more logs.")

            frequent_values = historical_analysis.get("frequently_changing_values", [])
            if frequent_values:
                print(f"\n--- FREQUENTLY CHANGING VALUES ({len(frequent_values)} found) ---")
                print(f"Threshold: > {metadata.get('infrequent_change_threshold', 0.0) * 100:.0f}% change frequency")
                for val_info in frequent_values:
                    source_type = "Direct" if val_info["type"] == "direct_value" else "Byte"
                    pos_info = f", Pos {val_info['byte_position']}" if "byte_position" in val_info else ""
                    print(f"• {source_type} Key {val_info['key']}{pos_info}:")
                    print(f"  Changes: {val_info['change_count']}, Frequency: {val_info['frequency']:.2f}, Last Value: {val_info['last_known_value']}")
            else:
                print("\n--- NO FREQUENTLY CHANGING VALUES IDENTIFIED ---")

        else:
            print(f"\n--- INSUFFICIENT LOGS FOR FREQUENCY ANALYSIS ({total_logs_for_freq_analysis} logs, need >= {metadata.get('min_logs_for_frequency_analysis', 0)}) ---")


        # Recommendations summary
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\n--- RECOMMENDATIONS ({len(recommendations)} items) ---")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. [{rec['priority']}] {rec['description']}")
                if rec.get("action"):
                    print(f"   Action: {rec['action']}")
        else:
            print("\n--- NO SPECIFIC RECOMMENDATIONS ---")

        print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Analyze Eufy robovac DPS logs for accessory wear sensors")
    parser.add_argument("input_dir", nargs='?', help="Directory containing JSON log files")
    parser.add_argument("output_file", nargs='?', help="Output file for analysis results")

    args = parser.parse_args()

    # Get input directory
    if args.input_dir:
        input_dir = args.input_dir
    else:
        input_dir = input("Enter path to directory containing JSON log files: ").strip()

    if not os.path.exists(input_dir):
        print(f"Error: Directory {input_dir} does not exist")
        sys.exit(1)

    # Get output file
    if args.output_file:
        output_file = args.output_file
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"eufy_analysis_{timestamp}_v2.json"

    try:
        analyzer = EufyDPSAnalyzer()
        print(f"Starting analysis of {input_dir} with v2 enhancements...")
        results = analyzer.analyze_directory(input_dir)
        analyzer.save_results(results, output_file)

    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        sys.exit(1)

if __name__ == "__main__":
    main()
