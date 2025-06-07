from flask import Blueprint, render_template, abort, request, redirect, url_for, flash
from app.models.category import Category, CreditCardReward
from app.models.credit_card import CreditCard
from flask_login import login_required, current_user
from sqlalchemy import and_
from app import db
from app.utils.decorators import admin_required

categories = Blueprint('categories', __name__, url_prefix='/categories')

@categories.route('/')
def index():
    """Show list of all active categories."""
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name).all()
    
    # Get rewards data for each category, filtering for active cards only
    category_rewards = {}
    for category in categories:
        # Join CreditCardReward with CreditCard to filter only active cards
        rewards = db.session.query(CreditCardReward).join(
            CreditCard, CreditCardReward.credit_card_id == CreditCard.id
        ).filter(
            CreditCardReward.category_id == category.id,
            CreditCard.is_active == True
        ).all()
        
        # Calculate max reward percentage
        max_reward = 0
        has_rewards = False
        for reward in rewards:
            if reward.reward_percent > max_reward:
                max_reward = reward.reward_percent
                has_rewards = True
        
        category_rewards[category.id] = {
            'max_reward': max_reward,
            'has_rewards': has_rewards
        }
    
    return render_template('categories/index.html', 
                           categories=categories, 
                           category_rewards=category_rewards)

@categories.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Create a new category."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-tag').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        
        if not name or not display_name:
            flash('Name and Display Name are required.', 'danger')
            return redirect(url_for('categories.new'))
        
        # Check for existing category
        existing = Category.query.filter_by(name=name).first()
        if existing:
            flash(f'Category "{name}" already exists.', 'danger')
            return redirect(url_for('categories.new'))
        
        category = Category(
            name=name,
            display_name=display_name,
            description=description,
            icon=icon,
            sort_order=sort_order
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash(f'Category "{display_name}" created successfully!', 'success')
        return redirect(url_for('categories.index'))
    
    return render_template('categories/new.html', category=None)

@categories.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """Edit an existing category."""
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-tag').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        
        if not name or not display_name:
            flash('Name and Display Name are required.', 'danger')
            return redirect(url_for('categories.edit', id=id))
        
        # Check if name changed and if new name already exists
        if name != category.name:
            existing = Category.query.filter_by(name=name).first()
            if existing:
                flash(f'Category with name "{name}" already exists.', 'danger')
                return redirect(url_for('categories.edit', id=id))
        
        # Update category
        category.name = name
        category.display_name = display_name
        category.description = description
        category.icon = icon
        category.sort_order = sort_order
        
        db.session.commit()
        
        flash(f'Category "{display_name}" updated successfully!', 'success')
        return redirect(url_for('categories.show', id=id))
    
    return render_template('categories/edit.html', category=category)

@categories.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    """Delete or deactivate a category."""
    category = Category.query.get_or_404(id)
    
    # Check if category is used by any credit cards
    card_rewards = CreditCardReward.query.filter_by(category_id=id).all()
    
    if card_rewards:
        # Soft delete - just mark as inactive
        category.is_active = False
        db.session.commit()
        flash(f'Category "{category.display_name}" has been deactivated because it is used by credit cards.', 'warning')
    else:
        # Hard delete if not used
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.display_name}" has been deleted.', 'success')
    
    return redirect(url_for('categories.index'))

@categories.route('/<int:id>')
def show(id):
    """Show category details and cards that reward this category."""
    category = Category.query.filter_by(id=id, is_active=True).first_or_404()
    
    # Get cards that reward this category, joined with active cards
    cards_with_rewards = []
    
    # Join query to get only active cards with their rewards for this category
    rewards_query = db.session.query(CreditCardReward, CreditCard).join(
        CreditCard, CreditCardReward.credit_card_id == CreditCard.id
    ).filter(
        CreditCardReward.category_id == id,
        CreditCard.is_active == True
    ).order_by(CreditCardReward.reward_percent.desc()).all()
    
    for reward, card in rewards_query:
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