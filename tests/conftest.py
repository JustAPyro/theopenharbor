"""
Test configuration and shared fixtures for The Open Harbor test suite.
"""

import os
import pytest
import tempfile
from app import create_app


@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    # Create a temporary file for the test database
    db_fd, db_path = tempfile.mkstemp()

    app = create_app()
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
    })

    # Create the app context
    ctx = app.app_context()
    ctx.push()

    # Import and create tables
    from app.models import db
    db.create_all()

    yield app

    # Cleanup
    ctx.pop()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='session')
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture(scope='session')
def runner(app):
    """Create a test runner for the app's CLI commands."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def authenticated_client(client):
    """Create a client with an authenticated session (for future use)."""
    # This is a placeholder for when authentication is implemented
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['_fresh'] = True
    return client