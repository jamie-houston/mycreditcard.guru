#!/usr/bin/env python3
"""
Enhanced script to scrape credit card reward categories from downloaded NerdWallet HTML file.
This script extracts detailed reward information including category bonuses and rates.
"""

import os
import sys
import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging

# Add the flask_app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_category_bonuses_from_tooltip(tooltip_text: str) -> Dict[str, float]:
    """
    Parse category bonuses from NerdWallet valueTooltip text.
    Based on the test_category_bonuses.py functionality.
    """
    if not tooltip_text or tooltip_text in [None, "", "$undefined"]:
        return {}
    
    # Clean up the text
    text = tooltip_text.replace('℠', '').replace('®', '').replace('™', '')
    text = re.sub(r'\s+', ' ', text).strip()
    
    categories = {}
    
    # Category mapping - standardized names
    category_mappings = {
        # Dining
        r'\b(?:dining|restaurants?)\b': 'Dining & Restaurants',
        
        # Travel
        r'\b(?:travel|flights?|hotels?|car rentals?)\b': 'Travel',
        
        # Gas
        r'\b(?:gas|gas stations?|fuel)\b': 'Gas Stations',
        
        # Groceries
        r'\b(?:groceries|supermarkets?|grocery stores?)\b': 'Groceries',
        
        # Streaming
        r'\b(?:streaming|streaming services?)\b': 'Streaming Services',
        
        # Entertainment
        r'\b(?:entertainment)\b': 'Entertainment',
        
        # Drugstores
        r'\b(?:drugstores?|pharmacies)\b': 'Drugstores',
        
        # Transit
        r'\b(?:transit|taxis?|rideshare|parking|tolls?|trains?|buses?)\b': 'Transit',
        
        # Other/Base rate
        r'\b(?:all other purchases?|other purchases?|everything else)\b': 'Other',
    }
    
    # Pattern to match reward rates with categories
    # Matches patterns like "5x on dining", "3% on gas stations", "2% cash back on groceries"
    rate_patterns = [
        r'(\d+(?:\.\d+)?)[x%]\s+(?:cash back\s+)?(?:at\s+|on\s+)([^,\.]+?)(?:[,\.]|$)',
        r'(\d+(?:\.\d+)?)[x%]\s+(?:cash back\s+)?([^,\.]+?)(?:[,\.]|$)',
        r'earn\s+(\d+(?:\.\d+)?)[x%]\s+(?:cash back\s+)?(?:at\s+|on\s+)([^,\.]+?)(?:[,\.]|$)',
    ]
    
    for pattern in rate_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            rate = float(match.group(1))
            category_text = match.group(2).strip()
            
            # Map the category text to standardized names
            for category_pattern, standard_name in category_mappings.items():
                if re.search(category_pattern, category_text, re.IGNORECASE):
                    # Only keep the highest rate for each category
                    if standard_name not in categories or categories[standard_name] < rate:
                        categories[standard_name] = rate
                    break
    
    # Special handling for compound categories like "dining, entertainment and streaming"
    compound_patterns = [
        r'(\d+(?:\.\d+)?)[x%]\s+(?:cash back\s+)?(?:at\s+|on\s+)([^\.]+?)(?:and\s+([^\.]+?))?(?:[,\.]|$)',
    ]
    
    for pattern in compound_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            rate = float(match.group(1))
            category_parts = [match.group(2)]
            if match.group(3):
                category_parts.append(match.group(3))
            
            # Split on commas and "and"
            all_categories = []
            for part in category_parts:
                all_categories.extend(re.split(r',\s*(?:and\s+)?|and\s+', part))
            
            for category_text in all_categories:
                category_text = category_text.strip()
                for category_pattern, standard_name in category_mappings.items():
                    if re.search(category_pattern, category_text, re.IGNORECASE):
                        if standard_name not in categories or categories[standard_name] < rate:
                            categories[standard_name] = rate
                        break
    
    return categories


