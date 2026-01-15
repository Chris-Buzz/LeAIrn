"""
Firestore Database Module for LearnAI Booking System

This module handles all Firestore database operations, replacing JSON file storage.
"""

import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
import pytz

# Global Firestore client
db = None

def initialize_firestore():
    """
    Initialize Firebase Admin SDK and Firestore client.

    Supports two authentication methods:
    1. Base64-encoded credentials (FIREBASE_CREDENTIALS_BASE64) - Best for Vercel
    2. JSON file path (FIREBASE_CREDENTIALS_PATH) - Best for local development

    Environment variables:
    - FIREBASE_CREDENTIALS_BASE64: Base64-encoded service account JSON
    - FIREBASE_CREDENTIALS_PATH: Path to service account JSON file
    """
    global db

    if db is not None:
        return db

    try:
        cred = None

        # Method 1: Try base64-encoded credentials (Vercel deployment)
        base64_creds = os.getenv('FIREBASE_CREDENTIALS_BASE64')
        if base64_creds:
            try:
                # Decode base64 string to JSON
                creds_json = base64.b64decode(base64_creds).decode('utf-8')
                creds_dict = json.loads(creds_json)
                cred = credentials.Certificate(creds_dict)
                print("OK: Using base64-encoded Firebase credentials")
            except Exception as e:
                print(f"WARNING: Failed to decode base64 credentials: {e}")

        # Method 2: Try file path (local development)
        if cred is None:
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                print(f"OK: Using Firebase credentials from {cred_path}")
            else:
                print(f"WARNING: Firebase credentials not found at {cred_path}")

        # If no credentials found, fall back to JSON files
        if cred is None:
            print("WARNING: No Firebase credentials found")
            print("   For Vercel: Set FIREBASE_CREDENTIALS_BASE64 environment variable")
            print("   For local: Place firebase-credentials.json in project root")
            print("   Continuing with fallback to JSON files for development...")
            return None

        # Initialize Firebase Admin
        firebase_admin.initialize_app(cred)

        # Get Firestore client
        db = firestore.client()
        print("OK: Firestore initialized successfully!")
        return db

    except Exception as e:
        print(f"ERROR: Error initializing Firestore: {e}")
        print("   Falling back to JSON file storage...")
        return None


def get_firestore_client():
    """Get the Firestore client, initializing if needed."""
    global db
    if db is None:
        db = initialize_firestore()
    return db


# ============================================================================
# BOOKINGS OPERATIONS
# ============================================================================

def get_all_bookings() -> List[Dict]:
    """
    Get all bookings from Firestore.

    Returns:
        List of booking dictionaries
    """
    db = get_firestore_client()
    if db is None:
        return []

    try:
        bookings_ref = db.collection('bookings')
        docs = bookings_ref.order_by('submission_date', direction=firestore.Query.DESCENDING).stream()

        bookings = []
        for doc in docs:
            booking = doc.to_dict()
            booking['id'] = doc.id  # Add document ID
            bookings.append(booking)

        return bookings

    except Exception as e:
        print(f"Error getting bookings: {e}")
        return []


def add_booking(booking_data: Dict) -> Optional[str]:
    """
    Add a new booking to Firestore.

    Args:
        booking_data: Dictionary containing booking information

    Returns:
        Document ID of the created booking, or None if failed
    """
    db = get_firestore_client()
    if db is None:
        return None

    try:
        # Add timestamp if not present
        if 'submission_date' not in booking_data:
            booking_data['submission_date'] = datetime.now().isoformat()

        # Add to Firestore
        result = db.collection('bookings').add(booking_data)

        # firebase_admin's add() may return a tuple (write_result, doc_ref) or a DocumentReference
        doc_id = None
        try:
            # Try tuple / sequence access
            doc_ref = result[1]
            doc_id = getattr(doc_ref, 'id', None)
        except Exception:
            # If result itself is a DocumentReference
            doc_ref = result
            doc_id = getattr(doc_ref, 'id', None)

        if not doc_id:
            print('Warning: Could not determine document id after add()')
            return None

        print(f"OK: Booking added: {doc_id}")
        return doc_id

    except Exception as e:
        print(f"Error adding booking: {e}")
        return None


def get_booking_by_id(booking_id: str) -> Optional[Dict]:
    """Get a specific booking by ID."""
    db = get_firestore_client()
    if db is None:
        return None

    try:
        doc_ref = db.collection('bookings').document(booking_id)
        doc = doc_ref.get()

        if doc.exists:
            booking = doc.to_dict()
            booking['id'] = doc.id
            return booking
        return None

    except Exception as e:
        print(f"Error getting booking: {e}")
        return None


def update_booking(booking_id: str, update_data: Dict) -> bool:
    """
    Update a booking in Firestore.

    Args:
        booking_id: Document ID of the booking
        update_data: Dictionary of fields to update

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        doc_ref = db.collection('bookings').document(booking_id)
        doc_ref.update(update_data)
        print(f"OK: Booking updated: {booking_id}")
        return True

    except Exception as e:
        print(f"Error updating booking: {e}")
        return False


def delete_booking(booking_id: str) -> bool:
    """
    Delete a booking from Firestore.

    Args:
        booking_id: Document ID of the booking

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        db.collection('bookings').document(booking_id).delete()
        print(f"OK: Booking deleted: {booking_id}")
        return True

    except Exception as e:
        print(f"Error deleting booking: {e}")
        return False


# ============================================================================
# TIME SLOTS OPERATIONS
# ============================================================================

def get_all_slots() -> List[Dict]:
    """
    Get all time slots from Firestore.

    Returns:
        List of time slot dictionaries, sorted by datetime
    """
    db = get_firestore_client()
    if db is None:
        return []

    try:
        slots_ref = db.collection('time_slots')
        docs = slots_ref.order_by('datetime').stream()

        slots = []
        for doc in docs:
            slot = doc.to_dict()
            slot['doc_id'] = doc.id  # Store Firestore doc ID separately
            slots.append(slot)

        return slots

    except Exception as e:
        print(f"Error getting slots: {e}")
        return []


def get_available_slots() -> List[Dict]:
    """Get only available (not booked) time slots."""
    db = get_firestore_client()
    if db is None:
        return []

    try:
        # Get all slots and filter in Python (avoids complex Firestore index)
        all_slots = get_all_slots()

        # Get current time in Eastern timezone
        eastern = pytz.timezone('America/New_York')
        now_eastern = datetime.now(eastern)

        # Filter for available slots in the future
        available_slots = []
        for slot in all_slots:
            # Skip booked slots
            if slot.get('booked', False):
                continue

            slot_datetime_str = slot.get('datetime', '')
            if not slot_datetime_str:
                continue

            try:
                # Parse slot datetime and convert to Eastern time for comparison
                slot_dt = datetime.fromisoformat(slot_datetime_str)
                if slot_dt.tzinfo is None:
                    # If no timezone info, assume Eastern
                    slot_dt = eastern.localize(slot_dt)
                else:
                    # Convert to Eastern for comparison
                    slot_dt = slot_dt.astimezone(eastern)

                # Only include if slot is in the future
                if slot_dt > now_eastern:
                    available_slots.append(slot)
            except Exception as e:
                print(f"Warning: Could not parse slot datetime {slot_datetime_str}: {e}")
                continue

        # Sort by datetime
        available_slots.sort(key=lambda x: x.get('datetime', ''))

        return available_slots

    except Exception as e:
        print(f"Error getting available slots: {e}")
        return []


def add_time_slot(slot_data: Dict) -> Optional[str]:
    """
    Add a new time slot to Firestore.

    Args:
        slot_data: Dictionary containing slot information
                   - datetime: Can be 'YYYY-MM-DDTHH:MM' (interpreted as Eastern) or ISO format

    Returns:
        Slot ID, or None if failed
    """
    db = get_firestore_client()
    if db is None:
        return None

    try:
        # Process datetime to ensure it's in ISO format with Eastern timezone info
        datetime_str = slot_data.get('datetime', '')
        
        if datetime_str and 'T' in datetime_str:
            # If it's in the format 'YYYY-MM-DDTHH:MM', convert to Eastern ISO
            try:
                if '+' not in datetime_str and 'Z' not in datetime_str:
                    # No timezone info, assume it's meant to be Eastern time
                    # Parse as naive datetime and add Eastern timezone
                    dt = datetime.fromisoformat(datetime_str)
                    eastern = pytz.timezone('America/New_York')
                    dt_eastern = eastern.localize(dt)
                    # Store as ISO format with timezone
                    slot_data['datetime'] = dt_eastern.isoformat()
            except Exception as e:
                print(f"Warning: Could not process datetime {datetime_str}: {e}")
        
        # Use the slot 'id' as the document ID for easy lookup
        slot_id = slot_data.get('id')
        if not slot_id:
            print("Error: Slot data must include 'id' field")
            return None

        # Check if slot already exists
        doc_ref = db.collection('time_slots').document(slot_id)
        if doc_ref.get().exists:
            print(f"WARNING:  Slot {slot_id} already exists")
            return None

        # Add the slot
        doc_ref.set(slot_data)
        print(f"OK: Time slot added: {slot_id}")
        return slot_id

    except Exception as e:
        print(f"Error adding time slot: {e}")
        return None


