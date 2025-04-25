#!/usr/bin/env python3
import re
import json
from bs4 import BeautifulSoup
import sys
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('extract_card_info')

def extract_card_info(html_file: str) -> List[Dict[str, Any]]:
    """
    Extract credit card information from NerdWallet HTML file.
    
    Args:
        html_file: Path to the HTML file
        
    Returns:
        List of dictionaries containing card information
    """
    print("Searching for credit card data in Material UI-based NerdWallet page...\n")
    
    try:
        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for embedded JSON data (common in modern React sites)
    cards_from_json = extract_cards_from_json(html_content)
    if cards_from_json:
        print(f"Found {len(cards_from_json)} cards from embedded JSON data")
        return cards_from_json
    
    # If no JSON data found, try searching for card names directly in the text
    card_names = extract_card_names_from_html(soup)
    if card_names:
        card_list = []
        for name in card_names:
            card_list.append({
                'name': name,
                'issuer': extract_issuer_from_name(name),
                'annual_fee': 0,
                'reward_categories': {},
                'ratings': {},
                'credit_needed': '',
                'intro_apr': '',
                'regular_apr': '',
                'intro_offer': '',
                'card_type': '',
                'card_network': ''
            })
        return card_list
    
    # As a last resort, try to extract cards based on HTML structure
    return extract_cards_from_html(soup)

def extract_card_names_from_html(soup: BeautifulSoup) -> List[str]:
    """Find credit card names in the HTML text content"""
    # Get full text
    text = soup.get_text()
    
    # Card pattern that matches common credit card naming patterns
    card_patterns = [
        # Pattern for cards like "Chase Sapphire Preferred® Card"
        r'([A-Z][a-z]+ [A-Z][a-z]+ (?:Preferred|Reserve|Premier|Cash|Rewards|Plus|Gold|Platinum|Sapphire|Explorer|One|World|Elite)(?:\s[A-Z][a-z]+)? Card)',
        # Pattern for cards with Credit Card suffix
        r'([A-Z][a-z]+ (?:Rewards|Cash|Travel|Platinum|Gold|Premier|Venture|Quicksilver|Freedom|Blue) Credit Card)',
        # Pattern for specific well-known cards
        r'(Capital One (?:Venture|Quicksilver|SavorOne))',
        r'(Chase (?:Sapphire|Freedom|Slate))',
        r'(Citi (?:Double Cash|Premier|Rewards\+))',
        r'(American Express (?:Gold|Platinum|Green) Card)',
        r'(Discover (?:it|Miles|Student))'
    ]
    
    # Find all card matches
    card_names = []
    for pattern in card_patterns:
        matches = re.findall(pattern, text)
        card_names.extend(matches)
    
    # Deduplicate and clean
    unique_cards = []
    seen = set()
    for name in card_names:
        name = name.strip()
        if name.lower() not in seen and is_valid_credit_card(name):
            unique_cards.append(name)
            seen.add(name.lower())
    
    return unique_cards

def extract_cards_from_json(html_content: str) -> List[Dict[str, Any]]:
    """Extract card data from embedded JSON in the HTML"""
    cards = []
    
    # Look for JSON data in script tags
    json_pattern = r'<script[^>]*?>\s*window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>'
    json_match = re.search(json_pattern, html_content, re.DOTALL)
    
    if not json_match:
        # Alternative pattern for newer NerdWallet React structure
        json_pattern = r'<script[^>]*?id="__NEXT_DATA__"[^>]*?>(.*?)</script>'
        json_match = re.search(json_pattern, html_content, re.DOTALL)
    
    if json_match:
        try:
            json_data = json.loads(json_match.group(1))
            
            # Search through JSON data for card information
            card_data = find_cards_in_json(json_data)
            if card_data:
                cards.extend(card_data)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
    
    # If we didn't find cards in the initial JSON, look for other JSON in the page
    if not cards:
        # Look for arrays of card data
        array_pattern = r'\[\s*\{\s*"name"\s*:\s*"[^"]*?".*?\}\s*\]'
        json_array_matches = re.findall(array_pattern, html_content, re.DOTALL)
        
        for array_match in json_array_matches:
            try:
                array_data = json.loads(array_match)
                if isinstance(array_data, list) and len(array_data) > 0 and 'name' in array_data[0]:
                    cards.extend(clean_card_data(array_data))
            except json.JSONDecodeError:
                continue
    
    return cards

