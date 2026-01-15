"""
Admin tests for LearnAI booking system.
Tests admin dashboard, slot management, and statistics.
"""

import pytest


class TestAdminDashboard:
    """Test admin dashboard functionality."""

    def test_admin_dashboard_loads(self, admin_client):
        """Test that admin dashboard loads for authenticated admin."""
        response = admin_client.get('/admin')
        assert response.status_code == 200

    def test_admin_dashboard_redirect_unauthenticated(self, client):
        """Test that unauthenticated users are redirected."""
        response = client.get('/admin')
        assert response.status_code == 302

    def test_get_users_as_admin(self, admin_client):
        """Test getting users list as admin."""
        response = admin_client.get('/api/users')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

    def test_get_statistics(self, admin_client):
        """Test getting statistics as admin."""
        response = admin_client.get('/api/statistics')
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data


class TestSlotManagement:
    """Test slot management functionality."""

    def test_generate_slots_requires_auth(self, client):
        """Test that generating slots requires admin auth."""
        response = client.post('/api/slots/generate', json={})
        assert response.status_code in [401, 302]

    def test_delete_slot_requires_auth(self, client):
        """Test that deleting slot requires admin auth."""
        response = client.delete('/api/slots/test_id')
        assert response.status_code in [401, 302]

    def test_unbook_slot_requires_auth(self, client):
        """Test that unbooking slot requires admin auth."""
        response = client.post('/api/slots/test_id/unbook')
        assert response.status_code in [401, 302]

    def test_bulk_delete_requires_auth(self, client):
        """Test that bulk delete requires admin auth."""
        response = client.post('/api/slots/bulk-delete', json={'slot_ids': []})
        assert response.status_code in [401, 302]


class TestTutorManagement:
    """Test tutor management functionality."""

    def test_get_tutors_as_admin(self, admin_client):
        """Test getting tutors list as admin."""
        response = admin_client.get('/api/tutors')
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
        assert 'tutors' in data


class TestSessionCompletion:
    """Test session completion functionality."""

    def test_complete_booking_requires_auth(self, client):
        """Test that completing booking requires admin auth."""
        response = client.post('/api/booking/test_id/complete', json={})
        # 401/302 for auth required, 429 if rate limited
        assert response.status_code in [401, 302, 429]

    def test_complete_booking_not_found(self, admin_client):
        """Test completing non-existent booking."""
        response = admin_client.post('/api/booking/nonexistent_id/complete',
                                    json={'notes': 'Test notes'})
        # 404 for not found, 429 if rate limited
        assert response.status_code in [404, 429]


class TestSessionOverviews:
    """Test session overview functionality."""

    def test_get_overviews_requires_auth(self, client):
        """Test that getting overviews requires admin auth."""
        response = client.get('/api/session-overviews')
        assert response.status_code in [401, 302]

    def test_get_overviews_as_admin(self, admin_client):
        """Test getting overviews as admin."""
        response = admin_client.get('/api/session-overviews')
        assert response.status_code == 200

    def test_create_manual_overview_requires_auth(self, client):
        """Test that creating manual overview requires auth."""
        response = client.post('/api/session-overviews/manual', json={})
        assert response.status_code in [401, 302]

    def test_preview_overview_requires_auth(self, client):
        """Test that previewing overview requires auth."""
        response = client.post('/api/session-overviews/preview', json={})
        assert response.status_code in [401, 302]


class TestUserManagement:
    """Test user management functionality."""

    def test_ban_user_requires_auth(self, client):
        """Test that banning user requires admin auth."""
        response = client.post('/api/users/test@test.com/ban', json={})
        assert response.status_code in [401, 302]

    def test_unban_user_requires_auth(self, client):
        """Test that unbanning user requires admin auth."""
        response = client.post('/api/users/test@test.com/unban', json={})
        assert response.status_code in [401, 302]

    def test_reset_misses_requires_auth(self, client):
        """Test that resetting misses requires admin auth."""
        response = client.post('/api/users/test@test.com/reset-misses', json={})
        assert response.status_code in [401, 302]

    def test_get_user_status_requires_auth(self, client):
        """Test that getting user status requires admin auth."""
        response = client.get('/api/users/test@test.com/status')
        assert response.status_code in [401, 302]


class TestSuperAdminOnly:
    """Test super admin only functionality."""

    def test_delete_admin_account_requires_super_admin(self, admin_client):
        """Test that deleting admin account requires super admin."""
        response = admin_client.delete('/api/admin-accounts/test@test.com')
        assert response.status_code == 403

    def test_delete_admin_account_as_super_admin(self, super_admin_client):
        """Test deleting admin account as super admin."""
        response = super_admin_client.delete('/api/admin-accounts/nonexistent@test.com')
        # Should return 404 for non-existent, not 403
        assert response.status_code in [200, 404]

    def test_test_email_requires_super_admin(self, admin_client):
        """Test that testing email requires super admin."""
        response = admin_client.post('/api/admin/test-email', json={})
        assert response.status_code == 403