def update_slot(slot_id: str, update_data: Dict) -> bool:
    """
    Update a time slot in Firestore.

    Args:
        slot_id: The slot ID
        update_data: Dictionary of fields to update

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        doc_ref = db.collection('time_slots').document(slot_id)
        doc_ref.update(update_data)
        print(f"OK: Slot updated: {slot_id}")
        return True

    except Exception as e:
        print(f"Error updating slot: {e}")
        return False


def delete_slot(slot_id: str) -> bool:
    """
    Delete a time slot from Firestore.

    Args:
        slot_id: The slot ID

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        db.collection('time_slots').document(slot_id).delete()
        print(f"OK: Slot deleted: {slot_id}")
        return True

    except Exception as e:
        print(f"Error deleting slot: {e}")
        return False


def book_slot(slot_id: str, user_email: str, room: str) -> bool:
    """
    Mark a time slot as booked.

    Args:
        slot_id: The slot ID
        user_email: Email of the user booking the slot
        room: Room where the meeting will take place

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        doc_ref = db.collection('time_slots').document(slot_id)
        doc = doc_ref.get()

        if not doc.exists:
            print(f"ERROR: Slot {slot_id} not found")
            return False

        slot_data = doc.to_dict()
        if slot_data.get('booked'):
            print(f"ERROR: Slot {slot_id} already booked")
            return False

        # Book the slot
        doc_ref.update({
            'booked': True,
            'booked_by': user_email,
            'room': room
        })

        print(f"OK: Slot {slot_id} booked for {user_email}")
        return True

    except Exception as e:
        print(f"Error booking slot: {e}")
        return False


def unbook_slot(slot_id: str) -> bool:
    """
    Unbook a time slot (make it available again).

    Args:
        slot_id: The slot ID

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()
    if db is None:
        return False

    try:
        doc_ref = db.collection('time_slots').document(slot_id)
        doc_ref.update({
            'booked': False,
            'booked_by': None,
            'room': None
        })
        print(f"OK: Slot unboked: {slot_id}")
        return True

    except Exception as e:
        print(f"Error unbooking slot: {e}")
        return False


# ============================================================================
# MIGRATION & UTILITY FUNCTIONS
# ============================================================================

def migrate_from_json(bookings_file: str = 'user_data.json',
                     slots_file: str = 'schedule.json') -> bool:
    """
    Migrate existing JSON data to Firestore.

    Args:
        bookings_file: Path to bookings JSON file
        slots_file: Path to time slots JSON file

    Returns:
        True if successful, False otherwise
    """
    import json

    db = get_firestore_client()
    if db is None:
        print("ERROR: Cannot migrate: Firestore not initialized")
        return False

    try:
        # Migrate bookings
        if os.path.exists(bookings_file):
            with open(bookings_file, 'r') as f:
                bookings = json.load(f)

            for booking in bookings:
                add_booking(booking)

            print(f"OK: Migrated {len(bookings)} bookings")

        # Migrate time slots
        if os.path.exists(slots_file):
            with open(slots_file, 'r') as f:
                slots = json.load(f)

            for slot in slots:
                add_time_slot(slot)

            print(f"OK: Migrated {len(slots)} time slots")

        print("🎉 Migration complete!")
        return True

    except Exception as e:
        print(f"ERROR: Migration error: {e}")
        return False

# ==================== FEEDBACK FUNCTIONS ====================

def add_feedback(feedback_data: dict) -> Optional[str]:
    """
    Add feedback to Firestore.

    Args:
        feedback_data: Dictionary containing feedback information

    Returns:
        Feedback ID if successful, None otherwise
    """
    try:
        initialize_firestore()

        # Add timestamp if not present
        if 'timestamp' not in feedback_data:
            feedback_data['timestamp'] = datetime.now().isoformat()

        # Add to Firestore
        doc_ref = db.collection('feedback').add(feedback_data)
        feedback_id = doc_ref[1].id

        print(f"OK: Feedback added with ID: {feedback_id}")
        return feedback_id

    except Exception as e:
        print(f"ERROR: Failed to add feedback: {e}")
        return None

def get_all_feedback() -> List[dict]:
    """
    Get all feedback from Firestore.

    Returns:
        List of feedback dictionaries with IDs
    """
    try:
        initialize_firestore()

        feedback_list = []
        docs = db.collection('feedback').stream()

        for doc in docs:
            feedback = doc.to_dict()
            feedback['id'] = doc.id
            feedback_list.append(feedback)

        return feedback_list

    except Exception as e:
        print(f"ERROR: Failed to get feedback: {e}")
        return []

def get_feedback_by_booking_id(booking_id: str) -> Optional[dict]:
    """
    Get feedback for a specific booking.

    Args:
        booking_id: The booking ID to look up

    Returns:
        Feedback dictionary if found, None otherwise
    """
    try:
        initialize_firestore()

        docs = db.collection('feedback').where('booking_id', '==', booking_id).limit(1).stream()

        for doc in docs:
            feedback = doc.to_dict()
            feedback['id'] = doc.id
            return feedback

        return None

    except Exception as e:
        print(f"ERROR: Failed to get feedback by booking ID: {e}")
        return None

def store_feedback_metadata(booking_id: str, user_data: dict) -> bool:
    """
    Store user metadata for feedback association before deleting booking.

    Args:
        booking_id: The booking ID
        user_data: Dictionary with user_name and user_email

    Returns:
        True if successful, False otherwise
    """
    try:
        initialize_firestore()

        metadata = {
            'user_name': user_data.get('user_name', 'Unknown'),
            'user_email': user_data.get('user_email', 'Unknown'),
            'stored_at': datetime.now().isoformat()
        }

        # Store in feedback_metadata collection with booking_id as document ID
        db.collection('feedback_metadata').document(booking_id).set(metadata)

        print(f"OK: Feedback metadata stored for booking {booking_id}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to store feedback metadata: {e}")
        return False

def get_feedback_metadata(booking_id: str) -> Optional[dict]:
    """
    Get stored user metadata for feedback.

    Args:
        booking_id: The booking ID

    Returns:
        Dictionary with user_name and user_email, or None if not found
    """
    try:
        initialize_firestore()

        doc = db.collection('feedback_metadata').document(booking_id).get()

        if doc.exists:
            return doc.to_dict()

        return None

    except Exception as e:
        print(f"ERROR: Failed to get feedback metadata: {e}")
        return None

def store_verification_code(email: str, code: str, expires_at: str) -> bool:
    """
    Store email verification code for booking lookup.

    Args:
        email: User's email address
        code: 6-digit verification code
        expires_at: ISO format timestamp when code expires

    Returns:
        True if successful, False otherwise
    """
    try:
        initialize_firestore()

        verification_data = {
            'email': email.lower(),
            'code': code,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at,
            'used': False
        }

        # Store with email as document ID (overwrites any existing code for this email)
        db.collection('verification_codes').document(email.lower()).set(verification_data)

        print(f"OK: Verification code stored for {email}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to store verification code: {e}")
        return False

def get_verification_code(email: str) -> Optional[dict]:
    """
    Get verification code for email.

    Args:
        email: User's email address

    Returns:
        Verification code data if found and valid, None otherwise
    """
    try:
        initialize_firestore()

        doc = db.collection('verification_codes').document(email.lower()).get()

        if doc.exists:
            data = doc.to_dict()
            # Check if code has expired
            if data.get('expires_at', '') > datetime.now().isoformat():
                return data

        return None

    except Exception as e:
        print(f"ERROR: Failed to get verification code: {e}")
        return None

def mark_verification_code_used(email: str) -> bool:
    """
    Mark verification code as used.

    Args:
        email: User's email address

    Returns:
        True if successful, False otherwise
    """
    try:
        initialize_firestore()

        db.collection('verification_codes').document(email.lower()).update({'used': True})

        print(f"OK: Verification code marked as used for {email}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to mark verification code as used: {e}")
        return False

def delete_verification_code(email: str) -> bool:
    """
    Delete verification code for email.

    Args:
        email: User's email address

    Returns:
        True if successful, False otherwise
    """
    try:
        initialize_firestore()

        db.collection('verification_codes').document(email.lower()).delete()

        print(f"OK: Verification code deleted for {email}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to delete verification code: {e}")
        return False

def store_session_overview(booking_id: str, overview_data: dict) -> bool:
    """
    Store session overview/notes for a completed session.

    Args:
        booking_id: The booking ID
        overview_data: Dictionary containing session notes and metadata

    Returns:
        True if successful, False otherwise
    """
    try:
        initialize_firestore()

        overview = {
            'booking_id': booking_id,
            'notes': overview_data.get('notes', ''),
            'enhanced_notes': overview_data.get('enhanced_notes', ''),
            'user_name': overview_data.get('user_name', ''),
            'user_email': overview_data.get('user_email', ''),
            'session_date': overview_data.get('session_date', ''),
            'created_at': datetime.now().isoformat(),
            'created_by': overview_data.get('created_by', 'admin')
        }

        # Store with booking_id as document ID
        db.collection('session_overviews').document(booking_id).set(overview)

        print(f"OK: Session overview stored for booking {booking_id}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to store session overview: {e}")
        return False

