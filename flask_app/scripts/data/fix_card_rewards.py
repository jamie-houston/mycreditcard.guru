#!/usr/bin/env python
"""
Credit Card Rewards Fixer

This script fixes existing credit cards that have reward_categories JSON data
but are missing the corresponding CreditCardReward relationship records.
This ensures that reward categories display properly in the UI.
"""

from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category, CreditCardReward
import json

def fix_card_rewards():
    """Fix existing cards that have JSON reward data but missing relationship records."""
    app = create_app()
    with app.app_context():
        # Get all credit cards
        cards = CreditCard.query.all()
        
        fixed_count = 0
        skipped_count = 0
        
        for card in cards:
            print(f"\nProcessing card: {card.name}")
            
            # Check if card has reward_categories JSON data
            if not card.reward_categories:
                print(f"  - Skipping: No reward categories JSON data")
                skipped_count += 1
                continue
            
            try:
                reward_categories = json.loads(card.reward_categories)
            except (json.JSONDecodeError, TypeError):
                print(f"  - Skipping: Invalid JSON in reward_categories")
                skipped_count += 1
                continue
            
            if not reward_categories:
                print(f"  - Skipping: Empty reward categories")
                skipped_count += 1
                continue
            
            # Check if card already has CreditCardReward records
            existing_rewards = CreditCardReward.query.filter_by(credit_card_id=card.id).count()
            if existing_rewards > 0:
                print(f"  - Skipping: Already has {existing_rewards} reward records")
                skipped_count += 1
                continue
            
            # Create CreditCardReward records from JSON data
            created_rewards = 0
            for reward_data in reward_categories:
                # Handle both 'rate' and 'percentage' keys for backward compatibility
                category_name = reward_data.get('category')
                rate = reward_data.get('rate') or reward_data.get('percentage', 1.0)
                
                if category_name:
                    # Find the category by name
                    category = Category.get_by_name(category_name)
                    if category:
                        # Create the reward relationship
                        credit_card_reward = CreditCardReward(
                            credit_card_id=card.id,
                            category_id=category.id,
                            reward_percent=float(rate),
                            is_bonus_category=(float(rate) > 1.0)
                        )
                        db.session.add(credit_card_reward)
                        created_rewards += 1
                        print(f"  - Created reward: {category.display_name} -> {rate}%")
                    else:
                        print(f"  - Warning: Category '{category_name}' not found")
            
            if created_rewards > 0:
                fixed_count += 1
                print(f"  - Fixed: Created {created_rewards} reward records")
            else:
                print(f"  - No valid categories found to create")
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Fix completed!")
            print(f"   - Fixed {fixed_count} cards")
            print(f"   - Skipped {skipped_count} cards")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error committing changes: {e}")

if __name__ == "__main__":
    fix_card_rewards() 