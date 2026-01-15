"""
LearnAI - AI Learning Management System
Professional modular Flask application with OAuth 2.0 SSO
"""

from flask import Flask
import os
import threading
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Import database
import firestore_db as db

# Import route blueprints
from routes import auth_bp, booking_bp, admin_bp, api_bp

# Import services
from services.slot_service import SlotService
from utils.datetime_utils import get_eastern_now, get_eastern_datetime

# Load environment variables
load_dotenv()

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

# Session Security
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'  # HTTPS only in production
app.config['SESSION_COOKIE_NAME'] = '__Host-session' if os.getenv('FLASK_ENV') == 'production' else 'session'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

# Additional Security
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files

# ============================================================================
# TIMEZONE UTILITY WRAPPER
# ============================================================================

class TimezoneUtil:
    """Wrapper for timezone utilities to maintain backward compatibility"""
    
    @staticmethod
    def get_eastern_now():
        return get_eastern_now()
    
    @staticmethod
    def get_eastern_datetime(dt_str):
        return get_eastern_datetime(dt_str)


# ============================================================================
# SERVICE INITIALIZATION
# ============================================================================

# Initialize slot service with database and timezone utilities
tz_util = TimezoneUtil()
slot_service = SlotService(db, tz_util)

# Initialize time slots on startup
slot_service.init_slots()

# ============================================================================
# BLUEPRINT REGISTRATION
# ============================================================================

# Register all route blueprints
app.register_blueprint(auth_bp)          # OAuth login, callback, logout
app.register_blueprint(booking_bp)       # Booking creation, update, delete
app.register_blueprint(admin_bp)         # Admin dashboard, session management
app.register_blueprint(api_bp)           # Slots, feedback, export, public pages

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

def start_background_scheduler():
    """Start background thread for morning reminders"""
    try:
        reminder_thread = threading.Thread(
            target=slot_service.morning_reminder_scheduler,
            daemon=True,
            name='MorningReminderScheduler'
        )
        reminder_thread.start()
        print("[OK] Morning reminder scheduler started")
    except Exception as e:
        print(f"[ERROR] Failed to start reminder scheduler: {e}")


# Start background scheduler when app starts
if os.getenv('FLASK_ENV') != 'development' or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
    start_background_scheduler()

# ============================================================================
# MAINTENANCE HOOK
# ============================================================================

@app.before_request
def enforce_session_timeout():
    """Enforce 24-hour session timeout for authenticated users"""
    from flask import session, redirect, url_for
    
    if session.get('authenticated'):
        # Check session age
        session_created = session.get('session_created')
        
        if session_created:
            try:
                created_time = datetime.fromisoformat(session_created)
                if datetime.now() - created_time > timedelta(hours=24):
                    # Session expired, clear it
                    session.clear()
                    return redirect(url_for('api.index', message='Your session has expired. Please sign in again.'))
            except Exception as e:
                print(f"[WARNING] Session timeout check failed: {e}")
        else:
            # First request after login, mark session creation time
            session['session_created'] = datetime.now().isoformat()


@app.before_request
def periodic_maintenance():
    """Run automatic cleanup and slot generation periodically"""
    slot_service.periodic_maintenance()


@app.before_request
def apply_rate_limiting():
    """Apply rate limiting to API endpoints"""
    from middleware.rate_limit import apply_global_rate_limit
    return apply_global_rate_limit()


@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers to all responses"""
    is_production = os.getenv('FLASK_ENV') == 'production'

    # Content Security Policy - Restrict resource loading
    # Note: 'unsafe-inline' for scripts is temporarily needed for SVG creation in displayBookingDetails
    # TODO: Remove 'unsafe-inline' after refactoring remaining innerHTML SVG code
    csp_directives = [
        "default-src 'self'",
        "script-src 'self' https://www.google.com/recaptcha/ https://www.gstatic.com/recaptcha/ https://cdn.jsdelivr.net",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",  # unsafe-inline needed for dynamic styles
        "font-src 'self' https://fonts.gstatic.com data:",
        "img-src 'self' data: https: blob:",
        "connect-src 'self' https://www.google.com/recaptcha/ https://login.microsoftonline.com https://accounts.google.com",
        "frame-src 'self' https://www.google.com/recaptcha/ https://login.microsoftonline.com",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "upgrade-insecure-requests" if is_production else ""
    ]
    response.headers['Content-Security-Policy'] = '; '.join([d for d in csp_directives if d])

    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Enable XSS protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Referrer Policy - Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions Policy - Disable unnecessary browser features
    permissions = [
        "geolocation=()",
        "microphone=()",
        "camera=()",
        "payment=()",
        "usb=()",
        "magnetometer=()",
        "gyroscope=()",
        "accelerometer=()",
        "ambient-light-sensor=()"
    ]
    response.headers['Permissions-Policy'] = ', '.join(permissions)

    # HSTS - Force HTTPS (production only)
    if is_production:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Additional security headers
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'

    # Cache control for sensitive pages
    if '/admin' in str(response.location) or '/api/' in str(response.location):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    return response

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors"""
    from flask import jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Invalid request'}), 400
    return "Bad Request", 400


@app.errorhandler(401)
def unauthorized(error):
    """Handle 401 Unauthorized errors"""
    from flask import jsonify, request, redirect, url_for
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    return redirect(url_for('api.index'))


@app.errorhandler(403)
def forbidden(error):
    """Handle 403 Forbidden errors"""
    from flask import jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return "Access Denied", 403


@app.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors"""
    from flask import jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Resource not found'}), 404
    return "Page Not Found", 404


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle 413 Payload Too Large errors"""
    from flask import jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'File too large. Maximum size is 16MB.'}), 413
    return "File too large", 413


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle 429 Rate Limit errors"""
    from flask import jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Too many requests. Please try again later.'}), 429
    return "Too Many Requests", 429


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors - Don't leak sensitive info"""
    from flask import jsonify, request
    # Log the actual error for debugging (but don't expose to user)
    print(f"[ERROR 500] Internal server error: {error}")

    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'An unexpected error occurred. Please try again.'}), 500
    return "Internal Server Error", 500


@app.errorhandler(503)
def service_unavailable(error):
    """Handle 503 Service Unavailable errors"""
    from flask import jsonify, request
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'Service temporarily unavailable. Please try again later.'}), 503
    return "Service Temporarily Unavailable", 503


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("  LearnAI - AI Learning Management System")
    print("  Professional Modular Architecture")
    print("=" * 60)
    print(f"  Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"  Port: {port}")
    print(f"  Debug: {debug}")
    print("=" * 60)
    print("\n[OK] Application initialized successfully")
    print("[OK] All services loaded")
    print("[OK] Route blueprints registered")
    print("[OK] Background scheduler active")
    print("\nServer starting...\n")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        use_reloader=debug
    )
