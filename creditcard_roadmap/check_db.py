#!/usr/bin/env python
"""
Script to check the database contents.
"""

from app import create_app, db
from app.models.credit_card import CreditCard

def main():
    """Check database contents."""
    app = create_app('default')
    with app.app_context():
        cards = CreditCard.query.all()
        print(f'Total cards in database: {len(cards)}')
        print("\nSample of credit cards:")
        for card in cards[:5]:
            print(f'- {card.name} (Source: {card.source})')
        
        # Count by source
        print("\nCards by source:")
        sources = {}
        for card in cards:
            source = card.source
            if source not in sources:
                sources[source] = 0
            sources[source] += 1
        
        for source, count in sources.items():
            print(f'- {source}: {count} cards')

if __name__ == '__main__':
    main() 