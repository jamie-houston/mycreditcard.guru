from app import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
import json

class UserCard(db.Model):
    """Model for tracking credit cards owned by users."""
    __tablename__ = 'user_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User relationship - supports both authenticated and anonymous users
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(36), nullable=True)  # For anonymous users
    
    # Card relationship
    credit_card_id = db.Column(db.Integer, db.ForeignKey('credit_cards.id'), nullable=False)
    
    # User-specific card data
    date_acquired = db.Column(db.Date, nullable=False)
    custom_signup_bonus_points = db.Column(db.Integer, nullable=True)  # Override if different from card default
    custom_signup_bonus_value = db.Column(db.Float, nullable=True)     # Override if different from card default
    custom_signup_bonus_min_spend = db.Column(db.Float, nullable=True) # Override if different from card default
    
    # Bonus tracking
    bonus_earned = db.Column(db.Boolean, default=False)
    bonus_earned_date = db.Column(db.Date, nullable=True)
    
    # Account status
    is_active = db.Column(db.Boolean, default=True)  # False if cancelled
    date_cancelled = db.Column(db.Date, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    credit_card = db.relationship('CreditCard', backref='user_cards')
    user = db.relationship('User', backref='owned_cards')
    
    # Constraints
    __table_args__ = (
        db.CheckConstraint('user_id IS NOT NULL OR session_id IS NOT NULL', 
                          name='user_or_session_required'),
        db.UniqueConstraint('user_id', 'credit_card_id', 'date_acquired', 
                           name='unique_user_card_date'),
        db.UniqueConstraint('session_id', 'credit_card_id', 'date_acquired', 
                           name='unique_session_card_date'),
    )
    
    @hybrid_property
    def effective_signup_bonus_points(self):
        """Get the effective signup bonus points (custom or card default)."""
        return self.custom_signup_bonus_points or self.credit_card.signup_bonus_points
    
    @hybrid_property
    def effective_signup_bonus_value(self):
        """Get the effective signup bonus value (custom or card default)."""
        return self.custom_signup_bonus_value or self.credit_card.signup_bonus_value
    
    @hybrid_property
    def effective_signup_bonus_min_spend(self):
        """Get the effective minimum spend requirement (custom or card default)."""
        return self.custom_signup_bonus_min_spend or self.credit_card.signup_bonus_min_spend
    
    @property
    def signup_bonus_deadline(self):
        """Calculate the deadline for earning the signup bonus."""
        if not self.credit_card.signup_bonus_max_months:
            return None
        
        from dateutil.relativedelta import relativedelta
        return self.date_acquired + relativedelta(months=self.credit_card.signup_bonus_max_months)
    
    @property
    def is_signup_bonus_expired(self):
        """Check if the signup bonus period has expired."""
        deadline = self.signup_bonus_deadline
        if not deadline:
            return False
        return datetime.now().date() > deadline
    
    @property
    def months_since_acquired(self):
        """Calculate months since card was acquired."""
        from dateutil.relativedelta import relativedelta
        today = datetime.now().date()
        delta = relativedelta(today, self.date_acquired)
        return delta.years * 12 + delta.months
    
    def to_dict(self):
        """Convert user card to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'credit_card_id': self.credit_card_id,
            'credit_card_name': self.credit_card.name if self.credit_card else None,
            'credit_card_issuer': self.credit_card.issuer_obj.name if self.credit_card and self.credit_card.issuer_obj else None,
            'date_acquired': self.date_acquired.isoformat() if self.date_acquired else None,
            'effective_signup_bonus_points': self.effective_signup_bonus_points,
            'effective_signup_bonus_value': self.effective_signup_bonus_value,
            'effective_signup_bonus_min_spend': self.effective_signup_bonus_min_spend,
            'bonus_earned': self.bonus_earned,
            'bonus_earned_date': self.bonus_earned_date.isoformat() if self.bonus_earned_date else None,
            'is_active': self.is_active,
            'date_cancelled': self.date_cancelled.isoformat() if self.date_cancelled else None,
            'signup_bonus_deadline': self.signup_bonus_deadline.isoformat() if self.signup_bonus_deadline else None,
            'is_signup_bonus_expired': self.is_signup_bonus_expired,
            'months_since_acquired': self.months_since_acquired,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def get_user_cards(cls, user_id=None, session_id=None, active_only=True):
        """Get all cards for a user or session."""
        query = cls.query
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        elif session_id:
            query = query.filter_by(session_id=session_id)
        else:
            return []
        
        if active_only:
            query = query.filter_by(is_active=True)
        
        return query.all()
    
    @classmethod
    def get_cards_by_issuer(cls, issuer_id, user_id=None, session_id=None):
        """Get user's cards from a specific issuer."""
        from app.models.credit_card import CreditCard
        query = cls.query.join(CreditCard).filter(CreditCard.issuer_id == issuer_id)
        
        if user_id:
            query = query.filter(cls.user_id == user_id)
        elif session_id:
            query = query.filter(cls.session_id == session_id)
        else:
            return []
        
        return query.filter_by(is_active=True).all()
    
    def __repr__(self):
        """String representation of the user card."""
        return f'<UserCard {self.credit_card.name if self.credit_card else "Unknown"} acquired {self.date_acquired}>'