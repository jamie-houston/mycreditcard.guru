from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.credit_card import CreditCard
from app.models.category import Category
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
    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash('Cannot remove the last admin user!', 'danger')
        return redirect(url_for('admin.users'))
    
    # Prevent removing your own admin privileges
    if user.id == current_user.id:
        flash('You cannot change your own admin status!', 'danger')
        return redirect(url_for('admin.users'))
    
    user.is_admin = not user.is_admin
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
    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash('Cannot delete the last admin user!', 'danger')
        return redirect(url_for('admin.users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been deleted', 'success')
    return redirect(url_for('admin.users')) 