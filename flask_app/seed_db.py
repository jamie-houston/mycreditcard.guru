#!/usr/bin/env python
"""
Comprehensive database seeding script.
This script will:
1. Create all database tables
2. Seed categories
3. Seed issuers
4. Seed sample credit cards
"""

import sys
import os

# Add current directory to path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db

# Import individual seed functions
from scripts.data.seed_categories import seed_categories
from scripts.data.seed_issuers import seed_issuers
from scripts.data.seed_credit_cards import seed_credit_cards

def main():
    """Main seeding function."""
    print("🚀 Starting comprehensive database seeding...")
    
    app = create_app()
    with app.app_context():
        print("\n1️⃣ Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        
        print("\n2️⃣ Seeding categories...")
        seed_categories()
        
        print("\n3️⃣ Seeding issuers...")
        seed_issuers()
        
        print("\n4️⃣ Seeding credit cards...")
        seed_credit_cards()
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nYou can now run the Flask app with:")
        print("  python run.py")

if __name__ == "__main__":
    main() 