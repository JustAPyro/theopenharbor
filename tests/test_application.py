"""
Test cases for The Open Harbor application factory and configuration.
"""

import pytest
from app import create_app


class TestApplicationFactory:
    """Test cases for the application factory pattern."""

    def test_app_creation(self):
        """Test that the application can be created successfully."""
        app = create_app()
        assert app is not None
        assert app.name == 'app'

    def test_app_has_secret_key(self):
        """Test that the application has a secret key configured."""
        app = create_app()
        assert app.config.get('SECRET_KEY') is not None

    def test_testing_config(self):
        """Test that testing configuration can be applied."""
        app = create_app()
        app.config.update({'TESTING': True})
        assert app.config['TESTING'] is True

    def test_app_context_works(self):
        """Test that application context can be created and used."""
        app = create_app()
        with app.app_context():
            from flask import current_app
            assert current_app.name == app.name

    def test_request_context_works(self):
        """Test that request context can be created and used."""
        app = create_app()
        with app.test_request_context('/'):
            from flask import request
            assert request.path == '/'

    def test_blueprints_registered(self):
        """Test that required blueprints are registered."""
        app = create_app()
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert 'main' in blueprint_names

    def test_app_url_map(self):
        """Test that the application has the expected routes."""
        app = create_app()
        with app.app_context():
            rules = [rule.rule for rule in app.url_map.iter_rules()]
            assert '/' in rules  # Home route should exist