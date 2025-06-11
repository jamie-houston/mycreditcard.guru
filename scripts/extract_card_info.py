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

def get_category_mapping_from_db() -> Dict[str, str]:
    """
    Get category mapping from database using aliases.
    Returns a dictionary mapping alias names to display names.
    """
    # Check if we're running in a test environment
    import sys
    if 'pytest' in sys.modules or 'unittest' in sys.modules:
        # Use fallback mapping for tests to ensure consistency
        return get_fallback_category_mapping()
    
    try:
        # Try to import Flask app and models
        import os
        import sys
        
        # Add Flask app directory to path if not already there
        flask_app_path = os.path.join(os.path.dirname(__file__), 'flask_app')
        if flask_app_path not in sys.path:
            sys.path.insert(0, flask_app_path)
        
        from app import create_app
        from app.models.category import Category
        
        # Create app context
        app = create_app('default')
        with app.app_context():
            categories = Category.get_active_categories()
            category_mapping = {}
            
            for category in categories:
                # Map the category name itself
                category_mapping[category.name.lower()] = category.display_name
                
                # Map all aliases
                aliases = category.get_aliases()
                for alias in aliases:
                    category_mapping[alias.lower()] = category.display_name
            
            return category_mapping
            
    except Exception as e:
        logger.warning(f"Could not load categories from database: {e}")
        # Fallback to hardcoded mapping if database is not available
        return get_fallback_category_mapping()

def get_fallback_category_mapping() -> Dict[str, str]:
    """
    Fallback category mapping when database is not available.
    """
    return {
        # Dining variations
        'dining': 'Dining & Restaurants',
        'restaurants': 'Dining & Restaurants', 
        'restaurant': 'Dining & Restaurants',
        'dining at restaurants': 'Dining & Restaurants',
        'takeout': 'Dining & Restaurants',
        'delivery service': 'Dining & Restaurants',
        
        # Travel variations
        'travel': 'Travel',
        'travel purchases': 'Travel',
        'travel purchased': 'Travel',
        'other travel': 'Travel',
        'travel booked': 'Travel',
        'hotels': 'Travel',
        'hotel': 'Travel',
        'rental cars': 'Travel',
        'car rentals': 'Travel',
        'flights': 'Travel',
        'airfare': 'Travel',
        'attractions': 'Travel',
        
        # Groceries variations
        'groceries': 'Groceries',
        'grocery': 'Groceries',
        'grocery stores': 'Groceries',
        'supermarkets': 'Groceries',
        'online groceries': 'Groceries',
        'wholesale clubs': 'Groceries',
        
        # Streaming variations
        'streaming': 'Streaming Services',
        'streaming services': 'Streaming Services',
        'select streaming services': 'Streaming Services',
        'streaming subscriptions': 'Streaming Services',
        
        # Gas variations
        'gas': 'Gas Stations',
        'gas stations': 'Gas Stations',
        'gasoline': 'Gas Stations',
        'fuel': 'Gas Stations',
        
        # Other categories
        'drugstore': 'Drugstores & Pharmacies',
        'drugstores': 'Drugstores & Pharmacies',
        'pharmacy': 'Drugstores & Pharmacies',
        'entertainment': 'Entertainment',
        'transit': 'Transportation',
        'transportation': 'Transportation',
        'rideshare': 'Transportation',
        'parking': 'Transportation',
        'tolls': 'Transportation',
        'trains': 'Transportation',
        'buses': 'Transportation',
        'paypal': 'PayPal',
        'amazon': 'Amazon',
        'online retail': 'Shopping',
        'online purchases': 'Shopping',
        'all purchases': 'Other',
        'everything else': 'Other',
        'everything': 'Other',
        'all other purchases': 'Other',
    }

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
    
    # First try the enhanced NerdWallet extraction for valueTooltip data
    nerdwallet_cards = extract_nerdwallet_card_data(html_content)
    if nerdwallet_cards:
        print(f"Found {len(nerdwallet_cards)} cards with category bonuses from NerdWallet valueTooltip data")
        return nerdwallet_cards
    
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
        
        # Try to extract reward categories from HTML content
        card_list = extract_reward_categories_from_html(soup, card_list)
        
        return card_list
    
    # As a last resort, try to extract cards based on HTML structure
    cards = extract_cards_from_html(soup)
    
    # Try to extract reward categories from HTML content
    cards = extract_reward_categories_from_html(soup, cards)
    
    return cards

