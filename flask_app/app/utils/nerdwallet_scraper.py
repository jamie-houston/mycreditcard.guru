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
        
        # Try to find the card containers
        card_containers = soup.select('[data-testid="card-container"], .CardBox_container__3d89c, .credit-card-container')
        
        if card_containers:
            logger.info(f"Found {len(card_containers)} card containers")
            
            for container in card_containers:
                try:
                    # Extract card name
                    card_name_elem = container.select_one('[data-testid="card-name"], h2, h3, .card-name')
                    if not card_name_elem:
                        continue
                    
                    card_name = card_name_elem.text.strip()
                    
                    # Extract issuer from card name
                    issuer = self._extract_issuer_from_name(card_name)
                    
                    # Extract annual fee
                    annual_fee = 0
                    fee_elem = container.select_one('[data-testid="annual-fee"], .annual-fee, .card-fee')
                    if fee_elem:
                        fee_text = fee_elem.text.strip()
                        if '$0' in fee_text or 'No annual fee' in fee_text:
                            annual_fee = 0
                        else:
                            fee_match = re.search(r'\$(\d+)', fee_text)
                            if fee_match:
                                annual_fee = int(fee_match.group(1))
                    
                    # Extract reward categories
                    reward_categories = []
                    rewards_elem = container.select_one('[data-testid="card-rewards"], .card-rewards, .reward-rates')
                    if rewards_elem:
                        rewards_text = rewards_elem.text.strip()
                        
                        # Look for patterns like "5% on travel" or "3X at restaurants"
                        category_patterns = [
                            r'(\d+)[%xX]\s+(?:cash\s+back|points|rewards|back)?(?:\s+on\s+|\s+at\s+)([a-zA-Z\s,]+)',
                            r'(\d+)[%xX]\s+(?:on|at)\s+([a-zA-Z\s,]+)',
                            r'Earn\s+(\d+)[%xX](?:\s+back)?\s+(?:on|at)\s+([a-zA-Z\s,]+)'
                        ]
                        
                        for pattern in category_patterns:
                            for match in re.finditer(pattern, rewards_text, re.IGNORECASE):
                                try:
                                    percentage = float(match.group(1))
                                    category = match.group(2).strip().lower()
                                    reward_categories.append({
                                        'category': category,
                                        'percentage': percentage
                                    })
                                except (ValueError, IndexError):
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
        
        else:
            # Try to extract data from the table format
            table_rows = soup.select('#summary-table > div > div > table > tbody > tr')
            logger.info(f"Found {len(table_rows)} card rows in table")
            
            if table_rows:
                for row in table_rows:
                    try:
                        # Extract card name and issuer
                        name_elem = row.select_one('td:nth-child(1)')
                        if not name_elem:
                            continue
                        
                        card_name = name_elem.text.strip()
                        # Clean up text and remove "Apply Now" and other button text
                        card_name = re.sub(r'Apply Now.*?Rates & Fees', '', card_name, flags=re.DOTALL).strip()
                        
                        # Extract issuer from card name
                        issuer = self._extract_issuer_from_name(card_name)
                        
                        # Get annual fee
                        annual_fee = 0
                        fee_cell = row.select_one('td:nth-child(3)')
                        if fee_cell:
                            fee_text = fee_cell.text.strip()
                            if '$0' in fee_text or 'No annual fee' in fee_text:
                                annual_fee = 0
                            else:
                                fee_match = re.search(r'\$(\d+)', fee_text)
                                if fee_match:
                                    annual_fee = int(fee_match.group(1))
                        
                        # Parse rewards from the appropriate column
                        reward_categories = []
                        rewards_cell = row.select_one('td:nth-child(2)')
                        if rewards_cell:
                            rewards_text = rewards_cell.text.strip()
                            
                            # Find patterns for reward rates
                            reward_patterns = [
                                r'(\d+)[%xX]\s+(?:cash\s+back|points|rewards|back)?(?:\s+on\s+|\s+at\s+)([a-zA-Z\s,]+)',
                                r'(\d+)[%xX]\s+(?:on|at)\s+([a-zA-Z\s,]+)'
                            ]
                            
                            for pattern in reward_patterns:
                                for match in re.finditer(pattern, rewards_text, re.IGNORECASE):
                                    try:
                                        percentage = float(match.group(1))
                                        category = match.group(2).strip().lower()
                                        reward_categories.append({
                                            'category': category,
                                            'percentage': percentage
                                        })
                                    except (ValueError, IndexError):
                                        pass
                        
                        # Extract signup bonus
                        signup_bonus_value = 0.0
                        signup_bonus_points = 0
                        signup_bonus_spend_requirement = 0.0
                        signup_bonus_time_period = 3
                        
                        bonus_cell = row.select_one('td:nth-child(4)')
                        if bonus_cell:
                            bonus_text = bonus_cell.text.strip()
                            
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
                        
                        # Create card data dictionary
                        card_data = {
                            'name': card_name,
                            'issuer': issuer,
                            'annual_fee': annual_fee,
                            'reward_categories': reward_categories,
                            'special_offers': [],  # No special offers in table format
                            'signup_bonus_points': signup_bonus_points,
                            'signup_bonus_value': signup_bonus_value,
                            'signup_bonus_spend_requirement': signup_bonus_spend_requirement,
                            'signup_bonus_time_period': signup_bonus_time_period,
                        }
                        
                        cards_data.append(card_data)
                        logger.info(f"Successfully scraped {card_name} from table")
                        
                    except Exception as e:
                        logger.error(f"Error processing table row: {e}")
        
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