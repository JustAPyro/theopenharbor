"""
Database models for The Open Harbor application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import re
import uuid

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hash and set the user's password."""
        if not self._is_valid_password(password):
            raise ValueError("Password does not meet security requirements")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def _is_valid_password(password):
        """
        Validate password meets security requirements.
        - At least 8 characters
        - Contains uppercase and lowercase letters
        - Contains at least one digit
        """
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        return True

    @staticmethod
    def is_valid_email(email):
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def get_id(self):
        """Return the user ID as required by Flask-Login."""
        return str(self.id)

    @property
    def is_authenticated(self):
        """Return True if the user is authenticated."""
        return True

    @property
    def is_anonymous(self):
        """Return False as this is not an anonymous user."""
        return False

    # Relationship to collections
    collections = db.relationship('Collection', backref='user', lazy=True, cascade='all, delete-orphan')


class Collection(db.Model):
    """Collection model for file groups."""

    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    privacy = db.Column(db.String(20), default='unlisted', nullable=False)  # public, unlisted, password
    password_hash = db.Column(db.String(255))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Foreign key to user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationship to files
    files = db.relationship('File', backref='collection', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Collection {self.name}>'

    @property
    def file_count(self):
        """Return the number of files in this collection."""
        return len(self.files)

    @property
    def total_size(self):
        """Return the total size of all files in bytes."""
        return sum(file.size for file in self.files)

    def set_password(self, password):
        """Set password for password-protected collections."""
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            self.password_hash = None

    def check_password(self, password):
        """Check password for password-protected collections."""
        if not self.password_hash:
            return True
        return check_password_hash(self.password_hash, password)


class File(db.Model):
    """File model for uploaded files."""

    __tablename__ = 'files'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False)  # Size in bytes
    storage_path = db.Column(db.String(500), nullable=False)  # Path in R2 storage
    thumbnail_path = db.Column(db.String(500))  # Path to thumbnail if generated
    upload_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Foreign key to collection
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=False)

    def __repr__(self):
        return f'<File {self.original_filename}>'

    @property
    def size_human(self):
        """Return human readable file size."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 * 1024 * 1024:
            return f"{self.size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size / (1024 * 1024 * 1024):.1f} GB"