def extract_card_names_from_html(soup: BeautifulSoup) -> List[str]:
    """Find credit card names in the HTML text content"""
    # Get full text
    text = soup.get_text()
    
    # Card pattern that matches common credit card naming patterns
    card_patterns = [
        # Pattern for Capital One cards
        r'(Capital One (?:Venture|Quicksilver|SavorOne|Savor Cash|Secured)(?:\s+Rewards)?(?:\s+Credit Card)?)',
        
        # Pattern for Chase cards
        r'(Chase (?:Sapphire|Freedom|Slate|Ink) (?:Preferred|Reserve|Unlimited|Flex|Cash|Business)(?:\s+Card)?)',
        
        # Pattern for Citi cards
        r'(Citi (?:Double Cash|Premier|Rewards\+|Custom Cash|Diamond Preferred)(?:\s+Card)?)',
        
        # Pattern for American Express cards
        r'(American Express (?:Gold|Platinum|Green|Blue Cash|Cash Magnet|Everyday)(?:\s+Card)?)',
        r'(Amex (?:Gold|Platinum|Green|Blue Cash|Cash Magnet|Everyday)(?:\s+Card)?)',
        
        # Pattern for Discover cards
        r'(Discover (?:it|Miles|Student|Secured|Business)(?:\s+Card)?)',
        
        # Generic pattern for cards with clear "Card" suffix
        r'([A-Z][a-z]+ [A-Z][a-z]+ (?:Preferred|Reserve|Premier|Cash|Rewards|Plus|Gold|Platinum|Sapphire|Explorer|Elite) Card)'
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
        
        # Ensure card names end with "Card" if they don't already
        if not (name.lower().endswith('card') or 'from american express' in name.lower()):
            name = name + " Card"
            
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
    
    # Extract category bonuses from valueTooltip (prioritized for NerdWallet)
    valueTooltip_bonuses = {}
    if 'valueTooltip' in card_json and card_json['valueTooltip'] and card_json['valueTooltip'] != "$undefined":
        valueTooltip_bonuses = parse_category_bonuses_from_tooltip(card_json['valueTooltip'])
        if valueTooltip_bonuses:
            card['reward_categories'].update(valueTooltip_bonuses)
            card['valueTooltip'] = card_json['valueTooltip']  # Keep original for debugging
    
    # Extract rewards rate (fallback if no valueTooltip bonuses found)
    if not valueTooltip_bonuses and 'rewardsRate' in card_json and card_json['rewardsRate']:
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
    # Reject if too long (likely a sentence, not a card name)
    if len(name) > 50:
        return False
        
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
        'perks', 'introductory', 'ongoing', 'what\'s the best',
        'what\'s the easiest', 'contact us', 'legal', 'about', 'privacy',
        'terms', 'our partners', 'for cash back', 'for travel', 'for balance',
        'for college', 'for business', 'for credit-building', 'interest-saving',
        'will automatically', 'matches all', 'earn in your first', 'says there',
        'doesn\'t', 'isn\'t', 'if you\'re', 'looking for', 'when you apply'
    ]
    
    name_lower = name.lower()
    
    # Minimum length for a card name
    if len(name) < 10:
        return False
    
    # Check exclusion keywords first
    if any(keyword in name_lower for keyword in exclude_keywords):
        return False
    
    # Must begin with a known issuer
    known_issuers = ['capital one', 'chase', 'citi', 'discover', 'american express', 'amex', 'bank of america', 'wells fargo', 'u.s. bank']
    if not any(name_lower.startswith(issuer) for issuer in known_issuers):
        return False
    
    # Must contain a card-like term
    return any(keyword in name_lower for keyword in card_keywords)

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

