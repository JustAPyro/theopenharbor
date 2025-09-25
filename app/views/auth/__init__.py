from flask import Blueprint

auth = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')

from . import auth_routes  # Import routes after blueprint is defined