def get_session_overview(booking_id: str) -> Optional[dict]:
    """
    Get session overview for a booking.

    Args:
        booking_id: The booking ID

    Returns:
        Overview data if found, None otherwise
    """
    try:
        initialize_firestore()

        doc = db.collection('session_overviews').document(booking_id).get()

        if doc.exists:
            overview = doc.to_dict()
            overview['id'] = doc.id
            return overview

        return None

    except Exception as e:
        print(f"ERROR: Failed to get session overview: {e}")
        return None

def get_all_session_overviews() -> List[dict]:
    """Get all session overviews from Firestore"""
    try:
        initialize_firestore()

        overviews = []
        docs = db.collection('session_overviews').stream()

        for doc in docs:
            overview = doc.to_dict()
            overview['id'] = doc.id
            overviews.append(overview)

        return overviews

    except Exception as e:
        print(f"ERROR: Failed to get session overviews: {e}")
        return []

def delete_session_overview(booking_id: str) -> bool:
    """Delete a session overview from Firestore"""
    try:
        initialize_firestore()

        db.collection('session_overviews').document(booking_id).delete()
        print(f"OK: Deleted session overview: {booking_id}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to delete session overview {booking_id}: {e}")
        return False


# ============================================================================
# PENDING BOOKINGS & VERIFICATION (NEW)
# ============================================================================

def store_pending_booking(email: str, code: str, expires_at: str, booking_data: dict, slot_data: dict) -> bool:
    """
    Store pending booking with verification code.

    Args:
        email: User's email address (normalized to lowercase)
        code: 6-digit verification code
        expires_at: ISO format expiration timestamp
        booking_data: Full booking data from form
        slot_data: Selected slot details

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        # Normalize email
        email = email.lower().strip()

        pending_doc = {
            'email': email,
            'code': code,
            'expires_at': expires_at,
            'created_at': datetime.now().isoformat(),
            'used': False,
            'attempts': 0,
            'booking_data': booking_data,
            'slot_data': slot_data
        }

        # Use email as document ID (overwrite if exists)
        db.collection('pending_bookings').document(email).set(pending_doc)

        print(f"OK: Stored pending booking for {email}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to store pending booking: {e}")
        return False


def get_pending_booking(email: str) -> Optional[dict]:
    """
    Get pending booking with verification code.

    Args:
        email: User's email address

    Returns:
        dict: Pending booking data or None if not found/expired
    """
    try:
        initialize_firestore()

        # Normalize email
        email = email.lower().strip()

        doc_ref = db.collection('pending_bookings').document(email)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        pending = doc.to_dict()

        # Check if expired
        expires_at = pending.get('expires_at', '')
        now = datetime.now().isoformat()

        if expires_at and expires_at < now:
            # Delete expired document
            doc_ref.delete()
            print(f"INFO: Deleted expired pending booking for {email}")
            return None

        return pending

    except Exception as e:
        print(f"ERROR: Failed to get pending booking: {e}")
        return None


def delete_pending_booking(email: str) -> bool:
    """
    Delete pending booking.

    Args:
        email: User's email address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        # Normalize email
        email = email.lower().strip()

        db.collection('pending_bookings').document(email).delete()
        print(f"OK: Deleted pending booking for {email}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to delete pending booking: {e}")
        return False


def increment_verification_attempts(email: str) -> bool:
    """
    Increment verification attempt counter.

    Args:
        email: User's email address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        # Normalize email
        email = email.lower().strip()

        doc_ref = db.collection('pending_bookings').document(email)
        doc = doc_ref.get()

        if doc.exists:
            current_attempts = doc.to_dict().get('attempts', 0)
            doc_ref.update({'attempts': current_attempts + 1})
            print(f"OK: Incremented attempts for {email} to {current_attempts + 1}")
            return True

        return False

    except Exception as e:
        print(f"ERROR: Failed to increment attempts: {e}")
        return False


def mark_pending_booking_used(email: str) -> bool:
    """
    Mark pending booking as used.

    Args:
        email: User's email address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        # Normalize email
        email = email.lower().strip()

        doc_ref = db.collection('pending_bookings').document(email)
        doc_ref.update({'used': True})
        print(f"OK: Marked pending booking as used for {email}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to mark pending booking as used: {e}")
        return False


def check_verification_rate_limit(email: str, request_type: str = 'booking') -> dict:
    """
    Check if email has exceeded verification code request rate limit.
    Limits:
    - 3 requests per hour for new bookings
    - 5 requests per hour for looking up existing bookings

    Args:
        email: User's email address
        request_type: 'booking' (3/hour) or 'lookup' (5/hour)

    Returns:
        dict: {'allowed': bool, 'wait_minutes': int}
    """
    try:
        initialize_firestore()

        # Normalize email and add request type to key
        email = email.lower().strip()
        doc_key = f"{email}_{request_type}"

        # Set limit based on request type
        limit = 5 if request_type == 'lookup' else 3

        # Get rate limit record
        doc_ref = db.collection('rate_limits').document(doc_key)
        doc = doc_ref.get()

        now = datetime.now()

        if not doc.exists:
            # First request, create record
            doc_ref.set({
                'email': email,
                'request_type': request_type,
                'requests': [{
                    'timestamp': now.isoformat()
                }],
                'last_request': now.isoformat()
            })
            return {'allowed': True, 'wait_minutes': 0}

        rate_limit = doc.to_dict()
        requests = rate_limit.get('requests', [])

        # Filter requests from last hour
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        recent_requests = [r for r in requests if r.get('timestamp', '') > one_hour_ago]

        if len(recent_requests) >= limit:
            # Rate limit exceeded
            oldest_request = min([r.get('timestamp', '') for r in recent_requests])
            oldest_dt = datetime.fromisoformat(oldest_request)
            wait_until = oldest_dt + timedelta(hours=1)
            wait_minutes = max(1, int((wait_until - now).total_seconds() / 60))

            return {'allowed': False, 'wait_minutes': wait_minutes}

        # Add new request
        recent_requests.append({'timestamp': now.isoformat()})
        doc_ref.set({
            'email': email,
            'request_type': request_type,
            'requests': recent_requests,
            'last_request': now.isoformat()
        })

        return {'allowed': True, 'wait_minutes': 0}

    except Exception as e:
        print(f"ERROR: Failed to check verification rate limit: {e}")
        # On error, allow the request
        return {'allowed': True, 'wait_minutes': 0}


def check_admin_login_rate_limit(ip_address: str) -> dict:
    """
    Check if IP address has exceeded admin login attempt rate limit.
    Limit: 5 failed attempts per hour per IP address.

    Args:
        ip_address: Client IP address

    Returns:
        dict: {'allowed': bool, 'wait_minutes': int, 'attempts': int}
    """
    try:
        initialize_firestore()

        # Normalize IP
        ip_address = str(ip_address).strip()

        # Get rate limit record
        doc_ref = db.collection('admin_login_attempts').document(ip_address)
        doc = doc_ref.get()

        now = datetime.now()

        if not doc.exists:
            # First failed attempt, create record
            doc_ref.set({
                'ip_address': ip_address,
                'attempts': [{
                    'timestamp': now.isoformat()
                }],
                'last_attempt': now.isoformat()
            })
            return {'allowed': True, 'wait_minutes': 0, 'attempts': 1}

        rate_limit = doc.to_dict()
        attempts = rate_limit.get('attempts', [])

        # Filter attempts from last hour
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        recent_attempts = [a for a in attempts if a.get('timestamp', '') > one_hour_ago]

        if len(recent_attempts) >= 5:
            # Rate limit exceeded
            oldest_attempt = min([a.get('timestamp', '') for a in recent_attempts])
            oldest_dt = datetime.fromisoformat(oldest_attempt)
            wait_until = oldest_dt + timedelta(hours=1)
            wait_minutes = max(1, int((wait_until - now).total_seconds() / 60))

            return {'allowed': False, 'wait_minutes': wait_minutes, 'attempts': len(recent_attempts)}

        # Add new attempt
        recent_attempts.append({'timestamp': now.isoformat()})
        doc_ref.set({
            'ip_address': ip_address,
            'attempts': recent_attempts,
            'last_attempt': now.isoformat()
        })

        return {'allowed': True, 'wait_minutes': 0, 'attempts': len(recent_attempts)}

    except Exception as e:
        print(f"ERROR: Failed to check admin login rate limit: {e}")
        # On error, allow the attempt
        return {'allowed': True, 'wait_minutes': 0, 'attempts': 0}


