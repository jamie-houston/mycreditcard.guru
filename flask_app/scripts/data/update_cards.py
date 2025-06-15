#!/usr/bin/env python
"""
Script to update credit card data in the database from NerdWallet.
This script can be run manually or scheduled to keep card data up-to-date.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.utils.card_scraper import scrape_credit_cards

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'card_updates.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('update_cards')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Update credit card data in the database')
    parser.add_argument('--force-update', action='store_true', help='Force update all cards even if no changes detected')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation for scraping')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of cards to scrape (0 for no limit)')
    return parser.parse_args()

def convert_list_dict_to_json(card_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert list and dict fields to JSON strings for database storage"""
    data_copy = card_data.copy()
    
    if 'reward_categories' in data_copy and isinstance(data_copy['reward_categories'], list):
        data_copy['reward_categories'] = json.dumps(data_copy['reward_categories'])
    
    if 'offers' in data_copy and isinstance(data_copy['offers'], list):
        data_copy['special_offers'] = json.dumps(data_copy['offers'])
        # Remove original field to avoid errors
        del data_copy['offers']
    
    # Map field names to match model
    if 'signup_bonus_spend_requirement' in data_copy:
        data_copy['signup_bonus_min_spend'] = data_copy['signup_bonus_spend_requirement']
        del data_copy['signup_bonus_spend_requirement']
    
    if 'signup_bonus_time_period' in data_copy:
        data_copy['signup_bonus_max_months'] = data_copy['signup_bonus_time_period']
        del data_copy['signup_bonus_time_period']
    
    # Remove the category field if it exists (we don't want to import it)
    if 'category' in data_copy:
        del data_copy['category']
    
    return data_copy

