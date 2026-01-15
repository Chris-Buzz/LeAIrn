"""
Authentication Routes Blueprint
Handles OAuth login, callback, logout, and access checking.
"""

from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from services.auth_service import AuthService
import firestore_db as db
import random
import os
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)


def get_authorized_admin_info(email: str) -> dict:
    """
    Get authorized admin configuration from database.
    Returns None if email is not an authorized admin.

    This replaces the hardcoded ADMIN_OAUTH_EMAILS dictionary.
    Admin emails are now stored securely in Firestore 'authorized_admins' collection.
    """
    admin_info = db.get_authorized_admin_by_email(email)
    if admin_info and admin_info.get('active', True):
        return admin_info
    return None


def is_authorized_admin(email: str) -> bool:
    """Check if an email is an authorized admin."""
    return get_authorized_admin_info(email) is not None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Microsoft OAuth login initiation - redirect directly to Microsoft"""
    try:
        # Use fixed redirect URI from env if set (for domain migration)
        fixed_uri = os.getenv('MICROSOFT_REDIRECT_URI')
        if fixed_uri:
            redirect_uri = fixed_uri
        else:
            redirect_uri = url_for('auth.auth_callback', _external=True)
            # Force localhost instead of 127.0.0.1 for local development
            if '127.0.0.1' in redirect_uri:
                redirect_uri = redirect_uri.replace('127.0.0.1', 'localhost')

        auth_url, state, flow = AuthService.get_authorization_url(redirect_uri)

        if not auth_url or not flow:
            return "OAuth service temporarily unavailable. Please try again later.", 503

        session.permanent = True
        session['auth_state'] = state
        session['auth_flow'] = flow
        session.modified = True

        return redirect(auth_url)

    except Exception as e:
        return f"Failed to initiate login: {str(e)}", 500


@auth_bp.route('/auth/callback', methods=['GET', 'POST'])
def auth_callback():
    """Microsoft OAuth callback handler"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')

        if error:
            return redirect(url_for('api.index', error=f"Login failed: {error_description}"))

        if not code:
            return redirect(url_for('api.index', error="No authorization code received"))

        flow = session.get('auth_flow')
        if not flow:
            return redirect(url_for('api.index', error="Session expired. Please try again."))

        token_response = AuthService.acquire_token_by_code(code, state, flow)

        if not token_response or 'error_message' in token_response:
            error_msg = token_response.get('error_message', 'Token acquisition failed') if token_response else 'Token acquisition failed'
            return redirect(url_for('api.index', error=error_msg))

        id_token = token_response.get('id_token')
        if not id_token:
            return redirect(url_for('api.index', error="No ID token received"))

        valid, email, error_msg = AuthService.verify_monmouth_token(id_token)
        if not valid:
            return redirect(url_for('api.index', error=f"Verification failed: {error_msg}"))

        name = token_response.get('id_token_claims', {}).get('name', email.split('@')[0])

        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['user_email'] = email
        session['user_name'] = name
        session['session_created'] = datetime.now().isoformat()

        admin_info = get_authorized_admin_info(email.lower())
        if admin_info:
            db_admin = db.get_admin_by_email(email.lower())

            session.permanent = True
            session['logged_in'] = True
            session['authenticated'] = True
            session['is_admin'] = True
            session['user_email'] = email
            session['user_name'] = name
            session['tutor_email'] = email

            if db_admin:
                session.clear()
                session['logged_in'] = True
                session['authenticated'] = True
                session['is_admin'] = True
                session['admin_username'] = db_admin.get('username')
                session['tutor_id'] = db_admin.get('tutor_id') or admin_info['tutor_id']
                session['tutor_role'] = db_admin.get('role', 'tutor_admin')
                session['tutor_name'] = db_admin.get('tutor_name') or admin_info['tutor_name']
                session['tutor_email'] = email
                session['user_email'] = email
                session['user_name'] = db_admin.get('tutor_name') or admin_info['tutor_name']
                session['auth_method'] = 'sso_database'
                session['needs_registration'] = False
                session.permanent = True
                session.modified = True

                db.update_admin_last_password_verification(db_admin.get('username'))
            else:
                session.clear()
                session['logged_in'] = True
                session['authenticated'] = True
                session['is_admin'] = True
                session['tutor_id'] = admin_info['tutor_id']
                session['tutor_role'] = admin_info['tutor_role']
                session['tutor_name'] = admin_info['tutor_name']
                session['tutor_email'] = email
                session['user_email'] = email
                session['user_name'] = admin_info['tutor_name']
                session['auth_method'] = 'sso_pending'
                session['needs_registration'] = True
                session['pending_registration_email'] = email
                session.permanent = True
                session.modified = True

            session.modified = True
            return redirect('/admin', code=302)

        return redirect(url_for('api.index'))

    except Exception:
        return redirect(url_for('api.index', error="Authentication failed. Please try again."))


@auth_bp.route('/login/google', methods=['GET'])
def login_google():
    """Google OAuth login initiation"""
    try:
        # Use fixed redirect URI from env if set (for domain migration)
        fixed_uri = os.getenv('GOOGLE_REDIRECT_URI')
        if fixed_uri:
            redirect_uri = fixed_uri
        else:
            redirect_uri = url_for('auth.auth_google_callback', _external=True)
            if '127.0.0.1' in redirect_uri:
                redirect_uri = redirect_uri.replace('127.0.0.1', 'localhost')

        auth_url = AuthService.get_google_authorization_url(redirect_uri)

        if not auth_url:
            return "Google OAuth service temporarily unavailable. Please try again later.", 503

        return redirect(auth_url)

    except Exception as e:
        print(f"[ERROR] Google login initiation failed: {e}")
        return "Failed to initiate Google login", 500


