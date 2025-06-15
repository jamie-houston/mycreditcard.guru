import pytest
import json
from app import create_app, db
from app.models.user_data import UserProfile
from app.models.credit_card import CreditCard, CardIssuer
from app.blueprints.recommendations.services import RecommendationService


@pytest.fixture(scope="function")
def test_app():
    """Create a test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def sample_cards(test_app):
    """Create sample credit cards with different annual fees."""
    with test_app.app_context():
        # Clear existing data to avoid conflicts
        CreditCard.query.delete()
        CardIssuer.query.delete()
        db.session.commit()
        
        # Create issuer with unique name
        issuer = CardIssuer(name='Test Bank Max Fee Constraint')
        db.session.add(issuer)
        db.session.commit()
        
        # Create cards with different annual fees
        free_card = CreditCard(
            name='Free Card',
            issuer_id=issuer.id,
            annual_fee=0,
            reward_type='points',
            reward_categories='[{"category": "other", "rate": 1.0}]'
        )
        
        mid_fee_card = CreditCard(
            name='Mid Fee Card',
            issuer_id=issuer.id,
            annual_fee=95,
            reward_type='points',
            reward_categories='[{"category": "dining", "rate": 3.0}, {"category": "other", "rate": 1.0}]'
        )
        
        high_fee_card = CreditCard(
            name='High Fee Card',
            issuer_id=issuer.id,
            annual_fee=550,
            reward_type='points',
            reward_categories='[{"category": "travel", "rate": 5.0}, {"category": "other", "rate": 1.0}]'
        )
        
        db.session.add_all([free_card, mid_fee_card, high_fee_card])
        db.session.commit()
        
        return {
            'free': free_card,
            'mid': mid_fee_card,
            'high': high_fee_card
        }


class TestMaxAnnualFeeConstraint:
    """Test max annual fee constraint functionality."""
    
    def test_max_annual_fees_none_allows_all_cards(self, test_app, sample_cards):
        """Test that max_annual_fees = None (blank field) allows all cards."""
        with test_app.app_context():
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
            assert len(rec.recommended_sequence) > 0
            # Total fees can be any amount (no constraint)
            assert rec.total_annual_fees >= 0
            
            # Should include high-value cards even with fees
            card_fees = []
            for card_id in rec.recommended_sequence:
                card = CreditCard.query.get(card_id)
                card_fees.append(card.annual_fee)
            
            # With no fee constraint, should include cards with fees for better rewards
            assert max(card_fees) > 0, "Should include cards with annual fees when no limit is set"
    
    def test_max_annual_fees_zero_only_free_cards(self, test_app, sample_cards):
        """Test that max_annual_fees = 0 only allows free cards."""
        with test_app.app_context():
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
            assert len(rec.recommended_sequence) > 0
            assert rec.total_annual_fees == 0, f"Expected $0 total fees, got ${rec.total_annual_fees}"
            
            # Verify all recommended cards have $0 annual fee
            for card_id in rec.recommended_sequence:
                card = CreditCard.query.get(card_id)
                assert card.annual_fee == 0, f"Card {card.name} has ${card.annual_fee} fee, expected $0"
    
    def test_max_annual_fees_specific_limit(self, test_app, sample_cards):
        """Test that max_annual_fees = specific amount respects the limit."""
        with test_app.app_context():
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
            assert len(rec.recommended_sequence) > 0
            assert rec.total_annual_fees <= 100, f"Expected fees <= $100, got ${rec.total_annual_fees}"
            
            # Should be able to include the mid-fee card ($95) but not high-fee card ($550)
            card_names = []
            for card_id in rec.recommended_sequence:
                card = CreditCard.query.get(card_id)
                card_names.append(card.name)
                assert card.annual_fee <= 100, f"Card {card.name} has ${card.annual_fee} fee, exceeds $100 limit"
            
            # Should include cards with fees up to the limit
            assert any(card_name in ['Free Card', 'Mid Fee Card'] for card_name in card_names)
            assert 'High Fee Card' not in card_names, "Should not include high-fee card that exceeds limit"
    
    def test_max_annual_fees_cumulative_constraint(self, test_app, sample_cards):
        """Test that max_annual_fees applies to the cumulative total of all recommended cards."""
        with test_app.app_context():
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
            
            # Total fees should not exceed the limit
            assert rec.total_annual_fees <= 150, f"Expected total fees <= $150, got ${rec.total_annual_fees}"
            
            # Should be able to combine free card ($0) + mid fee card ($95) = $95 total
            # But not include high fee card ($550) as that would exceed $150
            total_individual_fees = 0
            for card_id in rec.recommended_sequence:
                card = CreditCard.query.get(card_id)
                total_individual_fees += card.annual_fee
            
            assert total_individual_fees == rec.total_annual_fees, "Individual fees should sum to total fees"
            assert total_individual_fees <= 150, f"Cumulative fees ${total_individual_fees} exceed limit"
    
    def test_fallback_when_no_cards_meet_constraint(self, test_app, sample_cards):
        """Test fallback behavior when no cards meet the fee constraint."""
        with test_app.app_context():
            # Remove the free card to test fallback behavior
            free_card = CreditCard.query.filter_by(name='Free Card').first()
            if free_card:
                db.session.delete(free_card)
                db.session.commit()
            
            profile = UserProfile(
                name='Test Profile',
                credit_score=750,
                income=75000,
                total_monthly_spend=1000,
                category_spending=json.dumps({'dining': 500, 'travel': 300, 'other': 200}),
                reward_type='points',
                max_cards=3,
                max_annual_fees=0,  # $0 limit but no free cards available
                session_id='test_session_5'
            )
            db.session.add(profile)
            db.session.commit()
            
            rec = RecommendationService.generate_recommendation(
                profile_id=profile.id, 
                session_id='test_session_5'
            )
            
            # Should fall back to recommending at least one card even if it exceeds the constraint
            assert len(rec.recommended_sequence) >= 1, "Should recommend at least one card as fallback"
            
            # The fallback card will likely have fees > 0
            # This tests the fallback logic in the recommendation service 