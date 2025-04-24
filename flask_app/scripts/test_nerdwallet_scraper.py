#!/usr/bin/env python3
"""
Test script for NerdWallet scraper.
This script tests the NerdWallet scraper and prints the results.
"""

import sys
import os
import json
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the scraper
from app.utils.nerdwallet_scraper import scrape_nerdwallet_cards

def main():
    """Main function to test the NerdWallet scraper"""
    print("Starting NerdWallet scraper test...")
    
    # Get current timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Scrape cards from NerdWallet
        cards = scrape_nerdwallet_cards()
        
        # Print summary
        print(f"Successfully scraped {len(cards)} cards from NerdWallet")
        
        # Save results to JSON file
        output_file = f"nerdwallet_cards_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cards, f, indent=2)
        
        print(f"Results saved to {output_file}")
        
        # Print sample of cards
        if cards:
            print("\nSample Card Data:")
            sample_card = cards[0]
            print(f"Card Name: {sample_card['name']}")
            print(f"Issuer: {sample_card['issuer']}")
            print(f"Annual Fee: ${sample_card['annual_fee']}")
            
            # Print reward categories
            print("\nReward Categories:")
            for category in sample_card['reward_categories']:
                print(f"  {category['percentage']}% on {category['category']}")
            
            # Print signup bonus
            if sample_card['signup_bonus_value'] > 0 or sample_card['signup_bonus_points'] > 0:
                print("\nSignup Bonus:")
                if sample_card['signup_bonus_points'] > 0:
                    print(f"  {sample_card['signup_bonus_points']} points")
                if sample_card['signup_bonus_value'] > 0:
                    print(f"  ${sample_card['signup_bonus_value']} value")
                if sample_card['signup_bonus_spend_requirement'] > 0:
                    print(f"  ${sample_card['signup_bonus_spend_requirement']} spend required in {sample_card['signup_bonus_time_period']} months")
            
            # Print special offers
            if sample_card['special_offers']:
                print("\nSpecial Offers:")
                for offer in sample_card['special_offers']:
                    print(f"  ${offer['amount']} {offer['type']} ({offer['frequency']})")
        
    except Exception as e:
        print(f"Error running scraper: {e}")
        raise

if __name__ == "__main__":
    main() 