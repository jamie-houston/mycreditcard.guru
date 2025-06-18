from app import db
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.hybrid import hybrid_property
import json

class IssuerPolicy(db.Model):
    """Model for tracking issuer-specific application policies and restrictions."""
    __tablename__ = 'issuer_policies'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Policy identification
    issuer_id = db.Column(db.Integer, db.ForeignKey('card_issuers.id'), nullable=False)
    policy_name = db.Column(db.String(100), nullable=False)  # e.g., "5/24 Rule", "2/90 Rule"
    policy_type = db.Column(db.String(50), nullable=False)   # e.g., "application_limit", "minimum_wait"
    
    # Policy parameters (stored as JSON for flexibility)
    policy_config = db.Column(db.Text, nullable=False)  # JSON configuration
    
    # Policy description and details
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    issuer = db.relationship('CardIssuer', backref='policies')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('issuer_id', 'policy_name', name='unique_issuer_policy'),
    )
    
    @hybrid_property
    def config(self):
        """Parse policy configuration from JSON."""
        try:
            return json.loads(self.policy_config) if self.policy_config else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    
    @config.setter
    def config(self, value):
        """Set policy configuration as JSON."""
        self.policy_config = json.dumps(value)
    
    def check_policy_compliance(self, user_cards, target_card_date=None):
        """
        Check if a user's card history complies with this policy.
        
        Args:
            user_cards: List of UserCard objects for the user
            target_card_date: The proposed date for the new card application
        
        Returns:
            dict: {
                'compliant': bool,
                'reason': str,
                'next_eligible_date': date or None,
                'count': int (current count for application limit policies)
            }
        """
        if not self.is_active:
            return {'compliant': True, 'reason': 'Policy is inactive'}
        
        config = self.config
        target_date = target_card_date or date.today()
        
        if self.policy_type == 'application_limit':
            return self._check_application_limit(user_cards, target_date, config)
        elif self.policy_type == 'minimum_wait':
            return self._check_minimum_wait(user_cards, target_date, config)
        elif self.policy_type == 'issuer_specific_limit':
            return self._check_issuer_specific_limit(user_cards, target_date, config)
        else:
            return {'compliant': True, 'reason': f'Unknown policy type: {self.policy_type}'}
    
    def _check_application_limit(self, user_cards, target_date, config):
        """Check application limits like Chase 5/24."""
        max_cards = config.get('max_cards', 5)
        months_lookback = config.get('months_lookback', 24)
        scope = config.get('scope', 'all_issuers')  # 'all_issuers' or 'this_issuer'
        
        # Calculate the cutoff date
        cutoff_date = target_date - relativedelta(months=months_lookback)
        
        # Filter cards based on scope and date
        relevant_cards = []
        for card in user_cards:
            if card.date_acquired <= target_date and card.date_acquired >= cutoff_date:
                if scope == 'all_issuers':
                    relevant_cards.append(card)
                elif scope == 'this_issuer' and card.credit_card.issuer_id == self.issuer_id:
                    relevant_cards.append(card)
        
        current_count = len(relevant_cards)
        compliant = current_count < max_cards
        
        # Calculate next eligible date if not compliant
        next_eligible_date = None
        if not compliant and relevant_cards:
            # Find the earliest card that would fall outside the window
            sorted_cards = sorted(relevant_cards, key=lambda x: x.date_acquired)
            earliest_card_date = sorted_cards[0].date_acquired
            next_eligible_date = earliest_card_date + relativedelta(months=months_lookback, days=1)
        
        return {
            'compliant': compliant,
            'reason': f'Currently {current_count}/{max_cards} cards in {months_lookback} months' + 
                     ('' if compliant else ' - limit exceeded'),
            'next_eligible_date': next_eligible_date,
            'count': current_count
        }
    
    def _check_minimum_wait(self, user_cards, target_date, config):
        """Check minimum wait periods between applications."""
        wait_days = config.get('wait_days', 90)
        scope = config.get('scope', 'this_issuer')
        
        # Filter cards based on scope
        relevant_cards = []
        for card in user_cards:
            if scope == 'all_issuers':
                relevant_cards.append(card)
            elif scope == 'this_issuer' and card.credit_card.issuer_id == self.issuer_id:
                relevant_cards.append(card)
        
        if not relevant_cards:
            return {'compliant': True, 'reason': 'No previous cards found'}
        
        # Find the most recent card
        most_recent_card = max(relevant_cards, key=lambda x: x.date_acquired)
        days_since_last = (target_date - most_recent_card.date_acquired).days
        
        compliant = days_since_last >= wait_days
        next_eligible_date = most_recent_card.date_acquired + relativedelta(days=wait_days)
        
        return {
            'compliant': compliant,
            'reason': f'Last card acquired {days_since_last} days ago' + 
                     (f', need {wait_days} days minimum' if not compliant else ''),
            'next_eligible_date': next_eligible_date if not compliant else None,
            'count': len(relevant_cards)
        }
    
    def _check_issuer_specific_limit(self, user_cards, target_date, config):
        """Check issuer-specific limits (like max cards from one issuer)."""
        max_cards = config.get('max_cards', 2)
        
        # Count active cards from this issuer
        issuer_cards = [card for card in user_cards 
                       if card.credit_card.issuer_id == self.issuer_id and card.is_active]
        
        current_count = len(issuer_cards)
        compliant = current_count < max_cards
        
        return {
            'compliant': compliant,
            'reason': f'Currently have {current_count}/{max_cards} active cards from this issuer',
            'next_eligible_date': None,  # No time-based restriction
            'count': current_count
        }
    
    def to_dict(self):
        """Convert issuer policy to dictionary."""
        return {
            'id': self.id,
            'issuer_id': self.issuer_id,
            'issuer_name': self.issuer.name if self.issuer else None,
            'policy_name': self.policy_name,
            'policy_type': self.policy_type,
            'config': self.config,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_active_policies_for_issuer(cls, issuer_id):
        """Get all active policies for a specific issuer."""
        return cls.query.filter_by(issuer_id=issuer_id, is_active=True).all()
    
    @classmethod
    def create_chase_524_policy(cls, chase_issuer_id):
        """Helper method to create the famous Chase 5/24 policy."""
        policy = cls(
            issuer_id=chase_issuer_id,
            policy_name="5/24 Rule",
            policy_type="application_limit",
            description="Chase will generally not approve applications if you have opened 5 or more credit cards from any issuer in the past 24 months"
        )
        policy.config = {
            'max_cards': 5,
            'months_lookback': 24,
            'scope': 'all_issuers'
        }
        return policy
    
    @classmethod
    def create_amex_290_policy(cls, amex_issuer_id):
        """Helper method to create American Express 2/90 policy."""
        policy = cls(
            issuer_id=amex_issuer_id,
            policy_name="2/90 Rule",
            policy_type="minimum_wait",
            description="American Express typically limits approvals to 2 credit cards every 90 days"
        )
        policy.config = {
            'wait_days': 90,
            'scope': 'this_issuer',
            'max_in_period': 2
        }
        return policy
    
    def __repr__(self):
        """String representation of the issuer policy."""
        return f'<IssuerPolicy {self.issuer.name if self.issuer else "Unknown"}: {self.policy_name}>'