#!/usr/bin/env python3
"""
Debug script to examine the specific scripts containing valueTooltip data
and understand the exact structure.
"""

import os
import json
import re
from bs4 import BeautifulSoup

def debug_tooltip_extraction():
    """Debug the tooltip extraction process."""
    
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    html_file = os.path.join(base_dir, 'data', 'nerdwallet_bonus_offers.html')
    
    if not os.path.exists(html_file):
        print(f"❌ HTML file not found: {html_file}")
        return
    
    print(f"🔍 Debugging tooltip extraction: {html_file}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tags = soup.find_all('script')
    
    print(f"📜 Found {len(script_tags)} script tags")
    
    # Find scripts with valueTooltip
    tooltip_scripts = []
    for i, script in enumerate(script_tags):
        if script.string and 'valueTooltip' in script.string:
            tooltip_scripts.append((i, script))
            print(f"   Script {i}: Contains valueTooltip ({len(script.string):,} chars)")
    
    print(f"\n🎯 Found {len(tooltip_scripts)} scripts with valueTooltip")
    
    # Examine each script in detail
    for script_index, script in tooltip_scripts:
        print(f"\n" + "="*60)
        print(f"EXAMINING SCRIPT {script_index}")
        print("="*60)
        
        script_content = script.string
        
        # Count valueTooltip occurrences
        tooltip_count = script_content.count('valueTooltip')
        print(f"📊 valueTooltip occurrences: {tooltip_count}")
        
        # Find all valueTooltip patterns
        tooltip_patterns = [
            r'"valueTooltip"\s*:\s*"([^"]+)"',
            r'valueTooltip\s*:\s*"([^"]+)"',
            r'"valueTooltip"\s*:\s*`([^`]+)`',
        ]
        
        all_tooltips = []
        for pattern in tooltip_patterns:
            matches = re.findall(pattern, script_content, re.DOTALL)
            all_tooltips.extend(matches)
            if matches:
                print(f"   Pattern '{pattern}': {len(matches)} matches")
        
        print(f"📝 Total unique tooltips found: {len(set(all_tooltips))}")
        
        # Show sample tooltips
        unique_tooltips = list(set(all_tooltips))
        for i, tooltip in enumerate(unique_tooltips[:5]):
            if tooltip and tooltip != '$undefined':
                print(f"\n   Sample {i+1}: {tooltip[:100]}...")
        
        # Look for card names near tooltips
        name_patterns = [
            r'"name"\s*:\s*"([^"]+)"',
            r'name\s*:\s*"([^"]+)"',
        ]
        
        all_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, script_content)
            all_names.extend(matches)
        
        card_names = [name for name in all_names if len(name) > 5 and any(word in name.lower() for word in ['card', 'credit', 'chase', 'capital', 'american', 'citi', 'discover', 'wells', 'bank'])]
        
        print(f"🏷️  Potential card names found: {len(card_names)}")
        for i, name in enumerate(card_names[:5]):
            print(f"   {i+1}. {name}")
        
        # Try to find JSON objects containing both name and valueTooltip
        json_patterns = [
            r'\{[^{}]*"name"[^{}]*"valueTooltip"[^{}]*\}',
            r'\{[^{}]*"valueTooltip"[^{}]*"name"[^{}]*\}',
        ]
        
        json_objects = []
        for pattern in json_patterns:
            matches = re.findall(pattern, script_content, re.DOTALL)
            json_objects.extend(matches)
        
        print(f"🔧 JSON objects with name+tooltip: {len(json_objects)}")
        
        for i, obj_str in enumerate(json_objects[:3]):
            print(f"\n   JSON {i+1}: {obj_str[:200]}...")
            try:
                obj = json.loads(obj_str)
                if 'name' in obj and 'valueTooltip' in obj:
                    print(f"      ✅ Valid JSON - Name: {obj['name']}")
                    print(f"      ✅ Tooltip: {obj['valueTooltip'][:80]}...")
            except json.JSONDecodeError as e:
                print(f"      ❌ JSON parse error: {e}")
        
        # Look for larger structures that might contain the data
        print(f"\n🔍 Looking for larger data structures...")
        
        # Find potential data arrays or objects
        large_structures = re.findall(r'\[[^\[\]]*"valueTooltip"[^\[\]]*\]', script_content, re.DOTALL)
        if large_structures:
            print(f"   Found {len(large_structures)} arrays with valueTooltip")
            for i, struct in enumerate(large_structures[:2]):
                print(f"   Array {i+1}: {struct[:150]}...")
        
        # Look for object assignments
        assignments = re.findall(r'(\w+)\s*=\s*\{[^{}]*"valueTooltip"[^{}]*\}', script_content)
        if assignments:
            print(f"   Found {len(assignments)} variable assignments with valueTooltip")
            for var in assignments[:3]:
                print(f"   Variable: {var}")
        
        # Try to find the Chase Sapphire Preferred specifically
        if 'Chase Sapphire Preferred' in script_content:
            print(f"\n🎯 Found Chase Sapphire Preferred in this script!")
            
            # Extract context around Chase Sapphire Preferred
            chase_matches = re.finditer(r'.{0,200}Chase Sapphire Preferred.{0,500}', script_content, re.DOTALL)
            for i, match in enumerate(chase_matches):
                context = match.group(0)
                print(f"\n   Context {i+1}:")
                print(f"   {context[:300]}...")
                
                # Look for valueTooltip in this context
                if 'valueTooltip' in context:
                    tooltip_match = re.search(r'"valueTooltip"\s*:\s*"([^"]+)"', context)
                    if tooltip_match:
                        tooltip = tooltip_match.group(1)
                        print(f"   🎯 Found tooltip: {tooltip}")
                        
                        # Test the parsing function
                        from extract_nerdwallet_rewards import parse_category_bonuses_from_tooltip
                        categories = parse_category_bonuses_from_tooltip(tooltip)
                        print(f"   📊 Parsed categories: {categories}")


if __name__ == '__main__':
    debug_tooltip_extraction() 