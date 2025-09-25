import os
import logging
from flask import Flask
from flask_login import LoginManager

# Import configuration classes
from config import config

logger = logging.getLogger(__name__)


def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    config_class = config[config_name]
    app.config.from_object(config_class)

    # Validate required configuration
    try:
        config_class.validate_required_config()
    except ValueError as e:
        if not app.config.get('TESTING'):
            raise RuntimeError(f"Configuration error: {str(e)}")

    # Initialize R2 Storage
    try:
        if app.config.get('STORAGE_BACKEND') == 'r2':
            from app.integrations.file_storage import CloudflareR2Storage, FileStorageError
            app.r2_storage = CloudflareR2Storage()
            logger.info("CloudflareR2 storage initialized successfully")
        else:
            app.r2_storage = None
            logger.info("Using local storage backend")
    except Exception as e:
        logger.error(f"Failed to initialize R2 storage: {e}")
        if not app.config.get('TESTING'):
            raise RuntimeError(f"R2 storage initialization failed: {e}")

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

    