def extract_reward_data_from_html(soup: BeautifulSoup) -> List[Dict]:
    """Extract detailed reward data from NerdWallet HTML."""
    cards = []
    
    # Look for JSON data in script tags (common in modern web apps)
    script_tags = soup.find_all('script', type='application/json')
    for script in script_tags:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and 'props' in data:
                # Navigate through the data structure to find card data
                cards.extend(extract_cards_from_json_data(data))
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Look for inline JavaScript with card data
    script_tags = soup.find_all('script')
    for script in script_tags:
        if script.string:
            # Look for patterns like window.__INITIAL_STATE__ or similar
            js_content = script.string
            
            # Extract JSON objects from JavaScript
            json_matches = re.finditer(r'({[^{}]*"valueTooltip"[^{}]*})', js_content)
            for match in json_matches:
                try:
                    card_data = json.loads(match.group(1))
                    if 'name' in card_data:
                        cards.append(extract_single_card_from_json(card_data))
                except json.JSONDecodeError:
                    continue
    
    # Fallback: Look for data attributes in HTML elements
    card_elements = soup.find_all(attrs={'data-card-name': True})
    for element in card_elements:
        card_data = extract_card_from_element(element)
        if card_data:
            cards.append(card_data)
    
    # Another fallback: Look for elements with valueTooltip data
    tooltip_elements = soup.find_all(attrs={'data-value-tooltip': True})
    for element in tooltip_elements:
        card_data = extract_card_from_tooltip_element(element)
        if card_data:
            cards.append(card_data)
    
    return [card for card in cards if card]  # Filter out None values


def extract_cards_from_json_data(data: Dict) -> List[Dict]:
    """Extract cards from nested JSON data structure."""
    cards = []
    
    def find_cards_recursive(obj, path=""):
        if isinstance(obj, dict):
            # Check if this looks like a card object
            if 'name' in obj and ('valueTooltip' in obj or 'annualFee' in obj):
                card = extract_single_card_from_json(obj)
                if card:
                    cards.append(card)
            
            # Recurse into nested objects
            for key, value in obj.items():
                find_cards_recursive(value, f"{path}.{key}")
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                find_cards_recursive(item, f"{path}[{i}]")
    
    find_cards_recursive(data)
    return cards


def extract_single_card_from_json(card_data: Dict) -> Optional[Dict]:
    """Extract a single card from JSON data."""
    if not card_data.get('name'):
        return None
    
    name = card_data['name']
    
    # Skip generic entries
    if any(skip in name.lower() for skip in ['find the right', 'compare', 'get started']):
        return None
    
    # Extract basic info
    card = {
        'name': name,
        'issuer': extract_issuer_from_name(name),
        'annual_fee': parse_annual_fee(card_data.get('annualFee', '')),
        'reward_categories': {},
        'raw_data': card_data
    }
    
    # Extract reward categories from valueTooltip
    if 'valueTooltip' in card_data:
        tooltip = card_data['valueTooltip']
        if tooltip and tooltip != '$undefined':
            card['reward_categories'] = parse_category_bonuses_from_tooltip(tooltip)
            card['value_tooltip'] = tooltip
    
    # Extract other fields if available
    if 'introOffer' in card_data:
        card['intro_offer'] = card_data['introOffer']
    
    if 'regularApr' in card_data:
        card['apr'] = card_data['regularApr']
    
    return card


def extract_card_from_element(element) -> Optional[Dict]:
    """Extract card data from HTML element."""
    name = element.get('data-card-name')
    if not name:
        return None
    
    card = {
        'name': name,
        'issuer': extract_issuer_from_name(name),
        'reward_categories': {},
        'raw_element_attrs': dict(element.attrs)
    }
    
    # Look for tooltip data
    tooltip = element.get('data-value-tooltip') or element.get('title')
    if tooltip:
        card['reward_categories'] = parse_category_bonuses_from_tooltip(tooltip)
        card['value_tooltip'] = tooltip
    
    return card


