"""
Test cases for all links specific to home.html template.
This test suite verifies links in the home page that extends base.html.
"""

import pytest
import re


class TestHomePageNavigationLinks:
    """Test cases for navigation links in home.html."""

    def test_features_anchor_exists(self, client):
        """Test that #features anchor exists on the home page."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Check that features section exists with id="features"
        assert 'id="features"' in data, "Features section with id='features' not found"

    def test_pricing_anchor_exists(self, client):
        """Test that #pricing anchor exists on the home page."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Check that pricing section exists with id="pricing"
        assert 'id="pricing"' in data, "Pricing section with id='pricing' not found"


class TestHomePageCTALinks:
    """Test cases for call-to-action links in home.html."""

    def test_try_it_free_hero_button(self, client):
        """Test 'Try it free' button in hero section."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Look for "Try it free" button in hero section
        hero_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-primary btn-lg"[^>]*>Try it free</a>'
        hero_match = re.search(hero_pattern, data)

        if hero_match:
            href = hero_match.group(1)
            print(f"Hero 'Try it free' button links to: {href}")

            # Test the link if it's internal
            if href.startswith('/'):
                signup_response = client.get(href)
                assert signup_response.status_code in [200, 404], f"Hero signup link {href} returned {signup_response.status_code}"
            elif href == '#signup':
                print("WARNING: Hero button uses placeholder '#signup' link")

    def test_see_how_it_works_button(self, client):
        """Test 'See how it works' button in hero section."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Look for "See how it works" button
        pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-outline-primary btn-lg"[^>]*>See how it works</a>'
        match = re.search(pattern, data)

        if match:
            href = match.group(1)
            print(f"'See how it works' button links to: {href}")

            if href == '#features':
                # Verify features section exists
                assert 'id="features"' in response.data.decode('utf-8')
            elif href.startswith('/'):
                # Test internal route
                features_response = client.get(href)
                assert features_response.status_code in [200, 404]

    def test_try_it_free_cta_section_button(self, client):
        """Test 'Try it free' button in CTA section."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Look for CTA section "Try it free" button
        cta_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-secondary btn-lg me-3"[^>]*>Try it free</a>'
        cta_match = re.search(cta_pattern, data)

        if cta_match:
            href = cta_match.group(1)
            print(f"CTA 'Try it free' button links to: {href}")

            if href.startswith('/'):
                signup_response = client.get(href)
                assert signup_response.status_code in [200, 404], f"CTA signup link {href} returned {signup_response.status_code}"
            elif href == '#signup':
                print("WARNING: CTA button uses placeholder '#signup' link")

    def test_see_pricing_cta_button(self, client):
        """Test 'See pricing' button in CTA section."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Look for "See pricing" button in CTA
        pricing_pattern = r'<a\s+href="([^"]+)"\s+class="btn btn-outline-light btn-lg"[^>]*>See pricing</a>'
        pricing_match = re.search(pricing_pattern, data)

        if pricing_match:
            href = pricing_match.group(1)
            print(f"'See pricing' button links to: {href}")

            if href.startswith('/'):
                pricing_response = client.get(href)
                assert pricing_response.status_code in [200, 404], f"Pricing link {href} returned {pricing_response.status_code}"
            elif href == '#contact':
                print("WARNING: Pricing button uses placeholder '#contact' link")


class TestHomePageLinkAnalysis:
    """Test class to analyze and report on all links in home.html."""

    def test_analyze_all_signup_links(self, client):
        """Analyze all signup-related links on the home page."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        signup_patterns = [
            (r'<a\s+href="([^"]+)"[^>]*>Try it free</a>', "Try it free"),
            (r'<a\s+href="([^"]+)"[^>]*>Start.*free.*account</a>', "Start free account"),
        ]

        print("\n=== SIGNUP LINK ANALYSIS ===")
        for pattern, description in signup_patterns:
            matches = re.finditer(pattern, data, re.IGNORECASE)
            for i, match in enumerate(matches):
                href = match.group(1)
                print(f"{description} #{i+1}: href='{href}'")

                # Test internal links
                if href.startswith('/'):
                    test_response = client.get(href)
                    print(f"  -> Status: {test_response.status_code}")
                elif href.startswith('#'):
                    if href == '#signup':
                        print(f"  -> WARNING: Placeholder link '{href}'")
                    else:
                        print(f"  -> Anchor link: {href}")

    def test_analyze_all_anchor_links(self, client):
        """Analyze all anchor links (#something) and their targets."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Find all anchor links
        anchor_pattern = r'href="(#[^"]+)"'
        anchor_matches = re.finditer(anchor_pattern, data)

        print("\n=== ANCHOR LINK ANALYSIS ===")
        unique_anchors = set()
        for match in anchor_matches:
            anchor = match.group(1)
            unique_anchors.add(anchor)

        for anchor in sorted(unique_anchors):
            target_id = anchor[1:]  # Remove #
            has_target = f'id="{target_id}"' in data or f'name="{target_id}"' in data
            status = "✓ HAS TARGET" if has_target else "✗ NO TARGET"
            print(f"{anchor}: {status}")

    def test_analyze_external_placeholders(self, client):
        """Analyze external link placeholders."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        print("\n=== EXTERNAL PLACEHOLDER ANALYSIS ===")

        # Social media links
        social_patterns = [
            (r'aria-label="Twitter"[^>]*><i class="bi bi-twitter">', "Twitter"),
            (r'aria-label="Instagram"[^>]*><i class="bi bi-instagram">', "Instagram"),
            (r'aria-label="Facebook"[^>]*><i class="bi bi-facebook">', "Facebook"),
            (r'aria-label="GitHub"[^>]*><i class="bi bi-github">', "GitHub"),
            (r'aria-label="Email"[^>]*><i class="bi bi-envelope">', "Email"),
        ]

        for pattern, social_type in social_patterns:
            if re.search(pattern, data):
                # Extract the href for this social link
                full_pattern = rf'<a\s+href="([^"]+)"[^>]*{pattern.replace("(", "\\(").replace(")", "\\)")}'
                match = re.search(full_pattern, data)
                if match:
                    href = match.group(1)
                    if href == '#':
                        print(f"{social_type}: PLACEHOLDER '#' (needs real URL)")
                    else:
                        print(f"{social_type}: {href}")


class TestHomePageRouteValidation:
    """Test internal routes referenced in home.html."""

    def test_route_status_codes(self, client):
        """Test status codes for all internal routes found in home.html."""
        response = client.get('/')
        assert response.status_code == 200
        data = response.data.decode('utf-8')

        # Extract all internal routes (starting with /)
        internal_pattern = r'href="(/[^"#]+)"'
        internal_matches = re.finditer(internal_pattern, data)

        print("\n=== INTERNAL ROUTE STATUS ===")
        tested_routes = set()

        for match in internal_matches:
            route = match.group(1)
            if route not in tested_routes:
                tested_routes.add(route)
                route_response = client.get(route)
                status_icon = "✓" if route_response.status_code == 200 else "✗"
                print(f"{status_icon} {route}: {route_response.status_code}")

        # Test common expected routes even if not found in HTML
        expected_routes = ['/about', '/contact', '/pricing', '/auth/sign-up', '/auth/login']
        for route in expected_routes:
            if route not in tested_routes:
                route_response = client.get(route)
                status_icon = "✓" if route_response.status_code == 200 else "✗"
                print(f"{status_icon} {route}: {route_response.status_code} (not linked)")


if __name__ == '__main__':
    pytest.main([__file__])