def reset_admin_login_attempts(ip_address: str) -> bool:
    """
    Reset failed login attempts for an IP (on successful login).

    Args:
        ip_address: Client IP address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        ip_address = str(ip_address).strip()
        db.collection('admin_login_attempts').document(ip_address).delete()
        print(f"OK: Reset login attempts for IP {ip_address}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to reset login attempts: {e}")
        return False


# ============================================================================
# BOOKING RATE LIMITING
# ============================================================================

def check_device_booking_rate_limit(device_id: str) -> dict:
    """
    Check if device has exceeded booking rate limit (2 bookings per 24 hours).

    Args:
        device_id: Unique device identifier

    Returns:
        dict: {'allowed': bool, 'wait_hours': int, 'bookings': int}
    """
    try:
        initialize_firestore()

        device_id = str(device_id).strip()

        # Get rate limit record
        doc_ref = db.collection('device_booking_limits').document(device_id)
        doc = doc_ref.get()

        now = datetime.now()

        if not doc.exists:
            # First booking, create record
            doc_ref.set({
                'device_id': device_id,
                'bookings': [{
                    'timestamp': now.isoformat()
                }],
                'last_booking': now.isoformat()
            })
            return {'allowed': True, 'wait_hours': 0, 'bookings': 1}

        rate_limit = doc.to_dict()
        bookings = rate_limit.get('bookings', [])

        # Filter bookings from last 24 hours
        twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
        recent_bookings = [b for b in bookings if b.get('timestamp', '') > twenty_four_hours_ago]

        if len(recent_bookings) >= 2:
            # Rate limit exceeded (2 bookings per 24 hours)
            oldest_booking = min([b.get('timestamp', '') for b in recent_bookings])
            oldest_dt = datetime.fromisoformat(oldest_booking)
            wait_until = oldest_dt + timedelta(hours=24)
            wait_hours = max(1, int((wait_until - now).total_seconds() / 3600))

            return {'allowed': False, 'wait_hours': wait_hours, 'bookings': len(recent_bookings)}

        # Add new booking
        recent_bookings.append({'timestamp': now.isoformat()})
        doc_ref.set({
            'device_id': device_id,
            'bookings': recent_bookings,
            'last_booking': now.isoformat()
        })

        return {'allowed': True, 'wait_hours': 0, 'bookings': len(recent_bookings)}

    except Exception as e:
        print(f"ERROR: Failed to check device booking rate limit: {e}")
        # On error, allow the booking
        return {'allowed': True, 'wait_hours': 0, 'bookings': 0}


def check_ip_booking_rate_limit(ip_address: str) -> dict:
    """
    Check if IP has exceeded booking rate limit (25 bookings per 24 hours).

    Args:
        ip_address: Client IP address

    Returns:
        dict: {'allowed': bool, 'wait_hours': int, 'bookings': int}
    """
    try:
        initialize_firestore()

        ip_address = str(ip_address).strip()

        # Get rate limit record
        doc_ref = db.collection('ip_booking_limits').document(ip_address)
        doc = doc_ref.get()

        now = datetime.now()

        if not doc.exists:
            # First booking, create record
            doc_ref.set({
                'ip_address': ip_address,
                'bookings': [{
                    'timestamp': now.isoformat()
                }],
                'last_booking': now.isoformat()
            })
            return {'allowed': True, 'wait_hours': 0, 'bookings': 1}

        rate_limit = doc.to_dict()
        bookings = rate_limit.get('bookings', [])

        # Filter bookings from last 24 hours
        twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
        recent_bookings = [b for b in bookings if b.get('timestamp', '') > twenty_four_hours_ago]

        if len(recent_bookings) >= 25:
            # Rate limit exceeded (25 bookings per 24 hours)
            oldest_booking = min([b.get('timestamp', '') for b in recent_bookings])
            oldest_dt = datetime.fromisoformat(oldest_booking)
            wait_until = oldest_dt + timedelta(hours=24)
            wait_hours = max(1, int((wait_until - now).total_seconds() / 3600))

            return {'allowed': False, 'wait_hours': wait_hours, 'bookings': len(recent_bookings)}

        # Add new booking
        recent_bookings.append({'timestamp': now.isoformat()})
        doc_ref.set({
            'ip_address': ip_address,
            'bookings': recent_bookings,
            'last_booking': now.isoformat()
        })

        return {'allowed': True, 'wait_hours': 0, 'bookings': len(recent_bookings)}

    except Exception as e:
        print(f"ERROR: Failed to check IP booking rate limit: {e}")
        # On error, allow the booking
        return {'allowed': True, 'wait_hours': 0, 'bookings': 0}


def record_device_booking_request(device_id: str) -> bool:
    """
    Record a device booking request for rate limiting tracking.

    Args:
        device_id: Unique device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        device_id = str(device_id).strip()
        doc_ref = db.collection('device_booking_activity').document(device_id)
        
        doc_ref.set({
            'device_id': device_id,
            'last_request': datetime.now().isoformat()
        })
        
        return True

    except Exception as e:
        print(f"ERROR: Failed to record device booking request: {e}")
        return False


def record_ip_booking_request(ip_address: str) -> bool:
    """
    Record an IP booking request for rate limiting tracking.

    Args:
        ip_address: Client IP address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        ip_address = str(ip_address).strip()
        doc_ref = db.collection('ip_booking_activity').document(ip_address)
        
        doc_ref.set({
            'ip_address': ip_address,
            'last_request': datetime.now().isoformat()
        })
        
        return True

    except Exception as e:
        print(f"ERROR: Failed to record IP booking request: {e}")
        return False


def check_email_booking_rate_limit(email: str) -> dict:
    """
    Check if email has exceeded booking rate limit (1 booking per 24 hours).

    Args:
        email: User's email address

    Returns:
        dict: {'allowed': bool, 'wait_hours': int, 'has_active_booking': bool}
    """
    try:
        initialize_firestore()

        email = str(email).strip().lower()

        # First, check if user already has an active booking
        bookings = get_all_bookings()
        for booking in bookings:
            if booking.get('email', '').lower() == email:
                return {
                    'allowed': False,
                    'wait_hours': 0,
                    'has_active_booking': True,
                    'message': 'You already have an active booking. Please cancel it first to book a new session.'
                }

        # Check rate limit record for 24-hour booking requests
        doc_ref = db.collection('email_booking_limits').document(email.replace('@', '_at_').replace('.', '_dot_'))
        doc = doc_ref.get()

        now = datetime.now()

        if not doc.exists:
            return {'allowed': True, 'wait_hours': 0, 'has_active_booking': False}

        rate_limit = doc.to_dict()
        last_booking_str = rate_limit.get('last_booking', '')

        if not last_booking_str:
            return {'allowed': True, 'wait_hours': 0, 'has_active_booking': False}

        last_booking_dt = datetime.fromisoformat(last_booking_str)
        hours_since_last = (now - last_booking_dt).total_seconds() / 3600

        if hours_since_last < 24:
            # Rate limit - can only book once per 24 hours
            wait_hours = max(1, int(24 - hours_since_last))
            return {
                'allowed': False,
                'wait_hours': wait_hours,
                'has_active_booking': False,
                'message': f'You can only book one session per day. Please try again in {wait_hours} hour{"s" if wait_hours != 1 else ""}.'
            }

        return {'allowed': True, 'wait_hours': 0, 'has_active_booking': False}

    except Exception as e:
        print(f"ERROR: Failed to check email booking rate limit: {e}")
        # On error, allow the booking
        return {'allowed': True, 'wait_hours': 0, 'has_active_booking': False}


def record_email_booking_request(email: str) -> bool:
    """
    Record an email booking request for rate limiting tracking.

    Args:
        email: User's email address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        email = str(email).strip().lower()
        doc_id = email.replace('@', '_at_').replace('.', '_dot_')
        doc_ref = db.collection('email_booking_limits').document(doc_id)

        doc_ref.set({
            'email': email,
            'last_booking': datetime.now().isoformat()
        })

        return True

    except Exception as e:
        print(f"ERROR: Failed to record email booking request: {e}")
        return False