def find_cards_in_json(json_data: Any, path: str = "", cards: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Recursively search through JSON data to find card information"""
    if cards is None:
        cards = []
    
    if isinstance(json_data, dict):
        # Check if this dict looks like a card
        if 'name' in json_data and ('annualFee' in json_data or 'annual_fee' in json_data or 'creditNeeded' in json_data):
            cards.append(clean_card_json(json_data))
        
        # Look for properties that might contain card info
        for key, value in json_data.items():
            if key in ('cards', 'creditCards', 'products', 'productsList', 'items'):
                if isinstance(value, list) and len(value) > 0:
                    for item in value:
                        if isinstance(item, dict) and 'name' in item:
                            cards.append(clean_card_json(item))
            else:
                # Recursively search nested objects
                find_cards_in_json(value, f"{path}.{key}" if path else key, cards)
    
    elif isinstance(json_data, list):
        # Check if this looks like a list of cards
        if len(json_data) > 0 and isinstance(json_data[0], dict) and 'name' in json_data[0]:
            for item in json_data:
                if isinstance(item, dict) and 'name' in item:
                    cards.append(clean_card_json(item))
        else:
            # Recursively search each list item
            for i, item in enumerate(json_data):
                find_cards_in_json(item, f"{path}[{i}]", cards)
    
    return cards

def clean_card_json(card_json: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and normalize card JSON data"""
    card = {
        'name': card_json.get('name', ''),
        'issuer': extract_issuer_from_name(card_json.get('name', '')),
        'annual_fee': 0,
        'reward_categories': {},
        'ratings': {},
        'credit_needed': '',
        'intro_apr': '',
        'regular_apr': '',
        'intro_offer': '',
        'card_type': '',
        'card_network': ''
    }
    
    # Extract annual fee
    if 'annualFee' in card_json:
        fee_text = card_json['annualFee']
        if isinstance(fee_text, str):
            if '$0' in fee_text or 'No annual fee' in fee_text or 'no annual fee' in fee_text.lower():
                card['annual_fee'] = 0
            else:
                fee_match = re.search(r'\$(\d+(?:,\d{3})*)', fee_text)
                if fee_match:
                    card['annual_fee'] = int(fee_match.group(1).replace(',', ''))
    elif 'annual_fee' in card_json:
        fee = card_json['annual_fee']
        if isinstance(fee, (int, float)):
            card['annual_fee'] = fee
        elif isinstance(fee, str) and fee.isdigit():
            card['annual_fee'] = int(fee)
    
    # Extract rewards rate
    if 'rewardsRate' in card_json and card_json['rewardsRate']:
        card['rewards_rate'] = card_json['rewardsRate']
        
        # Try to parse rewards into categories
        if isinstance(card['rewards_rate'], str):
            rewards_text = card['rewards_rate']
            # Look for patterns like "5% on categories" or "3X points on dining"
            patterns = [
                r'(\d+(?:\.\d+)?)% (?:cash ?back|rewards?|points?) (?:on|for) ([^.;]+)',
                r'(\d+)X? (?:points?|miles?|rewards?) (?:on|for) ([^.;]+)',
                r'(\d+) ?% (?:back|cash ?back) (?:on|in|for) ([^.;]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, rewards_text)
                for rate, category in matches:
                    try:
                        rate_value = float(rate.replace('X', '').strip())
                        category = category.strip().lower()
                        card['reward_categories'][category] = rate_value
                    except (ValueError, AttributeError):
                        pass
    
    # Extract credit needed
    if 'creditNeeded' in card_json:
        card['credit_needed'] = card_json['creditNeeded']
    
    # Extract intro APR
    if 'introApr' in card_json:
        card['intro_apr'] = card_json['introApr']
    
    # Extract regular APR
    if 'regularApr' in card_json:
        card['regular_apr'] = card_json['regularApr']
    
    # Extract intro offer
    if 'introOffer' in card_json:
        card['intro_offer'] = card_json['introOffer']
    elif 'bonus' in card_json:
        card['intro_offer'] = card_json['bonus']
    
    # Extract card type/category
    if 'category' in card_json:
        card['card_type'] = card_json['category']
    elif 'cardType' in card_json:
        card['card_type'] = card_json['cardType']
    
    # Extract card network
    if 'network' in card_json:
        card['card_network'] = card_json['network']
    
    return card

def extract_cards_from_html(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract card data directly from the HTML"""
    cards = []
    
    # Look for tables - specifically the summary tables
    tables = soup.select('.MuiTable-root')
    for table in tables:
        # Check if this looks like a credit card table
        headers = [th.get_text().strip().lower() for th in table.select('th')]
        if any(term in ' '.join(headers) for term in ['annual fee', 'rewards rate', 'card name']):
            extracted_cards = extract_cards_from_table(table)
            cards.extend(extracted_cards)
    
    # Look for card containers (common in MUI layouts)
    card_containers = soup.select('.MuiPaper-root, div[class*="card-container"], div[class*="product-card"]')
    for container in card_containers:
        card = extract_card_from_container(container)
        if card and is_valid_credit_card(card['name']):
            cards.append(card)
    
    # Look for direct links to card pages, which often show card names
    card_links = []
    for link in soup.select('a[href*="credit-card"], a[href*="creditcard"]'):
        card_name = link.get_text().strip()
        if is_valid_credit_card(card_name):
            card_links.append({
                'name': card_name,
                'issuer': extract_issuer_from_name(card_name),
                'annual_fee': 0,
                'reward_categories': {},
                'credit_needed': '',
                'intro_apr': '',
                'regular_apr': '',
                'intro_offer': '',
                'card_type': '',
                'card_network': ''
            })
    
    # Add unique card names from links
    seen_names = {card['name'].lower() for card in cards}
    for link_card in card_links:
        if link_card['name'].lower() not in seen_names:
            cards.append(link_card)
            seen_names.add(link_card['name'].lower())
    
    return filter_valid_cards(cards)

def extract_cards_from_table(table: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract card data from a table"""
    cards = []
    
    # Get header indices
    headers = [th.get_text().strip().lower() for th in table.select('th')]
    name_idx = next((i for i, h in enumerate(headers) if 'card name' in h or 'name' in h), None)
    fee_idx = next((i for i, h in enumerate(headers) if 'annual fee' in h), None)
    rewards_idx = next((i for i, h in enumerate(headers) if 'rewards' in h), None)
    intro_apr_idx = next((i for i, h in enumerate(headers) if 'intro apr' in h), None)
    
    if name_idx is None:
        return []
    
    # Process each row
    for row in table.select('tbody tr'):
        cells = row.select('td')
        if len(cells) <= name_idx:
            continue
        
        card_name = cells[name_idx].get_text().strip()
        if not is_valid_credit_card(card_name):
            continue
        
        card = {
            'name': card_name,
            'issuer': extract_issuer_from_name(card_name),
            'annual_fee': 0,
            'reward_categories': {},
            'credit_needed': '',
            'intro_apr': '',
            'regular_apr': '',
            'intro_offer': '',
            'card_type': '',
            'card_network': ''
        }
        
        # Extract annual fee
        if fee_idx is not None and len(cells) > fee_idx:
            fee_text = cells[fee_idx].get_text().strip()
            if '$0' in fee_text or 'No annual fee' in fee_text or 'no annual fee' in fee_text.lower():
                card['annual_fee'] = 0
            else:
                fee_match = re.search(r'\$(\d+(?:,\d{3})*)', fee_text)
                if fee_match:
                    card['annual_fee'] = int(fee_match.group(1).replace(',', ''))
        
        # Extract rewards rate
        if rewards_idx is not None and len(cells) > rewards_idx:
            rewards_text = cells[rewards_idx].get_text().strip()
            card['rewards_rate'] = rewards_text
            
            # Try to parse rewards into categories
            patterns = [
                r'(\d+(?:\.\d+)?)% (?:cash ?back|rewards?|points?) (?:on|for) ([^.;]+)',
                r'(\d+)X? (?:points?|miles?|rewards?) (?:on|for) ([^.;]+)',
                r'(\d+) ?% (?:back|cash ?back) (?:on|in|for) ([^.;]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, rewards_text)
                for rate, category in matches:
                    try:
                        rate_value = float(rate.replace('X', '').strip())
                        category = category.strip().lower()
                        card['reward_categories'][category] = rate_value
                    except (ValueError, AttributeError):
                        pass
        
        # Extract intro APR
        if intro_apr_idx is not None and len(cells) > intro_apr_idx:
            card['intro_apr'] = cells[intro_apr_idx].get_text().strip()
        
        cards.append(card)
    
    return cards

def extract_card_from_container(container: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extract card data from a UI container"""
    # Look for card name
    name_elem = container.select_one('h2, h3, h4, [class*="title"], [class*="name"]')
    if not name_elem:
        return None
    
    card_name = name_elem.get_text().strip()
    if not card_name or len(card_name) < 5:
        return None
    
    # Filter out section headers and navigation elements
    if not is_valid_credit_card(card_name):
        return None
    
    # Basic card info
    card = {
        'name': card_name,
        'issuer': extract_issuer_from_name(card_name),
        'annual_fee': 0,
        'reward_categories': {},
        'credit_needed': '',
        'intro_apr': '',
        'regular_apr': '',
        'intro_offer': '',
        'card_type': '',
        'card_network': ''
    }
    
    # Extract annual fee
    fee_elem = container.select_one('[class*="annual-fee"], [class*="annualFee"], span:contains("Annual fee")')
    if fee_elem:
        fee_text = fee_elem.get_text().strip()
        if '$0' in fee_text or 'No annual fee' in fee_text or 'no annual fee' in fee_text.lower():
            card['annual_fee'] = 0
        else:
            fee_match = re.search(r'\$(\d+(?:,\d{3})*)', fee_text)
            if fee_match:
                card['annual_fee'] = int(fee_match.group(1).replace(',', ''))
    
    # Extract rewards rate
    rewards_elem = container.select_one('[class*="rewards-rate"], [class*="rewardsRate"]')
    if rewards_elem:
        rewards_text = rewards_elem.get_text().strip()
        card['rewards_rate'] = rewards_text
        
        # Try to parse rewards into categories
        patterns = [
            r'(\d+(?:\.\d+)?)% (?:cash ?back|rewards?|points?) (?:on|for) ([^.;]+)',
            r'(\d+)X? (?:points?|miles?|rewards?) (?:on|for) ([^.;]+)',
            r'(\d+) ?% (?:back|cash ?back) (?:on|in|for) ([^.;]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, rewards_text)
            for rate, category in matches:
                try:
                    rate_value = float(rate.replace('X', '').strip())
                    category = category.strip().lower()
                    card['reward_categories'][category] = rate_value
                except (ValueError, AttributeError):
                    pass
    
    # Look for credit needed info
    credit_elem = container.select_one('[class*="credit-needed"], [class*="creditNeeded"]')
    if credit_elem:
        card['credit_needed'] = credit_elem.get_text().strip()
    
    # Look for APR information
    apr_elem = container.select_one('[class*="apr"], [class*="APR"]')
    if apr_elem:
        apr_text = apr_elem.get_text().strip()
        if 'intro' in apr_text.lower():
            card['intro_apr'] = apr_text
        else:
            card['regular_apr'] = apr_text
    
    return card

def is_valid_credit_card(name: str) -> bool:
    """Check if a name is likely to be a credit card"""
    # Common credit card keywords
    card_keywords = [
        'credit card', 'card', 'visa', 'mastercard', 'amex', 'discover',
        'rewards', 'cash back', 'platinum', 'gold', 'sapphire', 'preferred',
        'reserve', 'freedom', 'quicksilver', 'venture', 'blue', 'slate',
        'double cash', 'premier', 'southwest', 'united', 'delta', 'aadvantage'
    ]
    
    # Section headers and UI elements to exclude
    exclude_keywords = [
        'why trust', 'breakdown', 'details', 'take', 'faq', 'compare',
        'annual fee', 'credit-building', 'interest rate', 'sign-up bonus',
        'perks', 'introductory', 'ongoing', 'rewards', 'what\'s the best',
        'what\'s the easiest', 'contact us', 'legal', 'about', 'privacy',
        'terms', 'our partners', 'for cash back', 'for travel', 'for balance',
        'for college', 'for business', 'for credit-building', 'interest-saving'
    ]
    
    name_lower = name.lower()
    
    # Minimum length for a card name
    if len(name) < 10:
        return False
    
    # Check exclusion keywords first
    if any(keyword in name_lower for keyword in exclude_keywords):
        return False
    
    # Check for card type words
    return (
        # Check for common card indicators
        any(keyword in name_lower for keyword in card_keywords) or
        # Check for issuer names
        any(issuer.lower() in name_lower for issuer in common_issuers) or
        # Check for card naming patterns (e.g., "Chase Sapphire Preferred®")
        bool(re.search(r'[A-Z][a-z]+ (?:[A-Z][a-z]+ )+(?:Card|Preferred|Reserve)', name))
    )

def extract_issuer_from_name(card_name: str) -> str:
    """Extract the card issuer from the card name"""
    # Ensure common_issuers is accessible
    global common_issuers
    
    for issuer in common_issuers:
        if issuer.lower() in card_name.lower():
            # Special case for American Express abbreviation
            if issuer == 'Amex' and 'american express' not in card_name.lower():
                return 'American Express'
            return issuer
    
    return "Unknown Issuer"

def clean_card_data(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean up a list of card data"""
    return [clean_card_json(card) for card in cards]

def filter_valid_cards(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out invalid card entries"""
    filtered_cards = []
    seen_names = set()
    
    for card in cards:
        card_name = card['name'].lower()
        if is_valid_credit_card(card['name']) and card_name not in seen_names:
            # Ensure all required fields exist
            if 'card_type' not in card:
                card['card_type'] = ''
            
            filtered_cards.append(card)
            seen_names.add(card_name)
    
    return filtered_cards

def display_card_info(cards: List[Dict[str, Any]]) -> None:
    """Display extracted card information"""
    if not cards:
        print("No cards found")
        return
    
    print(f"\nExtracted {len(cards)} credit cards:")
    print("\n" + "="*60)
    
    for i, card in enumerate(cards, 1):
        print(f"\n{i}. {card['name']}")
        print("-" * 40)
        
        # Display issuer
        if card['issuer']:
            print(f"Issuer: {card['issuer']}")
        
        # Display annual fee
        if isinstance(card['annual_fee'], (int, float)):
            if card['annual_fee'] == 0:
                print("Annual Fee: No annual fee")
            else:
                print(f"Annual Fee: ${card['annual_fee']}")
        elif card['annual_fee']:
            print(f"Annual Fee: {card['annual_fee']}")
        
        # Display rewards
        if 'rewards_rate' in card and card['rewards_rate']:
            print(f"Rewards Rate: {card['rewards_rate']}")
        elif card['reward_categories']:
            print("Reward Categories:")
            for category, rate in card['reward_categories'].items():
                print(f"  • {rate}% on {category}")
        
        # Display credit needed
        if card['credit_needed']:
            print(f"Credit Score Needed: {card['credit_needed']}")
        
        # Display APR information
        if card['intro_apr']:
            print(f"Intro APR: {card['intro_apr']}")
        
        if card['regular_apr']:
            print(f"Regular APR: {card['regular_apr']}")
        
        # Display intro offer
        if card['intro_offer']:
            print(f"Intro Offer: {card['intro_offer']}")
        
        # Display card type
        if card['card_type']:
            print(f"Card Type: {card['card_type']}")
        
        # Display card network
        if card['card_network']:
            print(f"Card Network: {card['card_network']}")
        
        print("="*60)

# Common issuers to look for
common_issuers = [
    'Chase', 'American Express', 'Amex', 'Citi', 'Capital One', 
    'Discover', 'Bank of America', 'Wells Fargo', 'U.S. Bank'
]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cards = extract_card_info(sys.argv[1])
    else:
        cards = extract_card_info("nerdwallet_debug.html")
    
    display_card_info(cards)
    
    # Save to JSON
    with open('extracted_cards.json', 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2)
    
    print(f"\nSaved card data to extracted_cards.json") 