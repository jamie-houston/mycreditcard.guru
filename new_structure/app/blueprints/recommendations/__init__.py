from flask import Blueprint

bp = Blueprint('recommendations', __name__, url_prefix='/recommendations', template_folder='templates')

from app.blueprints.recommendations import routes 