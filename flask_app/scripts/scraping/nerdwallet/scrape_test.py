#!/usr/bin/env python
"""
Web Scraping Test

This script tests web scraping functionality with sample NerdWallet URLs.
Scrapes credit card data and saves results to JSON files for validation.
"""

from app.utils.nerdwallet_scraper import scrape_nerdwallet_cards
import json

# Test URLs to scrape
test_urls = [
    'https://www.nerdwallet.com/best/credit-cards/travel',
    'https://www.nerdwallet.com/best/credit-cards/rewards'
]

for url in test_urls:
    print(f"Scraping cards from {url}...")
    try:
        cards = scrape_nerdwallet_cards(source_url=url)
        print(f"Successfully scraped {len(cards)} cards")
        
        # Save the results to a JSON file
        output_file = f"cards_from_{url.split('/')[-1]}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2)
        print(f"Results saved to {output_file}")
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    
    print("-" * 50) 