def store_confirmed_booking(email: str, booking_data: dict, slot_data: dict) -> bool:
    """
    Store a confirmed booking in Firestore.

    Args:
        email: User's email address
        booking_data: Full booking data from form
        slot_data: Selected slot details

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        # Add the booking
        result = add_booking(booking_data)
        
        if result:
            # Mark the slot as booked
            slot_id = slot_data.get('id') or slot_data.get('doc_id')
            if slot_id:
                book_slot(slot_id, email, booking_data.get('selected_room'))
            return True
        
        return False

    except Exception as e:
        print(f"ERROR: Failed to store confirmed booking: {e}")
        return False


# ============================================================================
# TUTOR MANAGEMENT
# ============================================================================

def get_all_tutors() -> List[Dict]:
    """Get all tutors"""
    db = get_firestore_client()
    if db is None:
        return []

    try:
        tutors_ref = db.collection('tutors')
        docs = tutors_ref.stream()

        tutors = []
        for doc in docs:
            tutor_data = doc.to_dict()
            tutor_data['id'] = doc.id
            tutors.append(tutor_data)

        return tutors
    except Exception as e:
        print(f"Error getting tutors: {e}")
        return []


def get_tutor_by_id(tutor_id: str) -> Optional[Dict]:
    """Get a specific tutor by ID"""
    db = get_firestore_client()
    if db is None:
        return None

    try:
        doc_ref = db.collection('tutors').document(tutor_id)
        doc = doc_ref.get()

        if doc.exists:
            tutor_data = doc.to_dict()
            tutor_data['id'] = doc.id
            return tutor_data
        return None
    except Exception as e:
        print(f"Error getting tutor: {e}")
        return None


def get_tutor_by_username(username: str) -> Optional[Dict]:
    """Get a tutor by their admin username"""
    db = get_firestore_client()
    if db is None:
        return None

    try:
        tutors_ref = db.collection('tutors')
        query = tutors_ref.where('username', '==', username).limit(1)
        docs = list(query.stream())

        if docs:
            tutor_data = docs[0].to_dict()
            tutor_data['id'] = docs[0].id
            return tutor_data
        return None
    except Exception as e:
        print(f"Error getting tutor by username: {e}")
        return None


def add_tutor(tutor_data: Dict) -> Optional[str]:
    """Add a new tutor"""
    db = get_firestore_client()
    if db is None:
        return None

    try:
        tutors_ref = db.collection('tutors')
        doc_ref = tutors_ref.document(tutor_data.get('id', None))
        doc_ref.set(tutor_data)
        return doc_ref.id
    except Exception as e:
        print(f"Error adding tutor: {e}")
        return None


def update_tutor(tutor_id: str, updates: Dict) -> bool:
    """Update tutor information"""
    db = get_firestore_client()
    if db is None:
        return False

    try:
        doc_ref = db.collection('tutors').document(tutor_id)
        doc_ref.update(updates)
        return True
    except Exception as e:
        print(f"Error updating tutor: {e}")
        return False


def initialize_tutors():
    """Initialize default tutors if they don't exist"""
    db = get_firestore_client()
    if db is None:
        return

    from datetime import timezone
    now_utc = datetime.now(timezone.utc).isoformat()

    tutors = [
        {
            'id': 'christopher_buzaid',
            'username': 'christopher',
            'full_name': 'Christopher Buzaid',
            'email': 's1363246@monmouth.edu',
            'role': 'super_admin',  # Can see all tutors
            'max_slots_per_week': 999,  # Unlimited for super admin
            'active': True,
            'created_at': now_utc
        },
        {
            'id': 'danny',
            'username': 'danny',
            'full_name': 'Danny',
            'email': 's1323702@monmouth.edu',
            'role': 'tutor_admin',  # Can only see own slots
            'max_slots_per_week': 10,
            'active': True,
            'created_at': now_utc
        },
        {
            'id': 'kiumbura',
            'username': 'kiumbura',
            'full_name': 'Kiumbura',
            'email': 's1358017@monmouth.edu',
            'role': 'tutor_admin',  # Can only see own slots
            'max_slots_per_week': 10,
            'active': True,
            'created_at': now_utc
        }
    ]

    for tutor in tutors:
        existing = get_tutor_by_id(tutor['id'])
        if not existing:
            print(f"Creating tutor: {tutor['full_name']}")
            add_tutor(tutor)
        else:
            # Update existing tutor if email is missing or has changed
            existing_email = existing.get('email', '')
            expected_email = tutor.get('email', '')
            if expected_email and existing_email != expected_email:
                print(f"Updating tutor email: {tutor['full_name']} -> {expected_email}")
                update_tutor(tutor['id'], {'email': expected_email})
            else:
                print(f"Tutor already exists: {tutor['full_name']}")


# ============================================================================
# ADMIN OAUTH LOGIN TRACKING (For auto-admin with verification safety net)
# ============================================================================

def track_admin_oauth_login(email: str) -> int:
    """
    Track OAuth login count for admin emails and return current count.
    Used to determine when verification is required (after 10 logins).
    """
    try:
        initialize_firestore()
        email = email.lower().strip()
        doc_ref = db.collection('admin_oauth_logins').document(email)
        doc = doc_ref.get()

        now = datetime.now(timezone.utc).isoformat()

        if doc.exists:
            current_count = doc.to_dict().get('login_count', 0) + 1
            doc_ref.update({
                'login_count': current_count,
                'last_login': now
            })
            print(f"[OK] Admin OAuth login tracked: {email} (count: {current_count})")
            return current_count
        else:
            doc_ref.set({
                'email': email,
                'login_count': 1,
                'first_login': now,
                'last_login': now,
                'verified': False,
                'verified_at': None
            })
            print(f"[OK] New admin OAuth login tracked: {email}")
            return 1
    except Exception as e:
        print(f"ERROR tracking admin OAuth login: {e}")
        return 0


def get_admin_verification_status(email: str) -> dict:
    """Get admin verification status including login count."""
    try:
        initialize_firestore()
        email = email.lower().strip()
        doc = db.collection('admin_oauth_logins').document(email).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        print(f"ERROR getting admin verification status: {e}")
        return None


def store_admin_verification_code(email: str, code: str) -> bool:
    """Store a verification code for admin with 10-minute expiry."""
    try:
        initialize_firestore()
        email = email.lower().strip()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=10)

        db.collection('admin_verification_codes').document(email).set({
            'email': email,
            'code': code,
            'created_at': now.isoformat(),
            'expires_at': expires_at.isoformat()
        })
        print(f"[OK] Verification code stored for: {email}")
        return True
    except Exception as e:
        print(f"ERROR storing verification code: {e}")
        return False


def get_admin_verification_code(email: str) -> dict:
    """Get stored verification code if valid (not expired)."""
    try:
        initialize_firestore()
        email = email.lower().strip()
        doc = db.collection('admin_verification_codes').document(email).get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        expires_at = datetime.fromisoformat(data.get('expires_at', ''))
        now = datetime.now(timezone.utc)

        # Check if expired
        if now > expires_at:
            print(f"[WARN] Verification code expired for: {email}")
            return None

        return data
    except Exception as e:
        print(f"ERROR getting verification code: {e}")
        return None


def verify_admin_oauth(email: str) -> bool:
    """Mark admin as verified and reset login counter."""
    try:
        initialize_firestore()
        email = email.lower().strip()
        now = datetime.now(timezone.utc).isoformat()

        db.collection('admin_oauth_logins').document(email).update({
            'verified': True,
            'verified_at': now,
            'login_count': 0  # Reset counter after successful verification
        })

        # Delete the used verification code
        db.collection('admin_verification_codes').document(email).delete()

        print(f"[OK] Admin verified and counter reset: {email}")
        return True
    except Exception as e:
        print(f"ERROR verifying admin OAuth: {e}")
        return False


# ============================================================================
# BOOKING STATISTICS (Historical data tracking)
# ============================================================================

def get_booking_statistics() -> dict:
    """
    Get booking statistics including historical data.
    Returns stats per tutor and master totals.
    """
    try:
        initialize_firestore()
        doc = db.collection('app_statistics').document('booking_stats').get()

        if doc.exists:
            return doc.to_dict()
        else:
            # Initialize with historical data if not exists
            return initialize_booking_statistics()
    except Exception as e:
        print(f"ERROR getting booking statistics: {e}")
        return {
            'tutors': {
                'christopher_buzaid': {'total_bookings': 0, 'unique_clients': []}
            },
            'initialized': False
        }


def initialize_booking_statistics() -> dict:
    """
    Initialize booking statistics with historical data.
    Christopher: 31 total bookings, 21 unique clients
    """
    try:
        initialize_firestore()

        # Historical data - 21 unique client emails for Christopher
        # These are placeholder emails representing the 21 unique clients
        historical_clients = [
            f"historical_client_{i}@monmouth.edu" for i in range(1, 22)
        ]

        stats = {
            'tutors': {
                'christopher_buzaid': {
                    'tutor_name': 'Christopher Buzaid',
                    'total_bookings': 31,
                    'unique_clients': historical_clients
                },
                'danny': {
                    'tutor_name': 'Danny',
                    'total_bookings': 0,
                    'unique_clients': []
                },
                'kiumbura': {
                    'tutor_name': 'Kiumbura',
                    'total_bookings': 0,
                    'unique_clients': []
                }
            },
            'initialized': True,
            'initialized_at': datetime.now(timezone.utc).isoformat()
        }

        db.collection('app_statistics').document('booking_stats').set(stats)
        print("[OK] Booking statistics initialized with historical data")
        return stats
    except Exception as e:
        print(f"ERROR initializing booking statistics: {e}")
        return {'tutors': {}, 'initialized': False}


