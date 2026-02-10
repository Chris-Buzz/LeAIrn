"""
Authentication Routes Blueprint
Handles OAuth login, callback, logout, and access checking.
"""

from flask import Blueprint, request, session, redirect, url_for, jsonify, render_template
from services.auth_service import AuthService
import firestore_db as db
import random
import secrets
import re
import os
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta, timezone

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
        # Generate the natural redirect URI first
        natural_uri = url_for('auth.auth_callback', _external=True)
        is_localhost = 'localhost' in natural_uri or '127.0.0.1' in natural_uri

        # Use fixed redirect URI from env only in production (not localhost)
        fixed_uri = os.getenv('MICROSOFT_REDIRECT_URI')
        if fixed_uri and not is_localhost:
            redirect_uri = fixed_uri
        else:
            redirect_uri = natural_uri
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
        import traceback
        traceback.print_exc()
        return "Failed to initiate login. Please try again later.", 500


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
        stored_state = session.get('auth_state')
        if not flow:
            return redirect(url_for('api.index', error="Session expired. Please try again."))

        # Validate OAuth state parameter to prevent CSRF
        if not stored_state or not hmac.compare_digest(stored_state, state):
            return redirect(url_for('api.index', error="Invalid authentication state. Please try again."))

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
                # Use authorized_admins role as source of truth, fall back to admin_accounts
                session['tutor_role'] = admin_info.get('tutor_role') or db_admin.get('role', 'tutor_admin')
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

    except Exception as e:
        print(f"[ERROR] Auth callback failed: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('api.index', error="Authentication failed. Please try again."))


@auth_bp.route('/login/google', methods=['GET'])
def login_google():
    """Google OAuth login initiation"""
    try:
        # Generate the natural redirect URI first
        natural_uri = url_for('auth.auth_google_callback', _external=True)
        is_localhost = 'localhost' in natural_uri or '127.0.0.1' in natural_uri

        # Use fixed redirect URI from env only in production (not localhost)
        fixed_uri = os.getenv('GOOGLE_REDIRECT_URI')
        if fixed_uri and not is_localhost:
            redirect_uri = fixed_uri
        else:
            redirect_uri = natural_uri
            if '127.0.0.1' in redirect_uri:
                redirect_uri = redirect_uri.replace('127.0.0.1', 'localhost')

        auth_url = AuthService.get_google_authorization_url(redirect_uri)

        if not auth_url:
            return "Google OAuth service temporarily unavailable. Please try again later.", 503

        # Generate CSRF state token for Google OAuth
        state = secrets.token_urlsafe(32)
        session['google_oauth_state'] = state

        # Append state parameter to the authorization URL
        auth_url = auth_url + f'&state={state}'

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

        # Validate CSRF state parameter to prevent cross-site request forgery
        state = request.args.get('state')
        stored_state = session.pop('google_oauth_state', None)
        if not stored_state or not state:
            return redirect(url_for('api.index', error='Authentication failed: missing state parameter'))
        if not hmac.compare_digest(stored_state, state):
            return redirect(url_for('api.index', error='Authentication failed: invalid state parameter'))

        # Generate the natural redirect URI first
        natural_uri = url_for('auth.auth_google_callback', _external=True)
        is_localhost = 'localhost' in natural_uri or '127.0.0.1' in natural_uri

        # Use fixed redirect URI from env only in production (not localhost)
        fixed_uri = os.getenv('GOOGLE_REDIRECT_URI')
        if fixed_uri and not is_localhost:
            redirect_uri = fixed_uri
        else:
            redirect_uri = natural_uri
            if '127.0.0.1' in redirect_uri:
                redirect_uri = redirect_uri.replace('127.0.0.1', 'localhost')

        print(f"[DEBUG] Google callback - using redirect_uri: {redirect_uri}")
        token_response = AuthService.exchange_google_code_for_token(code, redirect_uri)

        # Check for error in response
        if 'error' in token_response:
            error_type = token_response.get('error', 'unknown')
            error_desc = token_response.get('error_description', 'Unknown error')
            print(f"[ERROR] Google token exchange failed: {error_type} - {error_desc}")
            # Show specific error to help debugging
            if error_type == 'redirect_uri_mismatch':
                return redirect(url_for('api.index', error="OAuth: redirect_uri_mismatch - URI not registered in Google Console"))
            elif error_type == 'invalid_client':
                return redirect(url_for('api.index', error="OAuth: invalid_client - Check GOOGLE_CLIENT_SECRET"))
            elif error_type == 'invalid_grant':
                return redirect(url_for('api.index', error="OAuth: invalid_grant - Code expired or already used"))
            elif error_type == 'config_error':
                return redirect(url_for('api.index', error=f"OAuth config: {error_desc}"))
            else:
                return redirect(url_for('api.index', error=f"OAuth: {error_type}"))

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
                # Use authorized_admins role as source of truth, fall back to admin_accounts
                session['tutor_role'] = admin_info.get('tutor_role') or db_admin.get('role', 'tutor_admin')
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

    except Exception as e:
        print(f"[ERROR] Google auth callback failed: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('api.index', error="Authentication failed. Please try again."))


SSO_SHARED_SECRET = os.getenv("SSO_SHARED_SECRET", "")
ALLOWED_SSO_ORIGIN = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


@auth_bp.route('/auth/sso', methods=['POST'])
def sso_login():
    """SSO bridge from React MVP.

    Validates an HMAC-signed token generated by Backend-MVP and creates a
    Flask session identical to what the standard OAuth flow would produce.
    Token is delivered via hidden form POST (not URL) to avoid leaking in
    browser history, Referer headers, and server logs.
    """
    if not SSO_SHARED_SECRET:
        return redirect(url_for('api.index', error="Authentication unavailable"))

    # Validate Origin (prevents cross-origin form submission from malicious sites)
    origin = (request.headers.get('Origin') or '').rstrip('/')
    if not origin:
        # Fallback to Referer (some browsers omit Origin on form POST)
        referer = request.headers.get('Referer', '')
        origin = '/'.join(referer.split('/')[:3]) if referer else ''
    if origin and origin != ALLOWED_SSO_ORIGIN:
        print(f"[AUTH SSO] Rejected: invalid origin")
        return redirect(url_for('api.index', error="Authentication failed"))

    # Token comes via POST form body (hidden form submission from React)
    sso_token = request.form.get('token', '')
    if not sso_token:
        return redirect(url_for('api.index', error="Authentication failed"))

    # Validate size and format before any processing
    if len(sso_token) > 2000 or sso_token.count('.') != 1:
        print("[AUTH SSO] Rejected: invalid token size or format")
        return redirect(url_for('api.index', error="Authentication failed"))

    try:
        payload_b64, sig_b64 = sso_token.split('.')

        # Verify HMAC-SHA256 signature (timing-safe comparison)
        expected_sig = hmac.new(
            SSO_SHARED_SECRET.encode(), payload_b64.encode(), hashlib.sha256
        ).digest()

        try:
            provided_sig = base64.urlsafe_b64decode(sig_b64.encode())
        except Exception:
            print("[AUTH SSO] Rejected: bad signature encoding")
            return redirect(url_for('api.index', error="Authentication failed"))

        if not hmac.compare_digest(expected_sig, provided_sig):
            print("[AUTH SSO] Rejected: signature mismatch")
            return redirect(url_for('api.index', error="Authentication failed"))

        # Decode payload
        try:
            payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode('utf-8')
            payload = json.loads(payload_json)
        except Exception:
            print("[AUTH SSO] Rejected: bad payload encoding")
            return redirect(url_for('api.index', error="Authentication failed"))

        email = (payload.get('email') or '').lower()
        # Basic email format validation (must have exactly one @ with content on both sides)
        if not email or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            print("[AUTH SSO] Rejected: invalid email format")
            return redirect(url_for('api.index', error="Authentication failed"))
        # Sanitize name: strip HTML tags, limit length
        raw_name = payload.get('name', email.split('@')[0])
        name = re.sub(r'<[^>]+>', '', str(raw_name)).strip()[:100] or 'User'
        # Whitelist valid providers (prevents arbitrary values in session)
        allowed_providers = {'email', 'google', 'azure', 'microsoft', 'github', 'apple'}
        provider = payload.get('provider', 'email')
        if provider not in allowed_providers:
            provider = 'unknown'
        exp = payload.get('exp', 0)
        nonce = str(payload.get('jti', ''))

        # Validate nonce format (secrets.token_urlsafe(32) produces ~43 chars)
        if not nonce or len(nonce) < 20 or len(nonce) > 100 or not re.match(r'^[A-Za-z0-9_-]+$', nonce):
            print("[AUTH SSO] Rejected: invalid nonce format")
            return redirect(url_for('api.index', error="Authentication failed"))

        # Validate expiry is a reasonable integer
        if not isinstance(exp, (int, float)) or exp <= 0:
            print("[AUTH SSO] Rejected: invalid expiry")
            return redirect(url_for('api.index', error="Authentication failed"))
        exp = int(exp)

        # Check expiry (must be in the past-to-near-future window)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > exp:
            print("[AUTH SSO] Rejected: token expired")
            return redirect(url_for('api.index', error="Authentication failed"))
        # Reject tokens expiring too far in the future (max 120s leeway for clock skew)
        if exp > now_ts + 120:
            print("[AUTH SSO] Rejected: expiry too far in future")
            return redirect(url_for('api.index', error="Authentication failed"))

        # Atomic nonce check-and-store (replay prevention)
        if not db.claim_sso_nonce(nonce, exp):
            print(f"[AUTH SSO] Rejected: nonce already used or DB error")
            return redirect(url_for('api.index', error="Authentication failed"))

        # Build session (identical to OAuth callback)
        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['user_email'] = email
        session['user_name'] = name
        session['oauth_provider'] = f'sso_{provider}'
        session['session_created'] = datetime.now().isoformat()

        # Monmouth email → free internal user
        is_monmouth = email.endswith('@monmouth.edu')
        session['user_type'] = 'internal' if is_monmouth else 'external'

        print(f"[AUTH SSO] OK: session created (type={'internal' if is_monmouth else 'external'})")

        # Handle admin users (same logic as Google/Microsoft OAuth callbacks)
        admin_info = get_authorized_admin_info(email)
        if admin_info:
            db_admin = db.get_admin_by_email(email)
            if db_admin:
                session['is_admin'] = True
                session['admin_username'] = db_admin.get('username')
                session['tutor_id'] = db_admin.get('tutor_id') or admin_info['tutor_id']
                session['tutor_role'] = admin_info.get('tutor_role') or db_admin.get('role', 'tutor_admin')
                session['tutor_name'] = db_admin.get('tutor_name') or admin_info['tutor_name']
                session['tutor_email'] = email
                session['auth_method'] = 'sso_database'
                session['needs_registration'] = False
                db.update_admin_last_password_verification(db_admin.get('username'))
                return redirect('/admin')
            else:
                session['is_admin'] = True
                session['tutor_id'] = admin_info['tutor_id']
                session['tutor_role'] = admin_info['tutor_role']
                session['tutor_name'] = admin_info['tutor_name']
                session['tutor_email'] = email
                session['auth_method'] = 'sso_pending'
                session['needs_registration'] = True
                session['pending_registration_email'] = email
                return redirect('/admin')

        return redirect(url_for('api.index'))

    except Exception as e:
        print(f"[AUTH SSO] Validation error: {e}")
        return redirect(url_for('api.index', error="Authentication failed"))


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

    except Exception as e:
        print(f"[ERROR] Auth check failed: {e}")
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

        if stored and hmac.compare_digest(stored.get('code', ''), code):
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
        code = ''.join([str(secrets.choice(range(10))) for _ in range(6)])
        db.store_admin_verification_code(pending_email, code)

        from services.email_service import EmailService
        EmailService.send_admin_verification_code(pending_email, code, pending_admin_info['tutor_name'])

    return render_template('admin_verify.html', error=error, email=pending_email)
