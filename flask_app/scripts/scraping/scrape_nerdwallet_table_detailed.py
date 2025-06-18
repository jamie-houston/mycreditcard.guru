#!/usr/bin/env python3
"""
Targeted scraper for the NerdWallet bonus offers table HTML.
This script extracts credit card data including reward categories from aria-label tooltips.
"""

import os
import sys
import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
import logging

# Add the flask_app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_category_bonuses_from_tooltip(tooltip_text: str) -> Dict[str, float]:
    """
    Parse category bonuses from NerdWallet aria-label tooltip text.
    Enhanced version based on test_category_bonuses.py.
    """
    if not tooltip_text or tooltip_text.strip() == "":
        return {}
    
    # Clean up the text
    text = tooltip_text.replace('℠', '').replace('®', '').replace('™', '')
    text = re.sub(r'\s+', ' ', text).strip()
    
    categories = {}
    
    # Category mapping - standardized names matching your database
    category_mappings = {
        # Dining
        r'\b(?:dining|restaurants?)\b': 'Dining & Restaurants',
        
        # Travel (including hotels, flights, car rentals)
        r'\b(?:travel|flights?|hotels?|vacation rentals?|car rentals?)\b': 'Travel',
        
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
        r'\b(?:all other purchases?|other purchases?|everything else|every purchase)\b': 'Other',
    }
    
    # Enhanced patterns to match various formats from NerdWallet
    rate_patterns = [
        # "Earn unlimited 2X miles on every purchase"
        r'earn\s+(?:unlimited\s+)?(\d+(?:\.\d+)?)x\s+(?:miles|points|cash back)\s+on\s+([^,\.]+?)(?:[,\.]|$)',
        
        # "Earn 5X miles on hotels, vacation rentals and rental cars"
        r'earn\s+(\d+(?:\.\d+)?)x\s+(?:miles|points|cash back)\s+on\s+([^,\.]+?)(?:[,\.]|$)',
        
        # "2x on all other travel purchases" - prioritize this over general travel
        r'(\d+(?:\.\d+)?)x\s+on\s+(all other [^,\.]+?)(?:[,\.]|$)',
        
        # Specific pattern for compound categories like "3x on dining, select streaming services and online groceries"
        r'(\d+(?:\.\d+)?)x\s+on\s+(dining,\s*select streaming services(?:\s+and\s+[^,\.]+)*)',
        
        # "3x on dining, select streaming services and online groceries" - but skip "purchased through" variants
        r'(\d+(?:\.\d+)?)x\s+on\s+([^,\.]+?)(?:[,\.]|$)',
        
        # "5% cash back on dining"
        r'(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?on\s+([^,\.]+?)(?:[,\.]|$)',
        
        # "Earn 3% cash back at grocery stores"
        r'earn\s+(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?(?:at\s+|on\s+)([^,\.]+?)(?:[,\.]|$)',
        
        # "1x on all other purchases"
        r'(\d+(?:\.\d+)?)x\s+on\s+(all other purchases?)(?:[,\.]|$)',
        
        # "2% on everything" or "2% cash back on all purchases"
        r'(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?on\s+(everything|all purchases)(?:[,\.]|$)',
    ]
    
    for pattern in rate_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                rate = float(match.group(1))
                category_text = match.group(2).strip()
                
                # Skip portal-specific bonuses (purchased through, booked through)
                if re.search(r'\b(?:purchased|booked)\s+through\b', category_text, re.IGNORECASE):
                    continue
                
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
    
    # Special handling for compound categories like "dining, select streaming services and online groceries"
    # Look for patterns that have commas or "and" in them, but not "purchased through"
    compound_patterns = [
        r'(\d+(?:\.\d+)?)x\s+on\s+([^,\.]*(?:,\s*[^,\.]+)+(?:\s+and\s+[^,\.]+)*)',  # Must have at least one comma
        r'(\d+(?:\.\d+)?)x\s+on\s+([^,\.]+\s+and\s+[^,\.]+)',  # Or have "and" without commas
        r'(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?on\s+([^,\.]*(?:,\s*[^,\.]+)+(?:\s+and\s+[^,\.]+)*)',
        r'(\d+(?:\.\d+)?)%\s+(?:cash back\s+)?on\s+([^,\.]+\s+and\s+[^,\.]+)',
    ]
    
    for compound_pattern in compound_patterns:
        matches = re.finditer(compound_pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                rate = float(match.group(1))
                category_text = match.group(2).strip()
                
                # Skip portal-specific bonuses (purchased through, booked through)
                if re.search(r'\b(?:purchased|booked)\s+through\b', category_text, re.IGNORECASE):
                    continue
                
                # Split on commas and "and" - handle "select streaming services" as one unit
                # First, protect compound phrases
                protected_text = category_text
                protected_text = re.sub(r'select streaming services?', 'STREAMING_SERVICES_PLACEHOLDER', protected_text, flags=re.IGNORECASE)
                protected_text = re.sub(r'online groceries', 'ONLINE_GROCERIES_PLACEHOLDER', protected_text, flags=re.IGNORECASE)
                
                # Now split
                category_parts = re.split(r',\s*(?:and\s+)?|\s+and\s+', protected_text)
                
                for part in category_parts:
                    part = part.strip()
                    
                    # Restore protected phrases
                    part = part.replace('STREAMING_SERVICES_PLACEHOLDER', 'select streaming services')
                    part = part.replace('ONLINE_GROCERIES_PLACEHOLDER', 'online groceries')
                    
                    if len(part) > 2:
                        # Map to standardized names
                        mapped = False
                        for category_pattern, standard_name in category_mappings.items():
                            if re.search(category_pattern, part, re.IGNORECASE):
                                if standard_name not in categories or categories[standard_name] < rate:
                                    categories[standard_name] = rate
                                mapped = True
                                break
                        
                        # If not mapped, try some specific cases
                        if not mapped:
                            part_lower = part.lower()
                            if 'streaming' in part_lower or 'select streaming' in part_lower:
                                if 'Streaming Services' not in categories or categories['Streaming Services'] < rate:
                                    categories['Streaming Services'] = rate
                            elif 'groceries' in part_lower:
                                if 'Groceries' not in categories or categories['Groceries'] < rate:
                                    categories['Groceries'] = rate
                            elif 'dining' in part_lower:
                                if 'Dining & Restaurants' not in categories or categories['Dining & Restaurants'] < rate:
                                    categories['Dining & Restaurants'] = rate
                        
            except (ValueError, IndexError):
                continue
    
    # Special case: look for "select streaming services" specifically
    # Pattern: "3x on dining, select streaming services and online groceries"
    streaming_match = re.search(r'(\d+(?:\.\d+)?)x\s+on\s+[^,]*,\s*select streaming services', text, re.IGNORECASE)
    if streaming_match:
        rate = float(streaming_match.group(1))
        if 'Streaming Services' not in categories or categories['Streaming Services'] < rate:
            categories['Streaming Services'] = rate
    
    return categories


def parse_intro_offer(intro_text: str) -> Dict[str, any]:
    """Parse intro offer text to extract bonus details."""
    if not intro_text:
        return {'points': 0, 'value': 0.0, 'spending_requirement': 0.0, 'months': 3}
    
    result = {'points': 0, 'value': 0.0, 'spending_requirement': 0.0, 'months': 3}
    
    # Extract bonus amount - improved patterns
    bonus_patterns = [
        # Specific patterns for points/miles first
        r'earn (\d{1,3}(?:,\d{3})*)\s+(?:bonus\s+)?(?:hilton honors\s+bonus\s+)?(?:miles|points)',
        r'bonus of (\d{1,3}(?:,\d{3})*)\s+(?:miles|points)',
        r'earn (\d{1,3}(?:,\d{3})*)\s+(?:membership rewards|thankyou|aadvantage|skymiles)?\s*(?:bonus\s+)?(?:miles|points)',
        r'(\d{1,3}(?:,\d{3})*)\s+(?:bonus\s+)?(?:hilton honors\s+bonus\s+)?(?:miles|points)',
        # Cash patterns
        r'earn a \$(\d{1,3}(?:,\d{3})*)\s+(?:cash back|bonus|statement credit)',
        r'\$(\d{1,3}(?:,\d{3})*)\s+(?:cash back|bonus|statement credit|online cash rewards bonus)',
        # Generic patterns
        r'earn (\d{1,3}(?:,\d{3})*)',
        r'bonus of (\d{1,3}(?:,\d{3})*)',
    ]
    
    for pattern in bonus_patterns:
        match = re.search(pattern, intro_text, re.IGNORECASE)
        if match:
            amount = int(match.group(1).replace(',', ''))
            # Check if this is a cash bonus
            if '$' in match.group(0) or 'cash' in match.group(0).lower() or 'statement credit' in match.group(0).lower():
                result['value'] = float(amount)
            else:
                result['points'] = amount
            break
    
    # Extract spending requirement
    spend_patterns = [
        r'spend \$(\d{1,3}(?:,\d{3})*)',
        r'after you spend \$(\d{1,3}(?:,\d{3})*)',
        r'after \$(\d{1,3}(?:,\d{3})*)',
        r'make at least \$(\d{1,3}(?:,\d{3})*)',
        r'make \$(\d{1,3}(?:,\d{3})*)',
    ]
    
    for pattern in spend_patterns:
        match = re.search(pattern, intro_text, re.IGNORECASE)
        if match:
            result['spending_requirement'] = float(match.group(1).replace(',', ''))
            break
    
    # Extract time period - improved patterns
    month_patterns = [
        r'within (\d+) months?',
        r'in the first (\d+) months?',
        r'first (\d+) months?',
        r'in (\d+) months?',
        r'within the first (\d+) months?',
        r'in your first (\d+) months?',
        r'first (\d+) months? from account opening',
        r'within (\d+) months? from account opening',
        r'(\d+) months? of card membership',
        r'first (\d+) months? of account opening',
        r'first (\d+) days' # Handle days and convert to months
    ]
    
    for pattern in month_patterns:
        match = re.search(pattern, intro_text, re.IGNORECASE)
        if match:
            time_value = int(match.group(1))
            if 'days' in pattern:
                # Convert days to months (approximation)
                result['months'] = max(1, round(time_value / 30))
            else:
                result['months'] = time_value
            break
    
    # Extract value if mentioned (e.g., "equal to $750 in travel")
    value_patterns = [
        r'equal to \$(\d{1,3}(?:,\d{3})*)',
        r'worth \$(\d{1,3}(?:,\d{3})*)',
        r'value of \$(\d{1,3}(?:,\d{3})*)',
        r'redeemable for \$(\d{1,3}(?:,\d{3})*)',
        r'that\'s a \$(\d{1,3}(?:,\d{3})*)'
    ]
    
    for pattern in value_patterns:
        match = re.search(pattern, intro_text, re.IGNORECASE)
        if match and result['value'] == 0.0:
            result['value'] = float(match.group(1).replace(',', ''))
            break
    
    return result


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


def determine_reward_type(card_name: str, reward_text: str) -> str:
    """Determine the reward type based on card name and reward description."""
    combined_text = f"{card_name} {reward_text}".lower()
    
    if any(keyword in combined_text for keyword in ['cash back', 'cashback', 'cash rewards']):
        return 'cash_back'
    elif any(keyword in combined_text for keyword in ['miles', 'airline', 'delta', 'united', 'american airlines', 'southwest']):
        return 'miles'
    elif any(keyword in combined_text for keyword in ['hotel', 'marriott', 'hilton', 'hyatt', 'ihg']):
        return 'hotel'
    else:
        return 'points'  # Default


def scrape_nerdwallet_table(html_content: str) -> List[Dict]:
    """Scrape the NerdWallet table HTML and extract card data."""
    soup = BeautifulSoup(html_content, 'html.parser')
    cards = []
    
    # Find the table
    table = soup.find('table', class_='MuiTable-root')
    if not table:
        logger.error("Could not find the main table")
        return cards
    
    # Find all table rows (skip header)
    rows = table.find('tbody').find_all('tr', class_='MuiTableRow-root')
    logger.info(f"Found {len(rows)} card rows in table")
    
    for i, row in enumerate(rows):
        try:
            card_data = extract_card_from_row(row, i)
            if card_data:
                cards.append(card_data)
        except Exception as e:
            logger.warning(f"Error processing row {i}: {e}")
            continue
    
    return cards


def extract_card_from_row(row, row_index: int) -> Optional[Dict]:
    """Extract card data from a single table row."""
    cells = row.find_all('td')
    if len(cells) < 5:
        logger.warning(f"Row {row_index} has insufficient cells: {len(cells)}")
        return None
    
    card = {}
    
    # Extract card name (first cell)
    name_element = cells[0].find('span', {'data-testid': 'summary-table-card-name'})
    if name_element:
        card['name'] = name_element.get_text(strip=True)
    else:
        logger.warning(f"Could not find card name in row {row_index}")
        return None
    
    # Extract issuer from name
    card['issuer'] = extract_issuer_from_name(card['name'])
    
    # Extract rating and best-for text (second cell)
    rating_element = cells[1].find('span', {'data-testid': 'rating-actual'})
    if rating_element:
        card['nerdwallet_rating'] = float(rating_element.get_text(strip=True))
    
    best_for_element = cells[1].find('span', {'data-testid': 'best-for-text'})
    if best_for_element:
        card['best_for'] = best_for_element.get_text(strip=True)
    
    # Extract annual fee (third cell)
    fee_element = cells[2].find('p')
    if fee_element:
        fee_text = fee_element.get_text(strip=True)
        card['annual_fee'] = parse_annual_fee(fee_text)
    
    # Extract rewards rate (fourth cell)
    rewards_cell = cells[3]
    
    # Get the rate display (e.g., "2x-5x")
    rate_element = rewards_cell.find('p', class_='MuiTypography-body1')
    if rate_element:
        card['rewards_rate_display'] = rate_element.get_text(strip=True)
    
    # Get the reward type (e.g., "Miles", "Cash back")
    type_element = rewards_cell.find('span', class_='MuiTypography-bodySmall')
    if type_element:
        card['reward_type_display'] = type_element.get_text(strip=True)
    
    # Extract detailed rewards from aria-label tooltip
    # Look for the span that contains the button - it has the detailed aria-label
    tooltip_span = rewards_cell.find('span', {'aria-label': True})
    if tooltip_span:
        aria_label = tooltip_span.get('aria-label')
        if aria_label and aria_label != "Reward Rate Details":
            card['rewards_tooltip'] = aria_label
            card['reward_categories'] = parse_category_bonuses_from_tooltip(aria_label)
            card['reward_type'] = determine_reward_type(card['name'], aria_label)
    
    # Fallback to button if span not found
    if not card.get('rewards_tooltip'):
        tooltip_button = rewards_cell.find('button', {'aria-label': True})
        if tooltip_button:
            aria_label = tooltip_button.get('aria-label')
            if aria_label and aria_label != "Reward Rate Details":
                card['rewards_tooltip'] = aria_label
                card['reward_categories'] = parse_category_bonuses_from_tooltip(aria_label)
                card['reward_type'] = determine_reward_type(card['name'], aria_label)
    
    # Extract intro offer (fifth cell)
    intro_cell = cells[4]
    
    # Get the intro offer amount
    intro_amount_element = intro_cell.find('span', class_='MuiTypography-body1')
    if intro_amount_element:
        card['intro_offer_display'] = intro_amount_element.get_text(strip=True)
    
    # Get the intro offer type
    intro_type_element = intro_cell.find('span', class_='MuiTypography-bodySmall')
    if intro_type_element:
        card['intro_offer_type'] = intro_type_element.get_text(strip=True)
    
    # Extract detailed intro offer from aria-label tooltip
    # Look for the span that contains the button - it has the detailed aria-label
    intro_tooltip_span = intro_cell.find('span', {'aria-label': True})
    if intro_tooltip_span:
        intro_aria_label = intro_tooltip_span.get('aria-label')
        if intro_aria_label and intro_aria_label != "Intro Offer Details":
            card['intro_offer_tooltip'] = intro_aria_label
            intro_details = parse_intro_offer(intro_aria_label)
            card.update({
                'signup_bonus_points': intro_details['points'],
                'signup_bonus_value': intro_details['value'],
                'signup_bonus_min_spend': intro_details['spending_requirement'],
                'signup_bonus_max_months': intro_details['months']
            })
    
    # Fallback to button if span not found
    if not card.get('intro_offer_tooltip'):
        intro_tooltip_button = intro_cell.find('button', {'aria-label': True})
        if intro_tooltip_button:
            intro_aria_label = intro_tooltip_button.get('aria-label')
            if intro_aria_label and intro_aria_label != "Intro Offer Details":
                card['intro_offer_tooltip'] = intro_aria_label
                intro_details = parse_intro_offer(intro_aria_label)
                card.update({
                    'signup_bonus_points': intro_details['points'],
                    'signup_bonus_value': intro_details['value'],
                    'signup_bonus_min_spend': intro_details['spending_requirement'],
                    'signup_bonus_max_months': intro_details['months']
                })
    
    # Set default values if not found
    card.setdefault('reward_categories', {})
    card.setdefault('reward_type', 'points')
    card.setdefault('annual_fee', 0.0)
    card.setdefault('signup_bonus_points', 0)
    card.setdefault('signup_bonus_value', 0.0)
    card.setdefault('signup_bonus_min_spend', 0.0)
    card.setdefault('signup_bonus_max_months', 3)
    
    # Add metadata
    card['source'] = 'nerdwallet_table'
    card['source_url'] = 'https://www.nerdwallet.com/best/credit-cards/bonus-offers'
    card['row_index'] = row_index
    
    return card


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


def check_issuer_in_database(issuer_name: str) -> bool:
    """Check if an issuer exists in the database."""
    try:
        from app import create_app, db
        from app.models.credit_card import CardIssuer
        
        # Create app context to access database
        app = create_app('default')
        with app.app_context():
            # Check if issuer exists in database
            issuer = CardIssuer.query.filter_by(name=issuer_name).first()
            return issuer is not None
    except Exception as e:
        logger.warning(f"Could not check issuer '{issuer_name}' in database: {e}")
        return False


def get_all_database_issuers() -> List[str]:
    """Get all issuer names from the database."""
    try:
        from app import create_app, db
        from app.models.credit_card import CardIssuer
        
        # Create app context to access database
        app = create_app('default')
        with app.app_context():
            issuers = CardIssuer.query.all()
            return [issuer.name for issuer in issuers]
    except Exception as e:
        logger.warning(f"Could not get issuers from database: {e}")
        return []


def categorize_cards(cards: List[Dict]) -> Dict[str, Any]:
    """Categorize cards into valid and problematic lists."""
    valid_cards = []
    problematic_cards = []
    
    # Get available issuers from database
    available_issuers = get_all_database_issuers()
    logger.info(f"Available issuers in database: {available_issuers}")
    
    for card in cards:
        issues = []
        card_name = card.get('name', 'Unknown')
        issuer_name = card.get('issuer', 'Unknown')
        
        # Check for various issues
        if not card_name or card_name == 'Unknown':
            issues.append('missing_name')
        
        if not issuer_name or issuer_name == 'Unknown':
            issues.append('missing_issuer')
        elif not check_issuer_in_database(issuer_name):
            issues.append('issuer_not_in_database')
        
        # Check for other potential data quality issues
        if card.get('annual_fee') is None:
            issues.append('missing_annual_fee')
        
        if not card.get('reward_categories') and not card.get('rewards_tooltip'):
            issues.append('missing_reward_info')
        
        if not card.get('intro_offer_display') and not card.get('intro_offer_tooltip'):
            issues.append('missing_intro_offer')
        
        # Add the issues to the card for reference
        if issues:
            card_with_issues = card.copy()
            card_with_issues['issues'] = issues
            card_with_issues['issue_reasons'] = {
                'missing_name': 'Card name is missing or unknown',
                'missing_issuer': 'Issuer information is missing or unknown',
                'issuer_not_in_database': f'Issuer "{issuer_name}" not found in database (available: {", ".join(available_issuers)})',
                'missing_annual_fee': 'Annual fee information is missing',
                'missing_reward_info': 'No reward categories or reward tooltip found',
                'missing_intro_offer': 'No intro offer information found'
            }
            problematic_cards.append(card_with_issues)
            logger.info(f"Card '{card_name}' has issues: {issues}")
        else:
            valid_cards.append(card)
            logger.info(f"Card '{card_name}' is valid for import")
    
    return {
        'valid_cards': valid_cards,
        'problematic_cards': problematic_cards,
        'available_issuers': available_issuers
    }


def main():
    """Main function to scrape the NerdWallet table."""
    # File paths
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    html_file = os.path.join(base_dir, 'data', 'input', 'nerdwallet_bonus_offers_table.html')
    output_dir = os.path.join(base_dir, 'flask_app', 'data', 'output')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(html_file):
        logger.error(f"HTML file not found: {html_file}")
        return
    
    logger.info(f"Loading table HTML file: {html_file}")
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    logger.info("Scraping NerdWallet table...")
    cards = scrape_nerdwallet_table(html_content)
    
    logger.info(f"Extracted {len(cards)} cards from table")
    
    # Categorize cards into valid and problematic lists
    logger.info("Categorizing cards based on issuer availability...")
    categorization = categorize_cards(cards)
    
    valid_cards = categorization['valid_cards']
    problematic_cards = categorization['problematic_cards']
    available_issuers = categorization['available_issuers']
    
    # Analyze results for valid cards
    valid_cards_with_rewards = [c for c in valid_cards if c.get('reward_categories')]
    valid_cards_with_tooltips = [c for c in valid_cards if c.get('rewards_tooltip')]
    valid_cards_with_intro_offers = [c for c in valid_cards if c.get('signup_bonus_points', 0) > 0 or c.get('signup_bonus_value', 0) > 0]
    
    # Analyze issues in problematic cards
    issue_summary = {}
    for card in problematic_cards:
        for issue in card.get('issues', []):
            issue_summary[issue] = issue_summary.get(issue, 0) + 1
    
    # Save detailed results with timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    output_file = os.path.join(output_dir, f'{timestamp}_nerdwallet_table_cards.json')
    results = {
        'extraction_summary': {
            'total_cards_extracted': len(cards),
            'valid_cards_count': len(valid_cards),
            'problematic_cards_count': len(problematic_cards),
            'valid_cards_with_reward_categories': len(valid_cards_with_rewards),
            'valid_cards_with_reward_tooltips': len(valid_cards_with_tooltips),
            'valid_cards_with_intro_offers': len(valid_cards_with_intro_offers),
            'issue_summary': issue_summary,
            'available_issuers': available_issuers,
            'extraction_method': 'table_html_parsing_with_issuer_validation',
            'source_file': 'nerdwallet_bonus_offers_table.html',
            'extraction_timestamp': datetime.now().isoformat()
        },
        'valid_cards': valid_cards,
        'problematic_cards': problematic_cards
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to: {output_file}")
    
    # Print comprehensive summary
    print("\n" + "="*70)
    print("NERDWALLET TABLE SCRAPING RESULTS")
    print("="*70)
    print(f"📊 Total cards extracted: {len(cards)}")
    print(f"✅ Valid cards (ready for import): {len(valid_cards)}")
    print(f"⚠️  Problematic cards: {len(problematic_cards)}")
    print(f"🏦 Available issuers in database: {len(available_issuers)}")
    print(f"   • {', '.join(available_issuers)}")
    
    if issue_summary:
        print(f"\n📋 Issue summary for problematic cards:")
        for issue, count in issue_summary.items():
            print(f"   • {issue.replace('_', ' ').title()}: {count} cards")
    
    if valid_cards:
        print(f"\n🎯 Valid cards analysis:")
        print(f"   • Cards with reward categories: {len(valid_cards_with_rewards)}")
        print(f"   • Cards with reward tooltips: {len(valid_cards_with_tooltips)}")
        print(f"   • Cards with intro offers: {len(valid_cards_with_intro_offers)}")
    
    if valid_cards_with_rewards:
        print(f"\n🏆 Sample valid cards with detailed reward categories:")
        for i, card in enumerate(valid_cards_with_rewards[:5]):
            print(f"\n{i+1}. {card['name']} ({card['issuer']})")
            print(f"   Annual Fee: ${card['annual_fee']}")
            if card.get('reward_categories'):
                for category, rate in card['reward_categories'].items():
                    print(f"   • {category}: {rate}x")
            if card.get('signup_bonus_points', 0) > 0:
                print(f"   🎁 Signup Bonus: {card['signup_bonus_points']:,} points")
            if card.get('signup_bonus_value', 0) > 0:
                print(f"   💰 Bonus Value: ${card['signup_bonus_value']}")
    
    if problematic_cards:
        print(f"\n⚠️  Sample problematic cards:")
        for i, card in enumerate(problematic_cards[:5]):
            print(f"\n{i+1}. {card['name']} ({card.get('issuer', 'Unknown')})")
            print(f"   Issues: {', '.join(card.get('issues', []))}")
            if 'issuer_not_in_database' in card.get('issues', []):
                print(f"   Note: Issuer '{card.get('issuer')}' not found in database")
    
    # Look specifically for Chase Sapphire Preferred
    chase_cards = [c for c in valid_cards if 'sapphire preferred' in c['name'].lower()]
    if chase_cards:
        print(f"\n🎯 CHASE SAPPHIRE PREFERRED VALIDATION:")
        card = chase_cards[0]
        print(f"   Name: {card['name']}")
        print(f"   Status: ✅ Valid for import")
        print(f"   Categories: {card.get('reward_categories', {})}")
        if card.get('rewards_tooltip'):
            print(f"   Rewards Tooltip: {card['rewards_tooltip'][:100]}...")
        
        # Test against expected categories
        expected_categories = {
            "Dining & Restaurants": 3.0,
            "Streaming Services": 3.0,
            "Travel": 2.0
        }
        
        actual_categories = card.get('reward_categories', {})
        print(f"\n   ✅ Category validation:")
        for category, expected_rate in expected_categories.items():
            if category in actual_categories:
                actual_rate = actual_categories[category]
                status = "✅" if actual_rate == expected_rate else "❌"
                print(f"   {status} {category}: {actual_rate}x (expected {expected_rate}x)")
            else:
                print(f"   ❌ Missing: {category} (expected {expected_rate}x)")
    else:
        # Check if it's in problematic cards
        problematic_chase = [c for c in problematic_cards if 'sapphire preferred' in c['name'].lower()]
        if problematic_chase:
            card = problematic_chase[0]
            print(f"\n⚠️  CHASE SAPPHIRE PREFERRED IN PROBLEMATIC CARDS:")
            print(f"   Name: {card['name']}")
            print(f"   Issues: {', '.join(card.get('issues', []))}")
    
    print(f"\n💾 Detailed results saved to: {output_file}")


if __name__ == '__main__':
    main()