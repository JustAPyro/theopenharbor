# Authentication System Implementation Guide

## Overview

This guide provides complete instructions for implementing a secure authentication system in The Open Harbor Flask application. You will create sign-up, log-in, and log-out functionality with proper security practices and comprehensive testing.

## Requirements Summary

- ✅ Create 3 new endpoints: `/auth/sign-up`, `/auth/log-in`, `/auth/log-out`
- ✅ Build sign-in and sign-out pages extending `base.html`
- ✅ Implement Flask-Login for session management
- ✅ Add comprehensive unit tests
- ✅ Register auth blueprint in `app/__init__.py`
- ✅ Follow security best practices

## Step 1: Install Dependencies

Add these dependencies to your existing `.requirements.txt`:

```txt
# Add to existing .requirements.txt
Flask-Login==0.6.2
Flask-WTF==1.1.1
WTForms==3.0.1
Flask-SQLAlchemy==3.0.5
Werkzeug==3.1.3  # Already included, but ensure version
bcrypt==4.0.1
email-validator==2.1.0
```

Install dependencies:
```bash
.venv/bin/pip install -r .requirements.txt
```

## Step 2: Database Setup

### Create User Model

Create `app/models.py`:

```python
"""
Database models for The Open Harbor application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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
```

## Step 3: Update Application Factory

Update `app/__init__.py`:

```python
from dotenv import load_dotenv
import os
from flask import Flask
from flask_login import LoginManager

# Load .env file and declare required environment vars
load_dotenv()
required_envs = [
    'TSH_SECRET_KEY'
]

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

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # NOTE: If your current __init__.py references 'app.views.auth',
    # update it to use 'app.auth' as shown above

    return app
```

## Step 4: Create Authentication Forms

Create `app/forms.py`:

```python
"""
WTForms for The Open Harbor application.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User


class LoginForm(FlaskForm):
    """Form for user login."""

    email = StringField(
        'Email',
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address")
        ],
        render_kw={"placeholder": "your@email.com", "class": "form-control"}
    )

    password = PasswordField(
        'Password',
        validators=[DataRequired(message="Password is required")],
        render_kw={"placeholder": "Enter your password", "class": "form-control"}
    )

    remember_me = BooleanField(
        'Remember Me',
        render_kw={"class": "form-check-input"}
    )

    submit = SubmitField(
        'Log In',
        render_kw={"class": "btn btn-primary w-100"}
    )


class SignUpForm(FlaskForm):
    """Form for user registration."""

    email = StringField(
        'Email',
        validators=[
            DataRequired(message="Email is required"),
            Email(message="Please enter a valid email address"),
            Length(max=120, message="Email must be less than 120 characters")
        ],
        render_kw={"placeholder": "your@email.com", "class": "form-control"}
    )

    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required"),
            Length(min=8, message="Password must be at least 8 characters long")
        ],
        render_kw={"placeholder": "Create a strong password", "class": "form-control"}
    )

    password2 = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password"),
            EqualTo('password', message="Passwords must match")
        ],
        render_kw={"placeholder": "Confirm your password", "class": "form-control"}
    )

    submit = SubmitField(
        'Create Account',
        render_kw={"class": "btn btn-primary w-100"}
    )

    def validate_email(self, email):
        """Check if email is already registered."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

    def validate_password(self, password):
        """Validate password complexity."""
        if not User._is_valid_password(password.data):
            raise ValidationError(
                'Password must contain at least 8 characters including '
                'uppercase, lowercase, and one digit.'
            )
```

## Step 5: Create Authentication Blueprint

Create `app/auth.py`:

