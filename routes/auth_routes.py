"""
Authentication Routes Blueprint
Handles OAuth login, callback, logout, and access checking.
"""

from flask import Blueprint, request, session, redirect, url_for, jsonify
from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Microsoft OAuth login initiation - redirect directly to Microsoft"""
    try:
        auth_url, state, flow = AuthService.get_authorization_url()
        
        if not auth_url or not flow:
            return "OAuth service temporarily unavailable. Please try again later.", 503
        
        # Store state and flow in session for CSRF protection and callback
        session['auth_state'] = state
        session['auth_flow'] = flow
        
        # Redirect directly to Microsoft login
        return redirect(auth_url)
        
    except Exception as e:
        print(f"Error initiating OAuth: {e}")
        return f"Failed to initiate login: {str(e)}", 500


@auth_bp.route('/auth/callback', methods=['GET', 'POST'])
def auth_callback():
    """Microsoft OAuth callback handler"""
    try:
        # Get authorization code from query params
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        error_description = request.args.get('error_description')
        
        # Check for errors from Microsoft
        if error:
            print(f"OAuth error: {error} - {error_description}")
            return redirect(url_for('api.index', error=f"Login failed: {error_description}"))
        
        if not code:
            return redirect(url_for('api.index', error="No authorization code received"))
        
        # Retrieve flow from session
        flow = session.get('auth_flow')
        if not flow:
            return redirect(url_for('api.index', error="Session expired. Please try again."))
        
        # Exchange authorization code for token
        token_response = AuthService.acquire_token_by_code(code, state, flow)

        # Check for error in response
        if not token_response or 'error_message' in token_response:
            error_msg = token_response.get('error_message', 'Token acquisition failed') if token_response else 'Token acquisition failed'
            print(f"Token acquisition failed: {error_msg}")
            return redirect(url_for('api.index', error=error_msg))

        # Get ID token
        id_token = token_response.get('id_token')
        if not id_token:
            return redirect(url_for('api.index', error="No ID token received"))
        
        # Verify token and get email
        valid, email, error_msg = AuthService.verify_monmouth_token(id_token)
        if not valid:
            print(f"Token verification failed: {error_msg}")
            return redirect(url_for('api.index', error=f"Verification failed: {error_msg}"))
        
        # Extract name from token
        name = token_response.get('id_token_claims', {}).get('name', email.split('@')[0])
        
        # Create session
        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['user_email'] = email
        session['user_name'] = name
        
        print(f"✓ User authenticated: {email} ({name})")
        
        # Redirect to home page
        return redirect(url_for('api.index'))
        
    except Exception as e:
        print(f"Error in auth callback: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('api.index', error="Authentication failed. Please try again."))


@auth_bp.route('/logout')
def logout():
    """Clear session and logout user"""
    AuthService.clear_session(session)
    print("User logged out")
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
        print(f"ERROR in check_access: {e}")
        return jsonify({
            'has_access': False,
            'message': 'Error checking authentication'
        }), 500
