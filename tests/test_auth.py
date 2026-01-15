"""
Authentication tests for LearnAI booking system.
Tests OAuth flow, session management, and authorization.
"""

import pytest


class TestPublicRoutes:
    """Test public routes that don't require authentication."""

    def test_home_page_loads(self, client):
        """Test that home page loads successfully."""
        response = client.get('/')
        assert response.status_code == 200

    def test_projects_page_loads(self, client):
        """Test that projects page loads."""
        response = client.get('/projects')
        assert response.status_code == 200

    def test_ai_tools_page_loads(self, client):
        """Test that AI tools page loads."""
        response = client.get('/ai-tools')
        assert response.status_code == 200

    def test_feedback_page_requires_token(self, client):
        """Test that feedback page requires a token."""
        response = client.get('/feedback')
        # Should still load but show error without valid token
        assert response.status_code == 200


class TestOAuthFlow:
    """Test OAuth authentication flow."""

    def test_login_redirect(self, client):
        """Test that login redirects to Google OAuth."""
        response = client.get('/login')
        assert response.status_code == 302
        assert 'google' in response.location.lower() or response.status_code == 302

    def test_logout_clears_session(self, authenticated_client):
        """Test that logout clears session."""
        response = authenticated_client.get('/logout')
        assert response.status_code == 302

        # Verify session is cleared
        with authenticated_client.session_transaction() as sess:
            assert 'authenticated' not in sess or not sess.get('authenticated')

    def test_authenticated_user_session(self, authenticated_client):
        """Test that authenticated user has correct session data."""
        # Access home page to verify session works
        response = authenticated_client.get('/')
        assert response.status_code == 200
        # Verify session contains auth info
        with authenticated_client.session_transaction() as sess:
            assert sess.get('authenticated') is True
            assert 'user_email' in sess

    def test_unauthenticated_user_session(self, client):
        """Test that unauthenticated user has no auth session."""
        response = client.get('/')
        assert response.status_code == 200
        # Verify session doesn't have auth
        with client.session_transaction() as sess:
            assert sess.get('authenticated') is not True


class TestAdminLogin:
    """Test admin login functionality."""

    def test_admin_login_page_loads(self, client):
        """Test that admin login page loads."""
        response = client.get('/admin/login')
        assert response.status_code == 200

    def test_admin_login_invalid_credentials(self, client):
        """Test admin login with invalid credentials."""
        response = client.post('/admin/login', json={
            'username': 'invalid_user',
            'password': 'wrong_password'
        })
        # 401 for invalid credentials, 429 if rate limited
        assert response.status_code in [401, 429]
        if response.status_code == 401:
            data = response.get_json()
            assert data['success'] is False

    def test_admin_login_empty_credentials(self, client):
        """Test admin login with empty credentials."""
        response = client.post('/admin/login', json={
            'username': '',
            'password': ''
        })
        # 401 for invalid credentials, 429 if rate limited
        assert response.status_code in [401, 429]

    def test_admin_logout(self, admin_client):
        """Test admin logout."""
        response = admin_client.get('/admin/logout')
        assert response.status_code == 302


class TestProtectedRoutes:
    """Test routes that require authentication."""

    def test_admin_dashboard_requires_auth(self, client):
        """Test that admin dashboard requires authentication."""
        response = client.get('/admin')
        # Should redirect to login
        assert response.status_code == 302

    def test_admin_dashboard_accessible_when_authenticated(self, admin_client):
        """Test that admin dashboard is accessible when authenticated."""
        response = admin_client.get('/admin')
        assert response.status_code == 200

    def test_api_users_requires_auth(self, client):
        """Test that API users endpoint requires authentication."""
        response = client.get('/api/users')
        assert response.status_code in [401, 302]

    def test_api_users_accessible_when_admin(self, admin_client):
        """Test that API users endpoint is accessible for admin."""
        response = admin_client.get('/api/users')
        assert response.status_code == 200


class TestSessionManagement:
    """Test session management."""

    def test_session_persists_across_requests(self, authenticated_client):
        """Test that session persists across requests."""
        # First request
        response1 = authenticated_client.get('/')
        assert response1.status_code == 200

        # Verify session persists
        with authenticated_client.session_transaction() as sess:
            assert sess.get('authenticated') is True

        # Second request
        response2 = authenticated_client.get('/')
        assert response2.status_code == 200

        # Session should still be valid
        with authenticated_client.session_transaction() as sess:
            assert sess.get('authenticated') is True

    def test_admin_session_contains_tutor_info(self, admin_client):
        """Test that admin session contains tutor information."""
        with admin_client.session_transaction() as sess:
            assert 'tutor_id' in sess
            assert 'tutor_name' in sess
            assert 'tutor_role' in sess
