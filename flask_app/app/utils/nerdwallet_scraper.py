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
        self.cards_list_url = f"{self.base_url}/best/credit-cards/rewards"
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
        
        # Extract JSON data from the page
        cards_data = []
        
        # Look for JSON data in script tags
        script_tags = soup.find_all('script', type=['application/json', 'application/ld+json'])
        json_data = None
        
        # First, try to find the specific product cards script
        product_cards_script = soup.find('script', id='product-cards-linked-data')
        if product_cards_script and product_cards_script.string:
            try:
                data = json.loads(product_cards_script.string)
                if self._contains_card_data(data):
                    json_data = data
                    logger.info("Found product cards JSON data")
            except (json.JSONDecodeError, AttributeError):
                pass
        
        # If not found, search through all script tags
        if not json_data:
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    # Look for card data in the JSON structure
                    if self._contains_card_data(data):
                        json_data = data
                        logger.info("Found JSON data containing card information")
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
        
        # If no JSON in script tags, look for inline JSON in the HTML
        if not json_data:
            logger.info("No JSON in script tags, looking for inline JSON data")
            # Look for JSON data patterns in the HTML text
            html_text = soup.get_text()
            
            # Try to find JSON objects that contain card data
            json_patterns = [
                r'"offers":\s*\[.*?\]',
                r'"products":\s*\[.*?\]',
                r'"cards":\s*\[.*?\]',
                r'\{"sectionBestFor".*?\}\]'
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, response.text, re.DOTALL)
                for match in matches:
                    try:
                        # Try to extract a complete JSON object
                        # Find the start of the JSON array/object
                        start_idx = response.text.find(match)
                        if start_idx == -1:
                            continue
                            
                        # Find the complete JSON structure
                        json_str = self._extract_complete_json(response.text, start_idx)
                        if json_str:
                            data = json.loads(json_str)
                            if self._contains_card_data(data):
                                json_data = data
                                logger.info(f"Found card data in JSON pattern: {pattern[:50]}...")
                                break
                    except (json.JSONDecodeError, Exception) as e:
                        logger.debug(f"Failed to parse JSON from pattern {pattern[:50]}: {e}")
                        continue
                
                if json_data:
                    break
        
        # If still no JSON data, try to extract from the full page content
        if not json_data:
            logger.info("Looking for card data in full page content")
            # Look for the specific JSON structure we saw in the debug output
            card_data_pattern = r'\[.*?"sectionBestFor".*?\]'
            matches = re.findall(card_data_pattern, response.text, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list) and len(data) > 0:
                        # Check if this looks like card data
                        first_item = data[0]
                        if isinstance(first_item, dict) and any(key in first_item for key in ['name', 'id', 'institution']):
                            json_data = data
                            logger.info(f"Found card data array with {len(data)} items")
                            break
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"Failed to parse card data array: {e}")
                    continue
        
        # Process the JSON data to extract card information
        if json_data:
            cards_data = self._extract_cards_from_json(json_data)
            logger.info(f"Extracted {len(cards_data)} cards from JSON data")
        else:
            logger.warning("No JSON card data found, falling back to HTML parsing")
            # Fallback to the original HTML parsing method
            cards_data = self._scrape_cards_from_html(soup)
        
        logger.info(f"Extracted {len(cards_data)} cards total")
        return cards_data
    
    def _contains_card_data(self, data: Any) -> bool:
        """Check if JSON data contains credit card information"""
        if isinstance(data, dict):
            # Look for card-related keys (including LD+JSON format)
            card_keys = ['name', 'institution', 'annualFee', 'rewardsRates', 'signUpBonusDetails']
            ld_json_keys = ['@type', 'itemListElement']
            
            # Check for LD+JSON structured data
            if data.get('@type') == 'ItemList' and 'itemListElement' in data:
                return True
            
            if any(key in data for key in card_keys):
                return True
            
            # Recursively check nested objects
            for value in data.values():
                if self._contains_card_data(value):
                    return True
        elif isinstance(data, list):
            # Check if it's a list of cards
            for item in data:
                if self._contains_card_data(item):
                    return True
        return False
    
    def _extract_complete_json(self, text: str, start_idx: int) -> Optional[str]:
        """Extract a complete JSON object/array from text starting at given index"""
        try:
            # Find the opening bracket/brace
            i = start_idx
            while i < len(text) and text[i] not in '[{':
                i += 1
            
            if i >= len(text):
                return None
            
            # Track bracket/brace depth
            open_char = text[i]
            close_char = ']' if open_char == '[' else '}'
            depth = 1
            i += 1
            
            while i < len(text) and depth > 0:
                if text[i] == open_char:
                    depth += 1
                elif text[i] == close_char:
                    depth -= 1
                elif text[i] == '"':
                    # Skip string content
                    i += 1
                    while i < len(text) and text[i] != '"':
                        if text[i] == '\\':
                            i += 1  # Skip escaped character
                        i += 1
                i += 1
            
            if depth == 0:
                return text[start_idx:i]
        except Exception as e:
            logger.debug(f"Error extracting JSON: {e}")
        
        return None
    
    def _extract_cards_from_json(self, json_data: Any) -> List[Dict[str, Any]]:
        """Extract card data from JSON structure"""
        cards = []
        
        def process_item(item):
            if not isinstance(item, dict):
                return None
            
            # Check if this looks like a credit card
            if not any(key in item for key in ['name', 'institution', 'details']):
                return None
            
            try:
                card_data = {
                    'name': item.get('name', '').strip(),
                    'issuer': '',
                    'annual_fee': 0,
                    'reward_categories': {},
                    'special_offers': [],
                    'signup_bonus_points': 0,
                    'signup_bonus_value': 0.0,
                    'signup_bonus_spend_requirement': 0.0,
                    'signup_bonus_time_period': 3,
                }
                
                # Extract issuer
                if 'institution' in item and isinstance(item['institution'], dict):
                    card_data['issuer'] = item['institution'].get('name', '')
                
                # Extract annual fee
                if 'details' in item and isinstance(item['details'], dict):
                    details = item['details']
                    if 'annualFee' in details and isinstance(details['annualFee'], dict):
                        annual_fee_value = details['annualFee'].get('value', 0)
                        if isinstance(annual_fee_value, (int, float)):
                            card_data['annual_fee'] = float(annual_fee_value)
                
                # Extract signup bonus information
                if 'details' in item and 'signUpBonusDetails' in item['details']:
                    bonus_details = item['details']['signUpBonusDetails']
                    if isinstance(bonus_details, dict):
                        # Extract bonus points/value
                        bonus_amount = bonus_details.get('bonus', 0)
                        if isinstance(bonus_amount, (int, float)):
                            card_data['signup_bonus_points'] = int(bonus_amount)
                        
                        # Extract bonus description to get spend requirement and time period
                        bonus_desc = bonus_details.get('description', '')
                        if bonus_desc:
                            # Extract spend requirement
                            spend_match = re.search(r'\$([0-9,]+)', bonus_desc)
                            if spend_match:
                                spend_str = spend_match.group(1).replace(',', '')
                                try:
                                    card_data['signup_bonus_spend_requirement'] = float(spend_str)
                                except ValueError:
                                    pass
                            
                            # Extract time period
                            time_match = re.search(r'(\d+)\s*months?', bonus_desc, re.IGNORECASE)
                            if time_match:
                                try:
                                    card_data['signup_bonus_time_period'] = int(time_match.group(1))
                                except ValueError:
                                    pass
                            
                            # Extract bonus value (for miles/points cards)
                            value_match = re.search(r'equal to \$([0-9,]+)', bonus_desc)
                            if value_match:
                                value_str = value_match.group(1).replace(',', '')
                                try:
                                    card_data['signup_bonus_value'] = float(value_str)
                                except ValueError:
                                    pass
                
                # Extract reward rates
                if 'details' in item and 'rewardsRates' in item['details']:
                    rewards_rates = item['details']['rewardsRates']
                    if isinstance(rewards_rates, list):
                        for rate_info in rewards_rates:
                            if isinstance(rate_info, dict):
                                rate = rate_info.get('rate', 0)
                                description = rate_info.get('description', '')
                                
                                if rate and description:
                                    # Parse the description to extract category
                                    category = self._parse_reward_category(description)
                                    if category:
                                        card_data['reward_categories'][category] = float(rate)
                
                # Also check for reward information in tooltips
                if 'driverRewardRate' in item and isinstance(item['driverRewardRate'], dict):
                    tooltip = item['driverRewardRate'].get('valueTooltip', '')
                    if tooltip:
                        # Parse complex reward descriptions like Chase Sapphire Preferred
                        reward_categories = self._parse_complex_rewards(tooltip)
                        card_data['reward_categories'].update(reward_categories)
                
                # Only return cards with valid names
                if card_data['name'] and len(card_data['name']) > 3:
                    logger.info(f"Successfully scraped {card_data['name']}")
                    return card_data
                
            except Exception as e:
                logger.error(f"Error processing card item: {e}")
                return None
        
        # Process the JSON data
        if isinstance(json_data, list):
            for item in json_data:
                card = process_item(item)
                if card:
                    cards.append(card)
        elif isinstance(json_data, dict):
            # Check for LD+JSON structured data format
            if json_data.get('@type') == 'ItemList' and 'itemListElement' in json_data:
                logger.info("Processing LD+JSON structured data")
                for list_item in json_data['itemListElement']:
                    if isinstance(list_item, dict) and 'item' in list_item:
                        item = list_item['item']
                        if isinstance(item, dict) and item.get('@type') == 'CreditCard':
                            # Convert LD+JSON format to our standard format
                            converted_item = self._convert_ld_json_to_standard(item)
                            card = process_item(converted_item)
                            if card:
                                cards.append(card)
            else:
                # Look for card arrays in the JSON structure
                for key, value in json_data.items():
                    if isinstance(value, list):
                        for item in value:
                            card = process_item(item)
                            if card:
                                cards.append(card)
        
        return cards
    
    def _convert_ld_json_to_standard(self, ld_json_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert LD+JSON structured data to our standard format"""
        card_name = ld_json_item.get('name', '')
        issuer_name = self._extract_issuer_from_name(card_name)
        
        converted = {
            'name': card_name,
            'institution': {'name': issuer_name},
            'details': {
                'annualFee': {'value': 0},
                'signUpBonusDetails': {'bonus': 0, 'description': ''},
                'rewardsRates': []
            }
        }
        
        # Extract annual fee from offers
        if 'offers' in ld_json_item and isinstance(ld_json_item['offers'], list):
            for offer in ld_json_item['offers']:
                if isinstance(offer, dict) and 'priceSpecification' in offer:
                    price_spec = offer['priceSpecification']
                    if isinstance(price_spec, dict) and 'price' in price_spec:
                        converted['details']['annualFee']['value'] = price_spec['price']
                        break
        
        return converted
    
    def _parse_complex_rewards(self, reward_text: str) -> Dict[str, float]:
        """Parse complex reward descriptions like '5x on travel, 3x on dining, 2x on other travel, 1x on all other'"""
        rewards = {}
        
        # Pattern to match "Nx on category" or "N% on category"
        patterns = [
            r'(\d+)x\s+on\s+([^,\.;]+)',
            r'(\d+)%\s+on\s+([^,\.;]+)',
            r'Earn\s+(\d+)x?\s+([^,\.;]+)',
            r'(\d+)\s+points?\s+per\s+\$1\s+(?:spent\s+)?on\s+([^,\.;]+)',
            r'(\d+)\s+miles?\s+per\s+\$1\s+(?:spent\s+)?on\s+([^,\.;]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, reward_text, re.IGNORECASE)
            for rate_str, category_desc in matches:
                try:
                    rate = float(rate_str)
                    category = self._parse_reward_category(category_desc)
                    if category and rate > 0:
                        rewards[category] = rate
                except ValueError:
                    continue
        
        return rewards
    
    def _scrape_cards_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Fallback method to scrape cards from HTML when JSON parsing fails"""
        logger.info("Using fallback HTML parsing method")
        
        cards_data = []
        card_containers = soup.select('tr.MuiTableRow-root, tbody tr')
        logger.info(f"Found {len(card_containers)} table rows for fallback parsing")
        
        for container in card_containers:
            try:
                # Extract card name
                card_name_elem = container.select_one('span[data-testid="summary-table-card-name"], td span, h3, h2')
                if not card_name_elem:
                    continue
                card_name = card_name_elem.text.strip()
                if len(card_name) < 3:
                    continue
                issuer = self._extract_issuer_from_name(card_name)
                # Extract annual fee from table cells
                annual_fee = 0
                fee_elements = container.select('td p, td span')
                for elem in fee_elements:
                    fee_text = elem.text.strip()
                    if '$' in fee_text and any(word in fee_text.lower() for word in ['fee', 'annual']):
                        fee_match = re.search(r'\$(\d+)', fee_text)
                        if fee_match:
                            annual_fee = int(fee_match.group(1))
                            break
                # --- New: Extract reward info and signup bonus from aria-label spans ---
                reward_categories = {}
                signup_bonus_points = 0
                signup_bonus_value = 0.0
                signup_bonus_spend_requirement = 0.0
                signup_bonus_time_period = 3
                # Find all aria-label spans
                aria_spans = container.select('span[aria-label]')
                reward_text = ''
                bonus_text = ''
                for span in aria_spans:
                    aria = span.get('aria-label', '')
                    if 'earn' in aria.lower() and ('mile' in aria.lower() or 'point' in aria.lower()):
                        reward_text = aria
                    if 'bonus' in aria.lower():
                        bonus_text = aria
                # Parse reward categories
                if reward_text:
                    reward_categories = self._parse_complex_rewards(reward_text)
                # Parse signup bonus
                if bonus_text:
                    # Extract points/miles
                    points_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s*(?:miles|points|point)', bonus_text, re.IGNORECASE)
                    if points_match:
                        try:
                            signup_bonus_points = int(points_match.group(1).replace(',', ''))
                        except Exception:
                            pass
                    # Extract spend requirement
                    spend_match = re.search(r'\$([0-9,]+)', bonus_text)
                    if spend_match:
                        try:
                            signup_bonus_spend_requirement = float(spend_match.group(1).replace(',', ''))
                        except Exception:
                            pass
                    # Extract time period
                    time_match = re.search(r'(\d+)\s*months?', bonus_text, re.IGNORECASE)
                    if time_match:
                        try:
                            signup_bonus_time_period = int(time_match.group(1))
                        except Exception:
                            pass
                    # Extract bonus value (for miles/points cards)
                    value_match = re.search(r'equal to \$([0-9,]+)', bonus_text)
                    if value_match:
                        try:
                            signup_bonus_value = float(value_match.group(1).replace(',', ''))
                        except Exception:
                            pass
                card_data = {
                    'name': card_name,
                    'issuer': issuer,
                    'annual_fee': annual_fee,
                    'reward_categories': reward_categories,
                    'special_offers': [],
                    'signup_bonus_points': signup_bonus_points,
                    'signup_bonus_value': signup_bonus_value,
                    'signup_bonus_spend_requirement': signup_bonus_spend_requirement,
                    'signup_bonus_time_period': signup_bonus_time_period,
                }
                cards_data.append(card_data)
                logger.info(f"Scraped {card_name} using HTML fallback")
            except Exception as e:
                logger.error(f"Error processing HTML container: {e}")
                continue
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