def add_completed_booking(tutor_id: str, tutor_name: str, client_email: str) -> bool:
    """
    Add a completed booking to statistics.
    Called when a booking is marked as completed.
    """
    try:
        initialize_firestore()
        doc_ref = db.collection('app_statistics').document('booking_stats')
        doc = doc_ref.get()

        if not doc.exists:
            stats = initialize_booking_statistics()
        else:
            stats = doc.to_dict()

        # Initialize tutor if not exists
        if tutor_id not in stats.get('tutors', {}):
            stats['tutors'][tutor_id] = {
                'tutor_name': tutor_name,
                'total_bookings': 0,
                'unique_clients': []
            }

        # Increment booking count
        stats['tutors'][tutor_id]['total_bookings'] += 1

        # Add unique client if not already exists
        client_email = client_email.lower().strip()
        if client_email and client_email not in stats['tutors'][tutor_id]['unique_clients']:
            stats['tutors'][tutor_id]['unique_clients'].append(client_email)

        # Update last modified
        stats['last_updated'] = datetime.now(timezone.utc).isoformat()

        doc_ref.set(stats)
        print(f"[OK] Booking stats updated for {tutor_name}: {stats['tutors'][tutor_id]['total_bookings']} total")
        return True
    except Exception as e:
        print(f"ERROR adding completed booking to stats: {e}")
        return False


def get_statistics_summary() -> dict:
    """
    Get a summary of all booking statistics for the admin dashboard.
    Returns total bookings and unique clients per tutor + master total.
    """
    try:
        stats = get_booking_statistics()

        result = {
            'tutors': {},
            'master_total': {
                'total_bookings': 0,
                'unique_clients': 0
            }
        }

        all_unique_emails = set()

        for tutor_id, tutor_data in stats.get('tutors', {}).items():
            total = tutor_data.get('total_bookings', 0)
            unique_list = tutor_data.get('unique_clients', [])

            result['tutors'][tutor_id] = {
                'tutor_name': tutor_data.get('tutor_name', tutor_id),
                'total_bookings': total,
                'unique_clients': len(unique_list)
            }

            result['master_total']['total_bookings'] += total
            all_unique_emails.update(unique_list)

        result['master_total']['unique_clients'] = len(all_unique_emails)

        return result
    except Exception as e:
        print(f"ERROR getting statistics summary: {e}")
        return {
            'tutors': {},
            'master_total': {'total_bookings': 0, 'unique_clients': 0}
        }


# ============================================================================
# ADMIN ACCOUNT MANAGEMENT WITH SECURE PASSWORD STORAGE
# ============================================================================

def create_admin_account(email: str, username: str, password: str, role: str = 'tutor_admin',
                        tutor_id: str = None, tutor_name: str = None) -> bool:
    """
    Create a new admin account with securely hashed password.

    Args:
        email: Admin email address
        username: Admin username
        password: Plain text password (will be hashed)
        role: Admin role (tutor_admin or super_admin)
        tutor_id: Optional tutor ID to associate with this admin
        tutor_name: Optional tutor name

    Returns:
        bool: True if account created successfully, False otherwise
    """
    try:
        from werkzeug.security import generate_password_hash

        client = get_firestore_client()
        if not client:
            print("ERROR: Firestore not initialized for admin account creation")
            return False

        # Check if admin with email or username already exists
        admins_ref = client.collection('admin_accounts')

        # Check email
        existing_email = admins_ref.where('email', '==', email).limit(1).get()
        if existing_email:
            print(f"ERROR: Admin account with email {email} already exists")
            return False

        # Check username
        existing_username = admins_ref.where('username', '==', username).limit(1).get()
        if existing_username:
            print(f"ERROR: Admin account with username {username} already exists")
            return False

        # Create admin account with hashed password
        admin_data = {
            'email': email.lower().strip(),
            'username': username.strip(),
            'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
            'role': role,
            'tutor_id': tutor_id or username,
            'tutor_name': tutor_name or username.capitalize(),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_password_verification': datetime.now(timezone.utc).isoformat(),
            'active': True
        }

        # Store in Firestore
        doc_ref = admins_ref.document()
        doc_ref.set(admin_data)

        print(f"[OK] Created admin account: {email} (username: {username})")
        return True

    except Exception as e:
        print(f"ERROR creating admin account: {e}")
        return False


def verify_admin_password(username: str, password: str) -> Optional[Dict]:
    """
    Verify admin password and return admin data if valid.

    Args:
        username: Admin username
        password: Plain text password to verify

    Returns:
        Dict with admin data if password is valid, None otherwise
    """
    try:
        from werkzeug.security import check_password_hash

        client = get_firestore_client()
        if not client:
            print("ERROR: Firestore not initialized for password verification")
            return None

        # Get admin by username
        admins_ref = client.collection('admin_accounts')
        query = admins_ref.where('username', '==', username).where('active', '==', True).limit(1)
        results = query.get()

        if not results:
            print(f"Admin account not found: {username}")
            return None

        admin_doc = results[0]
        admin_data = admin_doc.to_dict()
        admin_data['id'] = admin_doc.id

        # Verify password
        if check_password_hash(admin_data.get('password_hash', ''), password):
            print(f"[OK] Password verified for admin: {username}")
            return admin_data
        else:
            print(f"Invalid password for admin: {username}")
            return None

    except Exception as e:
        print(f"ERROR verifying admin password: {e}")
        return None


def get_admin_by_email(email: str) -> Optional[Dict]:
    """
    Get admin account by email address.

    Args:
        email: Admin email address

    Returns:
        Dict with admin data if found, None otherwise
    """
    try:
        client = get_firestore_client()
        if not client:
            return None

        admins_ref = client.collection('admin_accounts')
        query = admins_ref.where('email', '==', email.lower().strip()).where('active', '==', True).limit(1)
        results = query.get()

        if not results:
            return None

        admin_doc = results[0]
        admin_data = admin_doc.to_dict()
        admin_data['id'] = admin_doc.id

        return admin_data

    except Exception as e:
        print(f"ERROR getting admin by email: {e}")
        return None


def get_admin_by_username(username: str) -> Optional[Dict]:
    """
    Get admin account by username.

    Args:
        username: Admin username

    Returns:
        Dict with admin data if found, None otherwise
    """
    try:
        client = get_firestore_client()
        if not client:
            return None

        admins_ref = client.collection('admin_accounts')
        query = admins_ref.where('username', '==', username).where('active', '==', True).limit(1)
        results = query.get()

        if not results:
            return None

        admin_doc = results[0]
        admin_data = admin_doc.to_dict()
        admin_data['id'] = admin_doc.id

        return admin_data

    except Exception as e:
        print(f"ERROR getting admin by username: {e}")
        return None