@auth_bp.route('/auth/google/callback', methods=['GET'])
def auth_google_callback():
    """Google OAuth callback handler"""
    try:
        code = request.args.get('code')
        error = request.args.get('error')

        if error:
            return redirect(url_for('api.index', error=f"Login failed: {error}"))

        if not code:
            return redirect(url_for('api.index', error="No authorization code received"))

        # Use fixed redirect URI from env if set (must match what was used in login)
        fixed_uri = os.getenv('GOOGLE_REDIRECT_URI')
        if fixed_uri:
            redirect_uri = fixed_uri
        else:
            redirect_uri = url_for('auth.auth_google_callback', _external=True)
            if '127.0.0.1' in redirect_uri:
                redirect_uri = redirect_uri.replace('127.0.0.1', 'localhost')

        print(f"[DEBUG] Google callback - using redirect_uri: {redirect_uri}")
        token_response = AuthService.exchange_google_code_for_token(code, redirect_uri)

        if not token_response:
            print(f"[ERROR] Google token exchange returned None")
            return redirect(url_for('api.index', error="Failed to exchange authorization code"))

        id_token_str = token_response.get('id_token')
        if not id_token_str:
            return redirect(url_for('api.index', error="No ID token received"))

        valid, user_info, error_msg = AuthService.verify_google_token(id_token_str)

        if not valid:
            return redirect(url_for('api.index', error=f"Verification failed: {error_msg}"))

        email = user_info['email']
        name = user_info['name']

        is_monmouth = email.lower().endswith('@monmouth.edu')
        admin_info = get_authorized_admin_info(email.lower())

        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['user_email'] = email
        session['user_name'] = name
        session['oauth_provider'] = 'google'
        session['session_created'] = datetime.now().isoformat()

        if is_monmouth:
            session['user_type'] = 'internal'
        else:
            session['user_type'] = 'external'

        if admin_info:
            db_admin = db.get_admin_by_email(email.lower())

            if db_admin:
                session['is_admin'] = True
                session['admin_username'] = db_admin.get('username')
                session['tutor_id'] = db_admin.get('tutor_id') or admin_info['tutor_id']
                session['tutor_role'] = db_admin.get('role', 'tutor_admin')
                session['tutor_name'] = db_admin.get('tutor_name') or admin_info['tutor_name']
                session['tutor_email'] = email
                session['user_email'] = email
                session['user_name'] = db_admin.get('tutor_name') or admin_info['tutor_name']
                session['auth_method'] = 'google_database'
                session['needs_registration'] = False

                db.update_admin_last_password_verification(db_admin.get('username'))
                return redirect('/admin')
            else:
                session['is_admin'] = True
                session['tutor_id'] = admin_info['tutor_id']
                session['tutor_role'] = admin_info['tutor_role']
                session['tutor_name'] = admin_info['tutor_name']
                session['tutor_email'] = email
                session['auth_method'] = 'google_pending'
                session['needs_registration'] = True
                session['pending_registration_email'] = email

                return redirect('/admin')

        return redirect(url_for('api.index'))

    except Exception:
        return redirect(url_for('api.index', error="Authentication failed. Please try again."))


@auth_bp.route('/logout')
def logout():
    """Clear session and logout user"""
    AuthService.clear_session(session)
    return redirect(url_for('api.index'))


@auth_bp.route('/api/check-access', methods=['GET'])
def check_access():
    """Check if the current session has Monmouth SSO authentication"""
    try:
        is_valid, email = AuthService.validate_session(session)

        if is_valid:
            return jsonify({
                'has_access': True,
                'message': 'Authenticated via Monmouth SSO',
                'email': email
            }), 200
        else:
            return jsonify({
                'has_access': False,
                'message': 'Please sign in with your Monmouth University account'
            }), 200

    except Exception:
        return jsonify({
            'has_access': False,
            'message': 'Error checking authentication'
        }), 500


@auth_bp.route('/admin-verify', methods=['GET', 'POST'])
def admin_verify():
    """Admin verification page - required after 10 OAuth logins as security measure"""
    pending_email = session.get('pending_admin_email')
    pending_admin_info = session.get('pending_admin_info')

    if not pending_email or not pending_admin_info:
        return redirect(url_for('api.index'))

    error = None

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        stored = db.get_admin_verification_code(pending_email)

        if stored and stored.get('code') == code:
            db.verify_admin_oauth(pending_email)

            session['admin_username'] = pending_admin_info['admin_username']
            session['tutor_id'] = pending_admin_info['tutor_id']
            session['tutor_role'] = pending_admin_info['tutor_role']
            session['tutor_name'] = pending_admin_info['tutor_name']
            session['tutor_email'] = pending_email

            session.pop('pending_admin_email', None)
            session.pop('pending_admin_info', None)

            return redirect(url_for('admin.admin'))
        else:
            error = 'Invalid or expired verification code. Please try again.'

    if request.method == 'GET' or error:
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        db.store_admin_verification_code(pending_email, code)

        from services.email_service import EmailService
        EmailService.send_admin_verification_code(pending_email, code, pending_admin_info['tutor_name'])

    return render_template('admin_verify.html', error=error, email=pending_email)
