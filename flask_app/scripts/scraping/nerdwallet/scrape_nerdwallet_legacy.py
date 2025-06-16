#!/usr/bin/env python3
"""
Command-line script for scraping NerdWallet credit cards.
This script scrapes credit cards from NerdWallet and can either display the results,
save them to a JSON file, or import them directly into the database.
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the scraper and app modules
from app.utils.nerdwallet_scraper import scrape_nerdwallet_cards
from app.utils.data_utils import map_scraped_card_to_model
from app import create_app, db
from app.models.credit_card import CreditCard

def display_card(card, detailed=False):
    """Display a credit card in a formatted way"""
    print(f"\nCard: {card['name']}")
    print(f"Issuer: {card['issuer']}")
    print(f"Annual Fee: ${card['annual_fee']}")
    
    if detailed:
        # Print reward categories
        if card['reward_categories']:
            print("\nReward Categories:")
            for category in card['reward_categories']:
                print(f"  {category['percentage']}% on {category['category']}")
        
        # Print signup bonus
        if card['signup_bonus_value'] > 0 or card['signup_bonus_points'] > 0:
            print("\nSignup Bonus:")
            if card['signup_bonus_points'] > 0:
                print(f"  {card['signup_bonus_points']} points")
            if card['signup_bonus_value'] > 0:
                print(f"  ${card['signup_bonus_value']} value")
            if card['signup_bonus_spend_requirement'] > 0:
                print(f"  ${card['signup_bonus_spend_requirement']} spend required in {card['signup_bonus_time_period']} months")
        
        # Print special offers
        if card['special_offers']:
            print("\nSpecial Offers:")
            for offer in card['special_offers']:
                print(f"  ${offer['amount']} {offer['type']} ({offer['frequency']})")
    
    print("-" * 40)

def save_to_json(cards, filename=None):
    """Save card data to a JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nerdwallet_cards_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(cards, f, indent=2)
    
    print(f"Saved {len(cards)} cards to {filename}")
    return filename

def import_to_database(cards):
    """Import card data directly into the database"""
    # Create Flask app context for database operations
    app = create_app('development')
    
    with app.app_context():
        # Set source information
        source = 'nerdwallet'
        source_url = 'https://www.nerdwallet.com/the-best-credit-cards'
        import_date = datetime.utcnow()
        
        # Counter for added/updated cards
        added_count = 0
        updated_count = 0
        
        # Add cards to database
        for card_data in cards:
            try:
                # Map field names to match the CreditCard model
                mapped_data = map_scraped_card_to_model(card_data)
                
                # Add source information
                mapped_data['source'] = source
                mapped_data['source_url'] = source_url
                mapped_data['import_date'] = import_date
                
                # Check if card already exists
                existing_card = CreditCard.query.filter_by(name=mapped_data['name']).first()
                
                if existing_card:
                    # Update existing card
                    for key, value in mapped_data.items():
                        # Handle reward_categories and special_offers specially
                        if key in ['reward_categories', 'special_offers'] and isinstance(value, list):
                            setattr(existing_card, key, json.dumps(value))
                        else:
                            setattr(existing_card, key, value)
                    updated_count += 1
                else:
                    # Create new card
                    new_card = CreditCard(**mapped_data)
                    db.session.add(new_card)
                    added_count += 1
            
            except Exception as e:
                print(f"Error processing card {card_data.get('name', 'Unknown')}: {str(e)}")
        
        # Commit changes to database
        try:
            db.session.commit()
            print(f"Successfully imported {len(cards)} cards ({added_count} added, {updated_count} updated)")
        except Exception as e:
            db.session.rollback()
            print(f"Error committing to database: {str(e)}")

def main():
    """Main function for the command-line script"""
    # Set up command-line argument parser
    parser = argparse.ArgumentParser(description='Scrape credit cards from NerdWallet')
    parser.add_argument('--json', '-j', help='Save results to specified JSON file')
    parser.add_argument('--import', '-i', dest='import_db', action='store_true', 
                        help='Import results directly into the database')
    parser.add_argument('--detail', '-d', action='store_true', 
                        help='Display detailed information for each card')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress output except for errors')
    args = parser.parse_args()
    
    try:
        if not args.quiet:
            print("Starting NerdWallet scraper...")
        
        # Scrape cards from NerdWallet
        cards = scrape_nerdwallet_cards()
        
        if not args.quiet:
            print(f"Successfully scraped {len(cards)} cards from NerdWallet")
        
        # Save to JSON if requested
        if args.json:
            save_to_json(cards, args.json)
        
        # Import to database if requested
        if args.import_db:
            import_to_database(cards)
        
        # Display cards if not quiet and not importing to database
        if not args.quiet and not args.import_db:
            for card in cards:
                display_card(card, args.detail)
        
        # If no specific action was requested, save to a default JSON file
        if not args.json and not args.import_db and not args.quiet:
            save_to_json(cards)
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 