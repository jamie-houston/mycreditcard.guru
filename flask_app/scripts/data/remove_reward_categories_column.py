"""Remove deprecated reward_categories column from credit_cards table.

This script removes the deprecated reward_categories JSON column since we now
use the CreditCardReward relationship model instead.
"""

import sqlite3
import sys
import os

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app

def remove_reward_categories_column():
    """Remove the deprecated reward_categories column from credit_cards table."""
    print("Removing deprecated reward_categories column from credit_cards table...")
    
    app = create_app()
    with app.app_context():
        # Connect to SQLite database
        db_path = os.path.join(app.instance_path, 'creditcard_roadmap.db')
        if not os.path.exists(db_path):
            db_path = 'app.db'  # Fallback to app.db
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Check if column exists
            cursor.execute("PRAGMA table_info(credit_cards)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'reward_categories' not in columns:
                print("reward_categories column does not exist in credit_cards table")
                return
            
            print("Found reward_categories column, removing it...")
            
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
            # First, get the current table schema
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='credit_cards'")
            old_schema = cursor.fetchone()[0]
            
            # Create new table without reward_categories column
            new_schema = old_schema.replace(', reward_categories TEXT NOT NULL', '')
            new_schema = new_schema.replace('reward_categories TEXT NOT NULL,', '')
            new_schema = new_schema.replace('reward_categories TEXT NOT NULL', '')
            
            # Create new table
            new_table_name = 'credit_cards_new'
            new_schema = new_schema.replace('CREATE TABLE credit_cards', f'CREATE TABLE {new_table_name}')
            cursor.execute(new_schema)
            
            # Copy data from old table to new table (excluding reward_categories)
            cursor.execute("PRAGMA table_info(credit_cards)")
            all_columns = [column[1] for column in cursor.fetchall()]
            columns_to_copy = [col for col in all_columns if col != 'reward_categories']
            
            columns_str = ', '.join(columns_to_copy)
            cursor.execute(f"""
                INSERT INTO {new_table_name} ({columns_str})
                SELECT {columns_str} FROM credit_cards
            """)
            
            # Drop old table and rename new table
            cursor.execute("DROP TABLE credit_cards")
            cursor.execute(f"ALTER TABLE {new_table_name} RENAME TO credit_cards")
            
            # Commit changes
            conn.commit()
            print("✅ Successfully removed reward_categories column from credit_cards table")
            
        except Exception as e:
            print(f"❌ Error removing reward_categories column: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    remove_reward_categories_column()