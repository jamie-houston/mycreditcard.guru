#!/usr/bin/env python3
"""
Script to analyze scenarios and group them by type for splitting into files.
"""

import json
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
            'description': 'Basic user profile scenarios (spending patterns, demographics)',
            'scenarios': []
        },
        'portfolio_optimization': {
            'description': 'Portfolio-level optimization and management scenarios',
            'scenarios': []
        },
        'zero_fee_cards': {
            'description': 'Zero annual fee card protection and handling scenarios',
            'scenarios': []
        },
        'spending_credits': {
            'description': 'Spending credit preferences and calculation scenarios',
            'scenarios': []
        },
        'card_count_optimization': {
            'description': 'Optimal number of cards based on spending patterns',
            'scenarios': []
        },
        'edge_cases': {
            'description': 'Edge cases and boundary condition scenarios',
            'scenarios': []
        },
        'signup_bonus': {
            'description': 'Signup bonus and new card application scenarios',
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

def print_analysis(categories):
    """Print analysis of scenario categorization."""
    total_scenarios = sum(len(cat['scenarios']) for cat in categories.values())
    
    print(f"=== Scenario Analysis ({total_scenarios} total scenarios) ===\n")
    
    for cat_name, cat_data in categories.items():
        count = len(cat_data['scenarios'])
        print(f"📁 **{cat_name.replace('_', ' ').title()}** ({count} scenarios)")
        print(f"   {cat_data['description']}")
        for scenario in cat_data['scenarios']:
            print(f"   - {scenario['name']}")
        print()

if __name__ == "__main__":
    scenarios_data = load_scenarios()
    categories = categorize_scenarios(scenarios_data)
    print_analysis(categories)