def compare_card_data(existing_card: CreditCard, new_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Compare existing card data with new data and determine if update is needed
    
    Args:
        existing_card: Existing card from database
        new_data: New data from scraper
        
    Returns:
        Tuple containing:
        - Boolean indicating if update is needed
        - Dictionary of fields that changed (old value, new value)
    """
    changes = {}
    update_needed = False
    
    # Fields to compare - skip things like id, created_at
    fields_to_compare = [
        'annual_fee',
        'signup_bonus_points',
        'signup_bonus_value',
    ]
    
    # Map fields for comparison
    field_mapping = {
        'signup_bonus_spend_requirement': 'signup_bonus_min_spend',
        'signup_bonus_max_months': 'signup_bonus_time_period',
    }
    
    # Add standard fields
    for field in fields_to_compare:
        old_value = getattr(existing_card, field)
        new_value = new_data.get(field)
        
        if new_value is not None and old_value != new_value:
            changes[field] = (old_value, new_value)
            update_needed = True
    
    # Add mapped fields
    for scraped_field, model_field in field_mapping.items():
        if scraped_field in new_data:
            old_value = getattr(existing_card, model_field)
            new_value = new_data.get(scraped_field)
            
            if new_value is not None and old_value != new_value:
                changes[model_field] = (old_value, new_value)
                update_needed = True
    
    # Compare JSON fields
    try:
        existing_reward_categories = json.loads(existing_card.reward_categories)
        new_reward_categories = new_data.get('reward_categories', [])
        
        if sorted(existing_reward_categories, key=lambda x: f"{x.get('category')}:{x.get('percentage')}") != \
           sorted(new_reward_categories, key=lambda x: f"{x.get('category')}:{x.get('percentage')}"):
            changes['reward_categories'] = (existing_reward_categories, new_reward_categories)
            update_needed = True
    except (json.JSONDecodeError, TypeError):
        # If there's an error parsing, assume they're different
        changes['reward_categories'] = ("Error parsing", new_data.get('reward_categories', []))
        update_needed = True
    
    try:
        existing_offers = json.loads(existing_card.special_offers)
        new_offers = new_data.get('offers', [])
        
        if sorted(existing_offers, key=lambda x: f"{x.get('type')}:{x.get('amount')}") != \
           sorted(new_offers, key=lambda x: f"{x.get('type')}:{x.get('amount')}"):
            changes['special_offers'] = (existing_offers, new_offers)
            update_needed = True
    except (json.JSONDecodeError, TypeError):
        # If there's an error parsing, assume they're different
        changes['special_offers'] = ("Error parsing", new_data.get('offers', []))
        update_needed = True
    
    return update_needed, changes

def update_cards(force_update: bool = False, use_proxies: bool = False, limit: int = 0) -> Dict[str, int]:
    """
    Update credit cards from NerdWallet
    
    Args:
        force_update: Whether to force update all cards even if no changes detected
        use_proxies: Whether to use proxy rotation for scraping
        limit: Limit the number of cards to scrape (0 for no limit)
        
    Returns:
        Dictionary with counts of actions taken (added, updated, unchanged)
    """
    logger.info("Starting card update process")
    
    # Create app context
    app = create_app('default')
    with app.app_context():
        # Scrape credit cards data
        cards_data = scrape_credit_cards(use_proxies)
        
        if limit > 0 and len(cards_data) > limit:
            logger.info(f"Limiting to {limit} cards (out of {len(cards_data)} scraped)")
            cards_data = cards_data[:limit]
        
        if not cards_data:
            logger.warning("No credit cards found to import")
            return {"added": 0, "updated": 0, "unchanged": 0, "errors": 0}
        
        # Import each card to database
        added_count = 0
        updated_count = 0
        unchanged_count = 0
        error_count = 0
        
        for card_data in cards_data:
            try:
                # Convert list/dict fields to JSON strings
                db_card_data = convert_list_dict_to_json(card_data)
                
                # Check if card already exists by name and issuer
                existing_card = CreditCard.query.filter_by(
                    name=card_data['name'],
                    issuer=card_data['issuer']
                ).first()
                
                if existing_card:
                    # Compare data and update if needed
                    update_needed, changes = compare_card_data(existing_card, card_data)
                    
                    if update_needed or force_update:
                        # Update existing card
                        for key, value in db_card_data.items():
                            if key != 'id' and hasattr(existing_card, key):
                                setattr(existing_card, key, value)
                        
                        # Update the updated_at timestamp
                        existing_card.updated_at = datetime.utcnow()
                        
                        # Log changes
                        if changes:
                            logger.info(f"Updating card: {card_data['name']} with changes: {json.dumps(changes, default=str)}")
                        else:
                            logger.info(f"Force updating card: {card_data['name']} (no changes detected)")
                        
                        updated_count += 1
                    else:
                        # No changes needed
                        logger.info(f"Card unchanged: {card_data['name']}")
                        unchanged_count += 1
                else:
                    # Create new card
                    card = CreditCard(**db_card_data)
                    db.session.add(card)
                    added_count += 1
                    logger.info(f"Added new card: {card_data['name']}")
                
                # Commit after each card to prevent losing all progress if one fails
                db.session.commit()
                
            except Exception as e:
                db.session.rollback()
                error_count += 1
                logger.error(f"Error updating card {card_data.get('name', 'Unknown')}: {str(e)}")
        
        logger.info(f"Update completed. Added {added_count} cards, updated {updated_count} cards, "
                   f"unchanged {unchanged_count} cards, errors {error_count}.")
        
        return {
            "added": added_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
            "errors": error_count
        }

if __name__ == "__main__":
    args = parse_arguments()
    results = update_cards(args.force_update, args.use_proxies, args.limit)
    
    # Print summary
    print(f"\nUpdate Summary:")
    print(f"  New cards added: {results['added']}")
    print(f"  Existing cards updated: {results['updated']}")
    print(f"  Cards unchanged: {results['unchanged']}")
    print(f"  Errors encountered: {results['errors']}")
    print(f"\nTotal cards processed: {sum(results.values())}") 