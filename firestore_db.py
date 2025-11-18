
import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import List, Dict, Optional
from utils.datetime_utils import get_eastern_now

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
        # Add timestamp if not present (Eastern Time)
        if 'submission_date' not in booking_data:
            booking_data['submission_date'] = get_eastern_now().isoformat()

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
        now = get_eastern_now().isoformat()

        # Filter for available slots in the future
        available_slots = [
            slot for slot in all_slots
            if not slot.get('booked', False) and slot.get('datetime', '') > now
        ]

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

    Returns:
        Slot ID, or None if failed
    """
    db = get_firestore_client()
    if db is None:
        return None

    try:
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

        # Add timestamp if not present (Eastern Time)
        if 'timestamp' not in feedback_data:
            feedback_data['timestamp'] = get_eastern_now().isoformat()

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
            'stored_at': get_eastern_now().isoformat()
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
            'created_at': get_eastern_now().isoformat(),
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
            # Check if code has expired (Eastern Time)
            if data.get('expires_at', '') > get_eastern_now().isoformat():
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
            'created_at': get_eastern_now().isoformat(),
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
            'created_at': get_eastern_now().isoformat(),
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

        # Check if expired (Eastern Time)
        expires_at = pending.get('expires_at', '')
        now = get_eastern_now().isoformat()

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


def store_confirmed_booking(email: str, booking_data: dict, slot_data: dict) -> bool:
    """
    Create a confirmed booking directly (no verification code needed).
    Used when user is authenticated via OAuth with verified @monmouth.edu email.

    Args:
        email: OAuth-authenticated user's email address
        booking_data: Full booking information including name, phone, role, etc.
        slot_data: Selected time slot details

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        # Normalize email
        email = email.lower().strip()

        # Prepare confirmed booking document
        confirmed_booking = {
            'email': email,
            'full_name': booking_data.get('full_name', ''),
            'phone': booking_data.get('phone', ''),
            'role': booking_data.get('role', ''),
            'selected_room': booking_data.get('selected_room', ''),
            'selected_slot': slot_data,
            'timestamp': booking_data.get('timestamp', get_eastern_now().isoformat()),
            'submission_date': get_eastern_now().isoformat(),
            'status': 'confirmed',
            'oauth_authenticated': True,  # Flag indicating OAuth verification
            'verification_method': 'microsoft_oauth'
        }

        # Add to Firestore bookings collection
        result = db.collection('bookings').add(confirmed_booking)

        # Extract document ID
        doc_id = None
        try:
            doc_ref = result[1]
            doc_id = getattr(doc_ref, 'id', None)
        except Exception:
            doc_ref = result
            doc_id = getattr(doc_ref, 'id', None)

        if not doc_id:
            print('ERROR: Could not determine document id for confirmed booking')
            return False

        # Mark slot as booked
        try:
            slot_doc_id = slot_data.get('doc_id') or slot_data.get('id')
            if slot_doc_id:
                db.collection('time_slots').document(slot_doc_id).update({'booked': True})
                print(f"OK: Marked slot {slot_doc_id} as booked")
        except Exception as e:
            print(f"WARNING: Failed to mark slot as booked: {e}")
            # Don't fail the entire booking if slot update fails

        print(f"OK: Confirmed booking created for {email}: {doc_id}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to store confirmed booking: {e}")
        return False


