"""
Input Validation and Sanitization Utilities
Provides secure input validation for corporate-grade security
"""

import re
from typing import Any, Optional, Tuple
from html import escape


class InputValidator:
    """Corporate-grade input validation and sanitization"""

    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_PATTERN = re.compile(r'^\+?1?\d{9,15}$')  # International phone format
    NAME_PATTERN = re.compile(r'^[a-zA-Z\s\-\.\']{2,100}$')
    ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_]{1,255}$')

    # Max lengths for different field types
    MAX_LENGTH_NAME = 100
    MAX_LENGTH_EMAIL = 255
    MAX_LENGTH_SHORT_TEXT = 255
    MAX_LENGTH_LONG_TEXT = 5000
    MAX_LENGTH_COMMENT = 10000

    @staticmethod
    def sanitize_string(value: Any, max_length: int = MAX_LENGTH_SHORT_TEXT) -> str:
        """
        Sanitize string input by escaping HTML and limiting length

        Args:
            value: Input value to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if value is None:
            return ''

        # Convert to string and strip whitespace
        sanitized = str(value).strip()

        # Remove null bytes (security risk)
        sanitized = sanitized.replace('\x00', '')

        # Escape HTML to prevent XSS
        sanitized = escape(sanitized)

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """
        Validate email format

        Args:
            email: Email address to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"

        email = email.strip().lower()

        if len(email) > InputValidator.MAX_LENGTH_EMAIL:
            return False, "Email address is too long"

        if not InputValidator.EMAIL_PATTERN.match(email):
            return False, "Invalid email format"

        return True, ""

    @staticmethod
    def validate_name(name: str, field_name: str = "Name") -> Tuple[bool, str]:
        """
        Validate name fields (full name, etc.)

        Args:
            name: Name to validate
            field_name: Name of the field for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name:
            return False, f"{field_name} is required"

        name = name.strip()

        if len(name) < 2:
            return False, f"{field_name} must be at least 2 characters"

        if len(name) > InputValidator.MAX_LENGTH_NAME:
            return False, f"{field_name} is too long (max {InputValidator.MAX_LENGTH_NAME} characters)"

        if not InputValidator.NAME_PATTERN.match(name):
            return False, f"{field_name} contains invalid characters"

        return True, ""

    @staticmethod
    def validate_phone(phone: str, required: bool = False) -> Tuple[bool, str]:
        """
        Validate phone number

        Args:
            phone: Phone number to validate
            required: Whether phone is required

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not phone:
            if required:
                return False, "Phone number is required"
            return True, ""  # Optional field

        # Remove common phone formatting characters
        cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone.strip())

        if not InputValidator.PHONE_PATTERN.match(cleaned):
            return False, "Invalid phone number format"

        return True, ""

    @staticmethod
    def validate_choice(value: str, allowed_choices: list, field_name: str = "Field") -> Tuple[bool, str]:
        """
        Validate that value is in allowed choices

        Args:
            value: Value to validate
            allowed_choices: List of allowed values
            field_name: Name of the field for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, f"{field_name} is required"

        if value not in allowed_choices:
            return False, f"Invalid {field_name.lower()}"

        return True, ""

    @staticmethod
    def validate_text_length(text: str, min_length: int = 0, max_length: int = MAX_LENGTH_LONG_TEXT,
                            field_name: str = "Field", required: bool = True) -> Tuple[bool, str]:
        """
        Validate text field length

        Args:
            text: Text to validate
            min_length: Minimum required length
            max_length: Maximum allowed length
            field_name: Name of the field for error messages
            required: Whether field is required

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            if required:
                return False, f"{field_name} is required"
            return True, ""  # Optional field

        text = text.strip()
        text_length = len(text)

        if text_length < min_length:
            return False, f"{field_name} must be at least {min_length} characters"

        if text_length > max_length:
            return False, f"{field_name} must be less than {max_length} characters"

        return True, ""

    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None,
                        field_name: str = "Value") -> Tuple[bool, str, Optional[int]]:
        """
        Validate and convert integer value

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Name of the field for error messages

        Returns:
            Tuple of (is_valid, error_message, converted_value)
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid integer", None

        if min_val is not None and int_value < min_val:
            return False, f"{field_name} must be at least {min_val}", None

        if max_val is not None and int_value > max_val:
            return False, f"{field_name} must be at most {max_val}", None

        return True, "", int_value

    @staticmethod
    def validate_boolean(value: Any) -> bool:
        """
        Safely convert value to boolean

        Args:
            value: Value to convert

        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')

        return bool(value)

    @staticmethod
    def validate_slot_id(slot_id: str) -> Tuple[bool, str]:
        """
        Validate slot ID format

        Args:
            slot_id: Slot ID to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not slot_id:
            return False, "Slot ID is required"

        slot_id = slot_id.strip()

        # Slot IDs should be alphanumeric with underscores (format: YYYYMMDDHHMI_tutorID)
        if not re.match(r'^[a-zA-Z0-9_]+$', slot_id):
            return False, "Invalid slot ID format"

        if len(slot_id) > 100:
            return False, "Slot ID is too long"

        return True, ""

    @staticmethod
    def sanitize_booking_data(data: dict) -> Tuple[bool, dict, Optional[str]]:
        """
        Comprehensive validation and sanitization for booking data

        Args:
            data: Raw booking data dictionary

        Returns:
            Tuple of (is_valid, sanitized_data, error_message)
        """
        errors = []
        sanitized = {}

        # Validate and sanitize full_name
        full_name = data.get('full_name') or ''
        full_name = full_name.strip() if full_name else ''
        is_valid, error = InputValidator.validate_name(full_name, "Full name")
        if not is_valid:
            errors.append(error)
        else:
            sanitized['full_name'] = InputValidator.sanitize_string(full_name, InputValidator.MAX_LENGTH_NAME)

        # Validate role
        allowed_roles = ['student', 'faculty', 'staff', 'other']
        role = data.get('role') or ''
        role = role.strip().lower() if role else ''
        is_valid, error = InputValidator.validate_choice(role, allowed_roles, "Role")
        if not is_valid:
            errors.append(error)
        else:
            sanitized['role'] = role

        # Validate slot ID
        slot_id = data.get('selected_slot') or ''
        slot_id = slot_id.strip() if slot_id else ''
        is_valid, error = InputValidator.validate_slot_id(slot_id)
        if not is_valid:
            errors.append(error)
        else:
            sanitized['selected_slot'] = slot_id

        # Validate room (required)
        room = data.get('selected_room') or ''
        room = room.strip() if room else ''
        is_valid, error = InputValidator.validate_text_length(room, min_length=1, max_length=100,
                                                              field_name="Room selection")
        if not is_valid:
            errors.append(error)
        else:
            sanitized['selected_room'] = InputValidator.sanitize_string(room, 100)

        # Optional fields with sanitization
        optional_text_fields = {
            'department': 255,
            'ai_familiarity': 255,
            'ai_tools': 500,
            'primary_use': 500,
            'learning_goal': 1000,
            'personal_comments': InputValidator.MAX_LENGTH_COMMENT
        }

        for field, max_len in optional_text_fields.items():
            value = data.get(field) or ''
            value = value.strip() if value else ''
            if value:
                is_valid, error = InputValidator.validate_text_length(value, max_length=max_len,
                                                                      field_name=field.replace('_', ' ').title(),
                                                                      required=False)
                if not is_valid:
                    errors.append(error)
                else:
                    sanitized[field] = InputValidator.sanitize_string(value, max_len)
            else:
                sanitized[field] = ''

        # Validate phone (optional)
        phone = data.get('phone') or ''
        phone = phone.strip() if phone else ''
        is_valid, error = InputValidator.validate_phone(phone, required=False)
        if not is_valid:
            errors.append(error)
        else:
            sanitized['phone'] = InputValidator.sanitize_string(phone, 20)

        # Validate confidence level
        confidence = data.get('confidence_level', 3)
        is_valid, error, value = InputValidator.validate_integer(confidence, min_val=1, max_val=5,
                                                                 field_name="Confidence level")
        if not is_valid:
            errors.append(error)
        else:
            sanitized['confidence_level'] = value

        # Research consent (boolean)
        sanitized['research_consent'] = InputValidator.validate_boolean(data.get('research_consent'))

        # Device ID validation
        device_id = data.get('device_id') or ''
        device_id = device_id.strip() if device_id else ''
        if device_id:
            # Device IDs should be alphanumeric with hyphens and underscores
            if re.match(r'^[a-zA-Z0-9\-_]+$', device_id) and len(device_id) <= 100:
                sanitized['device_id'] = device_id
            else:
                errors.append("Invalid device ID")
        else:
            # Generate a device ID if not provided (for backwards compatibility)
            import uuid
            sanitized['device_id'] = f"auto_{uuid.uuid4().hex[:16]}"

        # Meeting type validation (zoom or in-person)
        meeting_type = data.get('meeting_type') or 'in-person'
        meeting_type = meeting_type.strip().lower() if meeting_type else 'in-person'
        allowed_meeting_types = ['zoom', 'in-person']
        if meeting_type not in allowed_meeting_types:
            meeting_type = 'in-person'  # Default to in-person if invalid
        sanitized['meeting_type'] = meeting_type

        # Attendee count validation
        attendee_count = data.get('attendee_count', 1)
        is_valid, error, value = InputValidator.validate_integer(attendee_count, min_val=1, max_val=50,
                                                                 field_name="Attendee count")
        if not is_valid:
            sanitized['attendee_count'] = 1  # Default to 1 if invalid
        else:
            sanitized['attendee_count'] = value

        # Return results
        if errors:
            return False, {}, "; ".join(errors)

        return True, sanitized, None