def normalize_card_name(name: str) -> str:
    """Normalize card name to its canonical form for better deduplication"""
    name = name.strip()
    
    # Standardize specific card names
    lower_name = name.lower()
    if ('capital one' in lower_name and 'venture' in lower_name and 'rewards' in lower_name):
        # Standardize to the canonical name
        return "Capital One Venture Rewards Card"
    elif ('chase' in lower_name and 'sapphire' in lower_name and 'preferred' in lower_name):
        return "Chase Sapphire Preferred Card"
    elif ('chase' in lower_name and 'sapphire' in lower_name and 'reserve' in lower_name):
        return "Chase Sapphire Reserve Card"
    elif ('citi' in lower_name and 'double cash' in lower_name):
        return "Citi Double Cash Card"
    elif ('discover' in lower_name and 'it' in lower_name):
        return "Discover it Card"
    
    # Standardize card suffixes
    if not lower_name.endswith('card'):
        if lower_name.endswith('credit card'):
            # Standardize to just "Card" suffix
            name = name[:-11] + "Card"
        else:
            # Add "Card" suffix if missing
            name = name + " Card"
    
    # Standardize issuer names
    if lower_name.startswith('amex '):
        name = 'American Express ' + name[5:]
    
    # Standardize spaces and punctuation
    name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
    name = name.replace('®', '').replace('℠', '').replace('™', '')  # Remove symbols
    
    return name