def delete_admin_account_by_email(email: str) -> bool:
    """
    Delete admin account by email address (for super_admin use).

    Args:
        email: Admin email address to delete

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        client = get_firestore_client()
        if not client:
            return False

        admins_ref = client.collection('admin_accounts')
        query = admins_ref.where('email', '==', email.lower().strip()).limit(1)
        results = query.get()

        if not results:
            print(f"No admin account found for email: {email}")
            return False

        admin_doc = results[0]
        admin_doc.reference.delete()
        print(f"[OK] Deleted admin account for: {email}")
        return True

    except Exception as e:
        print(f"ERROR deleting admin account: {e}")
        return False


def update_admin_last_password_verification(username: str) -> bool:
    """
    Update the last password verification timestamp for an admin.

    Args:
        username: Admin username

    Returns:
        bool: True if updated successfully, False otherwise
    """
    try:
        client = get_firestore_client()
        if not client:
            return False

        admins_ref = client.collection('admin_accounts')
        query = admins_ref.where('username', '==', username).limit(1)
        results = query.get()

        if not results:
            return False

        admin_doc = results[0]
        admin_doc.reference.update({
            'last_password_verification': datetime.now(timezone.utc).isoformat()
        })

        print(f"[OK] Updated password verification timestamp for admin: {username}")
        return True

    except Exception as e:
        print(f"ERROR updating password verification timestamp: {e}")
        return False


def check_admin_password_verification_needed(username: str, days: int = 3) -> bool:
    """
    Check if admin needs to re-verify their password (after N days).

    Args:
        username: Admin username
        days: Number of days before re-verification is required (default: 3)

    Returns:
        bool: True if password verification is needed, False otherwise
    """
    try:
        admin = get_admin_by_username(username)
        if not admin:
            return True  # Require verification if admin not found

        last_verification_str = admin.get('last_password_verification')
        if not last_verification_str:
            return True  # Require verification if never verified

        # Parse timestamp
        last_verification = datetime.fromisoformat(last_verification_str.replace('Z', '+00:00'))
        if last_verification.tzinfo is None:
            last_verification = last_verification.replace(tzinfo=timezone.utc)

        # Check if more than N days have passed
        now = datetime.now(timezone.utc)
        time_since_verification = now - last_verification

        needs_verification = time_since_verification.days >= days

        if needs_verification:
            print(f"Admin {username} needs password re-verification (last verified {time_since_verification.days} days ago)")

        return needs_verification

    except Exception as e:
        print(f"ERROR checking password verification status: {e}")
        return True  # Err on the side of caution


# ============================================================================
# AUTHORIZED ADMIN EMAILS (Database-driven, not hardcoded)
# ============================================================================

def get_authorized_admin_by_email(email: str) -> Optional[Dict]:
    """
    Get authorized admin configuration by email address.
    This replaces the hardcoded ADMIN_OAUTH_EMAILS dictionary.

    Args:
        email: Email address to check

    Returns:
        Dict with admin config if authorized, None otherwise
    """
    try:
        db = get_firestore_client()
        if not db:
            return None

        doc = db.collection('authorized_admins').document(email.lower().strip()).get()

        if doc.exists:
            return doc.to_dict()
        return None

    except Exception as e:
        print(f"ERROR getting authorized admin: {e}")
        return None


def get_all_authorized_admins() -> List[Dict]:
    """
    Get all authorized admin emails and their configurations.

    Returns:
        List of authorized admin configs
    """
    try:
        db = get_firestore_client()
        if not db:
            return []

        docs = db.collection('authorized_admins').stream()

        admins = []
        for doc in docs:
            admin_data = doc.to_dict()
            admin_data['email'] = doc.id
            admins.append(admin_data)

        return admins

    except Exception as e:
        print(f"ERROR getting all authorized admins: {e}")
        return []


def add_authorized_admin(email: str, tutor_id: str, tutor_name: str,
                         tutor_role: str = 'tutor_admin', admin_username: str = None) -> bool:
    """
    Add a new authorized admin email.

    Args:
        email: Email address to authorize
        tutor_id: Tutor ID for this admin
        tutor_name: Display name
        tutor_role: 'super_admin' or 'tutor_admin'
        admin_username: Optional username hint

    Returns:
        bool: True if added successfully
    """
    try:
        db = get_firestore_client()
        if not db:
            return False

        admin_config = {
            'tutor_id': tutor_id,
            'tutor_name': tutor_name,
            'tutor_role': tutor_role,
            'admin_username': admin_username or tutor_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'active': True
        }

        db.collection('authorized_admins').document(email.lower().strip()).set(admin_config)
        print(f"[OK] Added authorized admin: {email} ({tutor_name})")
        return True

    except Exception as e:
        print(f"ERROR adding authorized admin: {e}")
        return False


def remove_authorized_admin(email: str) -> bool:
    """
    Remove an authorized admin email.

    Args:
        email: Email address to remove

    Returns:
        bool: True if removed successfully
    """
    try:
        db = get_firestore_client()
        if not db:
            return False

        db.collection('authorized_admins').document(email.lower().strip()).delete()
        print(f"[OK] Removed authorized admin: {email}")
        return True

    except Exception as e:
        print(f"ERROR removing authorized admin: {e}")
        return False


def initialize_authorized_admins_if_empty() -> bool:
    """
    Initialize authorized admins collection ONLY if it's empty.
    This is a one-time migration from hardcoded values to database.
    After running once, admins are managed through the database only.

    Returns:
        bool: True if initialized or already exists
    """
    try:
        client = get_firestore_client()
        if not client:
            return False

        # Check if collection already has data
        existing = list(client.collection('authorized_admins').limit(1).stream())
        if existing:
            print("[OK] Authorized admins collection already initialized")
            return True

        # Collection is empty - initialize with default admins
        # This runs ONCE on first deployment, then data lives in database only
        print("[MIGRATION] Initializing authorized_admins collection...")

        default_admins = [
            {
                'email': 's1363246@monmouth.edu',
                'tutor_id': 'christopher_buzaid',
                'tutor_name': 'Christopher Buzaid',
                'tutor_role': 'super_admin',
                'admin_username': 'christopher'
            },
            {
                'email': 'cjpbuzaid@gmail.com',
                'tutor_id': 'christopher_buzaid',
                'tutor_name': 'Christopher Buzaid',
                'tutor_role': 'super_admin',
                'admin_username': 'christopher'
            },
            {
                'email': 's1323702@monmouth.edu',
                'tutor_id': 'danny',
                'tutor_name': 'Danny',
                'tutor_role': 'tutor_admin',
                'admin_username': 'danny'
            },
            {
                'email': 's1358017@monmouth.edu',
                'tutor_id': 'kiumbura',
                'tutor_name': 'Kiumbura',
                'tutor_role': 'tutor_admin',
                'admin_username': 'kiumbura'
            }
        ]

        for admin in default_admins:
            email = admin['email']
            add_authorized_admin(
                email=email,
                tutor_id=admin['tutor_id'],
                tutor_name=admin['tutor_name'],
                tutor_role=admin['tutor_role'],
                admin_username=admin['admin_username']
            )

        print(f"[OK] Initialized {len(default_admins)} authorized admins in database")
        return True

    except Exception as e:
        print(f"ERROR initializing authorized admins: {e}")
        return False


def store_pending_account_verification(email: str, username: str, password: str,
                                       verification_token: str, role: str = 'tutor_admin',
                                       tutor_id: str = None, tutor_name: str = None) -> bool:
    """
    Store pending admin account awaiting email verification.

    Args:
        email: Admin email address
        username: Chosen username
        password: Plain text password (will be hashed before storage)
        verification_token: Unique verification token
        role: Admin role
        tutor_id: Tutor ID
        tutor_name: Tutor name

    Returns:
        bool: True if stored successfully
    """
    try:
        from werkzeug.security import generate_password_hash

        client = get_firestore_client()
        if not client:
            print("ERROR: Firestore not initialized for pending account storage")
            return False

        # Store pending account with 1-hour expiry
        pending_data = {
            'email': email.lower().strip(),
            'username': username.strip(),
            'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
            'role': role,
            'tutor_id': tutor_id or username,
            'tutor_name': tutor_name or username.capitalize(),
            'verification_token': verification_token,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }

        # Store in Firestore with token as document ID for easy lookup
        pending_ref = client.collection('pending_admin_accounts')
        pending_ref.document(verification_token).set(pending_data)

        print(f"[OK] Stored pending admin account for: {email} (token: {verification_token[:10]}...)")
        return True

    except Exception as e:
        print(f"ERROR storing pending account: {e}")
        return False


def get_pending_account_verification(verification_token: str) -> Optional[Dict]:
    """
    Get pending admin account by verification token.

    Args:
        verification_token: The verification token

    Returns:
        Dict with pending account data if found and not expired, None otherwise
    """
    try:
        client = get_firestore_client()
        if not client:
            return None

        pending_ref = client.collection('pending_admin_accounts')
        doc = pending_ref.document(verification_token).get()

        if not doc.exists:
            print(f"Pending account not found for token: {verification_token[:10]}...")
            return None

        pending_data = doc.to_dict()

        # Check if token has expired
        expires_at = datetime.fromisoformat(pending_data['expires_at'].replace('Z', '+00:00'))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now > expires_at:
            print(f"Pending account token expired: {verification_token[:10]}...")
            # Clean up expired token
            delete_pending_account_verification(verification_token)
            return None

        return pending_data

    except Exception as e:
        print(f"ERROR getting pending account: {e}")
        return None


def delete_pending_account_verification(verification_token: str) -> bool:
    """
    Delete pending admin account verification entry.

    Args:
        verification_token: The verification token

    Returns:
        bool: True if deleted successfully
    """
    try:
        client = get_firestore_client()
        if not client:
            return False

        pending_ref = client.collection('pending_admin_accounts')
        pending_ref.document(verification_token).delete()

        print(f"[OK] Deleted pending account verification: {verification_token[:10]}...")
        return True

    except Exception as e:
        print(f"ERROR deleting pending account: {e}")
        return False

# ================== User Payment Management ==================

def get_user_payment_status(email: str) -> Dict:
    """
    Get payment status for a user

    Args:
        email: User's email address

    Returns:
        Dictionary with payment status information:
        {
            'has_paid': bool,
            'payment_date': str (ISO format),
            'amount_paid': float,
            'currency': str,
            'payment_id': str,
            'is_internal': bool  # True for @monmouth.edu users
        }
    """
    try:
        email = email.lower().strip()

        # Monmouth users get free access
        if email.endswith('@monmouth.edu'):
            return {
                'has_paid': True,
                'is_internal': True,
                'free_access': True,
                'reason': 'Monmouth University student/staff'
            }

        # Check external user payment status
        users_ref = db.collection('users')
        user_doc = users_ref.document(email).get()

        if not user_doc.exists:
            return {
                'has_paid': False,
                'is_internal': False,
                'free_access': False
            }

        user_data = user_doc.to_dict()
        return {
            'has_paid': user_data.get('has_paid', False),
            'is_internal': False,
            'free_access': False,
            'payment_date': user_data.get('payment_date'),
            'amount_paid': user_data.get('amount_paid'),
            'currency': user_data.get('currency', 'USD'),
            'payment_id': user_data.get('payment_id')
        }

    except Exception as e:
        print(f"ERROR getting user payment status: {e}")
        # Default to requiring payment for safety
        return {
            'has_paid': False,
            'is_internal': False,
            'free_access': False
        }


def record_user_payment(email: str, amount: float, currency: str = 'USD',
                       payment_id: str = None) -> bool:
    """
    Record a successful payment for a user

    Args:
        email: User's email address
        amount: Payment amount
        currency: Currency code (default: USD)
        payment_id: Payment transaction ID from payment provider

    Returns:
        bool: True if successful
    """
    try:
        email = email.lower().strip()

        users_ref = db.collection('users')
        user_doc_ref = users_ref.document(email)

        payment_data = {
            'email': email,
            'has_paid': True,
            'payment_date': datetime.now(timezone.utc).isoformat(),
            'amount_paid': amount,
            'currency': currency,
            'payment_id': payment_id,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        user_doc_ref.set(payment_data, merge=True)
        print(f"[OK] Payment recorded for {email}: {amount} {currency}")
        return True

    except Exception as e:
        print(f"ERROR recording user payment: {e}")
        return False


def get_or_create_user(email: str, name: str = None, oauth_provider: str = None) -> Dict:
    """
    Get or create user document with metadata

    Args:
        email: User's email address
        name: User's display name
        oauth_provider: OAuth provider used (google, microsoft)

    Returns:
        User data dictionary
    """
    try:
        email = email.lower().strip()

        users_ref = db.collection('users')
        user_doc = users_ref.document(email).get()

        if user_doc.exists:
            return user_doc.to_dict()

        # Create new user
        is_internal = email.endswith('@monmouth.edu')

        user_data = {
            'email': email,
            'name': name or email.split('@')[0],
            'oauth_provider': oauth_provider,
            'is_internal': is_internal,
            'has_paid': is_internal,  # Monmouth users auto-approved
            'free_access': is_internal,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'banned': False,
            'missed_sessions': 0,
            'unexcused_misses': 0
        }

        users_ref.document(email).set(user_data)
        print(f"[OK] Created user: {email} (internal={is_internal})")
        return user_data

    except Exception as e:
        print(f"ERROR getting/creating user: {e}")
        return {}


def record_missed_session(email: str, excused: bool = False, reason: str = None) -> bool:
    """
    Record a missed session for a user

    Args:
        email: User's email address
        excused: Whether the miss is excused (has valid reason)
        reason: Reason for missing (if provided)

    Returns:
        bool: True if successful
    """
    try:
        email = email.lower().strip()
        user = get_or_create_user(email)

        users_ref = db.collection('users')
        user_doc_ref = users_ref.document(email)

        # Increment counters
        missed_sessions = user.get('missed_sessions', 0) + 1
        unexcused_misses = user.get('unexcused_misses', 0)

        if not excused:
            unexcused_misses += 1

        # Auto-ban external users after 2 unexcused misses
        should_ban = False
        if not user.get('is_internal', False) and unexcused_misses >= 2:
            should_ban = True

        update_data = {
            'missed_sessions': missed_sessions,
            'unexcused_misses': unexcused_misses,
            'last_missed_at': datetime.now(timezone.utc).isoformat(),
            'last_miss_reason': reason or '',
            'last_miss_excused': excused,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }

        if should_ban:
            update_data['banned'] = True
            update_data['banned_at'] = datetime.now(timezone.utc).isoformat()
            update_data['ban_reason'] = f'Automatically banned after {unexcused_misses} unexcused missed sessions'
            print(f"[WARNING] User {email} automatically banned after {unexcused_misses} unexcused misses")

        user_doc_ref.update(update_data)
        print(f"[OK] Recorded {'excused' if excused else 'unexcused'} miss for {email} (total: {unexcused_misses})")
        return True

    except Exception as e:
        print(f"ERROR recording missed session: {e}")
        return False


def is_user_banned(email: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a user is banned

    Args:
        email: User's email address

    Returns:
        Tuple of (is_banned, ban_reason)
    """
    try:
        email = email.lower().strip()

        # Monmouth users cannot be banned
        if email.endswith('@monmouth.edu'):
            return False, None

        users_ref = db.collection('users')
        user_doc = users_ref.document(email).get()

        if not user_doc.exists:
            return False, None

        user_data = user_doc.to_dict()
        is_banned = user_data.get('banned', False)
        ban_reason = user_data.get('ban_reason', 'Account suspended')

        return is_banned, ban_reason

    except Exception as e:
        print(f"ERROR checking ban status: {e}")
        return False, None


