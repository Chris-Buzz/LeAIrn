"""
Rate Limiting Middleware
Corporate-grade rate limiting with multiple strategies
"""

from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import firestore_db as db


class RateLimiter:
    """Advanced rate limiting with tiered limits and strategies"""

    # Rate limit configurations (requests per time window)
    RATE_LIMITS = {
        # Global API limits (per IP)
        'global': {
            'requests': 1000,
            'window': 3600,  # 1 hour
            'message': 'Too many requests. Please try again later.'
        },
        # Authentication endpoints (stricter limits to prevent brute force)
        'auth': {
            'requests': 10,
            'window': 900,  # 15 minutes
            'message': 'Too many authentication attempts. Please wait 15 minutes.'
        },
        # Booking endpoints
        'booking': {
            'requests': 5,
            'window': 3600,  # 1 hour
            'message': 'Too many booking attempts. Please wait before trying again.'
        },
        # Admin endpoints
        'admin': {
            'requests': 200,
            'window': 3600,  # 1 hour
            'message': 'Rate limit exceeded for admin operations.'
        },
        # Slot management
        'slots': {
            'requests': 50,
            'window': 3600,  # 1 hour
            'message': 'Too many slot operations. Please wait.'
        }
    }

    @staticmethod
    def get_client_identifier() -> str:
        """
        Get unique client identifier for rate limiting
        Uses IP address with X-Forwarded-For support
        """
        if request.headers.get('X-Forwarded-For'):
            # Behind proxy - get real IP
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            ip = request.headers.get('X-Real-IP')
        else:
            ip = request.remote_addr or 'unknown'

        return ip

    @staticmethod
    def check_rate_limit(limit_type: str = 'global') -> Tuple[bool, Optional[int]]:
        """
        Check if request exceeds rate limit

        Args:
            limit_type: Type of rate limit to apply

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if limit_type not in RateLimiter.RATE_LIMITS:
            # Unknown limit type, allow by default
            return True, None

        config = RateLimiter.RATE_LIMITS[limit_type]
        client_id = RateLimiter.get_client_identifier()

        # Create unique key for this client and limit type
        rate_key = f"rate_limit:{limit_type}:{client_id}"

        try:
            # Check current request count from database
            # Note: This is a simplified implementation
            # In production, consider using Redis for better performance
            current_count = db.get_rate_limit_count(rate_key, config['window'])

            if current_count >= config['requests']:
                # Rate limit exceeded
                retry_after = config['window']  # Simplified - return full window
                return False, retry_after

            # Increment counter
            db.increment_rate_limit(rate_key, config['window'])
            return True, None

        except Exception as e:
            # On error, allow request (fail open) but log
            print(f"[WARNING] Rate limit check failed: {e}")
            return True, None

    @staticmethod
    def apply_rate_limit_headers(response, limit_type: str = 'global'):
        """
        Add rate limit information to response headers

        Args:
            response: Flask response object
            limit_type: Type of rate limit applied

        Returns:
            Modified response object
        """
        if limit_type not in RateLimiter.RATE_LIMITS:
            return response

        config = RateLimiter.RATE_LIMITS[limit_type]
        client_id = RateLimiter.get_client_identifier()
        rate_key = f"rate_limit:{limit_type}:{client_id}"

        try:
            current_count = db.get_rate_limit_count(rate_key, config['window'])
            remaining = max(0, config['requests'] - current_count)

            # Add standard rate limit headers
            response.headers['X-RateLimit-Limit'] = str(config['requests'])
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(int(datetime.now().timestamp()) + config['window'])

        except Exception as e:
            print(f"[WARNING] Could not add rate limit headers: {e}")

        return response


def rate_limit(limit_type: str = 'global'):
    """
    Decorator for applying rate limits to endpoints

    Args:
        limit_type: Type of rate limit to apply

    Usage:
        @app.route('/api/endpoint')
        @rate_limit('booking')
        def my_endpoint():
            return jsonify({'success': True})
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            is_allowed, retry_after = RateLimiter.check_rate_limit(limit_type)

            if not is_allowed:
                config = RateLimiter.RATE_LIMITS.get(limit_type, RateLimiter.RATE_LIMITS['global'])
                response = jsonify({
                    'success': False,
                    'error': 'rate_limit_exceeded',
                    'message': config['message'],
                    'retry_after': retry_after
                })
                response.status_code = 429

                # Add Retry-After header
                if retry_after:
                    response.headers['Retry-After'] = str(retry_after)

                return response

            # Execute the endpoint
            response = f(*args, **kwargs)

            # Add rate limit headers to response
            if hasattr(response, 'headers'):
                response = RateLimiter.apply_rate_limit_headers(response, limit_type)

            return response

        return decorated_function
    return decorator


def apply_global_rate_limit():
    """
    Global rate limiting middleware - apply to all API requests
    Add this as a before_request handler in app.py
    """
    from flask import session
    from routes.auth_routes import is_authorized_admin

    # Only apply to API endpoints
    if not request.path.startswith('/api/'):
        return None

    # Skip rate limiting for certain paths (health checks, static files, etc.)
    skip_paths = ['/api/health', '/api/ping']
    if request.path in skip_paths:
        return None

    # Check if user is an authorized admin by their authenticated email
    # Authorized admins bypass ALL rate limiting
    user_email = session.get('user_email', '').lower()
    is_authorized_admin_email = is_authorized_admin(user_email) if user_email else False

    if is_authorized_admin_email:
        # Authorized admin emails bypass rate limiting entirely
        return None

    # Check if logged into admin panel (for admin dashboard operations)
    is_admin_panel_logged_in = session.get('admin_logged_in', False)

    # Determine rate limit type based on endpoint
    limit_type = 'global'

    if '/auth/' in request.path or '/login' in request.path:
        limit_type = 'auth'
    elif '/booking' in request.path:
        # Use admin rate limit for admin panel users doing booking operations (delete, update)
        # Only apply strict booking rate limit for POST requests (new bookings)
        if is_admin_panel_logged_in or request.method in ['DELETE', 'PUT']:
            limit_type = 'admin'
        else:
            limit_type = 'booking'
    elif '/admin' in request.path:
        limit_type = 'admin'
    elif '/slots' in request.path:
        limit_type = 'slots'

    # Check rate limit
    is_allowed, retry_after = RateLimiter.check_rate_limit(limit_type)

    if not is_allowed:
        config = RateLimiter.RATE_LIMITS.get(limit_type, RateLimiter.RATE_LIMITS['global'])
        response = jsonify({
            'success': False,
            'error': 'rate_limit_exceeded',
            'message': config['message'],
            'retry_after': retry_after
        })
        response.status_code = 429

        if retry_after:
            response.headers['Retry-After'] = str(retry_after)

        return response

    return None
