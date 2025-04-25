import requests
from bs4 import BeautifulSoup
import json
import time
import logging
import re
import random
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('nerdwallet_scraper')

class NerdWalletScraper:
    """Scraper specifically for NerdWallet credit card data"""
    
    def __init__(self, proxies: Optional[Dict[str, str]] = None, retry_count: int = 3):
        self.base_url = "https://www.nerdwallet.com"
        self.cards_list_url = f"{self.base_url}/the-best-credit-cards"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/',
        }
        self.proxies = proxies
        self.retry_count = retry_count
        self.debug_mode = True
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        Make HTTP request with exponential backoff retry logic
        
        Args:
            url: URL to request
            
        Returns:
            Response object if successful, None otherwise
        """
        for attempt in range(1, self.retry_count + 1):
            try:
                logger.info(f"Request attempt {attempt} for {url}")
                response = requests.get(
                    url, 
                    headers=self.headers,
                    proxies=self.proxies,
                    timeout=30
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt}/{self.retry_count}): {e}")
                
                if attempt < self.retry_count:
                    # Exponential backoff with jitter
                    backoff_time = (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
                else:
                    logger.error(f"Failed after {self.retry_count} attempts: {url}")
                    return None
    
    def scrape_cards(self) -> List[Dict[str, Any]]:
        """
        Scrape credit card information from NerdWallet
        
        Returns:
            List of credit card data dictionaries
        """
        logger.info(f"Fetching cards from {self.cards_list_url}")
        
        response = self._make_request(self.cards_list_url)
        if not response:
            logger.error("Failed to get response for main cards page")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save the HTML for debugging if needed
        if self.debug_mode:
            with open('nerdwallet_debug.html', 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            logger.info("Saved HTML to nerdwallet_debug.html for debugging")
        
        # Find the table with credit card information
        cards_data = []
        
        # New approach: First try to detect if we're on a new-style page or old-style page
        is_new_style = '/best/credit-cards/' in self.cards_list_url
        logger.info(f"Detected page style: {'New' if is_new_style else 'Old'} format")
        
        # Custom selectors based on page type
        if is_new_style:
            # For new-style pages (best/credit-cards)
            # These are the common container patterns for the new NerdWallet format
            card_containers = soup.select(
                # Product cards on new NerdWallet pages
                'div[data-testid="product-card"], '
                '.Product__Grid-wrapper div[class^="_Card"], '
                '.best-product-card, '
                '.ProductCardWrapper, '
                # Find any div that might contain card information
                'div.card-info, div[class*="creditcard"], div[class*="credit-card"]'
            )
        else:
            # For old-style pages
            card_containers = soup.select(
                '[data-testid="card-container"], .CardBox_container__3d89c, .credit-card-container'
            )
        
        logger.info(f"Found {len(card_containers)} card containers using {'new' if is_new_style else 'old'} selectors")
        
        # If we didn't find any containers with the specific selectors, try a more generic approach
        if not card_containers:
            # Try a more generic approach to find any likely card containers
            logger.info("No cards found with specific selectors, trying generic approach")
            card_containers = soup.select(
                # Generic card containers
                'div[class*="card"], div[class*="product"], div[id*="card"], '
                # Common grid or list structures
                'li.product-item, div.product-list-item, div.card-list-item'
            )
            logger.info(f"Found {len(card_containers)} card containers using generic selectors")
        
        # Last resort: Try to extract directly from debug HTML
        if not card_containers and self.debug_mode:
            logger.info("No cards found with any selectors, extracting card names from HTML content")
            # Look for common card names in the HTML content
            card_name_patterns = [
                r'(Chase Sapphire Preferred)',
                r'(Capital One Venture)',
                r'(American Express Gold Card)',
                r'(Citi Premier)',
                r'(Discover it Cash Back)',
                r'(Bank of America.*Customized Cash)'
            ]
            cards_found_in_text = []
            for pattern in card_name_patterns:
                for match in re.finditer(pattern, soup.get_text()):
                    cards_found_in_text.append(match.group(1))
            
            logger.info(f"Found {len(cards_found_in_text)} cards by text searching")
            
            # Create basic card data for each card name found
            for card_name in cards_found_in_text:
                issuer = self._extract_issuer_from_name(card_name)
                cards_data.append({
                    'name': card_name,
                    'issuer': issuer,
                    'annual_fee': 0,  # Default
                    'reward_categories': [],
                    'special_offers': [],
                    'signup_bonus_points': 0,
                    'signup_bonus_value': 0.0,
                    'signup_bonus_spend_requirement': 0.0,
                    'signup_bonus_time_period': 3,
                })
            
            return cards_data
        
        # Process card containers found with selectors
        for container in card_containers:
            try:
                # Extract card name - use different selectors for new vs old format
                card_name_elem = None
                if is_new_style:
                    card_name_elem = container.select_one(
                        'h3, h2, div[class*="name"], span[class*="name"], '
                        'div[class*="title"], span[class*="title"]'
                    )
                else:
                    card_name_elem = container.select_one(
                        '[data-testid="card-name"], h2, h3, .card-name'
                    )
                
                if not card_name_elem:
                    # Try a more generic approach
                    card_name_elem = container.select_one('h2, h3, h4, [class*="title"], [class*="name"]')
                    
                if not card_name_elem:
                    continue
                
                card_name = card_name_elem.text.strip()
                
                # Limit the card name length and clean it up
                if len(card_name) > 100:
                    # Probably grabbed too much text, try to trim it down
                    card_name = card_name[:100].split('\n')[0].strip()
                
                # Extract issuer from card name
                issuer = self._extract_issuer_from_name(card_name)
                
                # Extract annual fee
                annual_fee = 0
                if is_new_style:
                    # Look for fee information in the new format
                    fee_patterns = [
                        # Direct fee elements
                        'div[class*="annual-fee"], div[class*="annualFee"]',
                        # Fee sections
                        'div:has(> span:contains("Annual fee"))',
                        # Standard fee elements
                        'div.fee, span.fee, div.card-fee',
                        # Generic fee mentions
                        '[class*="fee"]'
                    ]
                    
                    # Try each pattern until we find a fee
                    fee_elem = None
                    fee_text = ""
                    
                    for pattern in fee_patterns:
                        try:
                            # BeautifulSoup doesn't support :contains() selector directly
                            # Using a more compatible approach
                            if ':contains' in pattern:
                                # Extract text before and after :contains()
                                before, contains_part = pattern.split(':has(')
                                label = contains_part.split(':contains("')[1].split('")')[0]
                                
                                # Find elements that contain the label text
                                potential_elements = container.select(before)
                                for el in potential_elements:
                                    if label.lower() in el.text.lower():
                                        fee_elem = el
                                        break
                            else:
                                fee_elem = container.select_one(pattern)
                            
                            if fee_elem:
                                fee_text = fee_elem.text.strip()
                                break
                        except Exception as e:
                            logger.debug(f"Error finding fee with pattern {pattern}: {e}")
                            continue
                else:
                    # Original way of finding fee element
                    fee_elem = container.select_one(
                        '[data-testid="annual-fee"], .annual-fee, .card-fee'
                    )
                    if fee_elem:
                        fee_text = fee_elem.text.strip()
                
                # Process fee text to extract the amount
                if fee_text:
                    if '$0' in fee_text or 'No annual fee' in fee_text or 'no annual fee' in fee_text.lower():
                        annual_fee = 0
                    else:
                        # Try to extract fee amount with different patterns
                        fee_patterns = [
                            r'\$(\d+(?:,\d{3})*)',  # Basic dollar amount
                            r'Annual fee: \$(\d+(?:,\d{3})*)',  # With label
                            r'Annual fee of \$(\d+(?:,\d{3})*)',  # Alternative phrasing
                            r'(\d+)\/year',  # Format: 95/year
                            r'(\d+) per year'  # Format: 95 per year
                        ]
                        
                        for pattern in fee_patterns:
                            fee_match = re.search(pattern, fee_text)
                            if fee_match:
                                try:
                                    fee_str = fee_match.group(1).replace(',', '')
                                    annual_fee = int(fee_str)
                                    break
                                except (ValueError, IndexError):
                                    pass
                
                # Extract reward categories
                reward_categories = {}
                
                # Different selectors for rewards depending on page style
                if is_new_style:
                    reward_patterns = [
                        # New specific reward selectors
                        'div[class*="rewards"], div[class*="Rewards"]',
                        'ul[class*="rewards"], ul[class*="Rewards"]',
                        # More generic patterns
                        '[data-testid*="rewards"]',
                        # Sections that typically contain rewards
                        'div:has(> span:contains("Rewards")), div:has(> h3:contains("Rewards"))'
                    ]
                    
                    rewards_elem = None
                    for pattern in reward_patterns:
                        try:
                            if ':contains' in pattern:
                                # Extract text before and after :contains()
                                before, contains_part = pattern.split(':has(')
                                label = contains_part.split(':contains("')[1].split('")')[0]
                                
                                # Find elements that contain the label text
                                potential_elements = container.select(before)
                                for el in potential_elements:
                                    el_text = el.get_text(strip=True)
                                    if label.lower() in el_text.lower():
                                        rewards_elem = el
                                        break
                            else:
                                rewards_elem = container.select_one(pattern)
                            
                            if rewards_elem:
                                break
                        except Exception as e:
                            logger.debug(f"Error finding rewards with pattern {pattern}: {e}")
                            continue
                    
                    # If we found a rewards element, extract the text
                    rewards_text = ""
                    if rewards_elem:
                        rewards_text = rewards_elem.get_text(strip=True)
                    
                    # If we still don't have rewards text, try to find it in the full card text
                    if not rewards_text:
                        card_text = container.get_text(strip=True)
                        # Look for reward percentage patterns
                        percentage_matches = re.findall(r'(\d+(?:\.\d+)?)% (?:cash ?back|rewards?|points?) (?:on|for) ([^.;]+)', card_text)
                        for percentage, category in percentage_matches:
                            reward_categories[category.strip()] = float(percentage)
                else:
                    # Original rewards extraction logic
                    rewards_elem = container.select_one(
                        '[data-testid="rewards-rates"], .rewards-rates, .reward-rates'
                    )
                
                # Process any found rewards element
                if rewards_elem and not reward_categories:  # Only process if we haven't already extracted via regex
                    rewards_text = rewards_elem.get_text(strip=True)
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
                                reward_categories[category] = rate_value
                            except (ValueError, AttributeError):
                                pass
                
                # If we still don't have any reward categories, look in the full card text
                if not reward_categories:
                    card_text = container.get_text(strip=True)
                    # Additional fallback patterns
                    fallback_patterns = [
                        r'(\d+(?:\.\d+)?)% back on ([^.;]+)',
                        r'(\d+(?:\.\d+)?)% cash ?back on ([^.;]+)',
                        r'Earn (\d+(?:\.\d+)?)% (?:on|in) ([^.;]+)'
                    ]
                    
                    for pattern in fallback_patterns:
                        matches = re.findall(pattern, card_text)
                        for rate, category in matches:
                            try:
                                rate_value = float(rate)
                                category = category.strip().lower()
                                reward_categories[category] = rate_value
                            except (ValueError, AttributeError):
                                pass
                
                # Extract signup bonus
                signup_bonus_value = 0.0
                signup_bonus_points = 0
                signup_bonus_spend_requirement = 0.0
                signup_bonus_time_period = 3
                
                bonus_elem = container.select_one('[data-testid="card-bonus"], .card-bonus, .signup-bonus')
                if bonus_elem:
                    bonus_text = bonus_elem.text.strip()
                    
                    # Extract bonus value
                    value_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d+)?)', bonus_text)
                    if value_match:
                        signup_bonus_value = float(value_match.group(1).replace(',', ''))
                    
                    # Extract bonus points
                    points_match = re.search(r'(\d+(?:,\d{3})*)\s*(?:points|miles)', bonus_text, re.IGNORECASE)
                    if points_match:
                        signup_bonus_points = int(points_match.group(1).replace(',', ''))
                    
                    # Extract spend requirement
                    spend_match = re.search(r'(?:spend|spending)\s+\$(\d+(?:,\d{3})*)', bonus_text, re.IGNORECASE)
                    if spend_match:
                        signup_bonus_spend_requirement = float(spend_match.group(1).replace(',', ''))
                    
                    # Extract time period
                    time_match = re.search(r'(?:within|first)\s+(\d+)\s+months', bonus_text, re.IGNORECASE)
                    if time_match:
                        signup_bonus_time_period = int(time_match.group(1))
                
                # Extract special offers
                special_offers = []
                offers_elem = container.select_one('[data-testid="card-perks"], .card-perks, .special-offers')
                if offers_elem:
                    offers_text = offers_elem.text.strip()
                    
                    # Check for common offers like credits
                    offer_patterns = [
                        (r'\$(\d+)\s+annual\s+travel\s+credit', 'travel_credit', 'annual'),
                        (r'\$(\d+)\s+statement\s+credit', 'statement_credit', 'one_time'),
                        (r'Free\s+night\s+certificate', 'hotel_certificate', 'annual'),
                        (r'\$(\d+)\s+in\s+Uber\s+credits', 'uber_credit', 'annual'),
                        (r'\$(\d+)\s+dining\s+credit', 'dining_credit', 'annual')
                    ]
                    
                    for pattern, offer_type, frequency in offer_patterns:
                        for match in re.finditer(pattern, offers_text, re.IGNORECASE):
                            try:
                                if match.group(1):
                                    amount = float(match.group(1))
                                    special_offers.append({
                                        'type': offer_type,
                                        'amount': amount,
                                        'frequency': frequency
                                    })
                            except (ValueError, IndexError):
                                pass
                
                # Create card data dictionary
                card_data = {
                    'name': card_name,
                    'issuer': issuer,
                    'annual_fee': annual_fee,
                    'reward_categories': reward_categories,
                    'special_offers': special_offers,
                    'signup_bonus_points': signup_bonus_points,
                    'signup_bonus_value': signup_bonus_value,
                    'signup_bonus_spend_requirement': signup_bonus_spend_requirement,
                    'signup_bonus_time_period': signup_bonus_time_period,
                }
                
                cards_data.append(card_data)
                logger.info(f"Successfully scraped {card_name}")
                
            except Exception as e:
                logger.error(f"Error processing card container: {e}")
        
        logger.info(f"Extracted {len(cards_data)} cards total")
        return cards_data
    
    def _extract_issuer_from_name(self, card_name: str) -> str:
        """Extract the card issuer from the card name"""
        # Common issuers to look for
        common_issuers = [
            'Chase', 'American Express', 'Amex', 'Citi', 'Capital One', 
            'Discover', 'Bank of America', 'Wells Fargo', 'U.S. Bank'
        ]
        
        for issuer in common_issuers:
            if issuer.lower() in card_name.lower():
                # Special case for American Express abbreviation
                if issuer == 'Amex' and 'american express' in card_name.lower():
                    return 'American Express'
                return issuer
        
        return "Unknown Issuer"


def scrape_nerdwallet_cards(source_url=None):
    """
    Main function to scrape NerdWallet credit cards
    
    Args:
        source_url (str, optional): The specific NerdWallet URL to scrape from.
                                    If None, uses the default URL.
    
    Returns:
        List of credit card data dictionaries
    """
    logger.info(f"Using specialized NerdWallet scraper with source_url: {source_url}")
    
    scraper = NerdWalletScraper()
    
    # If a specific NerdWallet URL was provided, update the scraper's URL
    if source_url and 'nerdwallet.com' in source_url:
        scraper.cards_list_url = source_url
        logger.info(f"Using custom NerdWallet URL: {source_url}")
    
    return scraper.scrape_cards()


if __name__ == "__main__":
    # When run directly, save results to a JSON file
    cards = scrape_nerdwallet_cards()
    print(f"Scraped {len(cards)} credit cards from NerdWallet")
    
    with open('nerdwallet_cards.json', 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2)
        
    print(f"Results saved to nerdwallet_cards.json") 