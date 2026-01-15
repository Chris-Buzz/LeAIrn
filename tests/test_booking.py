"""
Booking tests for LearnAI booking system.
Tests booking creation, modification, and deletion.
"""

import pytest


class TestSlotRetrieval:
    """Test slot retrieval functionality."""

    def test_get_slots_public(self, client):
        """Test that slots endpoint is publicly accessible."""
        response = client.get('/api/slots')
        assert response.status_code == 200
        assert isinstance(response.get_json(), list)

    def test_get_tutors_requires_auth(self, client):
        """Test that tutors endpoint requires authentication."""
        response = client.get('/api/tutors')
        assert response.status_code in [401, 302]


class TestBookingCreation:
    """Test booking creation functionality."""

    def test_booking_requires_authentication(self, client, sample_booking_data):
        """Test that booking requires OAuth authentication."""
        response = client.post('/api/booking/request-verification',
                              json=sample_booking_data)
        # 401 for auth required, 429 if rate limited
        assert response.status_code in [401, 429]
        if response.status_code == 401:
            data = response.get_json()
            assert data['success'] is False

    def test_booking_validation_full_name(self, authenticated_client):
        """Test booking validation for full name."""
        response = authenticated_client.post('/api/booking/request-verification',
                                            json={
                                                'full_name': '',
                                                'role': 'student',
                                                'selected_slot': 'test',
                                                'selected_room': 'Test Room',
                                                'device_id': 'test123'
                                            })
        # 400 for validation error, 429 if rate limited
        assert response.status_code in [400, 429]

    def test_booking_validation_role(self, authenticated_client):
        """Test booking validation for role."""
        response = authenticated_client.post('/api/booking/request-verification',
                                            json={
                                                'full_name': 'Test User',
                                                'role': '',
                                                'selected_slot': 'test',
                                                'selected_room': 'Test Room',
                                                'device_id': 'test123'
                                            })
        # 400 for validation error, 429 if rate limited
        assert response.status_code in [400, 429]

    def test_booking_validation_device_id(self, authenticated_client):
        """Test booking requires device ID for rate limiting."""
        response = authenticated_client.post('/api/booking/request-verification',
                                            json={
                                                'full_name': 'Test User',
                                                'role': 'student',
                                                'selected_slot': 'test',
                                                'selected_room': 'Test Room'
                                                # Missing device_id
                                            })
        # 400 for validation error, 429 if rate limited
        assert response.status_code in [400, 429]


class TestBookingManagement:
    """Test booking management for admins."""

    def test_delete_booking_requires_auth(self, client):
        """Test that deleting booking requires admin auth."""
        response = client.delete('/api/booking/test_id')
        assert response.status_code in [401, 302]

    def test_update_booking_requires_auth(self, client):
        """Test that updating booking requires admin auth."""
        response = client.put('/api/booking/test_id', json={})
        assert response.status_code in [401, 302]

    def test_get_user_booking_requires_auth(self, client):
        """Test that getting user booking requires auth."""
        response = client.get('/api/user-booking')
        assert response.status_code == 401


class TestDeprecatedEndpoints:
    """Test deprecated booking endpoints."""

    def test_confirm_verification_deprecated(self, client):
        """Test that confirm verification endpoint is deprecated."""
        response = client.post('/api/booking/confirm-verification', json={})
        # 410 for deprecated, 429 if rate limited
        assert response.status_code in [410, 429]

    def test_booking_lookup_deprecated(self, client):
        """Test that booking lookup endpoint is deprecated."""
        response = client.post('/api/booking/lookup', json={})
        # 410 for deprecated, 429 if rate limited
        assert response.status_code in [410, 429]

    def test_booking_verify_deprecated(self, client):
        """Test that booking verify endpoint is deprecated."""
        response = client.post('/api/booking/verify', json={})
        # 410 for deprecated, 429 if rate limited
        assert response.status_code in [410, 429]

    def test_delete_by_email_deprecated(self, client):
        """Test that delete by email endpoint is deprecated."""
        response = client.post('/api/booking/delete-by-email', json={})
        # 410 for deprecated, 429 if rate limited
        assert response.status_code in [410, 429]

    def test_update_by_email_deprecated(self, client):
        """Test that update by email endpoint is deprecated."""
        response = client.post('/api/booking/update-by-email', json={})
        # 410 for deprecated, 429 if rate limited
        assert response.status_code in [410, 429]


class TestUserBooking:
    """Test user booking retrieval."""

    def test_get_user_booking_authenticated(self, authenticated_client):
        """Test getting user's booking when authenticated."""
        response = authenticated_client.get('/api/user-booking')
        # May return 404 if no booking exists, but should not be 401
        assert response.status_code in [200, 404]

    def test_get_user_booking_no_booking(self, authenticated_client):
        """Test response when user has no booking."""
        response = authenticated_client.get('/api/user-booking')
        if response.status_code == 404:
            data = response.get_json()
            assert data['success'] is False
