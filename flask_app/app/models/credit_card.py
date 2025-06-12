from app import db
from datetime import datetime
import json

class CreditCard(db.Model):
    """Credit card model."""
    __tablename__ = 'credit_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    # Basic Card Info
    name = db.Column(db.String(100), nullable=False)
    issuer = db.Column(db.String(100), nullable=False)
    annual_fee = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Rewards Structure
    point_value = db.Column(db.Float, default=0.01)  # Dollar value per point
    signup_bonus_points = db.Column(db.Integer, default=0)
    signup_bonus_value = db.Column(db.Float, default=0.0)
    signup_bonus_min_spend = db.Column(db.Float, default=0.0)
    signup_bonus_time_limit = db.Column(db.Integer, default=90)  # Days
    signup_bonus_type = db.Column(db.String(20), default='points')  # 'points', 'dollars', or 'other'
    
    # Categories and Offers (stored as JSON strings) - DEPRECATED in favor of CreditCardReward model
    reward_categories = db.Column(db.Text, nullable=False)  # JSON string of category multipliers
    special_offers = db.Column(db.Text, nullable=True)  # JSON string of special offers
    
    # Source information for import tracking
    source = db.Column(db.String(50), nullable=True)  # Source name (e.g., 'nerdwallet', 'creditcards.com')
    source_url = db.Column(db.String(255), nullable=True)  # URL of the source page
    import_date = db.Column(db.DateTime, nullable=True)  # Date when the card was imported
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Foreign key to User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    rewards = db.relationship('CreditCardReward', backref='credit_card', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CreditCard {self.name}, Annual Fee: ${self.annual_fee}>'
    
    def get_category_rate(self, category_name):
        """Get the reward rate for a specific category using the new reward system."""
        from app.models.category import Category
        # Always map 'base rate' and 'base' to 'other'
        if category_name.lower() in ['base rate', 'base']:
            category_name = 'other'
        category = Category.get_by_name(category_name)
        if category:
            reward = self.rewards.filter_by(category_id=category.id).first()
            if reward:
                return reward.reward_percent
        return 1.0  # Default base rate

    def add_reward_category(self, category_name, reward_percent, is_bonus=False, notes=None):
        """Add or update a reward category for this card."""
        from app.models.category import Category, CreditCardReward
        
        category = Category.get_by_name(category_name)
        if not category:
            return False  # Category doesn't exist
        
        # Check if reward already exists
        existing_reward = self.rewards.filter_by(category_id=category.id).first()
        if existing_reward:
            existing_reward.reward_percent = reward_percent
            existing_reward.is_bonus_category = is_bonus
            existing_reward.notes = notes
        else:
            new_reward = CreditCardReward(
                credit_card_id=self.id,
                category_id=category.id,
                reward_percent=reward_percent,
                is_bonus_category=is_bonus,
                notes=notes
            )
            db.session.add(new_reward)
        
        return True

    def get_all_rewards(self):
        """Get all reward categories for this card."""
        return [
            {
                'category': reward.category.name,
                'display_name': reward.category.display_name,
                'reward_percent': reward.reward_percent,
                'is_bonus_category': reward.is_bonus_category,
                'notes': reward.notes
            }
            for reward in self.rewards
        ]
    
    # Property for base reward rate (default reward rate)
    @property
    def base_reward_rate(self):
        """Get the base reward rate for the card (now always 'other')."""
        return self.get_category_rate('other')
    
    # Properties for category-specific reward rates
    @property
    def dining_reward_rate(self):
        """Get the dining reward rate for the card."""
        return self.get_category_rate('dining')
    
    @property
    def travel_reward_rate(self):
        """Get the travel reward rate for the card."""
        return self.get_category_rate('travel')
    
    @property
    def gas_reward_rate(self):
        """Get the gas reward rate for the card."""
        return self.get_category_rate('gas')
    
    @property
    def grocery_reward_rate(self):
        """Get the grocery reward rate for the card."""
        return self.get_category_rate('groceries')
    
    @property
    def entertainment_reward_rate(self):
        """Get the entertainment reward rate for the card."""
        return self.get_category_rate('entertainment')
    
    def calculate_category_value(self, category_spend, category):
        """Calculate the value earned from spending in a specific category."""
        rate = self.get_category_rate(category)
        return category_spend * rate * self.point_value
    
    def calculate_monthly_value(self, category_spending):
        """Calculate the total monthly value based on category spending."""
        total_value = 0
        category_values = {}
        
        for category, spend in category_spending.items():
            category_value = self.calculate_category_value(spend, category)
            category_values[category] = category_value
            total_value += category_value
        
        return {
            'total': total_value,
            'by_category': category_values
        }
    
    def calculate_annual_value(self, category_spending):
        """Calculate the annual value based on monthly category spending."""
        monthly_value = self.calculate_monthly_value(category_spending)
        annual_value = monthly_value['total'] * 12
        
        # Subtract annual fee
        net_value = annual_value - self.annual_fee
        
        return {
            'annual_value': annual_value,
            'annual_fee': self.annual_fee,
            'net_value': net_value,
            'by_category': monthly_value['by_category']
        }
    
    def calculate_signup_bonus_value(self, monthly_spend):
        """Calculate if the signup bonus is achievable and its value."""
        # Check if signup bonus can be achieved
        months_needed = self.signup_bonus_min_spend / monthly_spend
        days_needed = months_needed * 30
        
        achievable = days_needed <= self.signup_bonus_time_limit
        
        return {
            'value': self.signup_bonus_value if achievable else 0,
            'achievable': achievable,
            'months_needed': round(months_needed, 1),
            'days_needed': round(days_needed, 0)
        }
    
    def to_dict(self):
        """Convert card to dictionary with new structured rewards."""
        return {
            'id': self.id,
            'name': self.name,
            'issuer': self.issuer,
            'annual_fee': self.annual_fee,
            'is_active': self.is_active,
            'point_value': self.point_value,
            'signup_bonus_points': self.signup_bonus_points,
            'signup_bonus_value': self.signup_bonus_value,
            'signup_bonus_min_spend': self.signup_bonus_min_spend,
            'signup_bonus_time_limit': self.signup_bonus_time_limit,
            'signup_bonus_type': self.signup_bonus_type,
            'rewards': self.get_all_rewards(),  # New structured rewards system
            'source': self.source,
            'source_url': self.source_url,
            'import_date': self.import_date
        } 

    def get_signup_bonus_display_value(self):
        """Get the properly formatted signup bonus value for display."""
        if self.signup_bonus_type == 'dollars':
            # For dollar bonuses, use the value as-is
            return self.signup_bonus_value
        elif self.signup_bonus_type == 'points':
            # For points/miles, the signup_bonus_value should already be the dollar equivalent
            return self.signup_bonus_value
        else:
            # For 'other' type bonuses
            return self.signup_bonus_value
    
    def get_signup_bonus_display_text(self):
        """Get the full display text for signup bonus."""
        if self.signup_bonus_value <= 0:
            return "None"
        
        if self.signup_bonus_type == 'dollars':
            return f"${self.signup_bonus_value:.0f}"
        elif self.signup_bonus_type == 'points':
            return f"{self.signup_bonus_points:,} points (${self.signup_bonus_value:.0f})"
        else:
            return "Something mysterious (possibly a free llama)" 
