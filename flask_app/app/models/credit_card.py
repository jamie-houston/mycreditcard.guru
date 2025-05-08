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
    
    # Categories and Offers (stored as JSON strings)
    reward_categories = db.Column(db.Text, nullable=False)  # JSON string of category multipliers
    special_offers = db.Column(db.Text, nullable=True)  # JSON string of special offers
    
    # 
    source = db.Column(db.String(50), nullable=True)  # Source name (e.g., 'nerdwallet', 'creditcards.com')
    source_url = db.Column(db.String(255), nullable=True)  # URL of the source page
    import_date = db.Column(db.DateTime, nullable=True)  # Date when the card was imported
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CreditCard {self.name}, Annual Fee: ${self.annual_fee}>'
    
    def get_reward_categories(self):
        """Parse and return reward categories as a list of dictionaries."""
        try:
            return json.loads(self.reward_categories)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_special_offers(self):
        """Parse and return special offers as a list of dictionaries."""
        try:
            return json.loads(self.special_offers)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_category_rate(self, category):
        """Get the reward rate for a specific category."""
        categories = self.get_reward_categories()
        for cat in categories:
            if cat['category'].lower() == category.lower():
                return float(cat['rate'])
        return 1.0  # Default base rate
    
    # Property for base reward rate (default reward rate)
    @property
    def base_reward_rate(self):
        """Get the base reward rate for the card."""
        return self.get_category_rate('base') 
    
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
        """Convert card to dictionary with parsed JSON fields."""
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
            'reward_categories': self.get_reward_categories(),
            'special_offers': self.get_special_offers(),
            'source': self.source,
            'source_url': self.source_url,
            'import_date': self.import_date
        } 