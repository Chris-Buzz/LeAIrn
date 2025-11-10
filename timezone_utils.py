"""
Timezone utility functions for handling Eastern Time conversions.
Root-level module for use across the entire application.
"""
from datetime import datetime
import pytz

# Eastern timezone
EASTERN = pytz.timezone('America/New_York')


def get_eastern_now():
    """Get current time in Eastern timezone"""
    return datetime.now(EASTERN)


def get_eastern_datetime(dt_str):
    """
    Convert ISO datetime string to Eastern timezone.

    Args:
        dt_str: ISO format datetime string

    Returns:
        datetime object in Eastern timezone, or None if parsing fails
    """
    if not dt_str:
        return None
    try:
        # Parse the datetime string
        if 'Z' in dt_str:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        elif '+' in dt_str or dt_str.count('-') > 2:
            dt = datetime.fromisoformat(dt_str)
        else:
            # Assume naive datetime is already in Eastern
            dt = datetime.fromisoformat(dt_str)
            dt = EASTERN.localize(dt)
            return dt
        # Convert to Eastern
        return dt.astimezone(EASTERN)
    except Exception as e:
        print(f"Error parsing datetime '{dt_str}': {e}")
        return None
