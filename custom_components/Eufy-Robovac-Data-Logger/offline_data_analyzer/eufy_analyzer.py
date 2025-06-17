#!/usr/bin/env python3
"""
Eufy Robovac DPS Log Analyzer
Comprehensive tool for analyzing base64-encoded DPS logs to find accessory wear sensors

Usage:
    python eufy_analyzer.py [input_directory] [output_file]
    
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

class EufyDPSAnalyzer:
    def __init__(self):
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
        
        self.analysis_results = {
            "metadata": {},
            "percentage_matches": {},
            "all_percentage_candidates": {},
            "change_analysis": {},
            "recommendations": {},
            "raw_data_summary": {}
        }
    
    def decode_base64_safely(self, data: str) -> Tuple[bool, bytes, str]:
        """Safely decode base64 data and return success, bytes, and hex"""
        try:
            decoded = base64.b64decode(data)
            hex_string = decoded.hex()
            return True, decoded, hex_string
        except Exception as e:
            return False, b'', f"Error: {str(e)}"
    
    def extract_percentage_candidates(self, hex_data: str) -> List[Dict]:
        """Extract potential percentage values (1-100) from hex data"""
        candidates = []
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
                continue
        
        return candidates
    
    def calculate_confidence(self, value: int) -> str:
        """Calculate confidence level for percentage match"""
        if value in [v["expected_percentage"] for v in self.template_sensors.values()]:
            return "EXACT_MATCH"
        elif any(abs(value - v["expected_percentage"]) <= 2 for v in self.template_sensors.values()):
            return "CLOSE_MATCH"
        elif 80 <= value <= 100:
            return "HIGH_RANGE"
        elif 50 <= value <= 79:
            return "MEDIUM_RANGE"
        elif 1 <= value <= 49:
            return "LOW_RANGE"
        else:
            return "OUT_OF_RANGE"
    
    def analyze_json_file(self, file_path: str) -> Dict:
        """Analyze a single JSON log file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            file_analysis = {
                "file_path": file_path,
                "timestamp": data.get("metadata", {}).get("timestamp", "unknown"),
                "log_mode": data.get("metadata", {}).get("log_mode", "unknown"),
                "keys_analyzed": [],
                "percentage_candidates": {},
                "direct_percentage_values": {},
                "total_candidates_found": 0
            }
            
            # Look for multi_key_data section
            multi_key_data = data.get("multi_key_data", {})
            
            for key, key_data in multi_key_data.items():
                key_analysis = {
                    "raw_data": key_data.get("raw_data"),
                    "data_type": key_data.get("data_type"),
                    "data_hash": key_data.get("data_hash"),
                    "percentage_candidates": [],
                    "direct_values": []
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
                file_analysis["percentage_candidates"][key] = key_analysis
                file_analysis["total_candidates_found"] += len(key_analysis["percentage_candidates"])
            
            return file_analysis
            
        except Exception as e:
            return {"error": f"Failed to analyze {file_path}: {str(e)}"}
    
    def find_template_matches(self, file_analysis: Dict) -> Dict:
        """Find matches between discovered percentages and template sensor values"""
        matches = {}
        
        # Check direct percentage values
        for key, value in file_analysis.get("direct_percentage_values", {}).items():
            for sensor_id, sensor_info in self.template_sensors.items():
                expected = sensor_info["expected_percentage"]
                if value == expected:
                    matches[f"{key}_direct"] = {
                        "key": key,
                        "sensor": sensor_id,
                        "sensor_name": sensor_info["name"],
                        "found_value": value,
                        "expected_value": expected,
                        "match_type": "EXACT_DIRECT",
                        "confidence": "HIGH"
                    }
                elif abs(value - expected) <= 2:
                    matches[f"{key}_direct_close"] = {
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
                        matches[f"{key}_pos{position}"] = {
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
                        matches[f"{key}_pos{position}_close"] = {
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
        """Compare baseline and post-cleaning files to find changes"""
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
    
    def generate_recommendations(self, matches: Dict, changes: Dict) -> List[Dict]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # High confidence recommendations
        high_confidence_matches = {k: v for k, v in matches.items() if v["confidence"] == "HIGH"}
        if high_confidence_matches:
            recommendations.append({
                "priority": "HIGH",
                "type": "EXACT_MATCHES_FOUND",
                "description": f"Found {len(high_confidence_matches)} exact matches with template sensors",
                "action": "Update sensors.json with these key/byte positions",
                "matches": high_confidence_matches
            })
        
        # Medium confidence recommendations
        medium_confidence_matches = {k: v for k, v in matches.items() if v["confidence"] == "MEDIUM"}
        if medium_confidence_matches:
            recommendations.append({
                "priority": "MEDIUM",
                "type": "CLOSE_MATCHES_FOUND",
                "description": f"Found {len(medium_confidence_matches)} close matches (±2%) with template sensors",
                "action": "Investigate these positions - may be correct sensors with slight drift",
                "matches": medium_confidence_matches
            })
        
        # Change analysis recommendations
        if changes["summary"]["total_direct_changes"] > 0 or changes["summary"]["total_byte_changes"] > 0:
            recommendations.append({
                "priority": "HIGH",
                "type": "CHANGES_DETECTED",
                "description": f"Found {changes['summary']['total_direct_changes']} direct value changes and {changes['summary']['total_byte_changes']} byte changes",
                "action": "Monitor these changing values - they may be wear sensors",
                "changes": changes
            })
        else:
            recommendations.append({
                "priority": "MEDIUM",
                "type": "NO_CHANGES_DETECTED",
                "description": "No changes detected between baseline and post-cleaning",
                "action": "Run longer cleaning cycles or check if sensors update at different intervals"
            })
        
        return recommendations
    
    def analyze_directory(self, input_dir: str) -> Dict:
        """Analyze all JSON files in a directory"""
        input_path = Path(input_dir)
        json_files = list(input_path.glob("*.json"))
        
        if not json_files:
            raise ValueError(f"No JSON files found in {input_dir}")
        
        analysis_results = {
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "input_directory": str(input_path),
                "files_analyzed": len(json_files),
                "template_sensors": self.template_sensors
            },
            "file_analyses": {},
            "cross_file_comparison": {},
            "template_matches": {},
            "recommendations": []
        }
        
        # Analyze each file
        baseline_analysis = None
        post_cleaning_analysis = None
        
        for json_file in sorted(json_files):
            print(f"Analyzing {json_file.name}...")
            file_analysis = self.analyze_json_file(str(json_file))
            
            if "error" not in file_analysis:
                analysis_results["file_analyses"][json_file.name] = file_analysis
                
                # Find template matches for this file
                matches = self.find_template_matches(file_analysis)
                if matches:
                    analysis_results["template_matches"][json_file.name] = matches
                
                # Track baseline and post-cleaning files for comparison
                log_mode = file_analysis.get("log_mode", "")
                if "baseline" in log_mode.lower():
                    baseline_analysis = file_analysis
                elif "post" in log_mode.lower() or "cleaning" in log_mode.lower():
                    post_cleaning_analysis = file_analysis
            else:
                print(f"Error analyzing {json_file.name}: {file_analysis['error']}")
        
        # Compare baseline vs post-cleaning if both exist
        if baseline_analysis and post_cleaning_analysis:
            print("Comparing baseline vs post-cleaning...")
            changes = self.compare_files(baseline_analysis, post_cleaning_analysis)
            analysis_results["cross_file_comparison"] = changes
            
            # Generate recommendations based on all findings
            all_matches = {}
            for file_matches in analysis_results["template_matches"].values():
                all_matches.update(file_matches)
            
            analysis_results["recommendations"] = self.generate_recommendations(all_matches, changes)
        
        return analysis_results
    
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
        print("\n" + "="*60)
        print("EUFY DPS LOG ANALYSIS SUMMARY")
        print("="*60)
        
        metadata = results.get("metadata", {})
        print(f"Files analyzed: {metadata.get('files_analyzed', 0)}")
        print(f"Analysis timestamp: {metadata.get('analysis_timestamp', 'unknown')}")
        
        # Template matches summary
        all_matches = {}
        for file_matches in results.get("template_matches", {}).values():
            all_matches.update(file_matches)
        
        if all_matches:
            print(f"\nTEMPLATE MATCHES FOUND: {len(all_matches)}")
            print("-" * 30)
            for match_id, match_data in all_matches.items():
                print(f"• {match_data['sensor_name']}: Key {match_data['key']}")
                if 'byte_position' in match_data:
                    print(f"  Byte position {match_data['byte_position']}: {match_data['found_value']}% (expected {match_data['expected_value']}%)")
                else:
                    print(f"  Direct value: {match_data['found_value']}% (expected {match_data['expected_value']}%)")
                print(f"  Confidence: {match_data['confidence']}")
        else:
            print("\nNO TEMPLATE MATCHES FOUND")
        
        # Changes summary
        changes = results.get("cross_file_comparison", {})
        if changes:
            summary = changes.get("summary", {})
            print(f"\nCHANGES DETECTED: {summary.get('total_direct_changes', 0)} direct + {summary.get('total_byte_changes', 0)} byte changes")
            
            if summary.get("keys_with_changes"):
                print("Keys with changes:", ", ".join(summary["keys_with_changes"]))
        
        # Recommendations summary
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\nRECOMMENDATIONS: {len(recommendations)} items")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. [{rec['priority']}] {rec['description']}")

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
        output_file = f"eufy_analysis_{timestamp}.json"
    
    try:
        analyzer = EufyDPSAnalyzer()
        print(f"Starting analysis of {input_dir}...")
        results = analyzer.analyze_directory(input_dir)
        analyzer.save_results(results, output_file)
        
    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()