from app import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
import json

class CardIssuer(db.Model):
    __tablename__ = 'card_issuers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    cards = db.relationship('CreditCard', backref='issuer_obj', lazy='dynamic')
    def __repr__(self):
        return f'<CardIssuer {self.name}>'

    def __str__(self):
        return self.name

    @staticmethod
    def all_ordered():
        return CardIssuer.query.order_by(CardIssuer.name).all()

class CreditCard(db.Model):
    """Credit card model."""
    __tablename__ = 'credit_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    # Basic Card Info
    name = db.Column(db.String(100), nullable=False)
    issuer_id = db.Column(db.Integer, db.ForeignKey('card_issuers.id'), nullable=False)
    annual_fee = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    
    # Reward Type - new field to replace bonus_type
    reward_type = db.Column(db.String(20), default='points')  # 'points', 'cash_back', 'miles', 'hotel'
    
    # Rewards Structure
    reward_value_multiplier = db.Column(db.Float, default=0.01)  # Renamed from point_value - Dollar value per point/mile
    
    # JSON-based signup bonus structure
    signup_bonus = db.Column(db.Text, nullable=True)  # JSON string containing signup bonus details
    
    # Special offers (stored as JSON string)
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

    # Calculated property for estimated_value
    @hybrid_property
    def estimated_value(self):
        """Calculate estimated value based on signup bonus value from JSON structure."""
        return self.get_signup_bonus_value_new()

    def __repr__(self):
        return f'<CreditCard {self.name}, Annual Fee: ${self.annual_fee}>'
    
    def get_category_rate(self, category_name):
        """Get the reward rate for a specific category using the new reward system."""
        from app.models.category import Category
        # Always map 'base rate' and 'base' to 'other'
        if category_name.lower() in ['base rate', 'base']:
            category_name = 'other'
        
        # First try to find the specific category
        category = Category.get_by_name(category_name)
        if category:
            reward = self.rewards.filter_by(category_id=category.id).first()
            if reward:
                return reward.reward_percent
        
        # If no specific category found, fall back to 'other' category rate
        if category_name.lower() != 'other':
            other_category = Category.get_by_name('other')
            if other_category:
                other_reward = self.rewards.filter_by(category_id=other_category.id).first()
                if other_reward:
                    return other_reward.reward_percent
        
        return 1.0  # Default base rate if no 'other' category either

    def add_reward_category(self, category_name, reward_percent, is_bonus=False, notes=None, limit=None):
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
            existing_reward.limit = limit
        else:
            new_reward = CreditCardReward(
                credit_card_id=self.id,
                category_id=category.id,
                reward_percent=reward_percent,
                is_bonus_category=is_bonus,
                notes=notes,
                limit=limit
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
                'notes': reward.notes,
                'limit': reward.limit
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
        # New system: rate is percentage (e.g., 2.0 for 2%), convert to decimal and multiply by multiplier
        points_earned = category_spend * (rate / 100)
        return points_earned * self.reward_value_multiplier
    
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
        
        achievable = months_needed <= self.signup_bonus_max_months
        
        return {
            'value': self.signup_bonus_value if achievable else 0,
            'achievable': achievable,
            'months_needed': round(months_needed, 1)
        }
    
    def to_dict(self):
        """Convert card to dictionary with new structured rewards."""
        return {
            'id': self.id,
            'name': self.name,
            'issuer': self.issuer_id,
            'annual_fee': self.annual_fee,
            'is_active': self.is_active,
            'reward_type': self.reward_type,
            'reward_value_multiplier': self.reward_value_multiplier,
            'signup_bonus': self.get_signup_bonus_data(),  # New JSON structure
            'estimated_value': self.estimated_value,
            'rewards': self.get_all_rewards(),  # New structured rewards system
            'source': self.source,
            'source_url': self.source_url,
            'import_date': self.import_date
        } 

    def get_signup_bonus_display_value(self):
        """Get the properly formatted signup bonus value for display."""
        return self.get_signup_bonus_value_new()
    
    def get_signup_bonus_display_text(self):
        """Get the full display text for signup bonus."""
        bonus_data = self.get_signup_bonus_data()
        if not bonus_data:
            return "None"
            
        value = bonus_data.get('value', 0)
        if value <= 0:
            return "None"
        
        if self.reward_type == 'cash_back':
            amount = bonus_data.get('cash_back', 0)
            return f"${amount:.0f}"
        elif self.reward_type == 'miles':
            amount = bonus_data.get('miles', 0)
            return f"{amount:,} {self.get_reward_type_display_name().lower()} (${value:.0f})"
        elif self.reward_type == 'hotel':
            amount = bonus_data.get('points', 0)
            return f"{amount:,} {self.get_reward_type_display_name().lower()} (${value:.0f})"
        else:  # 'points' or default
            amount = bonus_data.get('points', 0)
            return f"{amount:,} {self.get_reward_type_display_name().lower()} (${value:.0f})"
    
    def get_reward_type_display_name(self):
        """Get the display name for the reward type."""
        reward_type_mapping = {
            'cash_back': 'Cash Back',
            'points': 'Points',
            'miles': 'Miles',
            'hotel': 'Hotel',
            'travel': 'Travel'
        }
        return reward_type_mapping.get(self.reward_type, self.reward_type.replace('_', ' ').title())

    # New signup bonus methods for JSON structure
    def get_signup_bonus_data(self):
        """Get signup bonus data as a dictionary."""
        if not self.signup_bonus:
            return None
        try:
            return json.loads(self.signup_bonus)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def set_signup_bonus_data(self, bonus_data):
        """Set signup bonus data from a dictionary."""
        if bonus_data:
            self.signup_bonus = json.dumps(bonus_data)
        else:
            self.signup_bonus = None
    
    def get_signup_bonus_amount(self):
        """Get the signup bonus amount based on reward type."""
        bonus_data = self.get_signup_bonus_data()
        if not bonus_data:
            return 0
        
        reward_type = self.reward_type
        if reward_type == 'cash_back':
            return bonus_data.get('cash_back', 0)
        elif reward_type == 'miles':
            return bonus_data.get('miles', 0)
        elif reward_type == 'hotel':
            return bonus_data.get('points', 0)  # Hotel points
        else:  # 'points' or default
            return bonus_data.get('points', 0)
    
    def get_signup_bonus_value_new(self):
        """Get the calculated value of the signup bonus."""
        bonus_data = self.get_signup_bonus_data()
        if not bonus_data:
            return 0.0
        return bonus_data.get('value', 0.0)
    
    def get_signup_bonus_min_spend_new(self):
        """Get the minimum spend requirement for the signup bonus."""
        bonus_data = self.get_signup_bonus_data()
        if not bonus_data:
            return 0.0
        return bonus_data.get('min_spend', 0.0)
    
    def get_signup_bonus_max_months_new(self):
        """Get the maximum months to achieve the signup bonus."""
        bonus_data = self.get_signup_bonus_data()
        if not bonus_data:
            return 3
        return bonus_data.get('max_months', 3)
    
    def update_signup_bonus(self, amount, min_spend=None, max_months=None):
        """Update signup bonus with new amount and requirements."""
        if amount <= 0:
            self.signup_bonus = None
            return
        
        bonus_data = {}
        reward_type = self.reward_type
        
        # Set the amount field based on reward type
        if reward_type == 'cash_back':
            bonus_data['cash_back'] = float(amount)
            bonus_data['value'] = float(amount)  # For cash back, value equals amount
        elif reward_type == 'miles':
            bonus_data['miles'] = int(amount)
            bonus_data['value'] = float(amount * self.reward_value_multiplier)
        elif reward_type == 'hotel':
            bonus_data['points'] = int(amount)  # Hotel points
            bonus_data['value'] = float(amount * self.reward_value_multiplier)
        else:  # 'points' or default
            bonus_data['points'] = int(amount)
            bonus_data['value'] = float(amount * self.reward_value_multiplier)
        
        # Set requirements
        if min_spend is not None:
            bonus_data['min_spend'] = float(min_spend)
        if max_months is not None:
            bonus_data['max_months'] = int(max_months)
        
        self.set_signup_bonus_data(bonus_data)

    # Backward compatibility properties
    @property
    def point_value(self):
        """Backward compatibility for point_value."""
        return self.reward_value_multiplier
    
    @point_value.setter
    def point_value(self, value):
        """Backward compatibility setter for point_value."""
        self.reward_value_multiplier = value
