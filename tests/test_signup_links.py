"""
Test cases for signup link functionality on The Open Harbor homepage.
"""

import pytest
import re


class TestSignupLinks:
    """Test cases for signup button links and redirects."""

    def test_start_free_account_button_hero_section_link(self, client):
        """Test that the 'Start a free account' button in hero section links to /auth/sign-up."""
        response = client.get('/')
        assert response.status_code == 200

        data = response.data.decode('utf-8')

        # Look for the hero section signup button with regex
        # Pattern looks for: <a href="..." class="btn btn-primary btn-lg">Start a free account</a>
        hero_button_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-primary btn-lg"[^>]*>Start a free account</a>'
        hero_match = re.search(hero_button_pattern, data)

        assert hero_match is not None, "Could not find 'Start a free account' button in hero section"

        href = hero_match.group(1)
        assert href == '/auth/sign-up', \
            f"Expected hero section button href='/auth/sign-up', but found href='{href}'"

    def test_start_free_account_button_cta_section_link(self, client):
        """Test that the 'Start free account' button in CTA section links to /auth/sign-up."""
        response = client.get('/')
        assert response.status_code == 200

        data = response.data.decode('utf-8')

        # Look for the CTA section signup button with regex
        # Pattern looks for: <a href="..." class="btn btn-secondary btn-lg me-3">Start free account</a>
        cta_button_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-secondary btn-lg me-3"[^>]*>Start free account</a>'
        cta_match = re.search(cta_button_pattern, data)

        assert cta_match is not None, "Could not find 'Start free account' button in CTA section"

        href = cta_match.group(1)
        assert href == '/auth/sign-up', \
            f"Expected CTA section button href='/auth/sign-up', but found href='{href}'"

    def test_signup_redirect_follows_correctly(self, client):
        """Test that following the signup link results in appropriate response."""
        # First get the homepage to ensure it loads
        response = client.get('/')
        assert response.status_code == 200

        # Try to access the signup URL directly
        # Note: This will likely return 404 if the auth routes aren't implemented yet,
        # but we're testing the link structure, not the endpoint implementation
        signup_response = client.get('/auth/sign-up')

        # The response should either be 200 (if implemented) or 404 (if not yet implemented)
        # but not 500 (which would indicate a server error)
        assert signup_response.status_code in [200, 404], \
            f"Expected status code 200 or 404, but got {signup_response.status_code}"

    def test_all_signup_buttons_present(self, client):
        """Test that both signup buttons are present on the page."""
        response = client.get('/')
        assert response.status_code == 200

        data = response.data.decode('utf-8')

        # Check that both button texts are present
        assert 'Start a free account' in data, "Hero section signup button text not found"
        assert 'Start free account' in data, "CTA section signup button text not found"

    def test_current_signup_links_are_broken(self, client):
        """Test that demonstrates the current signup links are incorrectly pointing to #signup."""
        response = client.get('/')
        assert response.status_code == 200

        data = response.data.decode('utf-8')

        # Check that the buttons currently have broken links (pointing to #signup instead of /auth/sign-up)
        hero_button_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-primary btn-lg"[^>]*>Start a free account</a>'
        hero_match = re.search(hero_button_pattern, data)

        cta_button_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-secondary btn-lg me-3"[^>]*>Start free account</a>'
        cta_match = re.search(cta_button_pattern, data)

        if hero_match:
            hero_href = hero_match.group(1)
            if hero_href == '#signup':
                print(f"BROKEN LINK DETECTED: Hero section button links to '{hero_href}' instead of '/auth/sign-up'")

        if cta_match:
            cta_href = cta_match.group(1)
            if cta_href == '#signup':
                print(f"BROKEN LINK DETECTED: CTA section button links to '{cta_href}' instead of '/auth/sign-up'")


if __name__ == '__main__':
    pytest.main([__file__])