def check_verification_rate_limit(email: str, request_type: str = 'booking') -> dict:
    """
    Check if email has exceeded verification code request rate limit.
    Limits:
    - 2 requests per 24 hours for new bookings
    - 3 requests per 24 hours for resending verification codes
    - 5 requests per hour for looking up existing bookings

    Args:
        email: User's email address
        request_type: 'booking' (2/24 hours), 'resend' (3/24 hours), or 'lookup' (5/hour)

    Returns:
        dict: {'allowed': bool, 'wait_minutes': int}
    """
    try:
        initialize_firestore()

        # Normalize email and add request type to key
        email = email.lower().strip()
        doc_key = f"{email}_{request_type}"

        # Set limit and time window based on request type
        if request_type == 'lookup':
            limit = 5
            time_window_hours = 1
        elif request_type == 'resend':
            limit = 3
            time_window_hours = 24
        else:  # booking
            limit = 2
            time_window_hours = 24

        # Get rate limit record
        doc_ref = db.collection('rate_limits').document(doc_key)
        doc = doc_ref.get()

        now = get_eastern_now()

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

        # Filter requests from last time window
        time_window_ago = (now - __import__('datetime').timedelta(hours=time_window_hours)).isoformat()
        recent_requests = [r for r in requests if r.get('timestamp', '') > time_window_ago]

        if len(recent_requests) >= limit:
            # Rate limit exceeded
            oldest_request = min([r.get('timestamp', '') for r in recent_requests])
            oldest_dt = datetime.fromisoformat(oldest_request)
            wait_until = oldest_dt + __import__('datetime').timedelta(hours=time_window_hours)
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

        now = get_eastern_now()

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
        one_hour_ago = (now - __import__('datetime').timedelta(hours=1)).isoformat()
        recent_attempts = [a for a in attempts if a.get('timestamp', '') > one_hour_ago]

        if len(recent_attempts) >= 5:
            # Rate limit exceeded
            oldest_attempt = min([a.get('timestamp', '') for a in recent_attempts])
            oldest_dt = datetime.fromisoformat(oldest_attempt)
            wait_until = oldest_dt + __import__('datetime').timedelta(hours=1)
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


def check_ip_booking_rate_limit(ip_address: str) -> dict:
    """
    Check if IP address has exceeded booking request rate limit.
    Limit: 25 booking requests per 24 hours per IP address.
    This is a SECONDARY defense that allows shared networks (university wifi, offices)
    while still blocking mass spam attacks. Device fingerprinting is the PRIMARY defense.

    Args:
        ip_address: Client IP address

    Returns:
        dict: {'allowed': bool, 'wait_hours': int}
    """
    try:
        initialize_firestore()

        # Normalize IP
        ip_address = str(ip_address).strip()
        limit = 25  # Increased to allow shared networks
        time_window_hours = 24

        # Get rate limit record
        doc_ref = db.collection('ip_booking_limits').document(ip_address)
        doc = doc_ref.get()

        now = get_eastern_now()

        if not doc.exists:
            # First request from this IP, create record
            doc_ref.set({
                'ip_address': ip_address,
                'requests': [{
                    'timestamp': now.isoformat()
                }],
                'last_request': now.isoformat()
            })
            return {'allowed': True, 'wait_hours': 0}

        rate_limit = doc.to_dict()
        requests = rate_limit.get('requests', [])

        # Filter requests from last 24 hours
        time_window_ago = (now - __import__('datetime').timedelta(hours=time_window_hours)).isoformat()
        recent_requests = [r for r in requests if r.get('timestamp', '') > time_window_ago]

        if len(recent_requests) >= limit:
            # Rate limit exceeded
            oldest_request = min([r.get('timestamp', '') for r in recent_requests])
            oldest_dt = datetime.fromisoformat(oldest_request)
            wait_until = oldest_dt + __import__('datetime').timedelta(hours=time_window_hours)
            wait_seconds = (wait_until - now).total_seconds()
            wait_hours = max(1, int(wait_seconds / 3600))

            return {'allowed': False, 'wait_hours': wait_hours}

        # Add new request
        recent_requests.append({'timestamp': now.isoformat()})
        doc_ref.set({
            'ip_address': ip_address,
            'requests': recent_requests,
            'last_request': now.isoformat()
        })

        return {'allowed': True, 'wait_hours': 0}

    except Exception as e:
        print(f"ERROR: Failed to check IP booking rate limit: {e}")
        # On error, allow the booking to prevent false positives
        return {'allowed': True, 'wait_hours': 0}