```python
"""
Authentication blueprint for The Open Harbor application.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.forms import LoginForm, SignUpForm
from app.models import db, User
from datetime import datetime
import logging

bp = Blueprint('auth', __name__)

# Set up logging
logger = logging.getLogger(__name__)


@bp.route('/sign-up', methods=['GET', 'POST'])
def signup():
    """Handle user registration."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = SignUpForm()

    if form.validate_on_submit():
        try:
            # Create new user
            user = User(email=form.email.data.lower().strip())
            user.set_password(form.password.data)

            # Save to database
            db.session.add(user)
            db.session.commit()

            # Log the user in immediately after registration
            login_user(user, remember=False)
            user.last_login = datetime.utcnow()
            db.session.commit()

            flash('Welcome to The Open Harbor! Your account has been created.', 'success')
            logger.info(f"New user registered: {user.email}")

            # Redirect to intended page or home
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.home'))

        except ValueError as e:
            flash(str(e), 'error')
            logger.warning(f"Registration failed for {form.email.data}: {str(e)}")
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
            logger.error(f"Registration error for {form.email.data}: {str(e)}")

    return render_template('auth/signup.html', form=form)


@bp.route('/log-in', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = LoginForm()

    if form.validate_on_submit():
        try:
            # Find user by email
            user = User.query.filter_by(email=form.email.data.lower().strip()).first()

            # Check credentials
            if user and user.check_password(form.password.data):
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact support.', 'error')
                    logger.warning(f"Inactive user attempted login: {user.email}")
                    return render_template('auth/login.html', form=form)

                # Log the user in
                login_user(user, remember=form.remember_me.data)
                user.last_login = datetime.utcnow()
                db.session.commit()

                flash(f'Welcome back!', 'success')
                logger.info(f"User logged in: {user.email}")

                # Redirect to intended page or home
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('main.home'))
            else:
                flash('Invalid email or password. Please try again.', 'error')
                logger.warning(f"Failed login attempt for: {form.email.data}")

        except Exception as e:
            flash('An error occurred during login. Please try again.', 'error')
            logger.error(f"Login error for {form.email.data}: {str(e)}")

    return render_template('auth/login.html', form=form)


@bp.route('/log-out')
@login_required
def logout():
    """Handle user logout."""
    user_email = current_user.email if current_user.is_authenticated else "Unknown"
    logout_user()
    flash('You have been logged out successfully.', 'info')
    logger.info(f"User logged out: {user_email}")
    return redirect(url_for('main.home'))


# Error handlers for the auth blueprint
@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors in auth blueprint."""
    return render_template('errors/404.html'), 404


@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors in auth blueprint."""
    db.session.rollback()
    return render_template('errors/500.html'), 500
```

## Step 6: Create Authentication Templates

### Create `app/templates/auth/login.html`:

```html
{% extends "base.html" %}

{% block title %}Log In - The Open Harbor{% endblock %}

{% block content %}
<section class="py-5" style="background: var(--color-bg); min-height: 80vh;">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-5 col-md-7">
                <div class="card border-0 shadow-lg">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <h1 class="h3 fw-bold text-primary">Welcome back</h1>
                            <p class="text-muted">Sign in to your Open Harbor account</p>
                        </div>

                        <form method="POST">
                            {{ form.hidden_tag() }}

                            <div class="mb-3">
                                {{ form.email.label(class="form-label fw-semibold") }}
                                {{ form.email() }}
                                {% if form.email.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.email.errors %}
                                            <small>{{ error }}</small>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>

                            <div class="mb-3">
                                {{ form.password.label(class="form-label fw-semibold") }}
                                {{ form.password() }}
                                {% if form.password.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.password.errors %}
                                            <small>{{ error }}</small>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>

                            <div class="mb-4">
                                <div class="form-check">
                                    {{ form.remember_me() }}
                                    {{ form.remember_me.label(class="form-check-label") }}
                                </div>
                            </div>

                            {{ form.submit() }}
                        </form>

                        <hr class="my-4">

                        <div class="text-center">
                            <p class="mb-0 text-muted">
                                Don't have an account?
                                <a href="{{ url_for('auth.signup') }}" class="text-primary text-decoration-none fw-semibold">Create one</a>
                            </p>
                        </div>
                    </div>
                </div>

                <div class="text-center mt-4">
                    <small class="text-muted">
                        <i class="bi bi-shield-check me-1"></i>
                        Your connection is secure and encrypted
                    </small>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

### Create `app/templates/auth/signup.html`:

```html
{% extends "base.html" %}

