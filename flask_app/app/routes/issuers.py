from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import CardIssuer, CreditCard
from app.forms.issuer_form import IssuerForm

issuers = Blueprint('issuers', __name__)

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('issuers.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@issuers.route('/')
def index():
    issuers = CardIssuer.all_ordered()
    return render_template('issuers/index.html', issuers=issuers)

@issuers.route('/<int:issuer_id>')
def show(issuer_id):
    issuer = CardIssuer.query.get_or_404(issuer_id)
    cards = CreditCard.query.filter_by(issuer_id=issuer.id).all()
    return render_template('issuers/show.html', issuer=issuer, cards=cards)

@issuers.route('/new', methods=['GET', 'POST'])
@admin_required
def new():
    form = IssuerForm()
    if form.validate_on_submit():
        if CardIssuer.query.filter_by(name=form.name.data).first():
            flash('Issuer already exists.', 'danger')
            return render_template('issuers/form.html', form=form, form_action=url_for('issuers.new'))
        issuer = CardIssuer(name=form.name.data)
        db.session.add(issuer)
        db.session.commit()
        flash('Issuer created.', 'success')
        return redirect(url_for('issuers.index'))
    return render_template('issuers/form.html', form=form, form_action=url_for('issuers.new'))

@issuers.route('/<int:issuer_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(issuer_id):
    issuer = CardIssuer.query.get_or_404(issuer_id)
    form = IssuerForm(obj=issuer)
    if form.validate_on_submit():
        if CardIssuer.query.filter(CardIssuer.name == form.name.data, CardIssuer.id != issuer.id).first():
            flash('Another issuer with that name already exists.', 'danger')
            return render_template('issuers/form.html', form=form, form_action=url_for('issuers.edit', issuer_id=issuer.id))
        issuer.name = form.name.data
        db.session.commit()
        flash('Issuer updated.', 'success')
        return redirect(url_for('issuers.show', issuer_id=issuer.id))
    return render_template('issuers/form.html', form=form, form_action=url_for('issuers.edit', issuer_id=issuer.id))

@issuers.route('/<int:issuer_id>/delete', methods=['POST'])
@admin_required
def delete(issuer_id):
    issuer = CardIssuer.query.get_or_404(issuer_id)
    db.session.delete(issuer)
    db.session.commit()
    flash('Issuer deleted.', 'success')
    return redirect(url_for('issuers.index')) 