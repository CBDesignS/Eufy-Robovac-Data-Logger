#!/usr/bin/env python3
"""
Eufy Robovac Sensor Baseline Analyzer
Analyzes baseline log files to find potential sensor data locations
"""

import json
import base64
import struct
import argparse
import os
from datetime import datetime
from typing import Dict, List, Tuple, Any


class EufySensorAnalyzer:
    def __init__(self, targets_file: str):
        """Initialize analyzer with sensor targets"""
        self.targets = self._load_targets(targets_file)
        self.results = {}
        
    def _load_targets(self, targets_file: str) -> Dict:
        """Load sensor targets from JSON file"""
        try:
            with open(targets_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Targets file '{targets_file}' not found")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in targets file: {e}")
            return {}
    
    def _decode_base64_data(self, raw_data: str) -> bytes:
        """Decode base64 string to bytes"""
        try:
            return base64.b64decode(raw_data)
        except Exception as e:
            print(f"Error decoding base64: {e}")
            return b''
    
    def _find_hour_candidates(self, data: bytes, target_hours: int) -> List[Dict]:
        """Find potential hour value locations in binary data"""
        candidates = []
        
        # Check for 16-bit representations (most likely for hour values)
        for i in range(len(data) - 1):
            # Big-endian 16-bit
            be_value = struct.unpack('>H', data[i:i+2])[0]
            if be_value == target_hours:
                candidates.append({
                    "bytes": [i, i+1],
                    "value": be_value,
                    "encoding": "big_endian_16bit"
                })
            
            # Little-endian 16-bit
            le_value = struct.unpack('<H', data[i:i+2])[0]
            if le_value == target_hours:
                candidates.append({
                    "bytes": [i, i+1],
                    "value": le_value,
                    "encoding": "little_endian_16bit"
                })
        
        # Check for 32-bit representations (less likely but possible)
        for i in range(len(data) - 3):
            # Big-endian 32-bit
            try:
                be_value = struct.unpack('>I', data[i:i+4])[0]
                if be_value == target_hours:
                    candidates.append({
                        "bytes": [i, i+1, i+2, i+3],
                        "value": be_value,
                        "encoding": "big_endian_32bit"
                    })
            except:
                pass
            
            # Little-endian 32-bit
            try:
                le_value = struct.unpack('<I', data[i:i+4])[0]
                if le_value == target_hours:
                    candidates.append({
                        "bytes": [i, i+1, i+2, i+3],
                        "value": le_value,
                        "encoding": "little_endian_32bit"
                    })
            except:
                pass
        
        # Also check single bytes for smaller hour values
        if target_hours <= 255:
            for i, byte_val in enumerate(data):
                if byte_val == target_hours:
                    candidates.append({
                        "bytes": [i],
                        "value": byte_val,
                        "encoding": "single_byte"
                    })
        
        return candidates
    
    def _find_percentage_candidates(self, data: bytes, target_percentage: int) -> List[Dict]:
        """Find potential percentage value locations in binary data"""
        candidates = []
        
        # Percentages should be single bytes (0-100 range)
        if 0 <= target_percentage <= 100:
            for i, byte_val in enumerate(data):
                if byte_val == target_percentage:
                    candidates.append({
                        "byte": i,
                        "value": byte_val
                    })
        
        return candidates
    
    def analyze_baseline_log(self, log_file: str) -> Dict:
        """Analyze a single baseline log file"""
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
        except Exception as e:
            print(f"Error loading log file '{log_file}': {e}")
            return {}
        
        # Extract timestamp from log or filename
        timestamp = log_data.get('metadata', {}).get('timestamp', 
                    os.path.basename(log_file).replace('.json', ''))
        
        analysis_results = {
            "timestamp": timestamp,
            "log_file": os.path.basename(log_file),
            "sensors": {}
        }
        
        # Get multi_key_data from the log
        multi_key_data = log_data.get('multi_key_data', {})
        
        # Analyze each sensor target
        for sensor_name, target_values in self.targets.get('sensors', {}).items():
            sensor_results = {
                "target_hours": target_values.get('hours'),
                "target_percentage": target_values.get('percentage'),
                "hour_candidates": [],
                "percentage_candidates": []
            }
            
            # Search through all available keys
            for key_name, key_data in multi_key_data.items():
                if not key_name.endswith('_data'):
                    continue
                
                key_number = key_name.replace('key_', '').replace('_data', '')
                raw_data = key_data.get('raw_data', '')
                
                if not raw_data:
                    continue
                
                # Decode the base64 data
                decoded_data = self._decode_base64_data(raw_data)
                if not decoded_data:
                    continue
                
                # Find hour candidates
                if target_values.get('hours') is not None:
                    hour_matches = self._find_hour_candidates(decoded_data, target_values['hours'])
                    for match in hour_matches:
                        match['key'] = key_number
                        sensor_results['hour_candidates'].append(match)
                
                # Find percentage candidates
                if target_values.get('percentage') is not None:
                    pct_matches = self._find_percentage_candidates(decoded_data, target_values['percentage'])
                    for match in pct_matches:
                        match['key'] = key_number
                        sensor_results['percentage_candidates'].append(match)
            
            analysis_results['sensors'][sensor_name] = sensor_results
        
        return analysis_results
    
    def save_results(self, results: Dict, output_file: str):
        """Save analysis results to JSON file"""
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results saved to: {output_file}")
        except Exception as e:
            print(f"Error saving results: {e}")
    
    def generate_summary_report(self, results: Dict) -> str:
        """Generate a human-readable summary of the analysis"""
        report = []
        report.append("=== EUFY SENSOR BASELINE ANALYSIS SUMMARY ===")
        report.append(f"Timestamp: {results.get('timestamp', 'Unknown')}")
        report.append(f"Log file: {results.get('log_file', 'Unknown')}")
        report.append("")
        
        for sensor_name, sensor_data in results.get('sensors', {}).items():
            report.append(f"🔍 {sensor_name.upper().replace('_', ' ')}")
            
            # Hour candidates
            target_hours = sensor_data.get('target_hours')
            hour_candidates = sensor_data.get('hour_candidates', [])
            if target_hours is not None:
                report.append(f"  Target Hours: {target_hours}")
                if hour_candidates:
                    report.append(f"  Hour Candidates Found: {len(hour_candidates)}")
                    for candidate in hour_candidates[:5]:  # Show first 5
                        bytes_str = ','.join(map(str, candidate['bytes']))
                        report.append(f"    Key {candidate['key']}, bytes [{bytes_str}] = {candidate['value']} ({candidate['encoding']})")
                else:
                    report.append("  No hour candidates found")
            
            # Percentage candidates
            target_pct = sensor_data.get('target_percentage')
            pct_candidates = sensor_data.get('percentage_candidates', [])
            if target_pct is not None:
                report.append(f"  Target Percentage: {target_pct}%")
                if pct_candidates:
                    report.append(f"  Percentage Candidates Found: {len(pct_candidates)}")
                    for candidate in pct_candidates[:5]:  # Show first 5
                        report.append(f"    Key {candidate['key']}, byte {candidate['byte']} = {candidate['value']}")
                else:
                    report.append("  No percentage candidates found")
            
            report.append("")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Eufy robovac baseline logs for sensor data locations"
    )
    parser.add_argument(
        "log_file", 
        help="Path to the baseline log JSON file"
    )
    parser.add_argument(
        "-t", "--targets", 
        default="sensor_targets.json",
        help="Path to sensor targets JSON file (default: sensor_targets.json)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: baseline_analysis_TIMESTAMP.json)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed summary report"
    )
    
    args = parser.parse_args()
    
    # Check if log file exists
    if not os.path.exists(args.log_file):
        print(f"Error: Log file '{args.log_file}' not found")
        return 1
    
    # Check if targets file exists
    if not os.path.exists(args.targets):
        print(f"Error: Targets file '{args.targets}' not found")
        print("Please create a sensor_targets.json file first")
        return 1
    
    # Initialize analyzer
    analyzer = EufySensorAnalyzer(args.targets)
    
    if not analyzer.targets:
        print("No valid targets loaded. Exiting.")
        return 1
    
    print(f"Analyzing baseline log: {args.log_file}")
    print(f"Using targets from: {args.targets}")
    
    # Analyze the log file
    results = analyzer.analyze_baseline_log(args.log_file)
    
    if not results:
        print("Analysis failed. No results generated.")
        return 1
    
    # Generate output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"baseline_analysis_{timestamp}.json"
    
    # Save results
    analyzer.save_results(results, args.output)
    
    # Show summary if verbose
    if args.verbose:
        print("\n" + analyzer.generate_summary_report(results))
    
    print(f"\nAnalysis complete! Check {args.output} for detailed results.")
    return 0


if __name__ == "__main__":
    exit(main())
