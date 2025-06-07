#!/usr/bin/env python3
import json
import sys
import os
from datetime import datetime
from extract_card_info import extract_card_info
from flask_app.app.utils.nerdwallet_scraper import scrape_nerdwallet_cards

def integrate_card_data(html_file=None, url=None):
    """
    Extract card data and prepare it for database import by
    ensuring all fields are properly serialized.
    
    Args:
        html_file: Optional HTML file to extract from
        url: Optional URL to scrape from
    
    Returns:
        List of card dictionaries with properly serialized fields
    """
    cards = []
    
    # Get cards from HTML file if provided
    if html_file and os.path.exists(html_file):
        print(f"Extracting cards from HTML file: {html_file}")
        extracted_cards = extract_card_info(html_file)
        cards.extend(extracted_cards)
    
    # Get cards from URL if provided
    if url:
        print(f"Scraping cards from URL: {url}")
        scraped_cards = scrape_nerdwallet_cards(source_url=url)
        cards.extend(scraped_cards)
    
    # Use a dictionary to track unique cards by name
    # This ensures that if we find duplicate cards, the later one overwrites the earlier one
    card_dict = {}
    for card in cards:
        # Use card name as the unique key
        card_dict[card['name']] = card
    
    # Convert back to a list for final processing
    unique_cards = list(card_dict.values())
    print(f"Found {len(cards)} cards, {len(unique_cards)} unique after deduplication")
    
    # Prepare cards for database import
    prepared_cards = []
    for card in unique_cards:
        # Ensure reward_categories is serialized to JSON string
        if isinstance(card.get('reward_categories'), dict):
            card['reward_categories'] = json.dumps(card['reward_categories'])
        
        # Ensure special_offers is serialized to JSON string
        if isinstance(card.get('special_offers'), list):
            card['special_offers'] = json.dumps(card.get('special_offers', []))
        
        # Ensure other fields have proper defaults
        card['point_value'] = card.get('point_value', 0.01)
        card['is_active'] = card.get('is_active', True)
        card['signup_bonus_points'] = card.get('signup_bonus_points', 0)
        card['signup_bonus_value'] = card.get('signup_bonus_value', 0.0)
        card['signup_bonus_min_spend'] = card.get('signup_bonus_spend_requirement', 0.0)
        card['signup_bonus_time_limit'] = card.get('signup_bonus_time_period', 3)
        
        prepared_cards.append(card)
    
    return prepared_cards

def save_to_json(cards, output_file='prepared_cards.json'):
    """Save prepared cards to a JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2)
    print(f"Saved {len(cards)} cards to {output_file}")

if __name__ == "__main__":
    # Parse command line arguments
    html_file = None
    url = None
    
    if len(sys.argv) > 1:
        if sys.argv[1].startswith('http'):
            url = sys.argv[1]
        else:
            html_file = sys.argv[1]
    else:
        # Default to using the debug HTML file
        html_file = "nerdwallet_debug.html"
    
    # Get and prepare card data
    prepared_cards = integrate_card_data(html_file, url)
    
    # Display summary
    print(f"\nPrepared {len(prepared_cards)} cards for database import")
    
    # Save to JSON
    save_to_json(prepared_cards)
    
    print("\nTo import these cards into your database, use the import_cards.py script with this JSON file") 