def ban_user(email: str, reason: str = 'Manually banned by administrator') -> bool:
    """
    Ban a user from the system

    Args:
        email: User's email address
        reason: Reason for banning

    Returns:
        bool: True if successful
    """
    try:
        email = email.lower().strip()

        # Cannot ban Monmouth users
        if email.endswith('@monmouth.edu'):
            print(f"[WARNING] Cannot ban Monmouth user: {email}")
            return False

        # Ensure user exists
        get_or_create_user(email)

        users_ref = db.collection('users')
        user_doc_ref = users_ref.document(email)

        user_doc_ref.update({
            'banned': True,
            'banned_at': datetime.now(timezone.utc).isoformat(),
            'ban_reason': reason,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

        print(f"[OK] Banned user: {email} - {reason}")
        return True

    except Exception as e:
        print(f"ERROR banning user: {e}")
        return False


def unban_user(email: str) -> bool:
    """
    Unban a user

    Args:
        email: User's email address

    Returns:
        bool: True if successful
    """
    try:
        email = email.lower().strip()

        users_ref = db.collection('users')
        user_doc = users_ref.document(email).get()

        if not user_doc.exists:
            print(f"[WARNING] User not found: {email}")
            return False

        users_ref.document(email).update({
            'banned': False,
            'unbanned_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

        print(f"[OK] Unbanned user: {email}")
        return True

    except Exception as e:
        print(f"ERROR unbanning user: {e}")
        return False


def reset_user_misses(email: str) -> bool:
    """
    Reset missed session counters for a user

    Args:
        email: User's email address

    Returns:
        bool: True if successful
    """
    try:
        email = email.lower().strip()

        users_ref = db.collection('users')
        user_doc = users_ref.document(email).get()

        if not user_doc.exists:
            print(f"[WARNING] User not found: {email}")
            return False

        users_ref.document(email).update({
            'missed_sessions': 0,
            'unexcused_misses': 0,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

        print(f"[OK] Reset miss counters for: {email}")
        return True

    except Exception as e:
        print(f"ERROR resetting misses: {e}")
        return False


def get_rate_limit_count(rate_key: str, window_seconds: int) -> int:
    """
    Get current request count for a rate limit key within the time window

    Args:
        rate_key: Unique key for rate limiting (e.g., "rate_limit:global:192.168.1.1")
        window_seconds: Time window in seconds

    Returns:
        int: Number of requests in the current time window
    """
    try:
        client = get_firestore_client()
        if not client:
            return 0

        rate_limits_ref = client.collection('rate_limits')
        doc = rate_limits_ref.document(rate_key).get()

        if not doc.exists:
            return 0

        data = doc.to_dict()

        # Check if window has expired
        last_reset_str = data.get('last_reset')
        if last_reset_str:
            last_reset = datetime.fromisoformat(last_reset_str.replace('Z', '+00:00'))
            if last_reset.tzinfo is None:
                last_reset = last_reset.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            time_elapsed = (now - last_reset).total_seconds()

            # If window has passed, reset counter
            if time_elapsed >= window_seconds:
                return 0

        return data.get('count', 0)

    except Exception as e:
        print(f"ERROR getting rate limit count: {e}")
        return 0


def increment_rate_limit(rate_key: str, window_seconds: int) -> bool:
    """
    Increment the request counter for a rate limit key

    Args:
        rate_key: Unique key for rate limiting
        window_seconds: Time window in seconds

    Returns:
        bool: True if successful
    """
    try:
        client = get_firestore_client()
        if not client:
            return False

        rate_limits_ref = client.collection('rate_limits')
        doc_ref = rate_limits_ref.document(rate_key)
        doc = doc_ref.get()

        now = datetime.now(timezone.utc)

        if not doc.exists:
            # Create new rate limit entry
            doc_ref.set({
                'count': 1,
                'last_reset': now.isoformat(),
                'window_seconds': window_seconds,
                'created_at': now.isoformat()
            })
            return True

        data = doc.to_dict()

        # Check if window has expired
        last_reset_str = data.get('last_reset')
        if last_reset_str:
            last_reset = datetime.fromisoformat(last_reset_str.replace('Z', '+00:00'))
            if last_reset.tzinfo is None:
                last_reset = last_reset.replace(tzinfo=timezone.utc)

            time_elapsed = (now - last_reset).total_seconds()

            # If window has passed, reset counter
            if time_elapsed >= window_seconds:
                doc_ref.set({
                    'count': 1,
                    'last_reset': now.isoformat(),
                    'window_seconds': window_seconds,
                    'updated_at': now.isoformat()
                })
                return True

        # Increment counter
        doc_ref.update({
            'count': data.get('count', 0) + 1,
            'updated_at': now.isoformat()
        })
        return True

    except Exception as e:
        print(f"ERROR incrementing rate limit: {e}")
        return False


if __name__ == "__main__":
    # Test connection
    print("Testing Firestore connection...")
    initialize_firestore()

    # Initialize tutors
    print("\nInitializing tutors...")
    initialize_tutors()

    # Initialize booking statistics with historical data
    print("\nInitializing booking statistics...")
    initialize_booking_statistics()
