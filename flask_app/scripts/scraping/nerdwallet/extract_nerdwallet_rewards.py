#!/usr/bin/env python3
"""
Targeted script to extract reward categories from NerdWallet HTML.
This script finds the JavaScript data structures containing valueTooltip information.
"""

import os
import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_category_bonuses_from_tooltip(tooltip_text: str) -> List[Dict[str, any]]:
    """
    Parse category bonuses from NerdWallet valueTooltip text.
    Enhanced version based on test_category_bonuses.py.
    Returns a list of reward categories with category, rate, and limit fields.
    """
    if not tooltip_text or tooltip_text in [None, "", "$undefined"]:
        return []
    
    # Clean up the text
    text = tooltip_text.replace('℠', '').replace('®', '').replace('™', '')
    text = re.sub(r'\s+', ' ', text).strip()
    
    categories = {}
    
    # Category mapping - standardized names matching your database
    category_mappings = {
        # Dining
        r'\b(?:dining|restaurants?)\b': 'Dining & Restaurants',
        
        # Travel
        r'\b(?:travel|flights?|hotels?|car rentals?)\b': 'Travel',
        
        # Gas
        r'\b(?:gas|gas stations?|fuel)\b': 'Gas Stations',
        
        # Groceries
        r'\b(?:groceries|supermarkets?|grocery stores?|online groceries)\b': 'Groceries',
        
        # Streaming
        r'\b(?:streaming|streaming services?|select streaming services?)\b': 'Streaming Services',
        
        # Entertainment
        r'\b(?:entertainment)\b': 'Entertainment',
        
        # Drugstores
        r'\b(?:drugstores?|pharmacies)\b': 'Drugstores',
        
        # Transit
        r'\b(?:transit|taxis?|rideshare|parking|tolls?|trains?|buses?)\b': 'Transit',
        
        # Other/Base rate
        r'\b(?:all other purchases?|other purchases?|everything else)\b': 'Other',
    }
    
    # Enhanced patterns to match various formats
    rate_patterns = [
        # "5x on travel purchased through Chase Travel℠"
        r'(\d+(?:\.\d+)?)x\s+on\s+([^,\.]+?)(?:\s+purchased\s+through[^,\.]*)?(?:[,\.]|$)',
        
        # "3x on dining, select streaming services and online groceries"
        r'(\d+(?:\.\d+)?)x\s+on\s+([^,\.]+?)(?:[,\.]|$)',
        
        # "2x on all other travel purchases"
        r'(\d+(?:\.\d+)?)x\s+on\s+(all other [^,\.]+?)(?:[,\.]|$)',
        
        # "5% cash back on dining"
        r'(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?on\s+([^,\.]+?)(?:[,\.]|$)',
        
        # "Earn 3% cash back at grocery stores"
        r'earn\s+(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?(?:at\s+|on\s+)([^,\.]+?)(?:[,\.]|$)',
        
        # "1x on all other purchases"
        r'(\d+(?:\.\d+)?)x\s+on\s+(all other purchases?)(?:[,\.]|$)',
    ]
    
    for pattern in rate_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                rate = float(match.group(1))
                category_text = match.group(2).strip()
                
                # Map the category text to standardized names
                mapped = False
                for category_pattern, standard_name in category_mappings.items():
                    if re.search(category_pattern, category_text, re.IGNORECASE):
                        # Only keep the highest rate for each category
                        if standard_name not in categories or categories[standard_name] < rate:
                            categories[standard_name] = rate
                        mapped = True
                        break
                
                # If not mapped and it's a reasonable category, add it as-is
                if not mapped and len(category_text) > 3 and rate > 0:
                    # Clean up the category name
                    clean_category = category_text.title().strip()
                    if clean_category not in categories or categories[clean_category] < rate:
                        categories[clean_category] = rate
                        
            except (ValueError, IndexError):
                continue
    
    # Special handling for compound categories like "dining, entertainment and streaming"
    compound_pattern = r'(\d+(?:\.\d+)?)x\s+on\s+([^\.]+?)(?:[,\.]|$)'
    matches = re.finditer(compound_pattern, text, re.IGNORECASE)
    
    for match in matches:
        try:
            rate = float(match.group(1))
            category_text = match.group(2).strip()
            
            # Split on commas and "and"
            category_parts = re.split(r',\s*(?:and\s+)?|and\s+', category_text)
            
            for part in category_parts:
                part = part.strip()
                if len(part) > 2:
                    # Map to standardized names
                    for category_pattern, standard_name in category_mappings.items():
                        if re.search(category_pattern, part, re.IGNORECASE):
                            if standard_name not in categories or categories[standard_name] < rate:
                                categories[standard_name] = rate
                            break
        except (ValueError, IndexError):
            continue
    
    # Convert dictionary to list format with limit field
    reward_categories = []
    for category, rate in categories.items():
        reward_categories.append({
            "category": category,
            "rate": rate,
            "limit": None  # Default to None - could be enhanced to parse limits from tooltip in the future
        })
    
    return reward_categories


