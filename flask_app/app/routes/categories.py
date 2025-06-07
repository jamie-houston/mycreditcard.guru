from flask import Blueprint, render_template, abort
from app.models.category import Category, CreditCardReward
from app.models.credit_card import CreditCard
from flask_login import login_required
from sqlalchemy import and_

categories = Blueprint('categories', __name__, url_prefix='/categories')

@categories.route('/')
def index():
    """Show list of all active categories."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name).all()
    return render_template('categories/index.html', categories=categories)

@categories.route('/<int:id>')
def show(id):
    """Show category details and cards that reward this category."""
    category = Category.query.filter_by(id=id, is_active=True).first_or_404()
    
    # Get cards that reward this category, ordered by reward rate
    cards_with_rewards = []
    card_rewards = CreditCardReward.query.filter_by(category_id=id).order_by(CreditCardReward.reward_percent.desc()).all()
    
    for reward in card_rewards:
        card = CreditCard.query.get(reward.credit_card_id)
        if card and card.is_active:
            cards_with_rewards.append({
                'card': card,
                'reward': reward
            })
    
    # Get other active categories for the related categories section
    other_categories = Category.query.filter(
        and_(
            Category.id != id,
            Category.is_active == True
        )
    ).order_by(Category.sort_order).limit(10).all()
    
    return render_template(
        'categories/show.html',
        category=category,
        cards_with_rewards=cards_with_rewards,
        other_categories=other_categories,
        Category=Category  # Pass the Category model to the template
    ) 