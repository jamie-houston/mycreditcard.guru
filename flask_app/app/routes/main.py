from flask import Blueprint, render_template, redirect, url_for

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Landing page of the application."""
    return render_template('index.html', title='Credit Card Roadmap') 