#!/usr/bin/env python3
"""
Test script to debug NerdWallet extraction.
"""

from extract_card_info import extract_nerdwallet_card_data, parse_category_bonuses_from_tooltip

def test_nerdwallet_extraction():
    """Test the NerdWallet extraction function directly."""
    
    with open('flask_app/nerdwallet_debug_travel.html', 'r') as f:
        html_content = f.read()
    
    print("🔍 Testing NerdWallet extraction directly")
    cards = extract_nerdwallet_card_data(html_content)
    print(f"Found {len(cards)} cards with category bonuses")
    
    for card in cards:
        print(f"  {card['name']}: {card['reward_categories']}")
    
    # Also test if we can find any valueTooltips at all
    import re
    tooltip_pattern = r'"valueTooltip":\s*"([^"]+)"'
    tooltip_matches = re.findall(tooltip_pattern, html_content)
    
    meaningful_tooltips = [t for t in tooltip_matches if t != "$undefined"]
    print(f"\nFound {len(meaningful_tooltips)} meaningful valueTooltips")
    
    for i, tooltip in enumerate(meaningful_tooltips[:3]):  # Show first 3
        print(f"  {i+1}: {tooltip[:100]}...")
        categories = parse_category_bonuses_from_tooltip(tooltip)
        print(f"     Categories: {categories}")

if __name__ == "__main__":
    test_nerdwallet_extraction() 