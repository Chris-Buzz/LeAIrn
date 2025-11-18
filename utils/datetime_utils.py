"""
DateTime Utilities Module
Handles Eastern timezone conversions and datetime formatting.
"""

from datetime import datetime
import pytz

# Eastern timezone
EASTERN_TZ = pytz.timezone('America/New_York')


def get_eastern_now() -> datetime:
    """
    Get current time in Eastern timezone
    
    Returns:
        datetime: Current datetime in Eastern timezone (aware)
    """
    return datetime.now(EASTERN_TZ)


def get_eastern_datetime(datetime_str: str) -> datetime:
    """
    Convert ISO datetime string to Eastern timezone
    
    Args:
        datetime_str: ISO format datetime string
        
    Returns:
        datetime: Datetime in Eastern timezone (aware) or None if parsing fails
    """
    try:
        # Parse ISO format datetime
        dt = datetime.fromisoformat(datetime_str)
        
        # If naive, assume UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to Eastern
        eastern_dt = dt.astimezone(EASTERN_TZ)
        return eastern_dt
        
    except Exception as e:
        print(f"Error converting datetime to Eastern: {e}")
        return None


def format_datetime_eastern(dt: datetime, format_str: str = '%Y-%m-%d %I:%M %p %Z') -> str:
    """
    Format datetime in Eastern timezone
    
    Args:
        dt: Datetime object (timezone-aware or naive)
        format_str: strftime format string
        
    Returns:
        str: Formatted datetime string in Eastern time
    """
    try:
        # If naive, assume UTC
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        # Convert to Eastern
        eastern_dt = dt.astimezone(EASTERN_TZ)
        return eastern_dt.strftime(format_str)
        
    except Exception as e:
        print(f"Error formatting datetime: {e}")
        return str(dt)


def is_past_time(datetime_str: str) -> bool:
    """
    Check if a datetime string represents a past time (Eastern timezone)
    
    Args:
        datetime_str: ISO format datetime string
        
    Returns:
        bool: True if time is in the past, False otherwise
    """
    try:
        dt = get_eastern_datetime(datetime_str)
        if dt is None:
            return True  # Treat parsing failures as past (safe deletion)
        
        now = get_eastern_now()
        return dt < now
        
    except Exception:
        return True


def get_time_until(datetime_str: str) -> int:
    """
    Get minutes until a specific datetime (Eastern timezone)
    
    Args:
        datetime_str: ISO format datetime string
        
    Returns:
        int: Minutes until datetime (negative if in past)
    """
    try:
        dt = get_eastern_datetime(datetime_str)
        if dt is None:
            return -1
        
        now = get_eastern_now()
        delta = dt - now
        return int(delta.total_seconds() / 60)
        
    except Exception:
        return -1
