# LearnAI Test Suite

## Overview

This directory contains the test suite for the LearnAI booking system.

## Test Files

- `test_auth.py` - Authentication and authorization tests
- `test_booking.py` - Booking creation and management tests
- `test_admin.py` - Admin dashboard and functionality tests
- `test_security.py` - Security and input validation tests
- `conftest.py` - Pytest fixtures and configuration

## Running Tests

### Prerequisites

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
python run_tests.py -v
```

### Run with Coverage

```bash
python run_tests.py -c
```

### Run Specific Test File

```bash
python run_tests.py -t tests/test_auth.py
```

### Run Only Failed Tests

```bash
python run_tests.py -f
```

### Run Security Scans

```bash
python run_tests.py -s
```

### Run Everything

```bash
python run_tests.py -a
```

## Test Categories

### Authentication Tests (`test_auth.py`)
- Public route access
- OAuth flow
- Admin login
- Session management
- Protected route authorization

### Booking Tests (`test_booking.py`)
- Slot retrieval
- Booking creation and validation
- Booking management (admin)
- Deprecated endpoint handling

### Admin Tests (`test_admin.py`)
- Dashboard access
- Slot management
- Session completion
- User management
- Super admin permissions

### Security Tests (`test_security.py`)
- XSS prevention
- SQL injection prevention
- Input validation
- Rate limiting
- CSRF protection
- Data exposure prevention

## Writing New Tests

1. Create test functions prefixed with `test_`
2. Use fixtures from `conftest.py`:
   - `client` - Unauthenticated test client
   - `authenticated_client` - OAuth authenticated user
   - `admin_client` - Admin user (tutor_admin role)
   - `super_admin_client` - Super admin user

Example:
```python
def test_example_feature(authenticated_client):
    response = authenticated_client.get('/api/example')
    assert response.status_code == 200
```
