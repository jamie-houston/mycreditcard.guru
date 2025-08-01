#!/usr/bin/env python3
"""
Script to split scenarios.json into multiple themed files.
"""

import json
import os
import re
from collections import defaultdict

def load_scenarios():
    """Load scenarios from JSON file."""
    with open('data/tests/scenarios.json', 'r') as f:
        return json.load(f)

def categorize_scenarios(scenarios_data):
    """Categorize scenarios based on their names and characteristics."""
    
    categories = {
        'basic_profiles': {
            'description': 'Basic user profile scenarios testing different spending patterns and demographics',
            'filename': 'basic_profiles.json',
            'scenarios': []
        },
        'portfolio_optimization': {
            'description': 'Portfolio-level optimization and management scenarios',
            'filename': 'portfolio_optimization.json',
            'scenarios': []
        },
        'zero_fee_cards': {
            'description': 'Zero annual fee card protection and handling scenarios',
            'filename': 'zero_fee_cards.json',
            'scenarios': []
        },
        'spending_credits': {
            'description': 'Spending credit preferences and calculation scenarios',
            'filename': 'spending_credits.json',
            'scenarios': []
        },
        'card_count_optimization': {
            'description': 'Optimal number of cards based on spending patterns',
            'filename': 'card_count_optimization.json',
            'scenarios': []
        },
        'edge_cases': {
            'description': 'Edge cases and boundary condition scenarios',
            'filename': 'edge_cases.json',
            'scenarios': []
        },
        'signup_bonus': {
            'description': 'Signup bonus and new card application scenarios',
            'filename': 'signup_bonus.json',
            'scenarios': []
        }
    }
    
    for scenario in scenarios_data['scenarios']:
        name = scenario['name']
        
        # Categorize based on scenario name patterns
        if any(pattern in name.lower() for pattern in ['young professional', 'business traveler', 'family', 'travel enthusiast', 'high grocery spender']):
            categories['basic_profiles']['scenarios'].append(scenario)
        elif 'portfolio optimization' in name.lower():
            categories['portfolio_optimization']['scenarios'].append(scenario)
        elif 'zero fee' in name.lower():
            categories['zero_fee_cards']['scenarios'].append(scenario)
        elif 'spending credits' in name.lower():
            categories['spending_credits']['scenarios'].append(scenario)
        elif 'optimal card count' in name.lower():
            categories['card_count_optimization']['scenarios'].append(scenario)
        elif 'signup bonus' in name.lower():
            categories['signup_bonus']['scenarios'].append(scenario)
        elif any(pattern in name.lower() for pattern in ['amazon-only', 'very low spending', 'minimal spending', 'high fee portfolio', 'category optimization']):
            categories['edge_cases']['scenarios'].append(scenario)
        elif any(pattern in name.lower() for pattern in ['existing', 'multiple cards', 'satisfied card holder', 'no double counting']):
            categories['portfolio_optimization']['scenarios'].append(scenario)
        else:
            # Default fallback
            categories['edge_cases']['scenarios'].append(scenario)
    
    return categories

def write_scenario_files(categories, output_dir):
    """Write each category to its own JSON file."""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    files_created = []
    
    for cat_name, cat_data in categories.items():
        if not cat_data['scenarios']:  # Skip empty categories
            continue
            
        filename = cat_data['filename']
        filepath = os.path.join(output_dir, filename)
        
        file_content = {
            "description": cat_data['description'],
            "category": cat_name,
            "scenarios": cat_data['scenarios']
        }
        
        with open(filepath, 'w') as f:
            json.dump(file_content, f, indent=2)
        
        files_created.append({
            'file': filename,
            'count': len(cat_data['scenarios']),
            'category': cat_name
        })
        
        print(f"✅ Created {filename} with {len(cat_data['scenarios'])} scenarios")
    
    return files_created

def create_index_file(files_created, output_dir):
    """Create an index file listing all scenario files."""
    
    index_content = {
        "description": "Index of all scenario test files",
        "total_scenarios": sum(f['count'] for f in files_created),
        "files": [
            {
                "filename": f['file'],
                "category": f['category'],
                "scenario_count": f['count'],
                "description": f"Test scenarios for {f['category'].replace('_', ' ')}"
            }
            for f in files_created
        ]
    }
    
    index_path = os.path.join(output_dir, 'index.json')
    with open(index_path, 'w') as f:
        json.dump(index_content, f, indent=2)
    
    print(f"✅ Created index.json with {len(files_created)} scenario files")
    return index_path

if __name__ == "__main__":
    # Load scenarios
    scenarios_data = load_scenarios()
    print(f"📥 Loaded {len(scenarios_data['scenarios'])} scenarios from data/tests/scenarios.json")
    
    # Categorize scenarios
    categories = categorize_scenarios(scenarios_data)
    
    # Write to files
    output_dir = 'data/input/tests/scenarios'
    files_created = write_scenario_files(categories, output_dir)
    
    # Create index
    index_path = create_index_file(files_created, output_dir)
    
    print(f"\n🎉 Successfully split scenarios into {len(files_created)} files in {output_dir}/")
    print(f"📊 Total scenarios: {sum(f['count'] for f in files_created)}")
    
    # Summary
    print(f"\n📁 Files created:")
    for f in files_created:
        print(f"   - {f['file']} ({f['count']} scenarios)")
    print(f"   - index.json (metadata)")