#!/usr/bin/env python
"""
Reset and initialize the database with the current models.
This bypasses migrations and directly creates tables from the models.
"""

import sys
import os
import subprocess
from app import create_app, db
from app.models.credit_card import CreditCard
from app.models.category import Category
from app.models import CardIssuer

def create_issuers():
    issuers = set([
        'Chase', 'Capital One', 'American Express', 'Citi', 'Discover', 'Bank of America', 'Wells Fargo', 'U.S. Bank'
    ])
    for name in issuers:
        if not CardIssuer.query.filter_by(name=name).first():
            db.session.add(CardIssuer(name=name))
    db.session.commit()

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

        # Seed categories using the existing script
        print("Seeding categories using seed_categories.py...")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'seed_categories.py')], check=True)
        
        create_issuers()
        
        print("Database initialization complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 