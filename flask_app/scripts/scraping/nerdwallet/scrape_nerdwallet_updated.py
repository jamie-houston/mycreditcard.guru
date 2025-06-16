#!/usr/bin/env python3
"""
Credit Card Rewards Data Scraper for NerdWallet
Extracts card names, annual fees, rewards categories, and percentages
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CreditCardScraper:
    def __init__(self):
        self.base_url = "https://www.nerdwallet.com"
        self.target_url = "https://www.nerdwallet.com/best/credit-cards/rewards"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.cards_data = []

    def get_page_content(self, url: str) -> BeautifulSoup:
        """Fetch and parse page content"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_card_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract individual card review links"""
        card_links = []
        
        # Look for card review links
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if '/reviews/credit-cards/' in href and href not in card_links:
                full_url = urljoin(self.base_url, href)
                card_links.append(full_url)
        
        logger.info(f"Found {len(card_links)} card review links")
        return card_links

    def parse_annual_fee(self, text: str) -> str:
        """Extract annual fee from text"""
        if not text:
            return "Not specified"
        
        # Common patterns for annual fees
        fee_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:annual\s*fee|fee)',
            r'(\$\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:annual\s*fee|fee)',
            r'\$(\d+)\s*(?:intro|first\s*year)',
            r'no\s*annual\s*fee',
            r'\$0\s*(?:annual\s*fee|fee)'
        ]
        
        text_lower = text.lower()
        
        if 'no annual fee' in text_lower or '$0' in text_lower:
            return "$0"
        
        for pattern in fee_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if 'no annual fee' in pattern:
                    return "$0"
                fee_value = match.group(1) if match.group(1) else match.group(0)
                return f"${fee_value}" if not fee_value.startswith('$') else fee_value
        
        return "Not specified"

    def extract_signup_bonus(self, text: str) -> Dict[str, str]:
        """Extract signup bonus and requirements from text."""
        bonus_patterns = [
            r"earn\s+([\d,]+)\s*(points|miles|cash back|bonus|reward[s]?)\s*(?:after|when)?[^\$\d]*(\$[\d,]+)?[^\d]*(?:in|within)?\s*(\d+)?\s*(month|months)?",
            r"welcome offer:.*?(\d+[\d,]*)\s*(points|miles|cash back|bonus|reward[s]?)",
            r"intro bonus:.*?(\d+[\d,]*)\s*(points|miles|cash back|bonus|reward[s]?)"
        ]
        text_lower = text.lower()
        for pattern in bonus_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                amount = match.group(1)
                bonus_type = match.group(2) if len(match.groups()) > 1 else ''
                spend = match.group(3) if len(match.groups()) > 2 else ''
                months = match.group(4) if len(match.groups()) > 3 else ''
                return {
                    'signup_bonus': f"{amount} {bonus_type}".strip(),
                    'signup_bonus_requirements': f"Spend {spend} in {months} months".strip() if spend or months else ''
                }
        return {'signup_bonus': '', 'signup_bonus_requirements': ''}

    def normalize_category(self, category: str) -> str:
        """Normalize category names (e.g., 'all other purchases' -> 'other')."""
        category = category.lower().strip()
        if 'all other' in category or 'everything else' in category or 'other purchases' in category:
            return 'other'
        if 'grocery' in category:
            return 'groceries'
        if 'restaurant' in category or 'dining' in category:
            return 'dining'
        if 'gas' in category:
            return 'gas'
        if 'travel' in category:
            return 'travel'
        if 'entertainment' in category:
            return 'entertainment'
        if 'shopping' in category:
            return 'shopping'
        if 'streaming' in category:
            return 'streaming'
        if 'drugstore' in category or 'pharmacy' in category:
            return 'drugstores'
        if 'home improvement' in category:
            return 'home_improvement'
        if 'office' in category:
            return 'office_supplies'
        if 'utility' in category:
            return 'utilities'
        if 'health' in category:
            return 'healthcare'
        if 'education' in category:
            return 'education'
        if 'paypal' in category:
            return 'paypal'
        if 'amazon' in category:
            return 'amazon'
        return category

    def parse_rewards_info(self, text: str) -> Dict[str, str]:
        """Extract rewards categories and percentages (improved)."""
        rewards_info = {
            'categories': [],
            'rates': [],
            'details': text
        }
        if not text:
            return rewards_info
        text_lower = text.lower()
        reward_patterns = [
            r'(\d+(?:\.\d+)?)[%x×]\s*(?:cash\s*back|points|miles)?\s*(?:on|at|for)\s*([^,\.;]+)',
            r'(\d+(?:\.\d+)?)[%x×]\s*([^,\.;]+?)(?:\s*(?:cash\s*back|points|miles))',
            r'earn\s*(\d+(?:\.\d+)?)[%x×]?\s*(?:cash\s*back|points|miles)?\s*(?:on|at|for)\s*([^,\.;]+)',
        ]
        categories_found = set()
        rates_found = set()
        for pattern in reward_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                rate = match.group(1)
                category = match.group(2).strip()
                category = re.sub(r'\s+', ' ', category)
                category = category.strip(' ,.').lower()
                norm_category = self.normalize_category(category)
                if 2 < len(norm_category) < 100:
                    categories_found.add(norm_category)
                    rates_found.add(f"{rate}% {norm_category}")
        rewards_info['categories'] = list(categories_found)
        rewards_info['rates'] = list(rates_found)
        return rewards_info

    def scrape_card_details(self, card_url: str) -> Optional[Dict]:
        """Scrape detailed information for a single card"""
        logger.info(f"Scraping card details from: {card_url}")
        
        soup = self.get_page_content(card_url)
        if not soup:
            return None
        
        card_data = {
            'name': 'Unknown',
            'annual_fee': 'Not specified',
            'rewards_categories': [],
            'rewards_rates': [],
            'rewards_details': '',
            'signup_bonus': '',
            'signup_bonus_requirements': '',
            'url': card_url
        }
        
        # Extract card name
        title_selectors = [
            'h1',
            '.card-title',
            '[data-testid="card-title"]',
            '.review-title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                card_data['name'] = title_elem.get_text().strip()
                break
        
        # Extract rewards information from multiple sections
        rewards_text = ""
        rewards_selectors = [
            '.rewards-breakdown',
            '.card-details',
            '[data-testid="rewards"]',
            '.earning-rates',
            '.benefits-list'
        ]
        
        for selector in rewards_selectors:
            elements = soup.select(selector)
            for elem in elements:
                rewards_text += " " + elem.get_text()
        
        # Also check for specific reward information in text
        all_text = soup.get_text()
        
        # Extract annual fee
        fee_text = all_text
        card_data['annual_fee'] = self.parse_annual_fee(fee_text)
        
        # Extract rewards information
        rewards_info = self.parse_rewards_info(rewards_text + " " + all_text)
        card_data['rewards_categories'] = rewards_info['categories']
        card_data['rewards_rates'] = rewards_info['rates']
        card_data['rewards_details'] = rewards_info['details'][:500]  # Limit length
        
        # Extract signup bonus
        bonus_info = self.extract_signup_bonus(rewards_text + " " + all_text)
        card_data['signup_bonus'] = bonus_info['signup_bonus']
        card_data['signup_bonus_requirements'] = bonus_info['signup_bonus_requirements']
        
        logger.info(f"Successfully scraped: {card_data['name']}")
        return card_data

    def scrape_main_page(self) -> List[Dict]:
        """Scrape the main rewards page for card information"""
        logger.info("Scraping main rewards page")
        
        soup = self.get_page_content(self.target_url)
        if not soup:
            return []
        
        cards_data = []
        
        # Extract cards from the comparison table
        table_rows = soup.find_all('tr')
        for row in table_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:  # Ensure we have enough columns
                card_data = {
                    'name': 'Unknown',
                    'annual_fee': 'Not specified',
                    'rewards_categories': [],
                    'rewards_rates': [],
                    'rewards_details': '',
                    'signup_bonus': '',
                    'signup_bonus_requirements': '',
                    'url': self.target_url
                }
                
                # Extract information from table cells
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text().strip()
                    
                    if i == 0:  # First column usually contains card name or category
                        if len(cell_text) > 10:  # Likely a card name
                            card_data['name'] = cell_text
                    elif 'annual fee' in cell_text.lower() or '$' in cell_text:
                        card_data['annual_fee'] = self.parse_annual_fee(cell_text)
                    elif any(term in cell_text.lower() for term in ['%', 'cash back', 'points', 'miles']):
                        rewards_info = self.parse_rewards_info(cell_text)
                        card_data['rewards_categories'].extend(rewards_info['categories'])
                        card_data['rewards_rates'].extend(rewards_info['rates'])
                
                if card_data['name'] != 'Unknown':
                    cards_data.append(card_data)
        
        # Also extract from card sections
        card_sections = soup.find_all(['section', 'div'], class_=re.compile(r'card|review'))
        for section in card_sections:
            section_text = section.get_text()
            
            # Look for card names in headers
            headers = section.find_all(['h1', 'h2', 'h3', 'h4'])
            for header in headers:
                header_text = header.get_text().strip()
                if len(header_text) > 10 and any(word in header_text.lower() for word in ['card', 'credit']):
                    card_data = {
                        'name': header_text,
                        'annual_fee': self.parse_annual_fee(section_text),
                        'rewards_categories': [],
                        'rewards_rates': [],
                        'rewards_details': section_text[:500],
                        'signup_bonus': '',
                        'signup_bonus_requirements': '',
                        'url': self.target_url
                    }
                    
                    rewards_info = self.parse_rewards_info(section_text)
                    card_data['rewards_categories'] = rewards_info['categories']
                    card_data['rewards_rates'] = rewards_info['rates']
                    
                    cards_data.append(card_data)
        
        logger.info(f"Extracted {len(cards_data)} cards from main page")
        return cards_data

    def scrape_all_cards(self):
        """Main scraping method"""
        logger.info("Starting credit card rewards scraping")
        
        # First, scrape the main page
        main_page_cards = self.scrape_main_page()
        self.cards_data.extend(main_page_cards)
        
        # Then get individual card links and scrape detailed pages
        soup = self.get_page_content(self.target_url)
        if soup:
            card_links = self.extract_card_links(soup)
            
            for link in card_links[:10]:  # Limit to first 10 to avoid being blocked
                card_data = self.scrape_card_details(link)
                if card_data:
                    self.cards_data.append(card_data)
                time.sleep(1)  # Be respectful to the server
        
        # Remove duplicates
        unique_cards = []
        seen_names = set()
        for card in self.cards_data:
            if card['name'] not in seen_names:
                unique_cards.append(card)
                seen_names.add(card['name'])
        
        self.cards_data = unique_cards
        logger.info(f"Total unique cards scraped: {len(self.cards_data)}")

    def save_to_csv(self, filename: str = 'credit_cards_rewards.csv'):
        """Save scraped data to CSV file"""
        if not self.cards_data:
            logger.warning("No data to save")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'annual_fee', 'rewards_categories', 'rewards_rates', 'rewards_details', 'signup_bonus', 'signup_bonus_requirements', 'url']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for card in self.cards_data:
                # Convert lists to strings for CSV
                csv_card = card.copy()
                csv_card['rewards_categories'] = '; '.join(card['rewards_categories']) if card['rewards_categories'] else ''
                csv_card['rewards_rates'] = '; '.join(card['rewards_rates']) if card['rewards_rates'] else ''
                writer.writerow(csv_card)
        
        logger.info(f"Data saved to {filename}")

    def save_to_json(self, filename: str = 'credit_cards_rewards.json'):
        """Save scraped data to JSON file"""
        if not self.cards_data:
            logger.warning("No data to save")
            return
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.cards_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {filename}")

    def print_summary(self):
        """Print a summary of scraped data"""
        if not self.cards_data:
            print("No data scraped")
            return
        
        print(f"\n{'='*60}")
        print(f"CREDIT CARD REWARDS DATA SUMMARY")
        print(f"{'='*60}")
        print(f"Total cards scraped: {len(self.cards_data)}")
        print(f"{'='*60}")
        
        for i, card in enumerate(self.cards_data, 1):
            print(f"\n{i}. {card['name']}")
            print(f"   Annual Fee: {card['annual_fee']}")
            if card['rewards_rates']:
                print(f"   Rewards Rates: {', '.join(card['rewards_rates'])}")
            if card['rewards_categories']:
                print(f"   Categories: {', '.join(card['rewards_categories'][:3])}{'...' if len(card['rewards_categories']) > 3 else ''}")
            if card.get('signup_bonus'):
                print(f"   Signup Bonus: {card['signup_bonus']} ({card['signup_bonus_requirements']})")

def main():
    """Main execution function"""
    scraper = CreditCardScraper()
    
    try:
        scraper.scrape_all_cards()
        scraper.print_summary()
        scraper.save_to_csv()
        scraper.save_to_json()
        
        print(f"\nScraping completed successfully!")
        print(f"Data saved to 'credit_cards_rewards.csv' and 'credit_cards_rewards.json'")
        
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Error during scraping: {e}")

if __name__ == "__main__":
    main()