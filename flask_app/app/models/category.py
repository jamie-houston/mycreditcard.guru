from app import db
from datetime import datetime
import json

class Category(db.Model):
    """Model for global spending/reward categories managed by admin."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    display_name = db.Column(db.String(100), nullable=False)  # User-friendly name
    description = db.Column(db.String(200))
    icon = db.Column(db.String(50), default='fas fa-tag')  # FontAwesome icon class
    aliases = db.Column(db.Text)  # JSON array of alternative names for this category
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)  # For ordering in lists
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    card_rewards = db.relationship('CreditCardReward', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'icon': self.icon,
            'aliases': self.get_aliases(),
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_active_categories(cls):
        """Get all active categories ordered by sort_order then name."""
        return cls.query.filter_by(is_active=True).order_by(cls.sort_order, cls.name).all()
    
    def get_aliases(self):
        """Get aliases as a list."""
        if self.aliases:
            try:
                return json.loads(self.aliases)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_aliases(self, aliases_list):
        """Set aliases from a list."""
        if aliases_list:
            self.aliases = json.dumps(aliases_list)
        else:
            self.aliases = None
    
    @classmethod
    def get_by_name(cls, name):
        """Get category by name (case-insensitive)."""
        return cls.query.filter(cls.name.ilike(name)).first()
    
    @classmethod
    def get_by_name_or_alias(cls, name):
        """Get category by name or alias (case-insensitive)."""
        name_lower = name.lower().strip()
        
        # First try exact name match
        category = cls.query.filter(cls.name.ilike(name_lower)).first()
        if category:
            return category
        
        # Then try alias match
        categories = cls.query.filter(cls.is_active == True).all()
        for category in categories:
            aliases = category.get_aliases()
            if any(alias.lower().strip() == name_lower for alias in aliases):
                return category
        
        return None


class CreditCardReward(db.Model):
    """Model for credit card reward rates by category."""
    __tablename__ = 'credit_card_rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign keys
    credit_card_id = db.Column(db.Integer, db.ForeignKey('credit_cards.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Reward details
    reward_percent = db.Column(db.Float, nullable=False, default=1.0)  # Percentage (e.g., 2.0 for 2%)
    is_bonus_category = db.Column(db.Boolean, default=False)  # If this is a bonus category vs base rate
    notes = db.Column(db.Text)  # Any special conditions or notes
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (db.UniqueConstraint('credit_card_id', 'category_id', name='_card_category_uc'),)
    
    def __repr__(self):
        return f'<CreditCardReward Card:{self.credit_card_id} Category:{self.category_id} Rate:{self.reward_percent}%>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'credit_card_id': self.credit_card_id,
            'category_id': self.category_id,
            'reward_percent': self.reward_percent,
            'is_bonus_category': self.is_bonus_category,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 