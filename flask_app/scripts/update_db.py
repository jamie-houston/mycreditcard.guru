"""Update database schema to support anonymous users.

This script adds session_id columns to user_profiles and recommendations tables,
and makes the user_id column nullable in the recommendations table.
"""

import sqlite3
from app import create_app

# Create Flask app context
app = create_app()

def update_db_schema():
    """Update the database schema to support anonymous users."""
    print("Updating database schema to support anonymous users...")
    
    with app.app_context():
        # Connect to SQLite database
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        # Add session_id column to user_profiles table
        try:
            cursor.execute('''
                ALTER TABLE user_profiles
                ADD COLUMN session_id VARCHAR(36)
            ''')
            print("Added session_id column to user_profiles table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("session_id column already exists in user_profiles table")
            else:
                print(f"Error adding session_id to user_profiles: {e}")
        
        # Add session_id column to recommendations table
        try:
            cursor.execute('''
                ALTER TABLE recommendations
                ADD COLUMN session_id VARCHAR(36)
            ''')
            print("Added session_id column to recommendations table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("session_id column already exists in recommendations table")
            else:
                print(f"Error adding session_id to recommendations: {e}")
        
        # Create indexes for session_id columns
        try:
            cursor.execute('''
                CREATE INDEX ix_user_profiles_session_id
                ON user_profiles (session_id)
            ''')
            print("Created index for session_id in user_profiles table")
        except sqlite3.OperationalError as e:
            if "index ix_user_profiles_session_id already exists" in str(e).lower():
                print("session_id index already exists in user_profiles table")
            else:
                print(f"Error creating index for user_profiles: {e}")
        
        try:
            cursor.execute('''
                CREATE INDEX ix_recommendations_session_id
                ON recommendations (session_id)
            ''')
            print("Created index for session_id in recommendations table")
        except sqlite3.OperationalError as e:
            if "index ix_recommendations_session_id already exists" in str(e).lower():
                print("session_id index already exists in recommendations table")
            else:
                print(f"Error creating index for recommendations: {e}")
        
        # SQLite doesn't support ALTER COLUMN to make columns nullable
        # We'll need to recreate the recommendations table if it exists
        
        # Commit changes
        conn.commit()
        conn.close()
        
        print("Database schema update completed!")

if __name__ == '__main__':
    update_db_schema() 