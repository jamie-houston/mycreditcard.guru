#!/usr/bin/env python
"""
Reset and initialize the database with the current models.
This bypasses migrations and directly creates tables from the models.
Calls all individual seed scripts to populate with sample data.
"""

import sys
import os

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db

# Import seed functions
from seed_categories import seed_categories
from seed_issuers import seed_issuers
from seed_credit_cards import seed_credit_cards_auto
# from seed_profiles import seed_profiles  # Skip for now due to model issues

def main():
    """Reset and initialize the database with sample data."""
    print("🔄 Resetting and initializing database...")
    
    # Create app context
    app = create_app('development')
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("🗑️  Dropped all existing tables.")
        
        # Create all tables based on current models
        db.create_all()
        print("🏗️  Created all tables from models.")

        # Seed data in proper order (dependencies matter!)
        print("\n📊 Seeding sample data...")
        
        # 1. Categories first (needed by credit cards)
        print("1️⃣  Seeding categories...")
        seed_categories()
        
        # 2. Issuers (needed by credit cards)
        print("2️⃣  Seeding card issuers...")
        seed_issuers()
        
        # 3. Credit cards (depends on categories and issuers)
        print("3️⃣  Seeding credit cards...")
        seed_credit_cards_auto()
        
        # 4. User profiles (optional sample data) - Skip for now due to model issues
        # print("4️⃣  Seeding sample user profiles...")
        # seed_profiles()
        
        print("\n🎉 Database reset and seeding complete!")
        print("💡 You now have a fresh database with sample data for development.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 