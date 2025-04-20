#!/usr/bin/env python
"""
Test script to verify the CreditCards.com scraper is working properly.
"""

import sys
import json
from pprint import pprint
from app.utils.card_scraper import scrape_credit_cards

def main():
    """Run the CreditCards.com scraper and display the results."""
    print("Fetching credit cards from CreditCards.com...")
    cards = scrape_credit_cards('creditcards.com')
    
    if not cards:
        print("No cards were found.")
        return 1
    
    print(f"\nFound {len(cards)} credit cards:")
    print("-" * 50)
    
    for i, card in enumerate(cards, 1):
        print(f"{i}. {card['name']} ({card['issuer']})")
        print(f"   Annual Fee: ${card['annual_fee']}")
        if card.get('signup_bonus_points'):
            print(f"   Signup Bonus: {card['signup_bonus_points']} points")
        if card.get('signup_bonus_value'):
            print(f"   Bonus Value: ${card['signup_bonus_value']}")
        if card.get('signup_bonus_spend_requirement'):
            print(f"   Min Spend: ${card['signup_bonus_spend_requirement']}")
        if card.get('signup_bonus_time_period'):
            print(f"   Time Period: {card['signup_bonus_time_period']} months")
        
        # Show reward categories
        if card.get('reward_categories') and len(card['reward_categories']) > 0:
            print("   Reward Categories:")
            for category in card['reward_categories']:
                print(f"      • {category['percentage']}% on {category['category']}")
        
        # Show special offers
        if card.get('offers') and len(card['offers']) > 0:
            print("   Special Offers:")
            for offer in card['offers']:
                print(f"      • {offer['type']}: ${offer.get('amount', 'N/A')}")
        
        # Show any additional category information
        if card.get('category'):
            print(f"   Category: {card['category']}")
        
        print("-" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 