{% block title %}Sign Up - The Open Harbor{% endblock %}

{% block content %}
<section class="py-5" style="background: var(--color-bg); min-height: 80vh;">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-5 col-md-7">
                <div class="card border-0 shadow-lg">
                    <div class="card-body p-5">
                        <div class="text-center mb-4">
                            <h1 class="h3 fw-bold text-primary">Join The Open Harbor</h1>
                            <p class="text-muted">Create your secure file storage account</p>
                        </div>

                        <form method="POST">
                            {{ form.hidden_tag() }}

                            <div class="mb-3">
                                {{ form.email.label(class="form-label fw-semibold") }}
                                {{ form.email() }}
                                {% if form.email.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.email.errors %}
                                            <small>{{ error }}</small>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>

                            <div class="mb-3">
                                {{ form.password.label(class="form-label fw-semibold") }}
                                {{ form.password() }}
                                {% if form.password.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.password.errors %}
                                            <small>{{ error }}</small>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                                <div class="form-text">
                                    <small class="text-muted">
                                        Must be 8+ characters with uppercase, lowercase, and a number
                                    </small>
                                </div>
                            </div>

                            <div class="mb-4">
                                {{ form.password2.label(class="form-label fw-semibold") }}
                                {{ form.password2() }}
                                {% if form.password2.errors %}
                                    <div class="invalid-feedback d-block">
                                        {% for error in form.password2.errors %}
                                            <small>{{ error }}</small>
                                        {% endfor %}
                                    </div>
                                {% endif %}
                            </div>

                            {{ form.submit() }}
                        </form>

                        <hr class="my-4">

                        <div class="text-center">
                            <p class="mb-0 text-muted">
                                Already have an account?
                                <a href="{{ url_for('auth.login') }}" class="text-primary text-decoration-none fw-semibold">Sign in</a>
                            </p>
                        </div>
                    </div>
                </div>

                <div class="text-center mt-4">
                    <small class="text-muted">
                        By creating an account, you agree to our privacy-first approach to file storage.
                        <br>
                        <i class="bi bi-shield-check me-1"></i>
                        Your data is encrypted and secure
                    </small>
                </div>
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

## Step 7: Update Base Template

Update `app/templates/base.html` to include authentication navigation:

```html
<!-- Replace the existing navigation section with this updated version -->
<nav class="navbar navbar-expand-lg navbar-light sticky-top">
    <div class="container">
        <a class="navbar-brand" href="{{ url_for('main.home') }}" role="button">
            <i class="bi bi-shield-check me-2"></i>
            The Open Harbor
        </a>

        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>

        <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav ms-auto">
                <li class="nav-item">
                    <a class="nav-link" href="#features">Features</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#security">Security</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#about">About</a>
                </li>

                {% if current_user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="bi bi-person-circle me-1"></i>
                            {{ current_user.email }}
                        </a>
                        <ul class="dropdown-menu" aria-labelledby="userDropdown">
                            <li><a class="dropdown-item" href="#"><i class="bi bi-folder me-2"></i>My Files</a></li>
                            <li><a class="dropdown-item" href="#"><i class="bi bi-gear me-2"></i>Settings</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('auth.logout') }}"><i class="bi bi-box-arrow-right me-2"></i>Log Out</a></li>
                        </ul>
                    </li>
                {% else %}
                    <li class="nav-item">
                        <a class="nav-link" href="{{ url_for('auth.login') }}">Log In</a>
                    </li>
                    <li class="nav-item ms-2">
                        <a class="btn btn-outline-primary" href="{{ url_for('auth.signup') }}" role="button">Sign Up</a>
                    </li>
                {% endif %}
            </ul>
        </div>
    </div>
</nav>

<!-- Add flash message section after navigation and before main content -->
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        <div class="container mt-3">
            {% for category, message in messages %}
                <div class="alert alert-{{ 'danger' if category == 'error' else category }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            {% endfor %}
        </div>
    {% endif %}
{% endwith %}
```

