import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
from flask import url_for

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.credit_card import CreditCard
from app.utils.data_utils import map_scraped_card_to_model

class TestCardImport(unittest.TestCase):
    """Test class for the card import functionality."""
    
    def setUp(self):
        """Set up test client and database."""
        self.app = create_app('testing')
        # Disable CSRF protection for testing
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Reset the database before each test
        db.drop_all()
        db.create_all()
        
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('app.utils.card_scraper.scrape_credit_cards')
    def test_import_cards(self, mock_scrape):
        """Test the import endpoint with mocked scraper."""
        # Set up mock data with scraper field names
        mock_cards = [
            {
                "name": "Test Travel Card",
                "issuer": "Test Bank",
                "annual_fee": 95.0,
                "signup_bonus_points": 60000,
                "signup_bonus_value": 750.0,
                "signup_bonus_spend_requirement": 4000.0,
                "signup_bonus_time_period": 3,
                "offers": json.dumps([
                    {"type": "travel_credit", "amount": 100, "frequency": "annual"}
                ]),
                "reward_categories": json.dumps([
                    {"category": "travel", "percentage": 3},
                    {"category": "dining", "percentage": 2}
                ]),
                "is_active": True
            },
        ]
        mock_scrape.return_value = mock_cards

        # Test the import endpoint
        response = self.client.post('/cards/import', data={'source': 'nerdwallet'})
        
        # Verify the response
        self.assertEqual(response.status_code, 302)  # Expect redirect
        
        # Verify that the card was created with the correct field names
        cards = CreditCard.query.all()
        self.assertEqual(len(cards), 1)
        card = cards[0]
        
        # Verify field mappings worked correctly
        self.assertEqual(card.name, "Test Travel Card")
        self.assertEqual(card.signup_bonus_min_spend, 4000.0)
        self.assertEqual(card.signup_bonus_time_limit, 3)
        
        # Verify special_offers was properly mapped and stored
        offers = json.loads(card.special_offers)
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["type"], "travel_credit")

    def test_import_card_with_field_mapping(self):
        """Test that cards can be imported with field mapping handling name differences."""
        # Mock card data from scraper (using scraper field names)
        scraped_card_data = {
            'name': 'Test Travel Card',
            'issuer': 'Test Bank',
            'annual_fee': 99.0,
            'signup_bonus_points': 60000,
            'signup_bonus_value': 600.0,
            # Field names that differ from model
            'signup_bonus_spend_requirement': 4000.0,
            'signup_bonus_time_period': 3,
            'offers': json.dumps([{'type': 'travel_credit', 'amount': 100}]),
            'reward_categories': json.dumps([
                {'category': 'travel', 'percentage': 3},
                {'category': 'dining', 'percentage': 2},
            ]),
            'is_active': True
        }
        
        # Map the fields using our utility function
        mapped_data = map_scraped_card_to_model(scraped_card_data)
        
        # Create a new CreditCard instance using the mapped data
        card = CreditCard(**mapped_data)
        
        # Verify the card has the correct field values
        self.assertEqual(card.name, 'Test Travel Card')
        self.assertEqual(card.issuer, 'Test Bank')
        self.assertEqual(card.annual_fee, 99.0)
        self.assertEqual(card.signup_bonus_points, 60000)
        self.assertEqual(card.signup_bonus_value, 600.0)
        self.assertEqual(card.signup_bonus_min_spend, 4000.0)
        self.assertEqual(card.signup_bonus_time_limit, 3)
        
        # Check that the offers field was properly mapped to special_offers
        self.assertEqual(card.special_offers, json.dumps([{'type': 'travel_credit', 'amount': 100}]))
        
        self.assertEqual(card.reward_categories, json.dumps([
            {'category': 'travel', 'percentage': 3},
            {'category': 'dining', 'percentage': 2},
        ]))
        
    def test_attribute_error_without_mapping(self):
        """Test that trying to access incorrect field names raises AttributeError."""
        # Create a card with the mapped field names
        card = CreditCard(
            name='Test Card',
            issuer='Test Bank',
            annual_fee=99.0,
            signup_bonus_min_spend=4000.0,
            signup_bonus_time_limit=3
        )
        
        # These should raise AttributeError as these field names don't exist in the model
        with self.assertRaises(AttributeError):
            _ = card.signup_bonus_spend_requirement
            
        with self.assertRaises(AttributeError):
            _ = card.signup_bonus_time_period
            
    def test_field_mapper(self):
        """Test that the field mapper correctly maps field names."""
        scraped_data = {
            'name': 'Test Card',
            'issuer': 'Test Bank',
            'signup_bonus_spend_requirement': 3000,
            'signup_bonus_time_period': 90,
            'signup_bonus_points': 50000,
            'signup_bonus_value': 500,
            'annual_fee': 95,
            'point_value': 0.01,
            'reward_categories': json.dumps([]),
            'offers': json.dumps([])
        }
        
        # Map the scraped data
        mapped_data = map_scraped_card_to_model(scraped_data)
        
        # Check that fields are correctly mapped
        self.assertEqual(mapped_data['signup_bonus_min_spend'], 3000)
        self.assertEqual(mapped_data['signup_bonus_time_limit'], 90)
        
        # Check that special_offers is correctly mapped from offers
        self.assertEqual(mapped_data['special_offers'], json.dumps([]))
        
        # Check that unmapped fields are preserved
        self.assertEqual(mapped_data['name'], 'Test Card')
        self.assertEqual(mapped_data['issuer'], 'Test Bank')
        self.assertEqual(mapped_data['reward_categories'], json.dumps([]))

    def test_field_mapping(self):
        """Test that scraped field names are properly mapped to model field names"""
        # Sample scraped data with scraper field names
        scraped_data = {
            'name': 'Test Card',
            'issuer': 'Test Bank',
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
        mapped_data = map_scraped_card_to_model(scraped_data)
        
        # Check that the fields were correctly mapped
        self.assertEqual(mapped_data.get('name'), 'Test Card')
        self.assertEqual(mapped_data.get('issuer'), 'Test Bank')
        self.assertEqual(mapped_data.get('annual_fee'), 95.0)
        
        # Check that the problematic fields were correctly mapped
        self.assertEqual(mapped_data.get('signup_bonus_min_spend'), 3000.0)
        self.assertEqual(mapped_data.get('signup_bonus_time_limit'), 3)
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

if __name__ == '__main__':
    unittest.main() 