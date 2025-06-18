# models package 

# Import all models for easier access
# Order matters here - define models with least dependencies first

# Import base models first
from app.models.category import Category, CreditCardReward
# Removed CreditCardProfile - consolidated into UserProfile
from app.models.credit_card import CreditCard, CardIssuer
from app.models.goal import Goal

# Import User-related models
from app.models.user import User
from app.models.user_data import UserProfile
from app.models.user_card import UserCard
from app.models.issuer_policy import IssuerPolicy

# Define __all__ to control what gets imported with 'from app.models import *'
__all__ = ['User', 'UserProfile', 'CreditCard', 'CardIssuer', 'Category', 'CreditCardReward', 'Goal', 'UserCard', 'IssuerPolicy'] 