def extract_card_from_tooltip_element(element) -> Optional[Dict]:
    """Extract card data from element with tooltip."""
    tooltip = element.get('data-value-tooltip')
    if not tooltip:
        return None
    
    # Try to find the card name from nearby elements
    name = None
    
    # Look for card name in parent or sibling elements
    parent = element.parent
    if parent:
        name_element = parent.find(attrs={'data-card-name': True})
        if name_element:
            name = name_element.get('data-card-name')
        else:
            # Look for text that might be a card name
            text_elements = parent.find_all(text=True)
            for text in text_elements:
                text = text.strip()
                if len(text) > 10 and any(word in text.lower() for word in ['card', 'credit']):
                    name = text
                    break
    
    if not name:
        return None
    
    card = {
        'name': name,
        'issuer': extract_issuer_from_name(name),
        'reward_categories': parse_category_bonuses_from_tooltip(tooltip),
        'value_tooltip': tooltip,
        'raw_element_attrs': dict(element.attrs)
    }
    
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
    """Main function to scrape NerdWallet rewards data."""
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
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    logger.info("Extracting reward data from HTML...")
    cards = extract_reward_data_from_html(soup)
    
    logger.info(f"Extracted {len(cards)} cards with reward data")
    
    # Analyze the results
    cards_with_rewards = [c for c in cards if c.get('reward_categories')]
    cards_with_tooltips = [c for c in cards if c.get('value_tooltip')]
    
    # Save detailed results
    output_file = os.path.join(output_dir, 'nerdwallet_rewards_detailed.json')
    results = {
        'extraction_summary': {
            'total_cards': len(cards),
            'cards_with_reward_categories': len(cards_with_rewards),
            'cards_with_tooltips': len(cards_with_tooltips),
            'extraction_method': 'enhanced_html_parsing'
        },
        'cards': cards
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Detailed results saved to: {output_file}")
    
    # Save simplified version for easy review
    simplified_cards = []
    for card in cards:
        simplified = {
            'name': card['name'],
            'issuer': card['issuer'],
            'annual_fee': card.get('annual_fee', 0),
            'reward_categories': card.get('reward_categories', {}),
            'has_tooltip': bool(card.get('value_tooltip'))
        }
        if card.get('value_tooltip'):
            simplified['tooltip_sample'] = card['value_tooltip'][:100] + '...' if len(card['value_tooltip']) > 100 else card['value_tooltip']
        simplified_cards.append(simplified)
    
    simplified_file = os.path.join(output_dir, 'nerdwallet_rewards_summary.json')
    with open(simplified_file, 'w', encoding='utf-8') as f:
        json.dump(simplified_cards, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Summary saved to: {simplified_file}")
    
    # Print summary
    print("\n" + "="*60)
    print("NERDWALLET REWARDS SCRAPING SUMMARY")
    print("="*60)
    print(f"Total cards found: {len(cards)}")
    print(f"Cards with reward categories: {len(cards_with_rewards)}")
    print(f"Cards with tooltips: {len(cards_with_tooltips)}")
    
    if cards_with_rewards:
        print(f"\nSample cards with reward categories:")
        for i, card in enumerate(cards_with_rewards[:5]):
            print(f"\n{i+1}. {card['name']} ({card['issuer']})")
            for category, rate in card['reward_categories'].items():
                print(f"   {category}: {rate}x")
            if card.get('value_tooltip'):
                print(f"   Tooltip: {card['value_tooltip'][:80]}...")
    
    # Test with Chase Sapphire Preferred example
    chase_cards = [c for c in cards if 'sapphire preferred' in c['name'].lower()]
    if chase_cards:
        print(f"\n🎯 Found Chase Sapphire Preferred:")
        card = chase_cards[0]
        print(f"   Name: {card['name']}")
        print(f"   Categories: {card.get('reward_categories', {})}")
        if card.get('value_tooltip'):
            print(f"   Tooltip: {card['value_tooltip']}")


if __name__ == '__main__':
    main() 