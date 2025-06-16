#!/usr/bin/env python3
"""
Script to analyze the HTML structure of the NerdWallet file to understand
where reward data is stored.
"""

import os
import json
import re
from bs4 import BeautifulSoup

def analyze_html_structure():
    """Analyze the HTML structure to find reward data patterns."""
    
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    html_file = os.path.join(base_dir, 'data', 'nerdwallet_bonus_offers.html')
    
    if not os.path.exists(html_file):
        print(f"❌ HTML file not found: {html_file}")
        return
    
    print(f"🔍 Analyzing HTML structure: {html_file}")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    print(f"📊 Total HTML size: {len(content):,} characters")
    print(f"📊 Total elements: {len(soup.find_all()):,}")
    
    # Look for different patterns
    patterns_to_search = [
        ('valueTooltip', r'valueTooltip'),
        ('tooltip', r'tooltip'),
        ('reward', r'reward'),
        ('dining', r'dining'),
        ('travel', r'travel'),
        ('cash back', r'cash\s+back'),
        ('points', r'points'),
        ('miles', r'miles'),
        ('Chase Sapphire', r'Chase\s+Sapphire'),
        ('JSON objects', r'\{[^{}]*"name"[^{}]*\}'),
        ('Script tags with data', r'<script[^>]*>.*?</script>'),
    ]
    
    for pattern_name, pattern in patterns_to_search:
        matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
        print(f"🔍 {pattern_name}: {len(matches)} matches")
        
        if matches and pattern_name in ['Chase Sapphire', 'JSON objects']:
            print(f"   Sample: {matches[0][:100]}...")
    
    # Look for script tags specifically
    script_tags = soup.find_all('script')
    print(f"\n📜 Script tags found: {len(script_tags)}")
    
    json_scripts = 0
    data_scripts = 0
    
    for i, script in enumerate(script_tags):
        if script.string:
            script_content = script.string
            
            # Check for JSON-like content
            if 'valueTooltip' in script_content:
                print(f"   Script {i}: Contains 'valueTooltip'")
                # Extract a sample around valueTooltip
                tooltip_match = re.search(r'.{0,100}valueTooltip.{0,200}', script_content, re.IGNORECASE)
                if tooltip_match:
                    print(f"      Sample: {tooltip_match.group(0)}")
                json_scripts += 1
            
            if 'Chase Sapphire' in script_content:
                print(f"   Script {i}: Contains 'Chase Sapphire'")
                chase_match = re.search(r'.{0,50}Chase Sapphire.{0,100}', script_content, re.IGNORECASE)
                if chase_match:
                    print(f"      Sample: {chase_match.group(0)}")
                data_scripts += 1
            
            if '"name"' in script_content and '"annualFee"' in script_content:
                print(f"   Script {i}: Contains card-like JSON structure")
                # Try to extract a sample JSON object
                json_match = re.search(r'\{[^{}]*"name"[^{}]*"annualFee"[^{}]*\}', script_content)
                if json_match:
                    print(f"      Sample JSON: {json_match.group(0)[:200]}...")
    
    print(f"\n📊 Scripts with JSON-like content: {json_scripts}")
    print(f"📊 Scripts with card data: {data_scripts}")
    
    # Look for specific data attributes
    data_attrs = [
        'data-card-name',
        'data-value-tooltip', 
        'data-tooltip',
        'data-rewards',
        'data-categories'
    ]
    
    print(f"\n🏷️  Data attributes:")
    for attr in data_attrs:
        elements = soup.find_all(attrs={attr: True})
        print(f"   {attr}: {len(elements)} elements")
        if elements:
            print(f"      Sample: {elements[0].get(attr)[:100]}...")
    
    # Look for class patterns that might contain reward data
    class_patterns = [
        'reward',
        'tooltip',
        'category',
        'bonus',
        'rate'
    ]
    
    print(f"\n🎨 CSS classes containing reward-related terms:")
    for pattern in class_patterns:
        elements = soup.find_all(class_=re.compile(pattern, re.IGNORECASE))
        print(f"   Classes with '{pattern}': {len(elements)} elements")
    
    # Try to find the largest script tag (likely contains the main data)
    largest_script = None
    largest_size = 0
    
    for i, script in enumerate(script_tags):
        if script.string:
            size = len(script.string)
            if size > largest_size:
                largest_size = size
                largest_script = (i, script)
    
    if largest_script:
        script_index, script = largest_script
        print(f"\n📜 Largest script tag (#{script_index}): {largest_size:,} characters")
        
        # Analyze the largest script for patterns
        script_content = script.string
        
        # Look for JSON structures
        json_objects = re.findall(r'\{[^{}]*"name"[^{}]*\}', script_content)
        print(f"   JSON-like objects: {len(json_objects)}")
        
        if json_objects:
            print(f"   Sample JSON object: {json_objects[0][:200]}...")
        
        # Look for specific card names
        card_names = [
            'Chase Sapphire Preferred',
            'Capital One Venture',
            'American Express',
            'Wells Fargo Active Cash'
        ]
        
        for card_name in card_names:
            if card_name in script_content:
                print(f"   Found card: {card_name}")
                # Extract context around the card name
                context_match = re.search(f'.{{0,100}}{re.escape(card_name)}.{{0,200}}', script_content, re.IGNORECASE)
                if context_match:
                    print(f"      Context: {context_match.group(0)[:150]}...")


if __name__ == '__main__':
    analyze_html_structure() 