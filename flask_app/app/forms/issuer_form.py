from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class IssuerForm(FlaskForm):
    name = StringField('Issuer Name', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Save') 