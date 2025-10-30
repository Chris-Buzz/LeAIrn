"""
Firestore Database Module for LeAIrn Booking System

This module handles all Firestore database operations, replacing JSON file storage.
"""

import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import List, Dict, Optional

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
        now = datetime.now().isoformat()

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
    return update_slot(slot_id, {
        'booked': False,
        'booked_by': None,
        'room': None
    })


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


if __name__ == "__main__":
    # Test connection
    print("Testing Firestore connection...")
    initialize_firestore()