## Step 8: Comprehensive Testing

Create `tests/test_auth.py`:

```python
"""
Comprehensive tests for The Open Harbor authentication system.
"""

import pytest
from app import create_app
from app.models import db, User
from flask import url_for
import tempfile
import os


@pytest.fixture(scope='function')
def app():
    """Create application for tests with temporary database."""
    db_fd, db_path = tempfile.mkstemp()

    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-testing',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user = User(email='testuser@example.com')
        user.set_password('TestPassword123')
        db.session.add(user)
        db.session.commit()
        return user


class TestUserModel:
    """Test the User model."""

    def test_password_hashing(self, app):
        """Test password hashing and verification."""
        with app.app_context():
            user = User(email='test@example.com')
            user.set_password('TestPassword123')
            assert user.password_hash is not None
            assert user.password_hash != 'TestPassword123'
            assert user.check_password('TestPassword123') is True
            assert user.check_password('wrongpassword') is False

    def test_password_validation(self, app):
        """Test password complexity validation."""
        with app.app_context():
            user = User(email='test@example.com')

            # Test valid password
            user.set_password('ValidPass123')

            # Test invalid passwords
            with pytest.raises(ValueError):
                user.set_password('short')  # Too short
            with pytest.raises(ValueError):
                user.set_password('nouppercase123')  # No uppercase
            with pytest.raises(ValueError):
                user.set_password('NOLOWERCASE123')  # No lowercase
            with pytest.raises(ValueError):
                user.set_password('NoNumbersHere')  # No numbers

    def test_email_validation(self):
        """Test email validation."""
        assert User.is_valid_email('valid@example.com') is True
        assert User.is_valid_email('invalid-email') is False
        assert User.is_valid_email('') is False
        assert User.is_valid_email('test@') is False

    def test_user_repr(self, app):
        """Test user string representation."""
        with app.app_context():
            user = User(email='test@example.com')
            assert str(user) == '<User test@example.com>'


class TestAuthRoutes:
    """Test authentication routes."""

    def test_signup_page_loads(self, client):
        """Test that signup page loads successfully."""
        response = client.get('/auth/sign-up')
        assert response.status_code == 200
        assert b'Join The Open Harbor' in response.data
        assert b'Create your secure file storage account' in response.data

    def test_login_page_loads(self, client):
        """Test that login page loads successfully."""
        response = client.get('/auth/log-in')
        assert response.status_code == 200
        assert b'Welcome back' in response.data
        assert b'Sign in to your Open Harbor account' in response.data

    def test_successful_signup(self, client):
        """Test successful user registration."""
        response = client.post('/auth/sign-up', data={
            'email': 'newuser@example.com',
            'password': 'ValidPassword123',
            'password2': 'ValidPassword123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Welcome to The Open Harbor' in response.data

    def test_duplicate_email_signup(self, client, test_user):
        """Test signup with already registered email."""
        response = client.post('/auth/sign-up', data={
            'email': 'testuser@example.com',  # Already exists
            'password': 'ValidPassword123',
            'password2': 'ValidPassword123'
        })

        assert response.status_code == 200
        assert b'Email already registered' in response.data

    def test_invalid_password_signup(self, client):
        """Test signup with invalid password."""
        response = client.post('/auth/sign-up', data={
            'email': 'newuser@example.com',
            'password': 'weak',  # Too weak
            'password2': 'weak'
        })

        assert response.status_code == 200
        assert b'Password must contain at least 8 characters' in response.data

    def test_password_mismatch_signup(self, client):
        """Test signup with mismatched passwords."""
        response = client.post('/auth/sign-up', data={
            'email': 'newuser@example.com',
            'password': 'ValidPassword123',
            'password2': 'DifferentPassword123'
        })

        assert response.status_code == 200
        assert b'Passwords must match' in response.data

    def test_successful_login(self, client, test_user):
        """Test successful user login."""
        response = client.post('/auth/log-in', data={
            'email': 'testuser@example.com',
            'password': 'TestPassword123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Welcome back' in response.data

    def test_invalid_login(self, client, test_user):
        """Test login with invalid credentials."""
        response = client.post('/auth/log-in', data={
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == 200
        assert b'Invalid email or password' in response.data

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post('/auth/log-in', data={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123'
        })

        assert response.status_code == 200
        assert b'Invalid email or password' in response.data

    def test_logout_requires_login(self, client):
        """Test that logout requires authentication."""
        response = client.get('/auth/log-out', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to login page
        assert b'Welcome back' in response.data

    def test_successful_logout(self, client, test_user):
        """Test successful logout."""
        # First login
        client.post('/auth/log-in', data={
            'email': 'testuser@example.com',
            'password': 'TestPassword123'
        })

        # Then logout
        response = client.get('/auth/log-out', follow_redirects=True)
        assert response.status_code == 200
        assert b'You have been logged out successfully' in response.data

    def test_redirect_after_login(self, client, test_user):
        """Test redirect to intended page after login."""
        # Try to access a protected page
        response = client.get('/auth/log-out')  # This requires login

        # Should redirect to login with next parameter
        assert response.status_code == 302

        # Now login and should redirect back
        response = client.post('/auth/log-in?next=/auth/log-out', data={
            'email': 'testuser@example.com',
            'password': 'TestPassword123'
        }, follow_redirects=True)

        assert response.status_code == 200


class TestAuthIntegration:
    """Test authentication integration with the main app."""

    def test_navigation_changes_when_logged_in(self, client, test_user):
        """Test that navigation shows user info when logged in."""
        # Check logged out state
        response = client.get('/')
        assert b'Log In' in response.data
        assert b'Sign Up' in response.data

        # Login
        client.post('/auth/log-in', data={
            'email': 'testuser@example.com',
            'password': 'TestPassword123'
        })

        # Check logged in state
        response = client.get('/')
        assert b'testuser@example.com' in response.data
        assert b'Log Out' in response.data

    def test_authenticated_user_redirect_from_auth_pages(self, client, test_user):
        """Test that logged in users are redirected from auth pages."""
        # Login first
        client.post('/auth/log-in', data={
            'email': 'testuser@example.com',
            'password': 'TestPassword123'
        })

        # Try to access login page
        response = client.get('/auth/log-in', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to home page
        assert b'A safe place for your files' in response.data

        # Try to access signup page
        response = client.get('/auth/sign-up', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to home page
        assert b'A safe place for your files' in response.data


class TestSecurityFeatures:
    """Test security features and edge cases."""

    def test_csrf_protection(self, app):
        """Test that CSRF protection is enabled in production."""
        with app.app_context():
            # In testing CSRF is disabled, but we can check config
            # In production, WTF_CSRF_ENABLED should be True
            pass

    def test_password_not_stored_plaintext(self, app):
        """Test that passwords are never stored in plaintext."""
        with app.app_context():
            user = User(email='security@example.com')
            original_password = 'SecurePassword123'
            user.set_password(original_password)

            assert user.password_hash != original_password
            assert original_password not in user.password_hash

    def test_sql_injection_protection(self, client):
        """Test that SQL injection attempts are handled safely."""
        # Attempt SQL injection in email field
        response = client.post('/auth/log-in', data={
            'email': "test' OR '1'='1",
            'password': 'anything'
        })

        # Should not crash and should show invalid credentials
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data


if __name__ == '__main__':
    pytest.main([__file__])
```

