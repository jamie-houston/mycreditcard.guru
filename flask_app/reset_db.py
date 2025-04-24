#!/usr/bin/env python
"""
Reset and initialize the database with the current models.
This bypasses migrations and directly creates tables from the models.
"""

import sys
from app import create_app, db
from app.models.credit_card import CreditCard

def main():
    """Reset and initialize the database."""
    print("Initializing database...")
    
    # Create app context
    app = create_app('development')
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("Dropped all existing tables.")
        
        # Create all tables based on current models
        db.create_all()
        print("Created all tables from models.")
        
        print("Database initialization complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 