def extract_json_from_script(script_content: str) -> List[Dict]:
    """Extract JSON objects from JavaScript content."""
    json_objects = []
    
    # Look for various JSON patterns
    patterns = [
        # Standard JSON objects with quotes
        r'\{[^{}]*"name"[^{}]*"valueTooltip"[^{}]*\}',
        r'\{[^{}]*"valueTooltip"[^{}]*"name"[^{}]*\}',
        
        # Larger JSON objects (may be nested)
        r'\{[^{}]*"name"[^{}]*\}',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, script_content, re.DOTALL)
        for match in matches:
            try:
                json_str = match.group(0)
                # Try to parse as JSON
                data = json.loads(json_str)
                if isinstance(data, dict) and 'name' in data:
                    json_objects.append(data)
            except json.JSONDecodeError:
                continue
    
    # Also look for JavaScript object literals (without quotes around keys)
    js_object_pattern = r'\{[^{}]*name\s*:[^{}]*valueTooltip\s*:[^{}]*\}'
    matches = re.finditer(js_object_pattern, script_content, re.DOTALL)
    
    for match in matches:
        try:
            js_str = match.group(0)
            # Convert JavaScript object to JSON by adding quotes around keys
            json_str = re.sub(r'(\w+)\s*:', r'"\1":', js_str)
            data = json.loads(json_str)
            if isinstance(data, dict) and 'name' in data:
                json_objects.append(data)
        except (json.JSONDecodeError, re.error):
            continue
    
    return json_objects


