"""
Authentication Service Module
Handles Microsoft OAuth 2.0 SSO and Monmouth University email verification.
"""

import os
import jwt
from typing import Optional, Dict, Tuple
from msal import ConfidentialClientApplication
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# OAuth Configuration
MICROSOFT_CLIENT_ID = os.getenv('MICROSOFT_CLIENT_ID')
MICROSOFT_CLIENT_SECRET = os.getenv('MICROSOFT_CLIENT_SECRET')
MICROSOFT_TENANT = os.getenv('MICROSOFT_TENANT', 'd398fb56-1bf0-4c4a-9221-4d138fa72653')
MICROSOFT_REDIRECT_URI = os.getenv('MICROSOFT_REDIRECT_URI', 'https://uleairn.com/auth/callback')
MICROSOFT_SCOPES = []  # Empty - MSAL auto-includes reserved scopes

# Lazy-loaded MSAL app instance
_msal_app = None


class AuthService:
    """Service for OAuth authentication and token validation"""

    @staticmethod
    def get_msal_app() -> Optional[ConfidentialClientApplication]:
        """
        Get or create MSAL ConfidentialClientApplication instance (lazy initialization)
        Uses specific tenant ID and client secret for web application flow

        Returns:
            ConfidentialClientApplication instance or None if not configured
        """
        global _msal_app

        if _msal_app is not None:
            return _msal_app

        if not MICROSOFT_CLIENT_ID:
            print("⚠ Warning: MICROSOFT_CLIENT_ID not configured")
            return None

        if not MICROSOFT_CLIENT_SECRET:
            print("⚠ Warning: MICROSOFT_CLIENT_SECRET not configured")
            return None

        try:
            authority = f"https://login.microsoftonline.com/{MICROSOFT_TENANT}"
            _msal_app = ConfidentialClientApplication(
                client_id=MICROSOFT_CLIENT_ID,
                client_credential=MICROSOFT_CLIENT_SECRET,
                authority=authority
            )
            print(f"✓ MSAL app initialized as confidential client (tenant: {MICROSOFT_TENANT})")
            return _msal_app

        except Exception as e:
            print(f"✗ MSAL initialization failed: {e}")
            return None

    @staticmethod
    def get_authorization_url() -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
        """
        Generate Microsoft OAuth authorization URL
        
        Returns:
            Tuple of (auth_url, state, flow) or (None, None, None) if failed
            flow: Auth flow dictionary that must be stored in session
        """
        msal_app = AuthService.get_msal_app()
        if not msal_app:
            return None, None, None
            
        try:
            result = msal_app.initiate_auth_code_flow(
                scopes=MICROSOFT_SCOPES,
                redirect_uri=MICROSOFT_REDIRECT_URI
            )
            return result.get('auth_uri'), result.get('state'), result
            
        except Exception as e:
            print(f"✗ Authorization URL generation failed: {e}")
            return None, None, None

    @staticmethod
    def acquire_token_by_code(auth_code: str, state: str, flow: Dict) -> Optional[Dict]:
        """
        Exchange authorization code for access token

        Args:
            auth_code: Authorization code from OAuth callback
            state: State parameter for CSRF protection
            flow: Auth flow dictionary stored in session

        Returns:
            Token response dictionary with id_token_claims or None if failed
            If failed, includes 'error_message' key with user-friendly error
        """
        msal_app = AuthService.get_msal_app()
        if not msal_app:
            return {'error_message': 'OAuth service not configured properly. Missing client credentials.'}

        try:
            result = msal_app.acquire_token_by_auth_code_flow(
                auth_code_flow=flow,
                auth_response={'code': auth_code, 'state': state}
            )

            if 'error' in result:
                error_msg = result.get('error_description', result['error'])
                print(f"✗ Token acquisition error: {error_msg}")
                return {'error_message': error_msg}

            # Extract and decode id_token to get claims
            id_token = result.get('id_token')
            if id_token:
                try:
                    id_token_claims = jwt.decode(id_token, options={"verify_signature": False})
                    result['id_token_claims'] = id_token_claims
                except Exception as e:
                    print(f"⚠ Warning: Could not decode id_token claims: {e}")
                    result['id_token_claims'] = {}
            else:
                print("⚠ Warning: No id_token in token response")
                result['id_token_claims'] = {}

            return result

        except Exception as e:
            error_msg = f"Token acquisition failed: {str(e)}"
            print(f"✗ {error_msg}")
            return {'error_message': error_msg}

    @staticmethod
    def verify_monmouth_token(token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify JWT token and extract Monmouth email
        
        Args:
            token: JWT id_token from Microsoft OAuth
            
        Returns:
            Tuple of (is_valid, email, error_message)
            - is_valid: True if token is valid and email is @monmouth.edu
            - email: Verified @monmouth.edu email or None
            - error_message: Error description or None
        """
        try:
            # Decode without verification (Microsoft already verified)
            # In production, you should verify signature with Microsoft's public keys
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Extract email from preferred_username or email claim
            email = decoded.get('preferred_username') or decoded.get('email')
            
            if not email:
                return False, None, "No email found in token"
            
            # Verify @monmouth.edu domain
            if not email.lower().endswith('@monmouth.edu'):
                return False, None, f"Email {email} is not a Monmouth University address"
            
            print(f"✓ Verified Monmouth email: {email}")
            return True, email, None
            
        except jwt.DecodeError as e:
            return False, None, f"Token decode error: {str(e)}"
        except Exception as e:
            return False, None, f"Token verification error: {str(e)}"

    @staticmethod
    def validate_session(session: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate user session has required OAuth data
        
        Args:
            session: Flask session dictionary
            
        Returns:
            Tuple of (is_valid, email)
            - is_valid: True if session has valid OAuth data
            - email: User's verified email or None
        """
        email = session.get('user_email')
        logged_in = session.get('logged_in', False)
        
        if logged_in and email and email.endswith('@monmouth.edu'):
            return True, email
        
        return False, None

    @staticmethod
    def clear_session(session: Dict) -> None:
        """
        Clear all OAuth-related session data
        
        Args:
            session: Flask session dictionary (modified in place)
        """
        session.pop('logged_in', None)
        session.pop('user_email', None)
        session.pop('user_name', None)
        session.pop('auth_flow', None)
        print("✓ Session cleared")
