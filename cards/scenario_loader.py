"""
Utility module for loading test scenarios from multiple files.
"""

import os
import json
import glob
from typing import List, Dict, Any, Optional


class ScenarioLoader:
    """Utility class for loading test scenarios from JSON files."""
    
    @staticmethod
    def load_single_file(file_path: str) -> Dict[str, Any]:
        """Load scenarios from a single JSON file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Scenario file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def load_from_directory(directory_path: str) -> Dict[str, Any]:
        """Load and combine scenarios from all JSON files in a directory."""
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Scenario directory not found: {directory_path}")
        
        # Find all JSON files except index.json
        pattern = os.path.join(directory_path, "*.json")
        scenario_files = [f for f in glob.glob(pattern) 
                         if not f.endswith('index.json')]
        
        if not scenario_files:
            raise FileNotFoundError(f"No scenario files found in: {directory_path}")
        
        all_scenarios = []
        file_info = {}
        
        for file_path in sorted(scenario_files):
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r') as f:
                    file_data = json.load(f)
                
                scenarios = file_data.get('scenarios', [])
                all_scenarios.extend(scenarios)
                
                file_info[filename] = {
                    'description': file_data.get('description', ''),
                    'category': file_data.get('category', ''),
                    'scenario_count': len(scenarios)
                }
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {filename}: {e}")
        
        return {
            'scenarios': all_scenarios,
            'metadata': {
                'total_scenarios': len(all_scenarios),
                'files_loaded': file_info,
                'source_directory': directory_path
            }
        }
    
    @staticmethod
    def load_scenarios(path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load scenarios from the specified path or default locations.
        
        Args:
            path: Path to a specific file or directory. If None, tries default locations.
        
        Returns:
            Dict containing scenarios and metadata
        """
        # If specific path provided, use it
        if path:
            if os.path.isfile(path):
                data = ScenarioLoader.load_single_file(path)
                # Ensure consistent format
                if 'scenarios' not in data:
                    data = {'scenarios': data.get('scenarios', [])}
                return data
            elif os.path.isdir(path):
                return ScenarioLoader.load_from_directory(path)
            else:
                raise FileNotFoundError(f"Path not found: {path}")
        
        # Try default locations in order of preference
        default_locations = [
            'data/tests/scenarios',        # New split format
            'data/tests/scenarios.json',   # Legacy single file (if restored)
        ]
        
        for location in default_locations:
            try:
                if os.path.isdir(location):
                    return ScenarioLoader.load_from_directory(location)
                elif os.path.isfile(location):
                    data = ScenarioLoader.load_single_file(location)
                    # Ensure consistent format
                    if 'scenarios' not in data:
                        data = {'scenarios': data.get('scenarios', [])}
                    return data
            except (FileNotFoundError, ValueError):
                continue
        
        raise FileNotFoundError(
            "No scenario files found. Tried: " + ", ".join(default_locations)
        )
    
    @staticmethod
    def get_scenario_by_name(scenarios_data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        """Find a specific scenario by name."""
        for scenario in scenarios_data.get('scenarios', []):
            if scenario.get('name') == name:
                return scenario
        return None
    
    @staticmethod
    def list_scenario_names(scenarios_data: Dict[str, Any]) -> List[str]:
        """Get list of all scenario names."""
        return [scenario.get('name', '') for scenario in scenarios_data.get('scenarios', [])]


# Backward compatibility functions
def load_scenarios(file_path: Optional[str] = None) -> Dict[str, Any]:
    """Load scenarios from file or default location."""
    return ScenarioLoader.load_scenarios(file_path)


def get_scenarios_path() -> str:
    """Get the default scenarios path (for backward compatibility)."""
    if os.path.exists('data/tests/scenarios'):
        return 'data/tests/scenarios'
    elif os.path.exists('data/tests/scenarios.json'):
        return 'data/tests/scenarios.json'
    else:
        raise FileNotFoundError("No scenario files found in default locations")