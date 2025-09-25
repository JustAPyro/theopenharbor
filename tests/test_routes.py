"""
Test cases for The Open Harbor application routes.
"""

import pytest
from flask import url_for


class TestHomePage:
    """Test cases for the home page."""

    def test_home_page_loads_successfully(self, client):
        """Test that the home page loads with 200 status code."""
        response = client.get('/')
        assert response.status_code == 200

    def test_home_page_contains_brand_name(self, client):
        """Test that the home page contains The Open Harbor brand name."""
        response = client.get('/')
        assert b'The Open Harbor' in response.data

    def test_home_page_contains_tagline(self, client):
        """Test that the home page contains the main tagline."""
        response = client.get('/')
        assert b'A safe place for your files' in response.data

    def test_home_page_contains_security_message(self, client):
        """Test that security messaging is present."""
        response = client.get('/')
        assert b'Files encrypted in transit and at rest' in response.data

    def test_home_page_has_proper_html_structure(self, client):
        """Test that the page has proper HTML structure."""
        response = client.get('/')
        data = response.data.decode('utf-8')

        # Check for essential HTML elements
        assert '<html lang="en">' in data
        assert '<title>' in data
        assert 'The Open Harbor' in data
        assert '</html>' in data

    def test_home_page_includes_navigation(self, client):
        """Test that navigation elements are present."""
        response = client.get('/')
        data = response.data.decode('utf-8')

        # Check for navigation elements
        assert 'navbar' in data
        assert 'Features' in data
        assert 'Security' in data

    def test_home_page_includes_cta_buttons(self, client):
        """Test that call-to-action buttons are present."""
        response = client.get('/')
        data = response.data.decode('utf-8')

        # Check for CTA buttons
        assert 'Start a free account' in data or 'Start free account' in data
        assert 'Learn more' in data

    def test_home_page_includes_features_section(self, client):
        """Test that features section is present."""
        response = client.get('/')
        data = response.data.decode('utf-8')

        # Check for features content
        assert 'Privacy First' in data
        assert 'Community Driven' in data
        assert 'Simple & Fast' in data

    def test_home_page_includes_footer(self, client):
        """Test that footer is present with copyright."""
        response = client.get('/')
        data = response.data.decode('utf-8')

        assert '2024 The Open Harbor' in data
        assert 'Built with care for your privacy' in data

    def test_home_page_content_type(self, client):
        """Test that the home page returns HTML content type."""
        response = client.get('/')
        assert 'text/html' in response.content_type


class TestApplicationHealth:
    """Test cases for application health and configuration."""

    def test_app_is_in_testing_mode(self, app):
        """Test that the app is configured for testing."""
        assert app.config['TESTING'] is True

    def test_secret_key_is_set(self, app):
        """Test that secret key is configured."""
        assert app.config['SECRET_KEY'] is not None
        assert len(app.config['SECRET_KEY']) > 0

    def test_app_has_main_blueprint(self, app):
        """Test that the main blueprint is registered."""
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert 'main' in blueprint_names


class TestErrorHandling:
    """Test cases for error handling."""

    def test_404_page_handling(self, client):
        """Test that 404 errors are handled appropriately."""
        response = client.get('/nonexistent-page')
        assert response.status_code == 404

    def test_405_method_not_allowed(self, client):
        """Test that POST to GET-only route returns 405."""
        response = client.post('/')
        assert response.status_code == 405


class TestSecurity:
    """Test cases for security headers and configuration."""

    def test_security_headers_present(self, client):
        """Test that basic security considerations are in place."""
        response = client.get('/')

        # Check that the response doesn't expose sensitive information
        assert 'Server' not in response.headers or 'Flask' not in response.headers.get('Server', '')

    def test_no_debug_info_in_production_mode(self, client):
        """Test that debug information is not exposed."""
        response = client.get('/nonexistent-route')
        data = response.data.decode('utf-8')

        # Should not contain debug information
        assert 'Traceback' not in data
        assert 'werkzeug' not in data.lower()


if __name__ == '__main__':
    pytest.main([__file__])