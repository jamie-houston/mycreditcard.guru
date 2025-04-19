from datetime import datetime
import uuid
from app.extensions import db

class CreditCardProfile(db.Model):
    __tablename__ = 'credit_card_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    annual_income = db.Column(db.Float, nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)
    existing_cards = db.Column(db.Integer, default=0)
    monthly_spending = db.Column(db.Float, default=0)
    preferred_categories = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    recommended_cards = db.relationship('RecommendedCard', backref='profile', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, name, annual_income, credit_score, existing_cards=0, 
                 monthly_spending=0, preferred_categories=None, user_id=None):
        self.public_id = str(uuid.uuid4())
        self.name = name
        self.annual_income = annual_income
        self.credit_score = credit_score
        self.existing_cards = existing_cards
        self.monthly_spending = monthly_spending
        self.preferred_categories = preferred_categories
        self.user_id = user_id
    
    def to_dict(self):
        return {
            'id': self.id,
            'public_id': self.public_id,
            'name': self.name,
            'annual_income': self.annual_income,
            'credit_score': self.credit_score,
            'existing_cards': self.existing_cards,
            'monthly_spending': self.monthly_spending,
            'preferred_categories': self.preferred_categories,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_by_id(cls, profile_id):
        return cls.query.get(int(profile_id))
    
    @classmethod
    def get_by_public_id(cls, public_id):
        return cls.query.filter_by(public_id=public_id).first()
    
    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all() 