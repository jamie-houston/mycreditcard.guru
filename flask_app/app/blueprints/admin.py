from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.credit_card import CreditCard
from app.models.category import Category, CreditCardReward
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@admin_required
def before_request():
    """Ensure all admin routes are protected by admin privileges."""
    pass

@admin_bp.route('/')
def dashboard():
    """Admin dashboard showing key metrics."""
    user_count = User.query.count()
    card_count = CreditCard.query.count()
    category_count = Category.query.count()
    
    # Get the most recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template(
        'admin/dashboard.html',
        user_count=user_count,
        card_count=card_count,
        category_count=category_count,
        recent_users=recent_users
    )

@admin_bp.route('/users')
def users():
    """List all users."""
    users = User.query.order_by(User.username).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:id>/toggle_admin', methods=['POST'])
def toggle_admin(id):
    """Toggle admin status for a user."""
    user = User.query.get_or_404(id)
    
    # Prevent removing the last admin
    if user.is_admin and User.query.filter_by(role=1).count() <= 1:
        flash('Cannot remove the last admin user!', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent removing your own admin privileges
    if user.id == current_user.id:
        flash('You cannot change your own admin status!', 'danger')
        return redirect(url_for('admin.users'))
    
    user.role = 0 if user.is_admin else 1
    db.session.commit()
    
    action = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {action} for {user.username}', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
def delete_user(id):
    """Delete a user account."""
    user = User.query.get_or_404(id)
    
    # Prevent deleting your own account through admin panel
    if user.id == current_user.id:
        flash('You cannot delete your own account here!', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent deleting the last admin
    if user.is_admin and User.query.filter_by(role=1).count() <= 1:
        flash('Cannot delete the last admin user!', 'danger')
        return redirect(url_for('admin.users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been deleted', 'success')
    return redirect(url_for('admin.users'))

# Category Management Routes

@admin_bp.route('/categories')
def categories():
    """List all categories."""
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/new', methods=['GET', 'POST'])
def category_new():
    """Create a new category."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-tag').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        
        if not name or not display_name:
            flash('Name and Display Name are required.', 'danger')
            return redirect(url_for('admin.category_new'))
        
        # Check for existing category
        existing = Category.query.filter_by(name=name).first()
        if existing:
            flash(f'Category "{name}" already exists.', 'danger')
            return redirect(url_for('admin.category_new'))
        
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
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/category_form.html', category=None, title='New Category')

@admin_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
def category_edit(id):
    """Edit an existing category."""
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'fas fa-tag').strip()
        sort_order = request.form.get('sort_order', 0, type=int)
        is_active = 'is_active' in request.form
        
        if not name or not display_name:
            flash('Name and Display Name are required.', 'danger')
            return redirect(url_for('admin.category_edit', id=id))
        
        # Check for existing category (excluding current one)
        existing = Category.query.filter(Category.name == name, Category.id != id).first()
        if existing:
            flash(f'Category "{name}" already exists.', 'danger')
            return redirect(url_for('admin.category_edit', id=id))
        
        category.name = name
        category.display_name = display_name
        category.description = description
        category.icon = icon
        category.sort_order = sort_order
        category.is_active = is_active
        
        db.session.commit()
        
        flash(f'Category "{display_name}" updated successfully!', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/category_form.html', category=category, title='Edit Category')

@admin_bp.route('/categories/<int:id>/delete', methods=['POST'])
def category_delete(id):
    """Delete a category."""
    category = Category.query.get_or_404(id)
    
    # Check if category is being used by credit cards
    reward_count = CreditCardReward.query.filter_by(category_id=id).count()
    if reward_count > 0:
        flash(f'Cannot delete category "{category.display_name}" - it is being used by {reward_count} credit card reward(s).', 'danger')
        return redirect(url_for('admin.categories'))
    
    # Check if category is being used by spending profiles
    from app.models.user_profile import SpendingCategory
    spending_count = SpendingCategory.query.filter_by(category_id=id).count()
    if spending_count > 0:
        flash(f'Cannot delete category "{category.display_name}" - it is being used by {spending_count} spending profile(s).', 'danger')
        return redirect(url_for('admin.categories'))
    
    category_name = category.display_name
    db.session.delete(category)
    db.session.commit()
    
    flash(f'Category "{category_name}" deleted successfully!', 'success')
    return redirect(url_for('admin.categories'))

@admin_bp.route('/categories/<int:id>/toggle', methods=['POST'])
def category_toggle(id):
    """Toggle category active status."""
    category = Category.query.get_or_404(id)
    
    category.is_active = not category.is_active
    db.session.commit()
    
    status = 'activated' if category.is_active else 'deactivated'
    flash(f'Category "{category.display_name}" {status} successfully!', 'success')
    return redirect(url_for('admin.categories'))

@admin_bp.route('/categories/<int:id>')
def category_detail(id):
    """Show detailed information about a category."""
    category = Category.query.get_or_404(id)
    
    # Get cards that use this category
    cards_with_category = CreditCard.query.join(
        CreditCardReward, CreditCard.id == CreditCardReward.credit_card_id
    ).filter(
        CreditCardReward.category_id == id
    ).order_by(
        CreditCardReward.reward_percent.desc()
    ).all()
    
    # Get rewards for each card
    cards_with_rewards = []
    for card in cards_with_category:
        reward = card.rewards.filter_by(category_id=id).first()
        if reward:
            cards_with_rewards.append({
                'card': card,
                'reward': reward
            })
    
    return render_template(
        'admin/category_detail.html',
        category=category,
        cards_with_rewards=cards_with_rewards
    )

@admin_bp.route('/api/categories')
def api_categories():
    """API endpoint to get all active categories (for AJAX calls)."""
    categories = Category.get_active_categories()
    return jsonify([category.to_dict() for category in categories]) 