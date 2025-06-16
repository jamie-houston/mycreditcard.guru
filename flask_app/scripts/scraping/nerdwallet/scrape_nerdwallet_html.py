#!/usr/bin/env python3
"""
Script to scrape credit card bonus offers from downloaded NerdWallet HTML file.
This script handles the large HTML file and extracts structured credit card data.
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


def load_html_file(file_path: str) -> BeautifulSoup:
    """Load and parse the HTML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return BeautifulSoup(content, 'html.parser')
    except Exception as e:
        logger.error(f"Error loading HTML file: {e}")
        raise


def extract_card_data(soup: BeautifulSoup) -> List[Dict]:
    """Extract credit card data from the parsed HTML."""
    cards = []
    
    # Look for common patterns in NerdWallet card listings
    # These are common selectors for card information
    card_selectors = [
        '[data-testid*="card"]',
        '.card-item',
        '.product-card',
        '.offer-card',
        '[class*="card"]',
        '[data-card-name]'
    ]
    
    card_elements = []
    for selector in card_selectors:
        elements = soup.select(selector)
        if elements:
            logger.info(f"Found {len(elements)} elements with selector: {selector}")
            card_elements.extend(elements)
            break  # Use the first selector that finds elements
    
    if not card_elements:
        # Fallback: look for any elements that might contain card data
        logger.info("No card elements found with standard selectors, trying fallback approach")
        card_elements = soup.find_all(['div', 'article', 'section'], 
                                    class_=re.compile(r'card|product|offer', re.I))
    
    logger.info(f"Processing {len(card_elements)} potential card elements")
    
    for element in card_elements:
        try:
            card_data = extract_single_card(element)
            if card_data and card_data.get('name'):  # Only add if we found a name
                cards.append(card_data)
        except Exception as e:
            logger.warning(f"Error extracting card data: {e}")
            continue
    
    return cards


def extract_single_card(element) -> Optional[Dict]:
    """Extract data from a single card element."""
    card_data = {}
    
    # Try to find card name
    name_selectors = [
        '[data-card-name]',
        '.card-name',
        '.product-name',
        'h1', 'h2', 'h3', 'h4',
        '[class*="title"]',
        '[class*="name"]'
    ]
    
    card_name = None
    for selector in name_selectors:
        name_element = element.select_one(selector)
        if name_element:
            card_name = name_element.get_text(strip=True)
            if card_name and len(card_name) > 5:  # Reasonable name length
                break
    
    if not card_name:
        return None
    
    card_data['name'] = card_name
    
    # Try to find bonus offer information
    bonus_patterns = [
        r'(\$?\d{1,3}(?:,\d{3})*)\s*(?:bonus|cash\s*back|points|miles)',
        r'(?:earn|get|receive)\s*(\$?\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*(?:points|miles)'
    ]
    
    element_text = element.get_text()
    for pattern in bonus_patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            card_data['bonus_offer'] = match.group(1)
            break
    
    # Try to find spending requirement
    spending_patterns = [
        r'spend\s*\$?(\d{1,3}(?:,\d{3})*)',
        r'after\s*\$?(\d{1,3}(?:,\d{3})*)',
        r'within\s*\d+\s*months.*\$?(\d{1,3}(?:,\d{3})*)'
    ]
    
    for pattern in spending_patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            card_data['spending_requirement'] = f"${match.group(1)}"
            break
    
    # Try to find annual fee
    fee_patterns = [
        r'annual\s*fee[:\s]*\$?(\d{1,3}(?:,\d{3})*)',
        r'\$(\d{1,3}(?:,\d{3})*)\s*annual\s*fee',
        r'no\s*annual\s*fee'
    ]
    
    for pattern in fee_patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            if 'no annual fee' in match.group(0).lower():
                card_data['annual_fee'] = '$0'
            else:
                card_data['annual_fee'] = f"${match.group(1)}"
            break
    
    # Try to find APR information
    apr_patterns = [
        r'(\d{1,2}\.?\d*%?)\s*(?:-\s*\d{1,2}\.?\d*%?)?\s*(?:variable\s*)?apr',
        r'apr[:\s]*(\d{1,2}\.?\d*%?)'
    ]
    
    for pattern in apr_patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            card_data['apr'] = match.group(1)
            break
    
    # Try to find issuer/bank
    issuer_patterns = [
        r'(chase|capital\s*one|american\s*express|citi|discover|bank\s*of\s*america|wells\s*fargo)',
        r'by\s+([a-z\s]+(?:bank|credit|financial))',
    ]
    
    for pattern in issuer_patterns:
        match = re.search(pattern, element_text, re.IGNORECASE)
        if match:
            card_data['issuer'] = match.group(1).strip()
            break
    
    # Add raw text for debugging (first 200 chars)
    card_data['raw_text_sample'] = element_text[:200].strip()
    
    return card_data


