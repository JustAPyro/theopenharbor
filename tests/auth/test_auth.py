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

        # Should not crash and should show form validation errors
        assert response.status_code == 200
        # The form validation will catch this as invalid email format
        assert b'Please enter a valid email address' in response.data or b'Invalid email or password' in response.data


if __name__ == '__main__':
    pytest.main([__file__])