#!/usr/bin/env python
"""
Seed Credit Cards

This script seeds the database with sample credit cards for development and testing.
Creates example credit cards with different reward structures and features.
Can also import cards from scraped data files in /data/output.
"""

import sys
import os
import json
import glob
import time
import sqlite3
from datetime import datetime

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category, CreditCardReward
from app.models import CardIssuer


def should_skip_category(category_name: str) -> bool:
    """
    Check if a category name should be skipped during import.
    Returns True for parsing artifacts and invalid category names.
    """
    if not category_name or not isinstance(category_name, str):
        return True
    
    category_lower = category_name.lower().strip()
    
    # Skip empty or very short names
    if len(category_lower) < 2:
        return True
    
    # Skip obvious parsing artifacts (dollar amounts, limits, etc.)
    skip_patterns = [
        'up to $',
        'the first $',
        'these purchases up to',
        'quarterly maximum',
        'select u',  # Truncated text
        'all other eligible',  # Generic text that's not a category
        'purchases in your choice'  # This is too generic
    ]
    
    for pattern in skip_patterns:
        if pattern in category_lower:
            return True
    
    # Skip single letters or obvious truncations
    if len(category_lower) <= 2 and not category_lower.isalpha():
        return True
    
    return False


def retry_db_operation(func, max_retries=5, delay=1):
    """Retry database operations with exponential backoff to handle locks."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_msg = str(e).lower()
            if 'database is locked' in error_msg or 'database locked' in error_msg:
                if attempt < max_retries - 1:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    print(f"⏳ Database locked, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"❌ Database remains locked after {max_retries} attempts")
                    print("💡 Try stopping the Flask development server and running again")
                    raise
            else:
                # Non-lock error, don't retry
                raise
    return None


def safe_db_commit():
    """Safely commit database changes with retry logic."""
    def commit_func():
        db.session.commit()
        return True
    
    return retry_db_operation(commit_func)


def safe_db_flush():
    """Safely flush database changes with retry logic."""
    def flush_func():
        db.session.flush()
        return True
    
    return retry_db_operation(flush_func)


def seed_credit_cards():
    """Seed the database with sample credit cards."""
    
    # Sample credit cards data based on user specifications
    cards_data = [
        {
            "name": "Chase Ink Business Unlimited Card",
            "issuer": "Chase",
            "annual_fee": 0,
            "reward_type": "cash_back",
            "reward_value_multiplier": 1,
            "signup_bonus": {"cash_back": 750, "value": 750, "min_spend": 6000, "max_months": 3},
            "reward_categories": [
                {"category": "other", "rate": 1.5, "limit": None}
            ],
            "special_offers": [
                "Business credit card",
                "No annual fee",
                "Flat rate on all purchases"
            ]
        },
        {
            "name": "Chase Sapphire Preferred® Card",
            "issuer": "Chase",
            "annual_fee": 95,
            "reward_type": "points",
            "reward_value_multiplier": 0.0125,
            "signup_bonus": {"points": 60000, "value": 750, "min_spend": 4000, "max_months": 3},
            "reward_categories": [
                {"category": "other", "rate": 1.0, "limit": None},
                {"category": "dining", "rate": 3.0, "limit": None},
                {"category": "travel", "rate": 2.0, "limit": None},
                {"category": "streaming", "rate": 3.0, "limit": None}
            ],
            "special_offers": [
                "Transfer partners",
                "No foreign transaction fees",
                "Travel protection"
            ]
        },
        {
            "name": "The Platinum Card® from American Express",
            "issuer": "American Express",
            "annual_fee": 695,
            "reward_type": "points",
            "reward_value_multiplier": 0.016,
            "signup_bonus": {"points": 175000, "value": 2800, "min_spend": 8000, "max_months": 6},
            "reward_categories": [
                {"category": "other", "rate": 1.0, "limit": None},
                {"category": "travel", "rate": 5.0, "limit": None}
            ],
            "special_offers": [
                "$200 annual airline fee credit",
                "$200 annual hotel credit",
                "Airport lounge access",
                "Concierge service"
            ]
        },
        {
            "name": "American Express Gold Card",
            "issuer": "American Express",
            "annual_fee": 325,
            "reward_type": "points",
            "reward_value_multiplier": 0.016,
            "signup_bonus": {"points": 100000, "value": 1600, "min_spend": 6000, "max_months": 6},
            "reward_categories": [
                {"category": "other", "rate": 1.0, "limit": None},
                {"category": "dining", "rate": 4.0, "limit": None},
                {"category": "travel", "rate": 3.0, "limit": None},
                {"category": "groceries", "rate": 4.0, "limit": 25000}
            ],
            "special_offers": [
                "$120 annual dining credit",
                "$120 annual Uber credit",
                "No foreign transaction fees"
            ]
        },
        {
            "name": "Bank of America Travel Rewards credit card for Students",
            "issuer": "Bank of America",
            "annual_fee": 0,
            "reward_type": "points",
            "reward_value_multiplier": 0.01,
            "signup_bonus": {"points": 25000, "value": 250, "min_spend": 1000, "max_months": 3},
            "reward_categories": [
                {"category": "other", "rate": 1.5, "limit": None},
            ],
            "special_offers": [
                "Earn 3 points per $1 spent on travel purchases booked through the Bank of America Travel Center."
            ]
        },
        {
            "name": "Capital One Venture Rewards Credit Card",
            "issuer": "Capital One",
            "annual_fee": 95,
            "reward_type": "miles",
            "reward_value_multiplier": 0.01,
            "signup_bonus": {"miles": 75000, "value": 750, "min_spend": 4000, "max_months": 3},
            "reward_categories": [
                {"category": "other", "rate": 2, "limit": None},
            ],
            "special_offers": [
                "Earn 5X miles on hotels, vacation rentals and rental cars booked through Capital One Travel."
            ]
        },
        {
            "name": "Citi Strata Premier℠ Card",
            "issuer": "Citi",
            "annual_fee": 95,
            "reward_type": "points",
            "reward_value_multiplier": 0.01,
            "signup_bonus": {"points": 60000, "value": 600, "min_spend": 4000, "max_months": 3},
            "reward_categories": [
                {"category": "travel", "rate": 3, "limit": None},
            ],
            "special_offers": [
                "Earn 5X miles on hotels, vacation rentals and rental cars booked through Capital One Travel."
            ]
        }
    ]
    
    created_count = 0
    skipped_count = 0
    
    for card_data in cards_data:
        # Get the issuer first
        issuer_name = card_data.pop('issuer')
        issuer = CardIssuer.query.filter_by(name=issuer_name).first()
        if not issuer:
            print(f"⚠️  Warning: Issuer '{issuer_name}' not found for card '{card_data['name']}'. Skipping.")
            continue
        
        # Check if card already exists
        existing_card = CreditCard.query.filter_by(
            name=card_data['name'], 
            issuer_id=issuer.id
        ).first()
        
        if existing_card:
            skipped_count += 1
            continue
        
        # Extract reward categories and special offers
        reward_categories = card_data.pop('reward_categories', [])
        special_offers = card_data.pop('special_offers', [])
        signup_bonus_data = card_data.pop('signup_bonus', None)
        
        # Convert lists to JSON strings for database storage
        card_data['special_offers'] = json.dumps(special_offers)
        
        # Convert signup bonus dict to JSON string if present
        if signup_bonus_data and isinstance(signup_bonus_data, dict):
            card_data['signup_bonus'] = json.dumps(signup_bonus_data)
        
        # Set the issuer_id
        card_data['issuer_id'] = issuer.id
        
        # Create the card
        card = CreditCard(**card_data)
        db.session.add(card)
        safe_db_flush()  # Get the card ID
        
        # Create CreditCardReward relationship records
        for reward_data in reward_categories:
            category_name = reward_data.get('category')
            rate = reward_data.get('rate', 1.0)
            limit = reward_data.get('limit')
            
            if category_name:
                # Find the category by name
                category = Category.get_by_name(category_name)
                if category:
                    # Create the reward relationship
                    credit_card_reward = CreditCardReward(
                        credit_card_id=card.id,
                        category_id=category.id,
                        reward_percent=rate,
                        is_bonus_category=(rate > 1.0),
                        limit=limit
                    )
                    db.session.add(credit_card_reward)
                else:
                    print(f"⚠️  Warning: Category '{category_name}' not found for card '{card.name}'")
        
        created_count += 1
    
    safe_db_commit()
    print(f"✅ Seeded {created_count} credit cards (skipped {skipped_count} existing)")
    return created_count

def import_scraped_cards(file_path: str = None) -> int:
    """Import credit cards from scraped data files."""
    
    # Get the flask_app/data/output directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output_dir = os.path.join(base_dir, 'data', 'output')
    
    if not os.path.exists(output_dir):
        print(f"⚠️  Output directory not found: {output_dir}")
        return 0
    
    # Get all JSON files in output directory, sorted by filename (which includes timestamp)
    if file_path:
        json_files = [file_path] if os.path.exists(file_path) else []
    else:
        json_files = sorted(glob.glob(os.path.join(output_dir, '*.json')))
    
    if not json_files:
        print(f"⚠️  No JSON files found in {output_dir}")
        return 0
    
    total_imported = 0
    successful_files = 0
    failed_files = 0
    
    print(f"📋 Processing {len(json_files)} file(s)...")
    
    for json_file in json_files:
        print(f"\n📁 Processing file: {os.path.basename(json_file)}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Try different possible keys for cards data
            cards_data = data.get('cards', []) or data.get('valid_cards', [])
            if not cards_data:
                print(f"   ⚠️  No cards found in file (tried 'cards' and 'valid_cards' keys)")
                failed_files += 1
                continue
            
            print(f"   📊 Found {len(cards_data)} cards to import...")
            imported_count = import_cards_from_data(cards_data, os.path.basename(json_file))
            total_imported += imported_count
            successful_files += 1
            print(f"   ✅ Successfully imported {imported_count} cards from {os.path.basename(json_file)}")
            
        except Exception as e:
            print(f"   ❌ Error processing {os.path.basename(json_file)}: {e}")
            failed_files += 1
            continue
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"📈 IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"📁 Total files processed: {len(json_files)}")
    print(f"✅ Successful files: {successful_files}")
    print(f"❌ Failed files: {failed_files}")
    print(f"🏷️  Total cards imported: {total_imported}")
    
    return total_imported


def import_cards_from_data(cards_data: list, source_file: str) -> int:
    """Import cards from a list of card data."""
    created_count = 0
    updated_count = 0
    failed_count = 0
    
    for card_data in cards_data:
        try:
            # Get or create issuer
            issuer_name = card_data.get('issuer', 'Unknown')
            issuer = CardIssuer.query.filter_by(name=issuer_name).first()
            if not issuer:
                # Create new issuer if it doesn't exist
                issuer = CardIssuer(name=issuer_name)
                db.session.add(issuer)
                safe_db_flush()
            
            # Check if card already exists
            existing_card = CreditCard.query.filter_by(
                name=card_data.get('name'),
                issuer_id=issuer.id
            ).first()
            
            # Prepare card data for database
            db_card_data = {
                'name': card_data.get('name'),
                'issuer_id': issuer.id,
                'annual_fee': card_data.get('annual_fee', 0.0),
                'reward_type': card_data.get('reward_type', 'points'),
                'reward_value_multiplier': card_data.get('reward_value_multiplier', 0.01),
                'source': card_data.get('source', 'scraped'),
                'source_url': card_data.get('source_url', ''),
                'import_date': datetime.utcnow()
            }
            
            # Handle signup bonus - support both new JSON format and old separate fields format
            if 'signup_bonus' in card_data and card_data['signup_bonus']:
                # New JSON format
                if isinstance(card_data['signup_bonus'], dict):
                    db_card_data['signup_bonus'] = json.dumps(card_data['signup_bonus'])
                elif isinstance(card_data['signup_bonus'], str):
                    db_card_data['signup_bonus'] = card_data['signup_bonus']  # Already JSON string
            elif any(k in card_data for k in ['signup_bonus_points', 'signup_bonus_value']):
                # Old format - convert to new JSON structure
                signup_points = card_data.get('signup_bonus_points', 0)
                signup_value = card_data.get('signup_bonus_value', 0.0)
                signup_min_spend = card_data.get('signup_bonus_min_spend', 0.0)
                signup_max_months = card_data.get('signup_bonus_max_months', 3)
                
                if signup_points > 0 or signup_value > 0:
                    reward_type = db_card_data['reward_type']
                    reward_multiplier = db_card_data['reward_value_multiplier']
                    
                    bonus_data = {}
                    if reward_type == 'cash_back':
                        bonus_data['cash_back'] = float(signup_value or signup_points)
                        bonus_data['value'] = float(signup_value or signup_points)
                    elif reward_type == 'miles':
                        bonus_data['miles'] = int(signup_points or (signup_value / reward_multiplier))
                        bonus_data['value'] = float(signup_value or (signup_points * reward_multiplier))
                    else:  # points or default
                        bonus_data['points'] = int(signup_points or (signup_value / reward_multiplier))
                        bonus_data['value'] = float(signup_value or (signup_points * reward_multiplier))
                    
                    if signup_min_spend > 0:
                        bonus_data['min_spend'] = float(signup_min_spend)
                    if signup_max_months > 0:
                        bonus_data['max_months'] = int(signup_max_months)
                    
                    db_card_data['signup_bonus'] = json.dumps(bonus_data)
            
            if existing_card:
                # Update existing card
                for key, value in db_card_data.items():
                    if key != 'import_date':  # Don't update import_date for existing cards
                        setattr(existing_card, key, value)
                card = existing_card
                updated_count += 1
            else:
                # Create new card
                card = CreditCard(**db_card_data)
                db.session.add(card)
                created_count += 1
            
            safe_db_flush()  # Get the card ID
            
            # Clear existing reward relationships for this card
            CreditCardReward.query.filter_by(credit_card_id=card.id).delete()
            
            # Create CreditCardReward relationship records
            reward_categories = card_data.get('reward_categories', [])
            for reward_data in reward_categories:
                if isinstance(reward_data, dict):
                    category_name = reward_data.get('category')
                    rate = reward_data.get('rate', 1.0)
                    limit = reward_data.get('limit')
                    
                    # Skip invalid category names that are parsing artifacts
                    if should_skip_category(category_name):
                        continue
                        
                    # Map category name to database category using name, display_name, or aliases
                    category = Category.get_by_name_or_alias(category_name)
                    if not category:
                        # Try matching by display_name directly
                        category = Category.query.filter(Category.display_name.ilike(category_name)).first()
                    
                    if category:
                        credit_card_reward = CreditCardReward(
                            credit_card_id=card.id,
                            category_id=category.id,
                            reward_percent=float(rate),
                            is_bonus_category=(float(rate) > 1.0),
                            limit=float(limit) if limit not in (None, '', 'null') else None
                        )
                        db.session.add(credit_card_reward)
                    else:
                        print(f"     ⚠️  Category '{category_name}' not found for card '{card.name}' - ignoring")
            
            # Commit after each card to avoid session rollback issues
            safe_db_commit()
            
        except Exception as e:
            print(f"     ❌ Error importing card '{card_data.get('name', 'Unknown')}': {e}")
            # Rollback the session to clear any error state
            db.session.rollback()
            failed_count += 1
            continue
    
    # Show detailed results
    if created_count > 0 or updated_count > 0 or failed_count > 0:
        print(f"     📊 Results: {created_count} created, {updated_count} updated, {failed_count} failed")
    
    return created_count + updated_count


def seed_credit_cards_auto():
    """
    Automatically seed credit cards by importing the newest scraped data file
    from data/output if available, otherwise fall back to sample cards.
    This is the main function called by reset_db.py.
    """
    # Get the flask_app/data/output directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output_dir = os.path.join(base_dir, 'data', 'output')
    
    # Check if output directory exists and has JSON files
    if os.path.exists(output_dir):
        json_files = sorted(glob.glob(os.path.join(output_dir, '*.json')))
        if json_files:
            # Get the newest file (files are sorted by timestamp in filename)
            newest_file = json_files[-1]
            print(f"🔍 Found scraped data files in {output_dir}")
            print(f"📁 Using newest file: {os.path.basename(newest_file)}")
            
            try:
                # Import from the newest scraped file
                return import_scraped_cards(newest_file)
            except Exception as e:
                print(f"❌ Error importing from scraped file: {e}")
                print("🔄 Falling back to sample cards...")
                return seed_credit_cards()
        else:
            print(f"⚠️  No JSON files found in {output_dir}")
            print("🔄 Using sample cards instead...")
            return seed_credit_cards()
    else:
        print(f"⚠️  Output directory not found: {output_dir}")
        print("🔄 Using sample cards instead...")
        return seed_credit_cards()


def get_import_files():
    """Get list of available import files from data/import directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    import_dir = os.path.join(base_dir, 'data', 'import')
    
    # Also check 'imput' directory in case it exists
    imput_dir = os.path.join(base_dir, 'data', 'imput')
    
    json_files = []
    
    # Check import directory
    if os.path.exists(import_dir):
        json_files.extend(glob.glob(os.path.join(import_dir, '*.json')))
    
    # Check imput directory (typo but may exist)
    if os.path.exists(imput_dir):
        json_files.extend(glob.glob(os.path.join(imput_dir, '*.json')))
    
    return sorted(json_files)