def analyze_html_structure(soup: BeautifulSoup) -> Dict:
    """Analyze the HTML structure to understand the page layout."""
    analysis = {
        'title': soup.title.get_text() if soup.title else 'No title found',
        'total_elements': len(soup.find_all()),
        'potential_card_containers': []
    }
    
    # Look for common container patterns
    container_patterns = [
        ('data-testid containing "card"', soup.find_all(attrs={'data-testid': re.compile(r'card', re.I)})),
        ('class containing "card"', soup.find_all(class_=re.compile(r'card', re.I))),
        ('class containing "product"', soup.find_all(class_=re.compile(r'product', re.I))),
        ('class containing "offer"', soup.find_all(class_=re.compile(r'offer', re.I))),
    ]
    
    for pattern_name, elements in container_patterns:
        if elements:
            analysis['potential_card_containers'].append({
                'pattern': pattern_name,
                'count': len(elements),
                'sample_classes': [elem.get('class', []) for elem in elements[:3]]
            })
    
    return analysis


def main():
    """Main function to scrape the NerdWallet HTML file."""
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    html_file = os.path.join(base_dir, 'data', 'nerdwallet_bonus_offers.html')
    output_dir = os.path.join(base_dir, 'data', 'scraped')
    output_file = os.path.join(output_dir, 'scraped_nerdwallet_cards.json')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(html_file):
        logger.error(f"HTML file not found: {html_file}")
        return
    
    logger.info(f"Loading HTML file: {html_file}")
    soup = load_html_file(html_file)
    
    logger.info("Analyzing HTML structure...")
    analysis = analyze_html_structure(soup)
    logger.info(f"Page analysis: {json.dumps(analysis, indent=2)}")
    
    logger.info("Extracting card data...")
    cards = extract_card_data(soup)
    
    logger.info(f"Extracted {len(cards)} cards")
    
    # Save results
    results = {
        'analysis': analysis,
        'cards': cards,
        'extraction_summary': {
            'total_cards': len(cards),
            'cards_with_bonus': len([c for c in cards if c.get('bonus_offer')]),
            'cards_with_fee_info': len([c for c in cards if c.get('annual_fee')]),
            'cards_with_issuer': len([c for c in cards if c.get('issuer')])
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*50)
    print("SCRAPING SUMMARY")
    print("="*50)
    print(f"Total cards found: {len(cards)}")
    print(f"Cards with bonus offers: {len([c for c in cards if c.get('bonus_offer')])}")
    print(f"Cards with annual fee info: {len([c for c in cards if c.get('annual_fee')])}")
    print(f"Cards with issuer info: {len([c for c in cards if c.get('issuer')])}")
    
    if cards:
        print("\nSample cards:")
        for i, card in enumerate(cards[:3]):
            print(f"\n{i+1}. {card.get('name', 'Unknown')}")
            if card.get('bonus_offer'):
                print(f"   Bonus: {card['bonus_offer']}")
            if card.get('annual_fee'):
                print(f"   Annual Fee: {card['annual_fee']}")
            if card.get('issuer'):
                print(f"   Issuer: {card['issuer']}")


if __name__ == '__main__':
    main() 