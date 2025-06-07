from flask import Blueprint

# Import and register all blueprint routes
from app.routes.main import main
from app.routes.user_data import user_data
from app.routes.credit_cards import credit_cards
from app.routes.categories import categories

# List of all blueprints
all_blueprints = [
    main,
    user_data, 
    credit_cards,
    categories
] 