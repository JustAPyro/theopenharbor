"""
Configuration module for The Open Harbor application.
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """Base configuration class."""

    # Flask configuration
    SECRET_KEY = os.environ.get('TSH_SECRET_KEY')

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///openharbor.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security configurations
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    # Storage Configuration
    STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local')

    # R2 Configuration
    R2_ACCOUNT_ID = os.environ.get('TOH_R2_ACCOUNT_ID')
    R2_ACCESS_KEY_ID = os.environ.get('TOH_R2_ACCESS_KEY')
    R2_SECRET_ACCESS_KEY = os.environ.get('TOH_R2_SECRET_KEY')
    R2_BUCKET_NAME = os.environ.get('TOH_R2_BUCKET_NAME')
    R2_REGION = os.environ.get('TOH_R2_REGION', 'auto')

    # File Upload Limits (matching R2 integration)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
    MAX_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10GB per collection
    MAX_BATCH_FILES = 100  # For batch operations

    @staticmethod
    def validate_required_config():
        """Validate that required configuration is present."""
        required_vars = ['SECRET_KEY']

        if Config.STORAGE_BACKEND == 'r2':
            required_vars.extend([
                'R2_ACCOUNT_ID', 'R2_ACCESS_KEY_ID',
                'R2_SECRET_ACCESS_KEY', 'R2_BUCKET_NAME'
            ])

        missing = [var for var in required_vars if not getattr(Config, var)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}