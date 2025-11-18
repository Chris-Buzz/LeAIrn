"""
LeAIrn - AI Learning Management System
Professional modular Flask application with OAuth 2.0 SSO
"""

from flask import Flask
import os
import threading
from dotenv import load_dotenv

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
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

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
def periodic_maintenance():
    """Run automatic cleanup and slot generation periodically"""
    slot_service.periodic_maintenance()

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return "Page not found", 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return "Internal server error", 500


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    print("=" * 60)
    print("  LeAIrn - AI Learning Management System")
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