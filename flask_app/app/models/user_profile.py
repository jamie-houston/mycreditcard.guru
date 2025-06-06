from app.extensions import db
from datetime import datetime
import uuid

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    spending_categories = db.relationship('SpendingCategory', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    benefits = db.relationship('PrioritizedBenefit', backref='profile', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<UserProfile {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'public_id': self.public_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'spending_categories': [cat.to_dict() for cat in self.spending_categories],
            'benefits': [benefit.to_dict() for benefit in self.benefits]
        }

class SpendingCategory(db.Model):
    __tablename__ = 'spending_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    monthly_spend = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    profile_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Relationships
    category = db.relationship('Category', backref='spending_usages')
    
    def __repr__(self):
        return f'<SpendingCategory {self.category.name if self.category else "Unknown"}: ${self.monthly_spend}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'category_display_name': self.category.display_name if self.category else None,
            'monthly_spend': self.monthly_spend,
            'created_at': self.created_at.isoformat()
        }

class PrioritizedBenefit(db.Model):
    __tablename__ = 'prioritized_benefits'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    importance = db.Column(db.Integer, nullable=False) # 1-5 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    profile_id = db.Column(db.Integer, db.ForeignKey('user_profiles.id'), nullable=False)
    
    def __repr__(self):
        return f'<PrioritizedBenefit {self.name}: {self.importance}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'importance': self.importance,
            'created_at': self.created_at.isoformat()
        } 