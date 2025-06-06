#!/usr/bin/env python
"""Script to import credit cards from NerdWallet."""

import os
import sys
import json
import logging
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category, CreditCardReward
from app.utils.card_scraper import scrape_credit_cards

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('import_cards')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Import credit cards from NerdWallet')
    parser.add_argument('--use-proxies', action='store_true', help='Use proxy rotation for scraping')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of cards to import (0 for no limit)')
    parser.add_argument('--clear', action='store_true', help='Clear existing cards before import')
    return parser.parse_args()

def validate_and_process_reward_categories(reward_categories_data, card_name):
    """Validate reward categories against global category system and return valid ones."""
    if not reward_categories_data:
        return []
    
    # Get all valid categories once for efficiency
    valid_categories = {cat.name.lower(): cat for cat in Category.get_active_categories()}
    
    valid_rewards = []
    invalid_categories = []
    
    try:
        # Parse JSON if it's a string
        if isinstance(reward_categories_data, str):
            categories = json.loads(reward_categories_data)
        else:
            categories = reward_categories_data
            
        for cat_data in categories:
            category_name = cat_data.get('category', '').lower().strip()
            rate = float(cat_data.get('rate', 1.0))
            
            if category_name in valid_categories:
                valid_rewards.append({
                    'category': valid_categories[category_name].name,
                    'category_id': valid_categories[category_name].id,
                    'rate': rate
                })
            else:
                invalid_categories.append(category_name)
                
        if invalid_categories:
            logger.warning(f"Card '{card_name}': Skipped invalid categories: {invalid_categories}")
            
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.error(f"Card '{card_name}': Error processing reward categories: {e}")
        return []
    
    return valid_rewards

def create_card_rewards(card, valid_rewards):
    """Create CreditCardReward entries for valid categories."""
    for reward_data in valid_rewards:
        # Check if reward already exists
        existing_reward = CreditCardReward.query.filter_by(
            credit_card_id=card.id,
            category_id=reward_data['category_id']
        ).first()
        
        if existing_reward:
            existing_reward.reward_percent = reward_data['rate']
        else:
            new_reward = CreditCardReward(
                credit_card_id=card.id,
                category_id=reward_data['category_id'],
                reward_percent=reward_data['rate'],
                is_bonus_category=(reward_data['rate'] > 1.0)
            )
            db.session.add(new_reward)

def import_cards(use_proxies: bool = False, limit: int = 0, clear: bool = False):
    """Import credit cards from NerdWallet."""
    logger.info("Starting card import script")
    
    # Create app context
    app = create_app('default')
    with app.app_context():
        # Clear existing cards if requested
        if clear:
            try:
                num_deleted = CreditCard.query.delete()
                db.session.commit()
                logger.info(f"Cleared {num_deleted} existing credit cards")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error clearing existing cards: {e}")
                return
        
        # Scrape credit cards data directly from the main table
        cards_data = scrape_credit_cards(use_proxies)
        
        if not cards_data:
            logger.warning("No credit cards found to import")
            return
        
        if limit > 0 and len(cards_data) > limit:
            logger.info(f"Limiting to {limit} cards (out of {len(cards_data)} scraped)")
            cards_data = cards_data[:limit]
        
        # Import each card to database
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        
        for card_data in cards_data:
            try:
                # Skip cards without a name
                if not card_data.get('name'):
                    logger.warning(f"Skipping card with missing name: {card_data}")
                    skipped_count += 1
                    continue
                
                card_name = card_data['name']
                
                # Process and validate reward categories
                reward_categories_data = card_data.get('reward_categories')
                valid_rewards = validate_and_process_reward_categories(reward_categories_data, card_name)
                
                # Remove fields that aren't in the model or are processed separately
                fields_to_remove = ['rewards_rate', 'reward_categories']
                for field in fields_to_remove:
                    if field in card_data:
                        card_data.pop(field)
                
                # Filter out any other fields that don't match the model
                valid_fields = ['name', 'issuer', 'annual_fee', 'special_offers', 
                               'signup_bonus_points', 'signup_bonus_value', 'signup_bonus_min_spend', 
                               'signup_bonus_time_limit', 'is_active', 'source', 'source_url']
                
                # Map scraper field names to model field names
                field_mapping = {
                    'signup_bonus_spend_requirement': 'signup_bonus_min_spend',
                    'signup_bonus_time_period': 'signup_bonus_time_limit',
                    'offers': 'special_offers'
                }
                
                # Rename fields to match model
                for scraper_field, model_field in field_mapping.items():
                    if scraper_field in card_data and model_field in valid_fields:
                        card_data[model_field] = card_data.pop(scraper_field)
                
                # Now filter the fields
                filtered_card_data = {k: v for k, v in card_data.items() if k in valid_fields}
                
                # Add empty reward_categories for backward compatibility
                filtered_card_data['reward_categories'] = json.dumps([])
                
                # Convert list/dict fields to JSON strings
                if 'special_offers' in filtered_card_data:
                    filtered_card_data['special_offers'] = json.dumps(filtered_card_data['special_offers'])
                
                # Check if card already exists by name and issuer
                existing_card = CreditCard.query.filter_by(
                    name=filtered_card_data['name'],
                    issuer=filtered_card_data['issuer']
                ).first()
                
                if existing_card:
                    # Update existing card
                    for key, value in filtered_card_data.items():
                        setattr(existing_card, key, value)
                    
                    # Clear existing rewards and add new ones
                    CreditCardReward.query.filter_by(credit_card_id=existing_card.id).delete()
                    create_card_rewards(existing_card, valid_rewards)
                    
                    updated_count += 1
                    logger.info(f"Updated card: {filtered_card_data['name']} (with {len(valid_rewards)} reward categories)")
                else:
                    # Create new card
                    card = CreditCard(**filtered_card_data)
                    db.session.add(card)
                    db.session.flush()  # Get the card ID
                    
                    # Add reward categories
                    create_card_rewards(card, valid_rewards)
                    
                    imported_count += 1
                    logger.info(f"Added new card: {filtered_card_data['name']} (with {len(valid_rewards)} reward categories)")
                
                # Commit every 10 cards to avoid large transactions
                if (imported_count + updated_count) % 10 == 0:
                    db.session.commit()
                    logger.info(f"Committed batch of cards (progress: {imported_count + updated_count}/{len(cards_data)})")
                
            except Exception as e:
                logger.error(f"Error importing card {card_data.get('name', 'unknown')}: {e}")
                logger.exception(e)
                skipped_count += 1
        
        # Final commit for any remaining cards
        try:
            db.session.commit()
            logger.info(f"Import completed. Added {imported_count} new cards, updated {updated_count} existing cards, skipped {skipped_count} cards.")
            return imported_count, updated_count, skipped_count
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during final commit: {e}")
            return None

if __name__ == "__main__":
    args = parse_arguments()
    import_cards(args.use_proxies, args.limit, args.clear) 