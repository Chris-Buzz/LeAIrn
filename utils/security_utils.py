"""
Security Utilities Module
Handles reCAPTCHA verification and security-related functions.
"""

import os
import requests


def verify_recaptcha(recaptcha_token: str) -> tuple:
    """
    Verify reCAPTCHA v3 token with Google
    
    Args:
        recaptcha_token: reCAPTCHA token from client
        
    Returns:
        tuple: (success: bool, score: float, error: str or None)
    """
    recaptcha_secret = os.getenv('RECAPTCHA_SECRET_KEY')
    
    if not recaptcha_secret:
        print("[WARNING] Warning: RECAPTCHA_SECRET_KEY not configured")
        return False, 0.0, "reCAPTCHA not configured"
    
    try:
        # Verify with Google
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': recaptcha_secret,
                'response': recaptcha_token
            },
            timeout=5
        )
        
        result = response.json()
        
        if not result.get('success'):
            error_codes = result.get('error-codes', [])
            print(f"[ERROR] reCAPTCHA verification failed: {error_codes}")
            return False, 0.0, f"Verification failed: {', '.join(error_codes)}"
        
        score = result.get('score', 0.0)
        action = result.get('action', '')
        
        print(f"[OK] reCAPTCHA verified: score={score}, action={action}")
        
        # Check score threshold (0.3 is lenient, adjust as needed)
        if score < 0.3:
            print(f"[WARNING] Low reCAPTCHA score: {score}")
            return False, score, f"Score too low: {score}"
        
        return True, score, None
        
    except requests.exceptions.Timeout:
        print("[ERROR] reCAPTCHA verification timeout")
        return False, 0.0, "Verification timeout"
    except Exception as e:
        print(f"[ERROR] reCAPTCHA verification error: {e}")
        return False, 0.0, str(e)


def validate_email_domain(email: str, allowed_domain: str = '@monmouth.edu') -> bool:
    """
    Validate email belongs to allowed domain
    
    Args:
        email: Email address to validate
        allowed_domain: Required email domain (with @)
        
    Returns:
        bool: True if email matches allowed domain
    """
    if not email:
        return False
    
    return email.lower().endswith(allowed_domain.lower())


def generate_booking_id() -> str:
    """
    Generate a unique booking ID
    
    Returns:
        str: Unique booking identifier
    """
    import uuid
    return f"book_{uuid.uuid4().hex[:12]}"


def generate_verification_token() -> str:
    """
    Generate a random 6-digit verification code
    
    Returns:
        str: 6-digit verification code
    """
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])
