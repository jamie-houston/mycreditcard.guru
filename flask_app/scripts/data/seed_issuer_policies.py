#!/usr/bin/env python3
"""
Seed database with common issuer policies.
"""
import os
import sys
from pathlib import Path

# Add the Flask app to the Python path
current_dir = Path(__file__).parent
flask_app_dir = current_dir.parent.parent
sys.path.insert(0, str(flask_app_dir))

from app import create_app, db
from app.models.credit_card import CardIssuer
from app.models.issuer_policy import IssuerPolicy

def seed_issuer_policies():
    """Seed the database with common issuer policies."""
    app = create_app('development')
    
    with app.app_context():
        print("🏦 Seeding issuer policies...")
        
        # Get or create issuers
        chase = CardIssuer.query.filter_by(name='Chase').first()
        if not chase:
            chase = CardIssuer(name='Chase')
            db.session.add(chase)
            db.session.commit()
        
        amex = CardIssuer.query.filter_by(name='American Express').first()
        if not amex:
            amex = CardIssuer(name='American Express')
            db.session.add(amex)
            db.session.commit()
        
        citi = CardIssuer.query.filter_by(name='Citi').first()
        if not citi:
            citi = CardIssuer(name='Citi')
            db.session.add(citi)
            db.session.commit()
        
        capital_one = CardIssuer.query.filter_by(name='Capital One').first()
        if not capital_one:
            capital_one = CardIssuer(name='Capital One')
            db.session.add(capital_one)
            db.session.commit()
        
        # Chase 5/24 Policy
        chase_524 = IssuerPolicy.query.filter_by(
            issuer_id=chase.id, 
            policy_name="5/24 Rule"
        ).first()
        
        if not chase_524:
            chase_524 = IssuerPolicy.create_chase_524_policy(chase.id)
            db.session.add(chase_524)
            print(f"✅ Added Chase 5/24 policy")
        else:
            print(f"ℹ️  Chase 5/24 policy already exists")
        
        # American Express 2/90 Policy
        amex_290 = IssuerPolicy.query.filter_by(
            issuer_id=amex.id,
            policy_name="2/90 Rule"
        ).first()
        
        if not amex_290:
            amex_290 = IssuerPolicy.create_amex_290_policy(amex.id)
            db.session.add(amex_290)
            print(f"✅ Added American Express 2/90 policy")
        else:
            print(f"ℹ️  American Express 2/90 policy already exists")
        
        # Citi 8/65 Policy (8 cards in 65 days)
        citi_865 = IssuerPolicy.query.filter_by(
            issuer_id=citi.id,
            policy_name="8/65 Rule"
        ).first()
        
        if not citi_865:
            citi_865 = IssuerPolicy(
                issuer_id=citi.id,
                policy_name="8/65 Rule",
                policy_type="application_limit",
                description="Citi typically denies applications if you have opened 8 or more credit cards from any issuer in the past 65 days"
            )
            citi_865.config = {
                'max_cards': 8,
                'days_lookback': 65,
                'scope': 'all_issuers'
            }
            db.session.add(citi_865)
            print(f"✅ Added Citi 8/65 policy")
        else:
            print(f"ℹ️  Citi 8/65 policy already exists")
        
        # Citi 24-month rule for same product
        citi_24mo = IssuerPolicy.query.filter_by(
            issuer_id=citi.id,
            policy_name="24-Month Rule"
        ).first()
        
        if not citi_24mo:
            citi_24mo = IssuerPolicy(
                issuer_id=citi.id,
                policy_name="24-Month Rule",
                policy_type="minimum_wait",
                description="Cannot get signup bonus if you have opened or closed the same Citi card within 24 months"
            )
            citi_24mo.config = {
                'wait_days': 730,  # 24 months
                'scope': 'same_product'
            }
            db.session.add(citi_24mo)
            print(f"✅ Added Citi 24-month rule")
        else:
            print(f"ℹ️  Citi 24-month rule already exists")
        
        # Capital One 2/30 Policy
        cap1_230 = IssuerPolicy.query.filter_by(
            issuer_id=capital_one.id,
            policy_name="2/30 Rule"
        ).first()
        
        if not cap1_230:
            cap1_230 = IssuerPolicy(
                issuer_id=capital_one.id,
                policy_name="2/30 Rule",
                policy_type="minimum_wait",
                description="Capital One typically limits approvals to 2 credit cards every 30 days"
            )
            cap1_230.config = {
                'wait_days': 30,
                'scope': 'this_issuer',
                'max_in_period': 2
            }
            db.session.add(cap1_230)
            print(f"✅ Added Capital One 2/30 policy")
        else:
            print(f"ℹ️  Capital One 2/30 policy already exists")
        
        try:
            db.session.commit()
            print("✅ Issuer policies seeded successfully!")
            
            # Print summary
            total_policies = IssuerPolicy.query.count()
            print(f"📊 Total issuer policies in database: {total_policies}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error seeding issuer policies: {str(e)}")
            return False
    
    return True

if __name__ == "__main__":
    seed_issuer_policies()