"""
Firestore Database Module for LeAIrn Booking System

This module handles all Firestore database operations, replacing JSON file storage.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import List, Dict, Optional

# Global Firestore client
db = None

def initialize_firestore():
    """
    Initialize Firebase Admin SDK and Firestore client.

    Uses firebase-credentials.json file for authentication.
    Set FIREBASE_CREDENTIALS_PATH environment variable or place file in project root.
    """
    global db

    if db is not None:
        return db

    try:
        # Get credentials path from environment or use default
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')

        if not os.path.exists(cred_path):
            print(f"WARNING:  WARNING: Firebase credentials not found at {cred_path}")
            print("   Please download from Firebase Console → Project Settings → Service Accounts")
            print("   Continuing with fallback to JSON files for development...")
            return None

        # Initialize Firebase Admin
        cred = credentials.Certificate(cred_path)
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


if __name__ == "__main__":
    # Test connection
    print("Testing Firestore connection...")
    initialize_firestore()