def filter_valid_cards(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out invalid card entries"""
    filtered_cards = []
    seen_names = set()
    
    # First normalize all card names
    for card in cards:
        # Store the reward categories before normalization
        reward_categories = card.get('reward_categories', {})
        
        # Normalize the card name
        card['name'] = normalize_card_name(card['name'])
        
        # Re-extract issuer in case the name was normalized
        card['issuer'] = extract_issuer_from_name(card['name'])
        
        # Ensure reward categories are preserved
        if not card.get('reward_categories') and reward_categories:
            card['reward_categories'] = reward_categories
    
    # Then deduplicate based on normalized names
    for card in cards:
        name_key = card['name'].lower()
        name_key_simple = re.sub(r'[^a-z0-9]', '', name_key)  # Remove all non-alphanumeric chars for comparison
        
        if is_valid_credit_card(card['name']) and name_key_simple not in seen_names:
            # Ensure all required fields exist
            if 'card_type' not in card:
                card['card_type'] = ''
            
            filtered_cards.append(card)
            seen_names.add(name_key_simple)
        elif card['reward_categories'] and name_key_simple in seen_names:
            # If we already have this card but this instance has reward categories, update the existing card
            existing_card = next((c for c in filtered_cards if re.sub(r'[^a-z0-9]', '', c['name'].lower()) == name_key_simple), None)
            if existing_card and not existing_card.get('reward_categories'):
                existing_card['reward_categories'] = card['reward_categories']
    
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

def parse_category_bonuses_from_tooltip(tooltip_text: str) -> Dict[str, float]:
    """
    Parse category bonuses from NerdWallet valueTooltip text.
    
    Handles patterns like:
    "5x on travel purchased through Chase Travel℠, 3x on dining, select streaming services and online groceries, 2x on all other travel purchases, 1x on all other purchases."
    
    Returns a dictionary mapping standardized category names to their multipliers.
    """
    if not tooltip_text or tooltip_text == "$undefined":
        return {}
    
    print(f"  Parsing tooltip: {tooltip_text}")
    
    # Category mapping from various text descriptions to standardized names
    category_mapping = get_category_mapping_from_db()
    
    categories = {}
    
    # Try different patterns to extract rewards info
    
    # Pattern 1: Simple X% on Y or Xx on Y pattern (most common)
    pattern1 = r'(\d+(?:\.\d+)?)[x%]\s+(?:cash ?back\s+)?(?:on|at|for)\s+([^,.;]+?)(?=\s*[,.;]|$)'
    for match in re.finditer(pattern1, tooltip_text, re.IGNORECASE):
        try:
            rate = float(match.group(1))
            category_text = match.group(2).strip().lower()
            
            # Validate rate is reasonable (less than 20%)
            if rate > 20:
                continue
                
            # Skip generic "all other" categories unless it's the only one
            if ('all other' in category_text or 'everything else' in category_text) and len(categories) > 0:
                continue
                
            # Find matching standard category
            found = False
            for key, standardized in category_mapping.items():
                if key in category_text:
                    categories[standardized] = rate
                    found = True
                    break
                    
            # If no standard category matched, use the text as is (cleaned up)
            if not found and len(category_text) > 3:
                # Clean up the category text
                clean_text = category_text.replace('u.s.', '').replace('select', '').strip()
                if clean_text:
                    categories[clean_text.title()] = rate
                
        except (ValueError, AttributeError):
            pass
    
    # Pattern 2: Earn X% cash back on Y pattern
    pattern2 = r'earn\s+(?:unlimited\s+)?(\d+(?:\.\d+)?)[x%]\s+cash\s+back\s+(?:on|at)\s+([^,.;]+?)(?=\s*[,.;]|$)'
    for match in re.finditer(pattern2, tooltip_text, re.IGNORECASE):
        try:
            rate = float(match.group(1))
            category_text = match.group(2).strip().lower()
            
            # Validate rate is reasonable (less than 20%)
            if rate > 20:
                continue
                
            # Find matching standard category
            found = False
            for key, standardized in category_mapping.items():
                if key in category_text:
                    categories[standardized] = rate
                    found = True
                    break
                    
            # If no standard category matched, use the text as is
            if not found and len(category_text) > 3:
                clean_text = category_text.replace('u.s.', '').replace('select', '').strip()
                if clean_text:
                    categories[clean_text.title()] = rate
                
        except (ValueError, AttributeError):
            pass
    
    # Pattern 3: Handle compound categories like "3x on dining, entertainment and streaming services"
    compound_pattern = r'(\d+(?:\.\d+)?)[x%]\s+(?:cash ?back\s+)?(?:on|at|for)\s+([^,.;]+(?:\s+and\s+[^,.;]+)*)'
    for match in re.finditer(compound_pattern, tooltip_text, re.IGNORECASE):
        try:
            rate = float(match.group(1))
            category_text = match.group(2).strip().lower()
            
            # Validate rate is reasonable (less than 20%)
            if rate > 20:
                continue
            
            # Split on "and" and commas to handle multiple categories
            category_parts = re.split(r'\s+and\s+|,\s*', category_text)
            
            for part in category_parts:
                part = part.strip()
                if len(part) > 3:
                    # Find matching standard category
                    found = False
                    for key, standardized in category_mapping.items():
                        if key in part:
                            categories[standardized] = rate
                            found = True
                            break
                            
                    # If no standard category matched, use the text as is
                    if not found:
                        clean_text = part.replace('u.s.', '').replace('select', '').strip()
                        if clean_text and not ('all other' in clean_text or 'everything else' in clean_text):
                            categories[clean_text.title()] = rate
                
        except (ValueError, AttributeError):
            pass

    print(f"  Extracted categories: {categories}")
    return categories

def extract_nerdwallet_card_data(html_content: str) -> List[Dict[str, Any]]:
    """
    Enhanced extraction specifically for NerdWallet's modern React-based structure.
    Looks for JSON data with valueTooltip information.
    """
    cards = []
    
    # Debug: Look for valueTooltip content in HTML
    print("\nSearching for valueTooltip data...")
    
    # Find all valueTooltip instances with meaningful content
    tooltip_pattern = r'"valueTooltip":\s*"([^"]+)"'
    tooltip_matches = re.findall(tooltip_pattern, html_content)
    
    print(f"Found {len(tooltip_matches)} valueTooltip instances")
    
    # For each tooltip, try to find the associated card name in the surrounding context
    for i, tooltip in enumerate(tooltip_matches):
        if tooltip and tooltip != "$undefined":
            print(f"\nTooltip {i+1}: {tooltip}")
            
            # Parse category bonuses from the tooltip
            category_bonuses = parse_category_bonuses_from_tooltip(tooltip)
            
            if category_bonuses:  
                print(f"  Extracted categories: {category_bonuses}")
                # Find the position of this tooltip in the HTML
                tooltip_pos = html_content.find(f'"valueTooltip":"{tooltip}"')
                
                if tooltip_pos != -1:
                    # Look for card name in a reasonable range around the tooltip
                    # Look backwards and forwards from the tooltip position
                    search_start = max(0, tooltip_pos - 5000)
                    search_end = min(len(html_content), tooltip_pos + 1000)
                    context = html_content[search_start:search_end]
                    
                    # Try to find annual fee in the context
                    annual_fee = 0
                    fee_match = re.search(r'"annualFee":\s*"([^"]+)"', context)
                    if fee_match:
                        fee_text = fee_match.group(1)
                        if '$0' in fee_text or 'No annual fee' in fee_text or 'no annual fee' in fee_text.lower():
                            annual_fee = 0
                        else:
                            fee_digit_match = re.search(r'\$(\d+(?:,\d{3})*)', fee_text)
                            if fee_digit_match:
                                annual_fee = int(fee_digit_match.group(1).replace(',', ''))
                    
                    # Look for name patterns in the context
                    name_patterns = [
                        r'"name":\s*"([^"]*(?:Chase Sapphire Preferred|Capital One|Citi|American Express|Discover|Bank of America|Wells Fargo|U\.S\. Bank)[^"]*)"',
                        r'"name":\s*"([^"]*Card[^"]*)"',  # Any name ending with "Card"
                        r'"name":\s*"([^"]{20,})"',       # Any reasonably long name
                    ]
                    
                    card_name = None
                    for pattern in name_patterns:
                        name_matches = re.findall(pattern, context, re.IGNORECASE)
                        for name in name_matches:
                            # Validate that this looks like a credit card name
                            if is_valid_credit_card(name):
                                card_name = name
                                print(f"  Found card name: {name}")
                                break
                        if card_name:
                            break
                    
                    if card_name:
                        # Also look for credit needed and rewards rate
                        credit_needed = ''
                        credit_match = re.search(r'"creditNeeded":\s*"([^"]+)"', context)
                        if credit_match:
                            credit_needed = credit_match.group(1)
                        
                        rewards_rate = ''
                        rewards_match = re.search(r'"rewardsRate":\s*"([^"]+)"', context)
                        if rewards_match:
                            rewards_rate = rewards_match.group(1)
                        
                        card = {
                            'name': card_name,
                            'issuer': extract_issuer_from_name(card_name),
                            'annual_fee': annual_fee,
                            'reward_categories': category_bonuses,
                            'rewards_rate': rewards_rate,
                            'valueTooltip': tooltip,  # Keep original for debugging
                            'ratings': {},
                            'credit_needed': credit_needed,
                            'intro_apr': '',
                            'regular_apr': '',
                            'intro_offer': '',
                            'card_type': '',
                            'card_network': ''
                        }
                        
                        # Check if we already have this card (avoid duplicates)
                        existing_card = next((c for c in cards if c['name'].lower() == card_name.lower()), None)
                        if not existing_card:
                            cards.append(card)
                            print(f"  Added card with reward categories")
                        elif not existing_card.get('reward_categories') and category_bonuses:
                            # Update existing card with reward categories if it doesn't have any
                            existing_card['reward_categories'] = category_bonuses
                            print(f"  Updated existing card with reward categories")
            else:
                print(f"  No categories found in tooltip")
    
    if not cards:
        print("No cards with reward categories found from valueTooltip data")
    
    return cards

def extract_reward_categories_from_html(soup: BeautifulSoup, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract reward categories from HTML content and add them to the cards"""
    print("\nAttempting to extract reward categories from HTML content...")
    
    # Create a map of card names to their indices
    card_name_map = {}
    for i, card in enumerate(cards):
        card_name = card['name'].lower()
        card_name_map[card_name] = i
        
        # Also add simplified versions of the name (without "card" suffix, etc.)
        simple_name = card_name.replace('card', '').replace('credit', '').strip()
        if simple_name != card_name:
            card_name_map[simple_name] = i
            
        # Add issuer-product combinations
        issuer = card['issuer'].lower()
        if ' ' in card_name:
            product = card_name.split(' ')[-2]  # Usually the distinguishing feature like "Sapphire", "Freedom", etc.
            if len(product) > 3:  # Meaningful product name
                issuer_product = f"{issuer} {product}".lower()
                card_name_map[issuer_product] = i
    
    # Find all text blocks that might contain rewards information
    rewards_text_blocks = []
    
    # Look for elements with rewards-related class names
    reward_elements = soup.select(
        '.rewards-rate, .rewardsRate, [class*="reward"], [class*="cashback"], [class*="points"], [class*="miles"]'
    )
    
    for element in reward_elements:
        text = element.get_text().strip()
        if len(text) > 10 and any(keyword in text.lower() for keyword in ['x on', '% on', 'cash back on', 'points on', 'miles on']):
            rewards_text_blocks.append(text)
    
    # Also look for paragraphs with rewards information
    paragraphs = soup.select('p')
    for p in paragraphs:
        text = p.get_text().strip()
        if len(text) > 10 and any(keyword in text.lower() for keyword in ['x on', '% on', 'cash back on', 'points on', 'miles on']):
            rewards_text_blocks.append(text)
    
    print(f"Found {len(rewards_text_blocks)} text blocks with potential reward information")
    
    # Map of text blocks to possible card matches (for better disambiguation)
    text_block_card_matches = {}
    
    # First pass: identify all possible card matches for each text block
    for i, rewards_text in enumerate(rewards_text_blocks):
        rewards_text_lower = rewards_text.lower()
        matches = []
        
        # Check for explicit card name mentions
        for card_name, idx in card_name_map.items():
            if card_name in rewards_text_lower:
                matches.append(idx)
        
        text_block_card_matches[i] = matches
    
    # Second pass: extract and assign categories
    cards_updated = 0
    for i, rewards_text in enumerate(rewards_text_blocks):
        print(f"\nAnalyzing rewards text block {i+1}:")
        print(f"  {rewards_text[:100]}...")  # Print first 100 chars
        
        # Extract categories
        categories = parse_category_bonuses_from_tooltip(rewards_text)
        
        if not categories:
            continue
            
        # Get pre-identified matches
        matches = text_block_card_matches[i]
        
        # If we have exactly one match, use it
        if len(matches) == 1:
            matched_card_idx = matches[0]
        # If we have multiple matches, try to disambiguate
        elif len(matches) > 1:
            # First try to find an exact match for the full card name
            exact_match = None
            for idx in matches:
                card_name = cards[idx]['name'].lower()
                if f'"{card_name}"' in rewards_text.lower() or f"'{card_name}'" in rewards_text.lower():
                    exact_match = idx
                    break
            
            matched_card_idx = exact_match if exact_match is not None else matches[0]
        # If no matches yet, try more advanced techniques
        else:
            matched_card_idx = None
            
            # Look for issuer mentions
            issuer_matches = {}
            for idx, card in enumerate(cards):
                issuer = card['issuer'].lower()
                if issuer in rewards_text.lower():
                    if issuer not in issuer_matches:
                        issuer_matches[issuer] = []
                    issuer_matches[issuer].append(idx)
            
            # If we have only one issuer with cards mentioned, and only one card from that issuer
            if len(issuer_matches) == 1:
                issuer, indices = next(iter(issuer_matches.items()))
                if len(indices) == 1:
                    matched_card_idx = indices[0]
            
            # As a last resort, try to associate with a nearby card based on position
            if matched_card_idx is None and i < len(cards):
                matched_card_idx = i
        
        if matched_card_idx is not None:
            # Update the card with reward categories
            card = cards[matched_card_idx]
            if not card.get('reward_categories'):
                card['reward_categories'] = {}
            card['reward_categories'].update(categories)
            print(f"  Updated {card['name']} with reward categories: {categories}")
            cards_updated += 1
    
    print(f"Updated {cards_updated} cards with reward categories from HTML content")
    return cards

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