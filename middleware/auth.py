"""
Authentication Middleware Module
Provides decorators for authentication and authorization.
"""

import os
from functools import wraps
from flask import session, redirect, url_for, request, jsonify

# Cron API key for securing cron endpoints
CRON_API_KEY = os.getenv('CRON_API_KEY')


def login_required(f):
    """
    Decorator to require admin login for routes with password re-verification

    Allows access for:
    1. Admins with database accounts (admin_username exists)
    2. SSO users in pending registration state (needs_registration = True)

    Usage:
        @app.route('/admin/dashboard')
        @login_required
        def admin_dashboard():
            return render_template('admin.html')
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check for admin session
        if 'logged_in' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required', 'redirect': '/admin/login'}), 401
            return redirect(url_for('admin.admin_login'))

        # Allow access if:
        # 1. They have an admin_username (database account exists), OR
        # 2. They're an SSO user pending registration (needs_registration = True)
        has_account = 'admin_username' in session
        needs_registration = session.get('needs_registration', False)

        if not has_account and not needs_registration:
            # Not authenticated and not in pending registration state
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required', 'redirect': '/admin/login'}), 401
            return redirect(url_for('admin.admin_login'))

        # Check if password re-verification is needed (every 7 days / weekly)
        # For all admins with database accounts (both direct login and SSO)
        if has_account:
            auth_method = session.get('auth_method', '')
            # Check verification for: database login, SSO with DB account, Google with DB account
            needs_verification_check = auth_method in ['database', 'sso_database', 'google_database']

            if needs_verification_check:
                import firestore_db as db
                username = session.get('admin_username')

                # Check if verification is needed
                if username and db.check_admin_password_verification_needed(username, days=7):
                    # Redirect to password re-verification page
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': 'Authentication required', 'redirect': '/admin/login'}), 401
                    return redirect(url_for('admin.admin_verify_password'))

        return f(*args, **kwargs)
    return decorated_function


def cron_auth_required(f):
    """
    Decorator to verify cron requests are legitimate
    
    Checks for X-Cron-API-Key header or api_key query parameter
    
    Usage:
        @app.route('/api/cron/send-reminders', methods=['POST'])
        @cron_auth_required
        def cron_send_reminders():
            # Protected cron job logic
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the API key from request headers or query params
        api_key = request.headers.get('X-Cron-API-Key') or request.args.get('api_key')
        
        # Verify it matches our secret
        if not api_key or api_key != CRON_API_KEY:
            print(f"ERROR: Unauthorized cron attempt from {request.remote_addr}")
            return jsonify({
                'success': False,
                'message': 'Unauthorized - Invalid cron API key'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def oauth_required(f):
    """
    Decorator to require OAuth authentication (Monmouth SSO)
    
    Usage:
        @app.route('/api/booking/create')
        @oauth_required
        def create_booking():
            email = session.get('user_email')
            # User is authenticated via OAuth
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logged_in = session.get('logged_in', False)
        user_email = session.get('user_email')
        
        if not logged_in or not user_email:
            return jsonify({
                'success': False,
                'message': 'Authentication required. Please sign in with your Monmouth account.',
                'redirect': '/login'
            }), 401
        
        # Verify email is @monmouth.edu
        if not user_email.endswith('@monmouth.edu'):
            return jsonify({
                'success': False,
                'message': 'Invalid email domain. Must use @monmouth.edu account.'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function
