import unittest
import sys
import os

# Add the correct path to the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, parent_dir)

try:
    from creditcard_roadmap.app.utils.field_mapper import map_scraped_card_to_model
except ImportError:
    # Try alternative import if the first one fails
    from app.utils.field_mapper import map_scraped_card_to_model

class TestFieldMapper(unittest.TestCase):
    def test_map_scraped_card_to_model(self):
        # Test data with scraper field names
        scraped_data = {
            'name': 'Test Card',
            'issuer': 'Test Bank',
            'annual_fee': 99.0,
            'signup_bonus_points': 50000,
            'signup_bonus_value': 500.0,
            'signup_bonus_spend_requirement': 3000.0,
            'signup_bonus_time_period': 3,
            'offers': [{'type': 'travel_credit', 'amount': 100}],
            'reward_categories': [{'category': 'travel', 'percentage': 3}]
        }
        
        # Map the field names
        mapped_data = map_scraped_card_to_model(scraped_data)
        
        # Check that fields were correctly mapped
        self.assertEqual(mapped_data['name'], 'Test Card')
        self.assertEqual(mapped_data['issuer'], 'Test Bank')
        self.assertEqual(mapped_data['annual_fee'], 99.0)
        self.assertEqual(mapped_data['signup_bonus_points'], 50000)
        self.assertEqual(mapped_data['signup_bonus_value'], 500.0)
        
        # Check that renamed fields were mapped correctly
        self.assertEqual(mapped_data['signup_bonus_min_spend'], 3000.0)
        self.assertEqual(mapped_data['signup_bonus_time_limit'], 3)
        self.assertEqual(mapped_data['special_offers'], [{'type': 'travel_credit', 'amount': 100}])
        
        # Original fields should be removed
        self.assertNotIn('signup_bonus_spend_requirement', mapped_data)
        self.assertNotIn('signup_bonus_time_period', mapped_data)
        self.assertNotIn('offers', mapped_data)
        
        # Reward categories should remain unchanged
        self.assertEqual(mapped_data['reward_categories'], [{'category': 'travel', 'percentage': 3}])

if __name__ == '__main__':
    unittest.main() 