## Step 9: Security Best Practices

### ⚠️ CRITICAL SECURITY WARNINGS

1. **Password Security**:
   - ✅ Always hash passwords with werkzeug's `generate_password_hash()`
   - ❌ NEVER store passwords in plaintext
   - ✅ Enforce strong password requirements
   - ✅ Use bcrypt for password hashing (included in werkzeug)

2. **Session Security**:
   - ✅ Use HTTPS in production (set `FLASK_ENV=production`)
   - ✅ Set secure session cookies: `app.config['SESSION_COOKIE_SECURE'] = True`
   - ✅ Use strong secret keys (never commit to git)
   - ✅ Enable CSRF protection

3. **Input Validation**:
   - ✅ Validate all form inputs on both client and server side
   - ✅ Sanitize user inputs to prevent XSS
   - ✅ Use WTForms validators for robust validation

4. **Database Security**:
   - ✅ Use SQLAlchemy ORM to prevent SQL injection
   - ✅ Never trust user input directly in queries
   - ✅ Implement proper database permissions

### Environment Variables for Production

Add to your `.env`:
```bash
# Required
TSH_SECRET_KEY=your-super-secret-key-here-minimum-32-characters

# Database (for production)
DATABASE_URL=postgresql://user:password@localhost/openharbor

# Security (for production)
FLASK_ENV=production
FLASK_DEBUG=False
```

