"""
Network Utilities Module
Handles IP address detection and network-related functions.
"""

from flask import request


def get_client_ip() -> str:
    """
    Get client's real IP address (handles proxies)
    
    Returns:
        str: Client's IP address
    """
    # Check common proxy headers in order of reliability
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can contain multiple IPs, take the first one
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    elif request.headers.get('CF-Connecting-IP'):  # Cloudflare
        return request.headers.get('CF-Connecting-IP')
    else:
        return request.remote_addr


def format_wait_time(minutes: int) -> str:
    """
    Format wait time in a human-readable format
    
    Args:
        minutes: Number of minutes to wait
        
    Returns:
        str: Formatted wait time (e.g., "2 hours", "45 minutes")
    """
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    
    hours = minutes // 60
    remaining_mins = minutes % 60
    
    if remaining_mins == 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    
    return f"{hours} hour{'s' if hours != 1 else ''} {remaining_mins} minute{'s' if remaining_mins != 1 else ''}"


def is_localhost(ip: str) -> bool:
    """
    Check if IP address is localhost
    
    Args:
        ip: IP address string
        
    Returns:
        bool: True if localhost, False otherwise
    """
    localhost_ips = ['127.0.0.1', '::1', 'localhost']
    return ip in localhost_ips


def is_private_ip(ip: str) -> bool:
    """
    Check if IP address is in a private range
    
    Args:
        ip: IP address string
        
    Returns:
        bool: True if private IP, False otherwise
    """
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        # Check private IP ranges
        if parts[0] == '10':
            return True
        if parts[0] == '172' and 16 <= int(parts[1]) <= 31:
            return True
        if parts[0] == '192' and parts[1] == '168':
            return True
        
        return False
    except Exception:
        return False
