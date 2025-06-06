# models package 

# Import all models for easier access
# Order matters here - define models with least dependencies first

# Import base models first
from app.models.category import Category, CreditCardReward
from app.models.profile import CreditCardProfile
from app.models.credit_card import CreditCard
from app.models.goal import Goal

# Import User last as it references the other models
from app.models.user import User

# Define __all__ to control what gets imported with 'from app.models import *'
__all__ = ['User', 'CreditCardProfile', 'CreditCard', 'Category', 'CreditCardReward', 'Goal'] 