def extract_cards_from_html(html_content: str) -> List[Dict]:
    """Extract credit card data from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    cards = []
    
    # Find all script tags
    script_tags = soup.find_all('script')
    logger.info(f"Found {len(script_tags)} script tags")
    
    cards_found = 0
    tooltips_found = 0
    
    for i, script in enumerate(script_tags):
        if script.string:
            script_content = script.string
            
            # Skip if script is too small to contain meaningful data
            if len(script_content) < 100:
                continue
            
            # Look for valueTooltip in this script
            if 'valueTooltip' in script_content:
                logger.info(f"Script {i} contains valueTooltip data")
                
                # Extract JSON objects from this script
                json_objects = extract_json_from_script(script_content)
                
                for obj in json_objects:
                    if 'name' in obj:
                        card = process_card_object(obj)
                        if card:
                            cards.append(card)
                            cards_found += 1
                            if card.get('value_tooltip'):
                                tooltips_found += 1
                
                # Also try regex extraction for cases where JSON parsing fails
                tooltip_matches = re.finditer(r'"valueTooltip"\s*:\s*"([^"]+)"', script_content)
                name_matches = re.finditer(r'"name"\s*:\s*"([^"]+)"', script_content)
                
                # Try to pair names with tooltips
                tooltips = [match.group(1) for match in tooltip_matches]
                names = [match.group(1) for match in name_matches]
                
                # Simple pairing - assumes they appear in similar order
                for name, tooltip in zip(names, tooltips):
                    if name and tooltip and tooltip != '$undefined':
                        card = {
                            'name': name,
                            'issuer': extract_issuer_from_name(name),
                            'value_tooltip': tooltip,
                            'reward_categories': parse_category_bonuses_from_tooltip(tooltip),
                            'extraction_method': 'regex_pairing'
                        }
                        
                        # Avoid duplicates
                        if not any(c.get('name') == name for c in cards):
                            cards.append(card)
                            cards_found += 1
                            tooltips_found += 1
    
    logger.info(f"Extracted {cards_found} cards, {tooltips_found} with tooltips")
    return cards


def process_card_object(card_obj: Dict) -> Optional[Dict]:
    """Process a single card object from JSON data."""
    if not card_obj.get('name'):
        return None
    
    name = card_obj['name']
    
    # Skip generic entries
    skip_patterns = [
        'find the right',
        'compare',
        'get started',
        'apply now',
        'learn more'
    ]
    
    if any(skip in name.lower() for skip in skip_patterns):
        return None
    
    card = {
        'name': name,
        'issuer': extract_issuer_from_name(name),
        'reward_categories': [],
        'raw_data': card_obj
    }
    
    # Extract tooltip and parse categories
    if 'valueTooltip' in card_obj:
        tooltip = card_obj['valueTooltip']
        if tooltip and tooltip != '$undefined':
            card['value_tooltip'] = tooltip
            card['reward_categories'] = parse_category_bonuses_from_tooltip(tooltip)
    
    # Extract other fields
    if 'annualFee' in card_obj:
        card['annual_fee'] = parse_annual_fee(card_obj['annualFee'])
    
    if 'introOffer' in card_obj:
        card['intro_offer'] = card_obj['introOffer']
    
    return card


def extract_issuer_from_name(name: str) -> str:
    """Extract issuer from card name."""
    name_lower = name.lower()
    
    issuers = {
        'chase': 'Chase',
        'capital one': 'Capital One',
        'american express': 'American Express',
        'amex': 'American Express',
        'citi': 'Citi',
        'discover': 'Discover',
        'bank of america': 'Bank of America',
        'wells fargo': 'Wells Fargo',
        'us bank': 'US Bank',
        'barclays': 'Barclays',
    }
    
    for key, issuer in issuers.items():
        if key in name_lower:
            return issuer
    
    return 'Unknown'


def parse_annual_fee(fee_str: str) -> float:
    """Parse annual fee string to float."""
    if not fee_str:
        return 0.0
    
    # Handle "no annual fee" cases
    if re.search(r'no\s+annual\s+fee', fee_str, re.IGNORECASE):
        return 0.0
    
    # Extract numeric value
    match = re.search(r'\$?(\d{1,3}(?:,\d{3})*)', fee_str)
    if match:
        return float(match.group(1).replace(',', ''))
    
    return 0.0


def main():
    """Main function to extract NerdWallet rewards data."""
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    html_file = os.path.join(base_dir, 'data', 'nerdwallet_bonus_offers.html')
    output_dir = os.path.join(base_dir, 'data', 'scraped')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(html_file):
        logger.error(f"HTML file not found: {html_file}")
        return
    
    logger.info(f"Loading HTML file: {html_file}")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    logger.info("Extracting card data with reward categories...")
    cards = extract_cards_from_html(html_content)
    
    # Filter and clean results
    valid_cards = []
    for card in cards:
        if card.get('name') and len(card['name']) > 5:
            # Remove duplicates based on name
            if not any(c['name'] == card['name'] for c in valid_cards):
                valid_cards.append(card)
    
    logger.info(f"Found {len(valid_cards)} unique cards")
    
    # Analyze results
    cards_with_rewards = [c for c in valid_cards if c.get('reward_categories')]
    cards_with_tooltips = [c for c in valid_cards if c.get('value_tooltip')]
    
    # Save detailed results
    output_file = os.path.join(output_dir, 'nerdwallet_rewards_extracted.json')
    results = {
        'extraction_summary': {
            'total_cards': len(valid_cards),
            'cards_with_reward_categories': len(cards_with_rewards),
            'cards_with_tooltips': len(cards_with_tooltips),
            'extraction_method': 'enhanced_javascript_parsing'
        },
        'cards': valid_cards
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("NERDWALLET REWARDS EXTRACTION RESULTS")
    print("="*70)
    print(f"📊 Total cards found: {len(valid_cards)}")
    print(f"🎯 Cards with reward categories: {len(cards_with_rewards)}")
    print(f"💬 Cards with tooltips: {len(cards_with_tooltips)}")
    
    if cards_with_rewards:
        print(f"\n🏆 Top cards with reward categories:")
        for i, card in enumerate(cards_with_rewards[:10]):
            print(f"\n{i+1}. {card['name']} ({card['issuer']})")
            for reward_cat in card['reward_categories']:
                limit_text = f" (limit: ${reward_cat['limit']:,})" if reward_cat['limit'] else ""
                print(f"   • {reward_cat['category']}: {reward_cat['rate']}x{limit_text}")
            if card.get('value_tooltip'):
                print(f"   💬 Tooltip: {card['value_tooltip'][:80]}...")
    
    # Look specifically for Chase Sapphire Preferred
    chase_cards = [c for c in valid_cards if 'sapphire preferred' in c['name'].lower()]
    if chase_cards:
        print(f"\n🎯 CHASE SAPPHIRE PREFERRED FOUND:")
        card = chase_cards[0]
        print(f"   Name: {card['name']}")
        print(f"   Categories: {card.get('reward_categories', [])}")
        if card.get('value_tooltip'):
            print(f"   Full tooltip: {card['value_tooltip']}")
        
        # Test against expected categories from test file
        expected_categories = {
            "Dining & Restaurants": 3.0,
            "Groceries": 3.0,
            "Streaming Services": 3.0,
            "Travel": 2.0
        }
        
        # Convert new list format to dictionary for validation
        reward_categories_list = card.get('reward_categories', [])
        actual_categories = {cat['category']: cat['rate'] for cat in reward_categories_list}
        print(f"\n   ✅ Category validation:")
        for category, expected_rate in expected_categories.items():
            if category in actual_categories:
                actual_rate = actual_categories[category]
                status = "✅" if actual_rate == expected_rate else "❌"
                print(f"   {status} {category}: {actual_rate}x (expected {expected_rate}x)")
            else:
                print(f"   ❌ Missing: {category} (expected {expected_rate}x)")


if __name__ == '__main__':
    main() 