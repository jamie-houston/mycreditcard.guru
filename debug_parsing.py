#!/usr/bin/env python3
"""
Debug script to test the category parsing function.
"""

import re
from extract_card_info import parse_category_bonuses_from_tooltip

def debug_parsing():
    """Debug the parsing function step by step."""
    
    # The problematic Chase Sapphire Preferred text
    tooltip_text = "5x on travel purchased through Chase Travel℠, 3x on dining, select streaming services and online groceries, 2x on all other travel purchases, 1x on all other purchases."
    
    print("🔍 Debugging Chase Sapphire Preferred parsing")
    print(f"Input: {tooltip_text}")
    print("=" * 80)
    
    # Test the main pattern
    main_pattern = r'(\d+(?:\.\d+)?)[x%]?\s+(?:cash back\s+)?(?:on|at|for)\s+([^,]+?)(?=\s*,\s*\d+[x%]|$)'
    main_matches = re.findall(main_pattern, tooltip_text, re.IGNORECASE)
    
    print(f"Main pattern matches: {main_matches}")
    
    for i, (rate, category_text) in enumerate(main_matches):
        print(f"\nMatch {i+1}:")
        print(f"  Rate: {rate}")
        print(f"  Category text: '{category_text}'")
        
        # Test splitting
        category_parts = re.split(r'\s+and\s+|,\s+(?!.*\d)', category_text)
        print(f"  Split into parts: {category_parts}")
    
    print("\n" + "=" * 80)
    print("Actual function result:")
    result = parse_category_bonuses_from_tooltip(tooltip_text)
    print(f"Categories found: {result}")
    
    print("\n" + "=" * 80)
    print("Expected categories:")
    expected = {
        "Dining & Restaurants": 3.0,
        "Groceries": 3.0,
        "Streaming Services": 3.0,
        "Travel": 2.0
    }
    print(f"Expected: {expected}")

def test_simple_case():
    """Test a simple compound case."""
    print("\n🔍 Testing simple compound case")
    tooltip_text = "3x on dining, entertainment and streaming services"
    
    print(f"Input: {tooltip_text}")
    
    # Test the main pattern
    main_pattern = r'(\d+(?:\.\d+)?)[x%]?\s+(?:cash back\s+)?(?:on|at|for)\s+([^,]+?)(?=\s*,\s*\d+[x%]|$)'
    main_matches = re.findall(main_pattern, tooltip_text, re.IGNORECASE)
    
    print(f"Main pattern matches: {main_matches}")
    
    result = parse_category_bonuses_from_tooltip(tooltip_text)
    print(f"Result: {result}")
    
    expected = {
        "Dining & Restaurants": 3.0,
        "Entertainment": 3.0,
        "Streaming Services": 3.0
    }
    print(f"Expected: {expected}")

if __name__ == "__main__":
    debug_parsing()
    test_simple_case() 