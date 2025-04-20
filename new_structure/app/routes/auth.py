from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse

from app import db
from app.models.user import User
from app.forms.auth_forms import LoginForm, RegistrationForm, ChangePasswordForm

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        user.update_last_login()
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        flash('You have been logged in successfully!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created successfully! You can now login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)


@auth.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/profile')
@login_required
def profile():
    """Display user profile."""
    return render_template('auth/profile.html', title='Profile')


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change."""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', title='Change Password', form=form) 