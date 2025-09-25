from dotenv import load_dotenv
import os
from flask import Flask
from flask_login import LoginManager
from app.integrations.file_storage import required_envs as file_storage_envs

# Load .env file and declare required environment vars
load_dotenv()
required_envs = [
    'TSH_SECRET_KEY'
]
required_envs += file_storage_envs

# Verify required environment variables
missing = []
for env in required_envs:
    if os.getenv(env) == None:
        missing.append(env)

# If any are missing raise an error
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def create_app(config_name=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('TSH_SECRET_KEY')

    # Database configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///openharbor.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Security configurations
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # No time limit for CSRF tokens

    # Initialize extensions
    from app.models import db
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Create tables
    with app.app_context():
        db.create_all()

    # Register blueprints
    from app.routes import app as main_routes
    app.register_blueprint(main_routes)

    from app.views.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.views.collections import collections as collections_bp
    app.register_blueprint(collections_bp, url_prefix='/collections')

    return app

    
