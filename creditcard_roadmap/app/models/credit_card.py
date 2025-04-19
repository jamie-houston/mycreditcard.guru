from app import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList

class CreditCard(db.Model):
    __tablename__ = 'credit_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    issuer = db.Column(db.String(50), nullable=False)
    annual_fee = db.Column(db.Float, default=0.0)
    
    # User relationship
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Reward categories (5% on gas, 3% on groceries, etc.)
    # Stored as JSON: [{"category": "gas", "percentage": 5}, ...]
    reward_categories = db.Column(db.Text, default='[]')
    
    # Card offers (travel credits, statement credits, etc.)
    # Stored as JSON: [{"type": "travel_credit", "amount": 300, "frequency": "annual"}, ...]
    offers = db.Column(db.Text, default='[]')
    
    # Signup bonus details
    signup_bonus_points = db.Column(db.Integer, default=0)
    signup_bonus_value = db.Column(db.Float, default=0.0)
    signup_bonus_spend_requirement = db.Column(db.Float, default=0.0)
    signup_bonus_time_period = db.Column(db.Integer, default=3)  # in months
    
    # Additional metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CreditCard {self.name} by {self.issuer}>' 