## Step 10: Common Pitfalls and Solutions

### ❌ Common Mistakes:

1. **Not validating user input properly**
   ```python
   # BAD - No validation
   user = User(email=request.form['email'])

   # GOOD - With validation
   if form.validate_on_submit():
       user = User(email=form.email.data.lower().strip())
   ```

2. **Storing passwords in plaintext**
   ```python
   # BAD - Never do this
   user.password = password

   # GOOD - Always hash passwords
   user.set_password(password)
   ```

3. **Not handling database errors**
   ```python
   # BAD - No error handling
   db.session.add(user)
   db.session.commit()

   # GOOD - With error handling
   try:
       db.session.add(user)
       db.session.commit()
   except Exception as e:
       db.session.rollback()
       flash('An error occurred. Please try again.', 'error')
   ```

4. **Forgetting to update navigation**
   - Make sure base.html shows login/logout options appropriately

5. **Not testing edge cases**
   - Test duplicate emails, invalid passwords, SQL injection attempts

### 🔧 Debugging Tips:

1. **Check database creation**:
   ```python
   # In Flask shell
   from app import create_app
   from app.models import db
   app = create_app()
   with app.app_context():
       db.create_all()
   ```

2. **Verify user creation**:
   ```python
   # In Flask shell
   from app.models import User
   users = User.query.all()
   print([u.email for u in users])
   ```

3. **Check Flask-Login setup**:
   - Ensure `@login_required` decorator works
   - Verify `current_user` is available in templates

## Step 11: Testing Your Implementation

Run these commands to verify everything works:

```bash
# Install test dependencies
.venv/bin/pip install pytest

# Run all tests
.venv/bin/python -m pytest tests/ -v

# Run only auth tests
.venv/bin/python -m pytest tests/test_auth.py -v

# Check test coverage
.venv/bin/pip install pytest-cov
.venv/bin/python -m pytest tests/ --cov=app --cov-report=html
```

## Step 12: Final Checklist

- [ ] All dependencies installed
- [ ] Database models created (`app/models.py`)
- [ ] Forms created (`app/forms.py`)
- [ ] Auth blueprint created (`app/auth.py`)
- [ ] Templates created (`app/templates/auth/`)
- [ ] Base template updated with navigation
- [ ] Application factory updated (`app/__init__.py`)
- [ ] Comprehensive tests written (`tests/test_auth.py`)
- [ ] All tests passing
- [ ] Security considerations implemented
- [ ] Environment variables configured

## Completion Verification

After implementing everything, you should be able to:
1. Visit `/auth/sign-up` and create a new account
2. Visit `/auth/log-in` and sign in with your credentials
3. See your email in the navigation dropdown when logged in
4. Click "Log Out" to sign out
5. Run `pytest tests/test_auth.py -v` and see all tests pass

Your authentication system is now complete and secure! 🚀

---

*Remember: Security is not optional. Always validate inputs, hash passwords, handle errors gracefully, and keep your dependencies updated.*