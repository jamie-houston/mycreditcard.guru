import unittest
import json
from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard, CardIssuer
from app.models.category import Category
from app.blueprints.recommendations.services import RecommendationService


class TestMaxAnnualFeeConstraint(unittest.TestCase):
    """Test max annual fee constraint functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test categories
        categories = [
            Category(name='dining', display_name='Dining'),
            Category(name='other', display_name='Other'),
            Category(name='travel', display_name='Travel'),
            Category(name='gas', display_name='Gas'),
        ]
        for category in categories:
            db.session.add(category)
        
        # Create issuer
        self.issuer = CardIssuer(name='Test Bank Max Fee Constraint')
        db.session.add(self.issuer)
        db.session.commit()
        
        # Create cards with different annual fees
        self.free_card = self.create_card_with_rewards(
            name='Free Card',
            annual_fee=0,
            reward_type='points',
            reward_categories=[{"category": "other", "rate": 1.0}]
        )
        
        self.mid_fee_card = self.create_card_with_rewards(
            name='Mid Fee Card',
            annual_fee=95,
            reward_type='points',
            reward_categories=[{"category": "dining", "rate": 3.0}, {"category": "other", "rate": 1.0}]
        )
        
        self.high_fee_card = self.create_card_with_rewards(
            name='High Fee Card',
            annual_fee=550,
            reward_type='points',
            reward_categories=[{"category": "travel", "rate": 5.0}, {"category": "other", "rate": 1.0}]
        )
    
    def create_card_with_rewards(self, name, annual_fee=0, reward_type='points', 
                                reward_value_multiplier=1.0, reward_categories=None):
        """Helper to create a card with the new reward system"""
        card = CreditCard(
            name=name,
            issuer_id=self.issuer.id,
            annual_fee=annual_fee,
            reward_type=reward_type,
            reward_value_multiplier=reward_value_multiplier,
            is_active=True
        )
        db.session.add(card)
        db.session.commit()
        
        # Add reward categories
        if reward_categories:
            for reward in reward_categories:
                card.add_reward_category(
                    reward['category'], 
                    reward['rate'],
                    limit=reward.get('limit')
                )
        
        db.session.commit()
        return card
    
    def tearDown(self):
        """Clean up test environment."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_max_annual_fees_none_allows_all_cards(self):
        """Test that max_annual_fees = None (blank field) allows all cards."""
        profile = UserProfile(
            name='Test Profile',
            credit_score=750,
            income=75000,
            total_monthly_spend=1000,
            category_spending=json.dumps({'dining': 500, 'travel': 300, 'other': 200}),
            reward_type='points',
            max_cards=3,
            max_annual_fees=None,  # Blank field - no limit
            session_id='test_session_1'
        )
        db.session.add(profile)
        db.session.commit()
        
        rec = RecommendationService.generate_recommendation(
            profile_id=profile.id, 
            session_id='test_session_1'
        )
        
        # Should recommend multiple cards including high-fee ones
        self.assertGreater(len(rec.recommended_sequence), 0)
        # Total fees can be any amount (no constraint)
        self.assertGreaterEqual(rec.total_annual_fees, 0)
        
        # Should include high-value cards even with fees
        card_fees = []
        for card_id in rec.recommended_sequence:
            card = CreditCard.query.get(card_id)
            card_fees.append(card.annual_fee)
        
        # With no fee constraint, should include cards with fees for better rewards
        self.assertGreater(max(card_fees), 0, "Should include cards with annual fees when no limit is set")

    def test_max_annual_fees_zero_only_free_cards(self):
        """Test that max_annual_fees = 0 only allows free cards."""
        profile = UserProfile(
            name='Test Profile',
            credit_score=750,
            income=75000,
            total_monthly_spend=1000,
            category_spending=json.dumps({'dining': 500, 'travel': 300, 'other': 200}),
            reward_type='points',
            max_cards=3,
            max_annual_fees=0,  # $0 limit - only free cards
            session_id='test_session_2'
        )
        db.session.add(profile)
        db.session.commit()
        
        rec = RecommendationService.generate_recommendation(
            profile_id=profile.id, 
            session_id='test_session_2'
        )
        
        # Should only recommend free cards
        self.assertGreater(len(rec.recommended_sequence), 0)
        self.assertEqual(rec.total_annual_fees, 0, f"Expected $0 total fees, got ${rec.total_annual_fees}")
        
        # Verify all recommended cards have $0 annual fee
        for card_id in rec.recommended_sequence:
            card = CreditCard.query.get(card_id)
            self.assertEqual(card.annual_fee, 0, f"Card {card.name} has ${card.annual_fee} fee, expected $0")

    def test_max_annual_fees_specific_limit(self):
        """Test that max_annual_fees = specific amount respects the limit."""
        profile = UserProfile(
            name='Test Profile',
            credit_score=750,
            income=75000,
            total_monthly_spend=1000,
            category_spending=json.dumps({'dining': 500, 'travel': 300, 'other': 200}),
            reward_type='points',
            max_cards=3,
            max_annual_fees=100,  # $100 limit
            session_id='test_session_3'
        )
        db.session.add(profile)
        db.session.commit()
        
        rec = RecommendationService.generate_recommendation(
            profile_id=profile.id, 
            session_id='test_session_3'
        )
        
        # Should recommend cards within the fee limit
        self.assertGreater(len(rec.recommended_sequence), 0)
        self.assertLessEqual(rec.total_annual_fees, 100, f"Expected fees <= $100, got ${rec.total_annual_fees}")
        
        # Should be able to include the mid-fee card ($95) but not high-fee card ($550)
        card_names = []
        for card_id in rec.recommended_sequence:
            card = CreditCard.query.get(card_id)
            card_names.append(card.name)
            self.assertLessEqual(card.annual_fee, 100, f"Card {card.name} has ${card.annual_fee} fee, exceeds $100 limit")
        
        # Should include cards with fees up to the limit
        self.assertTrue(any(card_name in ['Free Card', 'Mid Fee Card'] for card_name in card_names))
        self.assertNotIn('High Fee Card', card_names, "Should not include high-fee card that exceeds limit")

    def test_max_annual_fees_cumulative_constraint(self):
        """Test that max_annual_fees applies to the cumulative total of all recommended cards."""
        profile = UserProfile(
            name='Test Profile',
            credit_score=750,
            income=75000,
            total_monthly_spend=1000,
            category_spending=json.dumps({'dining': 500, 'travel': 300, 'other': 200}),
            reward_type='points',
            max_cards=5,  # Allow many cards
            max_annual_fees=150,  # $150 total limit
            session_id='test_session_4'
        )
        db.session.add(profile)
        db.session.commit()
        
        rec = RecommendationService.generate_recommendation(
            profile_id=profile.id, 
            session_id='test_session_4'
        )
        
        # Should recommend cards within the cumulative fee limit
        self.assertGreater(len(rec.recommended_sequence), 0)
        self.assertLessEqual(rec.total_annual_fees, 150, f"Expected cumulative fees <= $150, got ${rec.total_annual_fees}")
        
        # Calculate actual cumulative fees
        total_fees = 0
        for card_id in rec.recommended_sequence:
            card = CreditCard.query.get(card_id)
            total_fees += card.annual_fee
        
        self.assertEqual(total_fees, rec.total_annual_fees, "Cumulative fees should match recommendation total")
        self.assertLessEqual(total_fees, 150, "Cumulative fees should not exceed limit")


if __name__ == '__main__':
    unittest.main() 