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
    return render_template('categories/index.html', categories=categories, CreditCardReward=CreditCardReward)

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