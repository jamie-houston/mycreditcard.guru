#!/usr/bin/env python
"""
Seed Card Issuers

This script seeds the database with sample card issuers.
"""

import sys
import os

# Add flask_app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models import CardIssuer

def seed_issuers():
    """Seed the database with card issuers."""
    issuers_data = [
        'Chase',
        'Capital One', 
        'American Express',
        'Citi',
        'Discover',
        'Bank of America',
        'Wells Fargo',
        'U.S. Bank',
        'Barclays',
        'HSBC',
        'PNC Bank',
        'TD Bank',
        'USAA',
        'Navy Federal Credit Union',
        'Alliant Credit Union'
    ]
    
    created_count = 0
    for name in issuers_data:
        if not CardIssuer.query.filter_by(name=name).first():
            issuer = CardIssuer(name=name)
            db.session.add(issuer)
            created_count += 1
    
    db.session.commit()
    print(f"✅ Seeded {created_count} card issuers (skipped {len(issuers_data) - created_count} existing)")
    return created_count

def main():
    """Main function to seed issuers."""
    app = create_app('development')
    with app.app_context():
        return seed_issuers()

if __name__ == "__main__":
    sys.exit(main()) 