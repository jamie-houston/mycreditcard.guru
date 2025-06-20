#!/usr/bin/env python3
"""
Migration script to convert signup bonus fields to JSON structure.

This script migrates from:
- signup_bonus_points (Integer)
- signup_bonus_value (Float) 
- signup_bonus_min_spend (Float)
- signup_bonus_max_months (Integer)

To:
- signup_bonus (JSON Text) containing:
  {
    "points": 80000,           // or "miles", "cash_back", etc. based on reward_type
    "min_spend": 4000,
    "max_months": 3,
    "value": 800               // calculated: amount * reward_value_multiplier
  }
"""

import sys
import os
import json
from datetime import datetime

# Add the flask_app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.models.credit_card import CreditCard


def migrate_signup_bonus_to_json():
    """Migrate existing signup bonus fields to new JSON structure."""
    
    app = create_app()
    with app.app_context():
        print("Starting signup bonus migration...")
        
        # First, add the new column if it doesn't exist
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text("ALTER TABLE credit_cards ADD COLUMN signup_bonus TEXT"))
                conn.commit()
            print("Added signup_bonus column")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("signup_bonus column already exists")
            else:
                print(f"Error adding column: {e}")
                return False
        
        # Get all cards
        cards = CreditCard.query.all()
        
        updated_count = 0
        for card in cards:
            # Skip if already has signup_bonus JSON
            try:
                signup_bonus_attr = getattr(card, 'signup_bonus', None)
                if signup_bonus_attr:
                    existing = json.loads(signup_bonus_attr)
                    if existing:  # Already migrated
                        continue
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
            
            # Create new signup bonus structure
            signup_bonus_data = {}
            
            # Determine the reward type field name
            reward_type = getattr(card, 'reward_type', 'points')
            if reward_type == 'cash_back':
                amount_field = 'cash_back'
                amount = getattr(card, 'signup_bonus_value', 0)
            elif reward_type == 'miles':
                amount_field = 'miles'
                amount = getattr(card, 'signup_bonus_points', 0)
            elif reward_type == 'hotel':
                amount_field = 'points'  # Hotel points
                amount = getattr(card, 'signup_bonus_points', 0)
            else:  # 'points' or default
                amount_field = 'points'
                amount = getattr(card, 'signup_bonus_points', 0)
            
            # Only create signup bonus if there's actually a bonus
            if amount > 0:
                signup_bonus_data[amount_field] = int(amount) if amount_field != 'cash_back' else float(amount)
                signup_bonus_data['min_spend'] = float(getattr(card, 'signup_bonus_min_spend', 0))
                signup_bonus_data['max_months'] = int(getattr(card, 'signup_bonus_max_months', 3))
                
                # Calculate value
                if reward_type == 'cash_back':
                    signup_bonus_data['value'] = float(amount)
                else:
                    multiplier = getattr(card, 'reward_value_multiplier', 0.01)
                    signup_bonus_data['value'] = float(amount * multiplier)
            
            # Set the new JSON field using direct SQL update
            if signup_bonus_data:
                json_data = json.dumps(signup_bonus_data)
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text("UPDATE credit_cards SET signup_bonus = :json_data WHERE id = :card_id"),
                        {"json_data": json_data, "card_id": card.id}
                    )
                    conn.commit()
            else:
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text("UPDATE credit_cards SET signup_bonus = NULL WHERE id = :card_id"),
                        {"card_id": card.id}
                    )
                    conn.commit()
            
            updated_count += 1
            
            if updated_count % 10 == 0:
                print(f"Processed {updated_count} cards...")
        
        print(f"Migration completed successfully! Updated {updated_count} cards.")
        return True


def remove_old_columns():
    """Remove the old signup bonus columns after migration."""
    
    app = create_app()
    with app.app_context():
        print("Removing old signup bonus columns...")
        
        try:
            # Note: SQLite doesn't support DROP COLUMN, so we'd need to recreate the table
            # For now, we'll just print what we would do
            print("Would remove columns:")
            print("- signup_bonus_points")
            print("- signup_bonus_value") 
            print("- signup_bonus_min_spend")
            print("- signup_bonus_max_months")
            print("(Skipping actual removal for SQLite compatibility)")
            return True
        except Exception as e:
            print(f"Error removing columns: {e}")
            return False


if __name__ == '__main__':
    print("Signup Bonus Migration Script")
    print("=" * 40)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--remove-old':
        success = remove_old_columns()
    else:
        success = migrate_signup_bonus_to_json()
        
        if success:
            print("\nMigration completed successfully!")
            print("You can now update the model to use the new signup_bonus JSON field.")
            print("\nTo remove old columns (optional), run:")
            print("python migrate_signup_bonus_structure.py --remove-old")
        else:
            print("\nMigration failed!")
            sys.exit(1)