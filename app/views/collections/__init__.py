from flask import Blueprint

collections = Blueprint('collections', __name__,
                       template_folder='templates',
                       static_folder='static')

from app.views.collections import collections_routes