def check_device_booking_rate_limit(device_id: str) -> dict:
    """
    Check if device has exceeded booking request rate limit.
    Limit: 2 booking requests per 24 hours per device.
    This is the PRIMARY defense against email bombing attacks where someone
    spams bookings with different emails from the same device.

    Args:
        device_id: Unique device fingerprint ID

    Returns:
        dict: {'allowed': bool, 'wait_hours': int, 'requests_used': int}
    """
    try:
        initialize_firestore()

        # Normalize device ID
        device_id = str(device_id).strip()
        if not device_id:
            # If no device ID provided, deny the request
            return {'allowed': False, 'wait_hours': 24, 'requests_used': 0}

        limit = 2  # Allow 2 bookings per device per day (allows corrections/mistakes)
        time_window_hours = 24

        # Get rate limit record
        doc_ref = db.collection('device_booking_limits').document(device_id)
        doc = doc_ref.get()

        now = get_eastern_now()

        if not doc.exists:
            # First request from this device, create record
            doc_ref.set({
                'device_id': device_id,
                'requests': [{
                    'timestamp': now.isoformat()
                }],
                'last_request': now.isoformat()
            })
            return {'allowed': True, 'wait_hours': 0, 'requests_used': 1}

        rate_limit = doc.to_dict()
        requests = rate_limit.get('requests', [])

        # Filter requests from last 24 hours
        time_window_ago = (now - __import__('datetime').timedelta(hours=time_window_hours)).isoformat()
        recent_requests = [r for r in requests if r.get('timestamp', '') > time_window_ago]

        if len(recent_requests) >= limit:
            # Rate limit exceeded
            oldest_request = min([r.get('timestamp', '') for r in recent_requests])
            oldest_dt = datetime.fromisoformat(oldest_request)
            wait_until = oldest_dt + __import__('datetime').timedelta(hours=time_window_hours)
            wait_seconds = (wait_until - now).total_seconds()
            wait_hours = max(1, int(wait_seconds / 3600))

            return {'allowed': False, 'wait_hours': wait_hours, 'requests_used': len(recent_requests)}

        # Add new request
        recent_requests.append({'timestamp': now.isoformat()})
        doc_ref.set({
            'device_id': device_id,
            'requests': recent_requests,
            'last_request': now.isoformat()
        })

        return {'allowed': True, 'wait_hours': 0, 'requests_used': len(recent_requests)}

    except Exception as e:
        print(f"ERROR: Failed to check device booking rate limit: {e}")
        # On error, allow the booking to prevent false positives
        return {'allowed': True, 'wait_hours': 0, 'requests_used': 0}


