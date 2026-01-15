"""
Pytest fixtures for LearnAI test suite.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app


@pytest.fixture
def app():
    """Create application for testing."""
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    yield flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client (simulates OAuth login)."""
    with client.session_transaction() as sess:
        sess['authenticated'] = True
        sess['user_email'] = 'test@monmouth.edu'
        sess['user_name'] = 'Test User'
    return client


@pytest.fixture
def admin_client(client):
    """Create admin test client."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['authenticated'] = True
        sess['admin_username'] = 'test_admin'
        sess['tutor_id'] = 'test_tutor'
        sess['tutor_role'] = 'tutor_admin'
        sess['tutor_name'] = 'Test Admin'
        sess['tutor_email'] = 'admin@test.com'
        sess['user_email'] = 'admin@test.com'
    return client


@pytest.fixture
def super_admin_client(client):
    """Create super admin test client."""
    with client.session_transaction() as sess:
        sess['logged_in'] = True
        sess['authenticated'] = True
        sess['admin_username'] = 'super_admin'
        sess['tutor_id'] = 'christopher_buzaid'
        sess['tutor_role'] = 'super_admin'
        sess['tutor_name'] = 'Christopher Buzaid'
        sess['tutor_email'] = 'cjpbuzaid@gmail.com'
        sess['user_email'] = 'cjpbuzaid@gmail.com'
    return client


@pytest.fixture
def sample_booking_data():
    """Sample booking data for tests."""
    return {
        'full_name': 'Test Student',
        'email': 'student@monmouth.edu',
        'phone': '555-1234',
        'role': 'student',
        'department': 'Computer Science',
        'ai_familiarity': 'beginner',
        'ai_tools': 'ChatGPT',
        'primary_use': 'Academic research',
        'learning_goal': 'Learn AI basics',
        'confidence_level': 3,
        'personal_comments': 'Test booking',
        'selected_slot': 'test_slot_123',
        'selected_room': 'Howard Hall 123',
        'meeting_type': 'in-person',
        'attendee_count': 1,
        'device_id': 'test_device_abc123'
    }


@pytest.fixture
def sample_slot_data():
    """Sample slot data for tests."""
    return {
        'id': 'test_slot_123',
        'day': 'Monday',
        'date': 'January 20, 2025',
        'time': '10:00 AM',
        'datetime': '2025-01-20T10:00:00',
        'tutor_id': 'christopher_buzaid',
        'tutor_name': 'Christopher Buzaid',
        'tutor_email': 'cjpbuzaid@gmail.com',
        'booked': False,
        'location_type': 'user_choice'
    }
