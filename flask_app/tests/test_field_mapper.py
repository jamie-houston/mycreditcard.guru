import unittest
import os
import sys
import json

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.data_utils import map_scraped_card_to_model
from app.models import CardIssuer

class TestFieldMapper(unittest.TestCase):
    """Test the field mapping functionality"""
    
    def test_field_mapping(self):
        """Test that scraped field names are properly mapped to model field names"""
        from app import create_app, db
        app = create_app('testing')
        ctx = app.app_context()
        ctx.push()
        test_issuer = CardIssuer(name='Test Bank')
        db.session.add(test_issuer)
        db.session.commit()
        scraped_data = {
            'name': 'Test Card',
            'issuer_id': test_issuer.id,
            'annual_fee': 95.0,
            'signup_bonus_points': 50000,
            'signup_bonus_value': 500.0,
            'signup_bonus_spend_requirement': 3000.0,  # Field to be mapped
            'signup_bonus_time_period': 3,  # Field to be mapped
            'reward_categories': [
                {'category': 'dining', 'percentage': 3},
                {'category': 'travel', 'percentage': 2}
            ],
            'offers': [  # Field to be mapped
                {'type': 'travel_credit', 'amount': 100, 'frequency': 'annual'}
            ]
        }
        
        # Map the scraped data fields to model fields
        mapped_data = map_scraped_card_to_model(scraped_data, skip_category_lookup=True)
        
        # Check that the fields were correctly mapped
        self.assertEqual(mapped_data.get('name'), 'Test Card')
        self.assertEqual(mapped_data.get('issuer_id'), test_issuer.id)
        self.assertEqual(mapped_data.get('annual_fee'), 95.0)
        
        # Check that the problematic fields were correctly mapped
        self.assertEqual(mapped_data.get('signup_bonus_min_spend'), 3000.0)
        self.assertEqual(mapped_data.get('signup_bonus_max_months'), 3)
        self.assertEqual(mapped_data.get('special_offers'), json.dumps([{'type': 'travel_credit', 'amount': 100, 'frequency': 'annual'}]))
        
        # Check that reward_categories is converted to JSON string
        self.assertEqual(
            mapped_data.get('reward_categories'), 
            json.dumps([{'category': 'dining', 'percentage': 3}, {'category': 'travel', 'percentage': 2}])
        )
        
        # Test the fields that should not exist in the mapped data
        self.assertNotIn('signup_bonus_spend_requirement', mapped_data)
        self.assertNotIn('signup_bonus_time_period', mapped_data)
        self.assertNotIn('offers', mapped_data)
        ctx.pop()

if __name__ == '__main__':
    unittest.main() 