def display_file_menu():
    """Display available import files and get user selection."""
    json_files = get_import_files()
    
    if not json_files:
        print("❌ No JSON files found in data/import or data/imput directories")
        return None
    
    print("\n📁 Available import files:")
    print("=" * 50)
    
    for i, file_path in enumerate(json_files, 1):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        print(f"{i:2d}. {filename} ({file_size:,} bytes)")
    
    print(f"{len(json_files) + 1:2d}. all (import all files)")
    print("=" * 50)
    
    while True:
        try:
            choice = input("\nEnter your choice (number or press Enter to exit): ").strip()
            
            if not choice:
                return None
            
            choice_num = int(choice)
            
            if choice_num == len(json_files) + 1:
                return 'all'
            elif 1 <= choice_num <= len(json_files):
                return json_files[choice_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(json_files) + 1}")
                
        except ValueError:
            print("❌ Please enter a valid number")


def import_from_import_directory(file_selection):
    """Import cards from files in the import directory."""
    if file_selection == 'all':
        json_files = get_import_files()
        print(f"\n🚀 Importing from all {len(json_files)} files...")
    else:
        json_files = [file_selection]
        print(f"\n🚀 Importing from: {os.path.basename(file_selection)}")
    
    total_imported = 0
    successful_files = 0
    failed_files = 0
    
    for json_file in json_files:
        print(f"\n📁 Processing file: {os.path.basename(json_file)}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Try different possible keys for cards data
            cards_data = data.get('cards', []) or data.get('valid_cards', []) or data
            
            # If data is a list directly, use it
            if isinstance(data, list):
                cards_data = data
            elif not cards_data:
                print(f"   ⚠️  No cards found in file (tried 'cards', 'valid_cards' keys, and root level)")
                failed_files += 1
                continue
            
            print(f"   📊 Found {len(cards_data)} cards to import...")
            imported_count = import_cards_from_data(cards_data, os.path.basename(json_file))
            total_imported += imported_count
            successful_files += 1
            print(f"   ✅ Successfully imported {imported_count} cards from {os.path.basename(json_file)}")
            
        except Exception as e:
            print(f"   ❌ Error processing {os.path.basename(json_file)}: {e}")
            failed_files += 1
            continue
    
    # Final summary
    print(f"\n{'='*60}")
    print(f"📈 IMPORT COMPLETE")
    print(f"{'='*60}")
    print(f"📁 Total files processed: {len(json_files)}")
    print(f"✅ Successful files: {successful_files}")
    print(f"❌ Failed files: {failed_files}")
    print(f"🏷️  Total cards imported: {total_imported}")
    
    return total_imported


def main():
    """Main function to seed credit cards."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed credit cards database')
    parser.add_argument('--import-scraped', action='store_true', 
                       help='Import cards from scraped data files in /data/output')
    parser.add_argument('--file', type=str, 
                       help='Import from specific file path')
    parser.add_argument('--sample-only', action='store_true',
                       help='Only seed sample cards (default behavior)')
    parser.add_argument('--force', action='store_true',
                       help='Skip Flask server check and force execution')
    parser.add_argument('--interactive', action='store_true',
                       help='Show interactive file selection menu')
    
    args = parser.parse_args()
    
    print("🚀 Starting credit card import process...")
    
    try:
        app = create_app('development')
        with app.app_context():
            if args.interactive:
                # Show interactive menu
                file_selection = display_file_menu()
                if file_selection is None:
                    print("👋 Exiting without importing")
                    return 0
                return import_from_import_directory(file_selection)
            elif args.import_scraped or args.file:
                return import_scraped_cards(args.file)
            else:
                # Default behavior: show interactive menu instead of just sample cards
                file_selection = display_file_menu()
                if file_selection is None:
                    print("👋 Exiting without importing")
                    return 0
                return import_from_import_directory(file_selection)
    except Exception as e:
        error_msg = str(e).lower()
        if 'database is locked' in error_msg:
            print(f"\n❌ Database is locked!")
            print("💡 This usually happens when the Flask development server is running.")
            print("   Try stopping the server and running this script again.")
            print("   Or use --force flag to skip the server check.")
        else:
            print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 