def record_ip_booking(ip_address: str, email: str) -> bool:
    """
    Record a successful booking for an IP address.

    Args:
        ip_address: Client IP address
        email: Email address that made the booking

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        initialize_firestore()

        ip_address = str(ip_address).strip()
        now = get_eastern_now()

        doc_ref = db.collection('ip_booking_limits').document(ip_address)
        doc_ref.set({
            'ip_address': ip_address,
            'last_booking_time': now.isoformat(),
            'last_booking_email': email,
            'updated_at': now.isoformat()
        })

        print(f"OK: Recorded booking for IP {ip_address}")
        return True

    except Exception as e:
        print(f"ERROR: Failed to record IP booking: {e}")
        return False


# ============================================================================
# INVITE CODE SYSTEM - Security measure to prevent unauthorized access
# ============================================================================

def generate_invite_codes(count: int = 10, max_uses: int = 5) -> List[Dict]:
    """
    Generate cryptographically secure invite codes.

    Args:
        count: Number of invite codes to generate (default: 10)
        max_uses: Maximum uses per code (default: 5)

    Returns:
        List of dicts with 'code' (plaintext) and 'hashed_code' (for storage)
    """
    import secrets
    import hashlib

    codes = []

    for _ in range(count):
        # Generate 16-character alphanumeric code (uppercase only for easier sharing)
        # Format: XXXX-XXXX-XXXX-XXXX for readability
        code = '-'.join([
            ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(4))
            for _ in range(4)
        ])

        # Hash the code for secure storage (SHA-256)
        hashed_code = hashlib.sha256(code.encode()).hexdigest()

        codes.append({
            'code': code,  # Plaintext (only shown once)
            'hashed_code': hashed_code,  # For storage
            'max_uses': max_uses
        })

    return codes


def store_invite_codes(codes: List[Dict]) -> bool:
    """
    Store invite codes in Firestore (hashed for security).

    Args:
        codes: List of dicts with 'hashed_code' and 'max_uses'

    Returns:
        bool: Success status
    """
    try:
        initialize_firestore()

        for code_data in codes:
            # Store hashed code with usage tracking
            doc_ref = db.collection('invite_codes').document(code_data['hashed_code'])
            doc_ref.set({
                'hashed_code': code_data['hashed_code'],
                'max_uses': code_data.get('max_uses', 5),
                'current_uses': 0,
                'created_at': get_eastern_now().isoformat(),
                'is_active': True,
                'used_by': []  # Track which emails used this code
            })

        print(f"OK: Stored {len(codes)} invite codes securely")
        return True

    except Exception as e:
        print(f"ERROR: Failed to store invite codes: {e}")
        return False


def verify_invite_code(code: str) -> Dict:
    """
    Verify an invite code and check if it's still valid.

    Args:
        code: The plaintext invite code entered by user

    Returns:
        dict: {'valid': bool, 'message': str, 'hashed_code': str or None}
    """
    try:
        initialize_firestore()

        import hashlib

        # Hash the provided code to look it up
        hashed_code = hashlib.sha256(code.strip().upper().encode()).hexdigest()

        # Look up the code
        doc_ref = db.collection('invite_codes').document(hashed_code)
        doc = doc_ref.get()

        if not doc.exists:
            return {
                'valid': False,
                'message': 'Invalid invite code',
                'hashed_code': None
            }

        code_data = doc.to_dict()

        # Check if code is active
        if not code_data.get('is_active', False):
            return {
                'valid': False,
                'message': 'This invite code has been deactivated',
                'hashed_code': None
            }

        # Check if code has remaining uses
        current_uses = code_data.get('current_uses', 0)
        max_uses = code_data.get('max_uses', 5)

        if current_uses >= max_uses:
            return {
                'valid': False,
                'message': 'This invite code has reached its maximum uses',
                'hashed_code': None
            }

        # Code is valid
        return {
            'valid': True,
            'message': 'Valid invite code',
            'hashed_code': hashed_code,
            'remaining_uses': max_uses - current_uses
        }

    except Exception as e:
        print(f"ERROR: Failed to verify invite code: {e}")
        return {
            'valid': False,
            'message': 'Error verifying code',
            'hashed_code': None
        }


def use_invite_code(hashed_code: str, email: str) -> bool:
    """
    Mark an invite code as used by incrementing usage count.

    Args:
        hashed_code: The hashed invite code
        email: Email of user who used the code

    Returns:
        bool: Success status
    """
    try:
        initialize_firestore()

        doc_ref = db.collection('invite_codes').document(hashed_code)
        doc = doc_ref.get()

        if not doc.exists:
            return False

        code_data = doc.to_dict()
        current_uses = code_data.get('current_uses', 0)
        used_by = code_data.get('used_by', [])

        # Increment usage
        doc_ref.update({
            'current_uses': current_uses + 1,
            'used_by': used_by + [{
                'email': email,
                'timestamp': get_eastern_now().isoformat()
            }],
            'last_used_at': get_eastern_now().isoformat()
        })

        print(f"OK: Invite code used by {email} ({current_uses + 1} total uses)")
        return True

    except Exception as e:
        print(f"ERROR: Failed to mark invite code as used: {e}")
        return False


def check_invite_code_access_attempts(ip_address: str) -> Dict:
    """
    Track failed invite code attempts per IP.
    Limit: 2 failed attempts per 24 hours per IP address.

    Args:
        ip_address: Client IP address

    Returns:
        dict: {'allowed': bool, 'attempts': int, 'blocked': bool, 'wait_hours': int}
    """
    try:
        initialize_firestore()

        # Normalize IP
        ip_address = str(ip_address).strip()

        # Get attempt record
        doc_ref = db.collection('invite_code_attempts').document(ip_address)
        doc = doc_ref.get()

        now = get_eastern_now()

        if not doc.exists:
            # First attempt from this IP
            return {
                'allowed': True,
                'attempts': 0,
                'blocked': False,
                'wait_hours': 0
            }

        attempt_data = doc.to_dict()
        attempt_history = attempt_data.get('attempt_history', [])

        # Filter failed attempts from last 24 hours
        time_window_ago = (now - __import__('datetime').timedelta(hours=24)).isoformat()
        recent_failed_attempts = [
            a for a in attempt_history
            if a.get('result') == 'failed' and a.get('timestamp', '') > time_window_ago
        ]

        # Check if blocked (2 failed attempts in last 24 hours)
        if len(recent_failed_attempts) >= 2:
            # Calculate wait time
            oldest_failed = min([a.get('timestamp', '') for a in recent_failed_attempts])
            oldest_dt = datetime.fromisoformat(oldest_failed)
            wait_until = oldest_dt + __import__('datetime').timedelta(hours=24)
            wait_seconds = (wait_until - now).total_seconds()
            wait_hours = max(1, int(wait_seconds / 3600))

            return {
                'allowed': False,
                'attempts': len(recent_failed_attempts),
                'blocked': True,
                'wait_hours': wait_hours
            }

        # Still have attempts remaining
        return {
            'allowed': True,
            'attempts': len(recent_failed_attempts),
            'blocked': False,
            'wait_hours': 0
        }

    except Exception as e:
        print(f"ERROR: Failed to check invite code attempts: {e}")
        # On error, allow the attempt
        return {
            'allowed': True,
            'attempts': 0,
            'blocked': False
        }


def record_failed_invite_attempt(ip_address: str) -> Dict:
    """
    Record a failed invite code attempt.
    Blocking is time-based (24 hours) and handled by check_invite_code_access_attempts.

    Args:
        ip_address: Client IP address

    Returns:
        dict: {'attempts': int, 'blocked': bool, 'wait_hours': int}
    """
    try:
        initialize_firestore()

        # Normalize IP
        ip_address = str(ip_address).strip()

        # Get or create attempt record
        doc_ref = db.collection('invite_code_attempts').document(ip_address)
        doc = doc_ref.get()

        now = get_eastern_now()

        if not doc.exists:
            # First failed attempt
            doc_ref.set({
                'ip_address': ip_address,
                'first_attempt': now.isoformat(),
                'last_attempt': now.isoformat(),
                'attempt_history': [{
                    'timestamp': now.isoformat(),
                    'result': 'failed'
                }]
            })
            return {
                'attempts': 1,
                'blocked': False,
                'wait_hours': 0
            }

        # Add new failed attempt to history
        attempt_data = doc.to_dict()
        attempt_history = attempt_data.get('attempt_history', [])

        doc_ref.update({
            'last_attempt': now.isoformat(),
            'attempt_history': attempt_history + [{
                'timestamp': now.isoformat(),
                'result': 'failed'
            }]
        })

        # Check if now blocked (2 failed attempts in last 24 hours)
        time_window_ago = (now - __import__('datetime').timedelta(hours=24)).isoformat()
        recent_failed_attempts = [
            a for a in (attempt_history + [{'timestamp': now.isoformat(), 'result': 'failed'}])
            if a.get('result') == 'failed' and a.get('timestamp', '') > time_window_ago
        ]

        is_blocked = len(recent_failed_attempts) >= 2
        wait_hours = 0

        if is_blocked:
            # Calculate wait time
            oldest_failed = min([a.get('timestamp', '') for a in recent_failed_attempts])
            oldest_dt = datetime.fromisoformat(oldest_failed)
            wait_until = oldest_dt + __import__('datetime').timedelta(hours=24)
            wait_seconds = (wait_until - now).total_seconds()
            wait_hours = max(1, int(wait_seconds / 3600))

            print(f"NOTICE: IP {ip_address} temporarily blocked for {wait_hours} hours after 2 failed invite code attempts")

        return {
            'attempts': len(recent_failed_attempts),
            'blocked': is_blocked,
            'wait_hours': wait_hours
        }

    except Exception as e:
        print(f"ERROR: Failed to record invite attempt: {e}")
        return {
            'attempts': 0,
            'blocked': False,
            'wait_hours': 0
        }


def record_successful_invite_attempt(ip_address: str) -> bool:
    """
    Record a successful invite code verification.

    Args:
        ip_address: Client IP address

    Returns:
        bool: Success status
    """
    try:
        initialize_firestore()

        # Normalize IP
        ip_address = str(ip_address).strip()

        # Get or create attempt record
        doc_ref = db.collection('invite_code_attempts').document(ip_address)
        doc = doc_ref.get()

        now = get_eastern_now()

        if not doc.exists:
            # First attempt and it succeeded
            doc_ref.set({
                'ip_address': ip_address,
                'failed_attempts': 0,
                'blocked': False,
                'verified': True,
                'verified_at': now.isoformat(),
                'attempt_history': [{
                    'timestamp': now.isoformat(),
                    'result': 'success'
                }]
            })
        else:
            # Update with successful verification
            attempt_data = doc.to_dict()
            attempt_history = attempt_data.get('attempt_history', [])

            doc_ref.update({
                'verified': True,
                'verified_at': now.isoformat(),
                'last_attempt': now.isoformat(),
                'attempt_history': attempt_history + [{
                    'timestamp': now.isoformat(),
                    'result': 'success'
                }]
            })

        print(f"OK: IP {ip_address} successfully verified invite code")
        return True

    except Exception as e:
        print(f"ERROR: Failed to record successful invite attempt: {e}")
        return False


if __name__ == "__main__":
    # Test connection
    print("Testing Firestore connection...")
    initialize_firestore()
