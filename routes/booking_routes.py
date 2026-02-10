"""
Booking Routes Blueprint
Handles all booking-related operations (create, update, delete, lookup).
"""

from flask import Blueprint, request, session, jsonify
from datetime import datetime
import firestore_db as db
from utils import get_client_ip
from utils.validators import InputValidator
from services.email_service import EmailService
from middleware.auth import login_required
from middleware.rate_limit import rate_limit


def send_email_sync(email_func, *args, **kwargs):
    """Send email synchronously - guaranteed delivery on serverless"""
    try:
        func_name = email_func.__name__ if hasattr(email_func, '__name__') else str(email_func)
        print(f"[EMAIL] Sending: {func_name}")
        result = email_func(*args, **kwargs)
        if result:
            print(f"[EMAIL OK] {func_name} sent successfully")
        else:
            print(f"[EMAIL FAILED] {func_name} returned False - check SMTP credentials")
        return result
    except Exception as e:
        import traceback
        print(f"[EMAIL ERROR] {func_name} failed: {e}")
        traceback.print_exc()
        return False


def send_booking_emails(user_email, user_name, slot_data, user_data):
    """Send both booking confirmation and admin notification emails"""
    results = {'confirmation': False, 'admin': False}

    # Send user confirmation email
    try:
        results['confirmation'] = send_email_sync(
            EmailService.send_booking_confirmation,
            user_email, user_name, slot_data
        )
    except Exception as e:
        print(f"[EMAIL ERROR] Confirmation email failed: {e}")

    # Send admin notification email
    try:
        results['admin'] = send_email_sync(
            EmailService.send_admin_notification,
            user_data, slot_data
        )
    except Exception as e:
        print(f"[EMAIL ERROR] Admin notification failed: {e}")

    print(f"[EMAIL SUMMARY] Confirmation: {'OK' if results['confirmation'] else 'FAILED'}, Admin: {'OK' if results['admin'] else 'FAILED'}")
    return results

booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/api/booking/request-verification', methods=['POST'])
@rate_limit('booking')
def request_booking_verification():
    """Create booking directly using OAuth-authenticated email (no verification code needed)"""
    try:
        # Check if user is authenticated via OAuth
        if not session.get('authenticated'):
            return jsonify({
                'success': False,
                'message': 'You must sign in with your Monmouth University account to make a booking.'
            }), 401

        data = request.json

        # SECURITY: Get authenticated email from session ONLY (ignore any email in request body)
        email = session.get('user_email')

        if not email:
            return jsonify({
                'success': False,
                'message': 'Session expired. Please sign in again.'
            }), 401

        # Validate email format (defense in depth)
        is_valid, error = InputValidator.validate_email(email)
        if not is_valid:
            return jsonify({'success': False, 'message': 'Invalid session email'}), 401

        # Comprehensive input validation and sanitization
        is_valid, sanitized_data, error_message = InputValidator.sanitize_booking_data(data)
        if not is_valid:
            print(f"[VALIDATION ERROR] {error_message} | Data: role={data.get('role')}, slot={data.get('selected_slot')}")
            return jsonify({
                'success': False,
                'message': f'Validation error: {error_message}'
            }), 400

        # OAuth provides strong authentication - no additional verification needed
        print(f"[OK] Proceeding with booking - user authenticated via OAuth ({email})")

        # Check if user is banned
        is_banned, ban_reason = db.is_user_banned(email)
        if is_banned:
            return jsonify({
                'success': False,
                'banned': True,
                'message': f'Your account has been suspended. Reason: {ban_reason}',
                'ban_reason': ban_reason
            }), 403

        # Check email-based rate limiting (1 booking per 24 hours per email)
        email_rate_limit = db.check_email_booking_rate_limit(email)
        if not email_rate_limit['allowed']:
            if email_rate_limit.get('has_active_booking'):
                return jsonify({
                    'success': False,
                    'message': email_rate_limit.get('message', 'You already have an active booking.'),
                    'has_active_booking': True
                }), 400
            else:
                wait_hours = email_rate_limit['wait_hours']
                return jsonify({
                    'success': False,
                    'message': email_rate_limit.get('message', f'You can only book one session per day. Please try again in {wait_hours} hour{"s" if wait_hours != 1 else ""}.'),
                    'rate_limited': True,
                    'wait_hours': wait_hours
                }), 429

        # Check payment status for external users (but allow booking with payment pending)
        payment_status = db.get_user_payment_status(email)
        is_internal = payment_status.get('is_internal', False)
        has_paid = payment_status.get('has_paid', False)
        payment_pending = not is_internal and not has_paid

        # Check device-based rate limiting (2 bookings/24hrs per device)
        device_id = sanitized_data.get('device_id')
        if device_id:
            device_rate_limit = db.check_device_booking_rate_limit(device_id)
            if not device_rate_limit['allowed']:
                wait_hours = device_rate_limit['wait_hours']
                return jsonify({
                    'success': False,
                    'message': f'You have reached the limit of 2 booking requests per day from this device. Please try again in {wait_hours} hour{"s" if wait_hours != 1 else ""}.',
                    'rate_limited': True,
                    'wait_hours': wait_hours
                }), 429
        else:
            return jsonify({
                'success': False,
                'message': 'Security verification failed. Please enable JavaScript and try again.',
                'rate_limited': True
            }), 400

        # Check IP-based rate limiting (25 bookings/24hrs per IP)
        client_ip = get_client_ip()
        ip_rate_limit = db.check_ip_booking_rate_limit(client_ip)
        if not ip_rate_limit['allowed']:
            wait_hours = ip_rate_limit['wait_hours']
            return jsonify({
                'success': False,
                'message': f'Too many booking requests from your network. Please try again in {wait_hours} hour{"s" if wait_hours != 1 else ""}.',
                'rate_limited': True,
                'wait_hours': wait_hours
            }), 429

        # Validate the slot exists and is available (use sanitized slot ID)
        slots = db.get_all_slots()
        requested_slot = sanitized_data.get('selected_slot')

        slot_found = False
        selected_slot_data = None

        for slot in slots:
            slot_ids = [str(slot.get('id') or ''), str(slot.get('doc_id') or '')]
            if requested_slot in slot_ids:
                if slot.get('booked'):
                    return jsonify({
                        'success': False,
                        'message': 'This slot has already been booked'
                    }), 400
                selected_slot_data = slot.copy()
                slot_found = True
                break

        if not slot_found:
            return jsonify({
                'success': False,
                'message': 'Invalid time slot'
            }), 400

        # Get tutor information from the selected slot
        tutor_id = selected_slot_data.get('tutor_id')
        tutor_name = selected_slot_data.get('tutor_name', 'Christopher Buzaid')  # Default to Christopher
        tutor_email = selected_slot_data.get('tutor_email', '')

        # If tutor_email is missing from slot, look it up from tutors collection
        if not tutor_email and tutor_id:
            tutor_info = db.get_tutor_by_id(tutor_id)
            if tutor_info:
                tutor_email = tutor_info.get('email', '')
                tutor_name = tutor_info.get('full_name') or tutor_info.get('name') or tutor_name

        # Default to master admin email if still not found
        if not tutor_email:
            tutor_email = 'cjpbuzaid@gmail.com'

        # Create booking data using sanitized inputs
        booking_data = {
            'full_name': sanitized_data['full_name'],
            'email': email,
            'phone': sanitized_data.get('phone', ''),
            'role': sanitized_data['role'],
            'department': sanitized_data.get('department', ''),
            'ai_familiarity': sanitized_data.get('ai_familiarity', ''),
            'ai_tools': sanitized_data.get('ai_tools', ''),
            'primary_use': sanitized_data.get('primary_use', ''),
            'learning_goal': sanitized_data.get('learning_goal', ''),
            'confidence_level': sanitized_data.get('confidence_level', 3),
            'personal_comments': sanitized_data.get('personal_comments', ''),
            'research_consent': sanitized_data.get('research_consent', None),
            'selected_slot': selected_slot_data.get('id'),
            'slot_details': selected_slot_data,
            'selected_room': sanitized_data['selected_room'],
            'meeting_type': sanitized_data.get('meeting_type', 'in-person'),
            'attendee_count': sanitized_data.get('attendee_count', 1),
            'tutor_id': tutor_id,
            'tutor_name': tutor_name,
            'tutor_email': tutor_email,
            'timestamp': datetime.now().isoformat(),
            'submission_date': datetime.now().isoformat(),
            'status': 'confirmed',
            'payment_pending': payment_pending,
            'is_internal_user': is_internal,
            'device_id': device_id,
            'client_ip': client_ip
        }

        # Store confirmed booking
        success = db.store_confirmed_booking(email, booking_data, selected_slot_data)
        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to create booking'
            }), 500

        # Record rate limit usage
        if device_id:
            db.record_device_booking_request(device_id)
        db.record_ip_booking_request(client_ip)
        db.record_email_booking_request(email)

        # Send confirmation emails using sanitized data
        try:
            slot_data = {
                'day': selected_slot_data.get('day', ''),
                'date': selected_slot_data.get('date', ''),
                'time': selected_slot_data.get('time', ''),
                'location': sanitized_data['selected_room'],
                'tutor_name': tutor_name,
                'tutor_email': tutor_email
            }

            user_data = {
                'email': email,
                'full_name': sanitized_data['full_name'],
                'role': sanitized_data['role'],
                'selected_room': sanitized_data['selected_room'],
                'meeting_type': sanitized_data.get('meeting_type', 'in-person'),
                'attendee_count': sanitized_data.get('attendee_count', 1),
                'department': sanitized_data.get('department', ''),
                'ai_familiarity': sanitized_data.get('ai_familiarity', ''),
                'ai_tools': sanitized_data.get('ai_tools', ''),
                'primary_use': sanitized_data.get('primary_use', ''),
                'learning_goal': sanitized_data.get('learning_goal', ''),
                'personal_comments': sanitized_data.get('personal_comments', ''),
                'tutor_id': tutor_id,
                'tutor_name': tutor_name,
                'tutor_email': tutor_email
            }

            # Send emails synchronously to guarantee delivery on serverless
            send_booking_emails(email, sanitized_data['full_name'], slot_data, user_data)
        except Exception as e:
            print(f"[ERROR] Email sending failed: {e}")

        return jsonify({
            'success': True,
            'message': 'Booking confirmed! Check your email for details.',
            'slot_details': selected_slot_data
        })

    except Exception as e:
        print(f"Error in request_booking_verification: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your booking'
        }), 500


@booking_bp.route('/api/booking/confirm-verification', methods=['POST'])
def confirm_booking_verification():
    """DEPRECATED: This endpoint is no longer used."""
    return jsonify({
        'success': False,
        'message': 'This endpoint is deprecated. Please use the new OAuth-based booking flow.'
    }), 410


@booking_bp.route('/api/booking/<booking_id>', methods=['DELETE'])
@login_required
def delete_booking(booking_id):
    """Delete a booking and free up the time slot (admin only)"""
    try:
        users = db.get_all_bookings()
        deleted_user = None

        for user in users:
            if user.get('id') == booking_id:
                deleted_user = user
                break

        if not deleted_user:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        # Ownership check: tutor_admin can only delete their own bookings
        tutor_role = session.get('tutor_role')
        if tutor_role == 'tutor_admin':
            if deleted_user.get('tutor_id') != session.get('tutor_id'):
                return jsonify({'success': False, 'message': 'You can only delete your own bookings'}), 403

        # Archive booking before deletion to preserve user intake data
        try:
            db.archive_cancelled_booking(
                deleted_user,
                cancelled_by=session.get('admin_email', 'admin')
            )
        except Exception as e:
            print(f"[WARN] Failed to archive before delete: {e}")

        # Extract slot ID - handle both old (object) and new (string) formats
        slot_id = deleted_user.get('selected_slot')
        slot_details = deleted_user.get('slot_details', {})

        # If selected_slot is a dict/object (old format), extract the ID
        if isinstance(slot_id, dict):
            slot_id = slot_id.get('id')

        # Fallback to slot_details.id if selected_slot is not available
        if not slot_id and slot_details:
            slot_id = slot_details.get('id')

        # Free up the time slot BEFORE deleting the booking
        if slot_id:
            print(f"Unbooking slot {slot_id} before deleting booking {booking_id}")
            db.unbook_slot(slot_id)
        else:
            print(f"Warning: No slot ID found for booking {booking_id}, cannot unbook slot")

        # Delete from Firestore
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Send deletion notification email
        try:
            send_email_sync(EmailService.send_booking_deletion, deleted_user, slot_details)
        except Exception as e:
            print(f"[ERROR] Deletion email failed: {e}")

        return jsonify({'success': True, 'message': 'Booking deleted successfully'})

    except Exception as e:
        print(f"[ERROR] {request.path}: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again.'}), 500


@booking_bp.route('/api/booking/rebook', methods=['POST'])
@login_required
def rebook_session():
    """Create a new booking using the same user info from a previous booking (active or archived).
    Requires admin login. Copies all user profile data and assigns a new time slot."""
    try:
        data = request.json
        source_booking_id = data.get('source_booking_id')
        new_slot_id = data.get('new_slot_id')
        new_room = data.get('selected_room', '')
        meeting_type = data.get('meeting_type', 'in-person')
        source_type = data.get('source_type', 'active')  # 'active' or 'archived'

        if not source_booking_id or not new_slot_id:
            return jsonify({'success': False, 'message': 'Missing source booking ID or new slot ID'}), 400

        # Get source booking data
        if source_type == 'archived':
            source = db.get_archived_booking(source_booking_id)
        else:
            # Look up from active bookings
            users = db.get_all_bookings()
            source = next((u for u in users if u.get('id') == source_booking_id), None)

        if not source:
            return jsonify({'success': False, 'message': 'Source booking not found'}), 404

        # Validate the new slot exists and is available
        slots = db.get_all_slots()
        selected_slot_data = None
        for slot in slots:
            slot_ids = [str(slot.get('id') or ''), str(slot.get('doc_id') or '')]
            if new_slot_id in slot_ids:
                if slot.get('booked'):
                    return jsonify({'success': False, 'message': 'This slot has already been booked'}), 400
                selected_slot_data = slot.copy()
                break

        if not selected_slot_data:
            return jsonify({'success': False, 'message': 'Invalid time slot'}), 400

        # Get tutor info from the slot
        tutor_id = selected_slot_data.get('tutor_id')
        tutor_name = selected_slot_data.get('tutor_name', 'Christopher Buzaid')
        tutor_email = selected_slot_data.get('tutor_email', '')
        if not tutor_email and tutor_id:
            tutor_info = db.get_tutor_by_id(tutor_id)
            if tutor_info:
                tutor_email = tutor_info.get('email', '')
                tutor_name = tutor_info.get('full_name') or tutor_info.get('name') or tutor_name
        if not tutor_email:
            tutor_email = 'cjpbuzaid@gmail.com'

        email = source.get('email', '')

        # Create new booking with copied user profile data + new slot
        booking_data = {
            'full_name': source.get('full_name', ''),
            'email': email,
            'phone': source.get('phone', ''),
            'role': source.get('role', ''),
            'department': source.get('department', ''),
            'ai_familiarity': source.get('ai_familiarity', ''),
            'ai_tools': source.get('ai_tools', ''),
            'primary_use': source.get('primary_use', ''),
            'learning_goal': source.get('learning_goal', ''),
            'confidence_level': source.get('confidence_level', 3),
            'personal_comments': source.get('personal_comments', ''),
            'research_consent': source.get('research_consent', None),
            'selected_slot': selected_slot_data.get('id'),
            'slot_details': selected_slot_data,
            'selected_room': new_room or source.get('selected_room', ''),
            'meeting_type': meeting_type,
            'attendee_count': source.get('attendee_count', 1),
            'tutor_id': tutor_id,
            'tutor_name': tutor_name,
            'tutor_email': tutor_email,
            'timestamp': datetime.now().isoformat(),
            'submission_date': datetime.now().isoformat(),
            'status': 'confirmed',
            'payment_pending': source.get('payment_pending', False),
            'is_internal_user': source.get('is_internal_user', True),
            'rebooked_from': source_booking_id
        }

        success = db.store_confirmed_booking(email, booking_data, selected_slot_data)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to create rebooking'}), 500

        print(f"[OK] Rebooked session for {source.get('full_name')} from booking {source_booking_id}")

        return jsonify({
            'success': True,
            'message': f"New session booked for {source.get('full_name', 'user')}!"
        })

    except Exception as e:
        print(f"[ERROR] {request.path}: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again.'}), 500


@booking_bp.route('/api/booking/<booking_id>', methods=['PUT'])
@login_required
def update_booking(booking_id):
    """Update an existing booking (admin only)"""
    try:
        data = request.json

        # For updates, only validate fields that are actually being changed
        # Don't require all fields like a new booking would
        if data:
            sanitized = {}

            # Validate slot if provided
            if 'selected_slot' in data and data['selected_slot']:
                slot_id = str(data['selected_slot']).strip()
                is_valid, error = InputValidator.validate_slot_id(slot_id)
                if not is_valid:
                    return jsonify({'success': False, 'message': f'Validation error: {error}'}), 400
                sanitized['selected_slot'] = slot_id

            # Validate room if provided
            if 'selected_room' in data and data['selected_room']:
                room = str(data['selected_room']).strip()
                if len(room) > 200:
                    return jsonify({'success': False, 'message': 'Room name too long'}), 400
                sanitized['selected_room'] = room

            # Copy other safe fields
            for field in ['full_name', 'role', 'department', 'meeting_type', 'attendee_count']:
                if field in data and data[field]:
                    sanitized[field] = str(data[field]).strip() if isinstance(data[field], str) else data[field]

            data = sanitized

        users = db.get_all_bookings()

        booking_to_update = None
        for user in users:
            if user.get('id') == booking_id:
                booking_to_update = user
                break

        if not booking_to_update:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        # Ownership check: tutor_admin can only update their own bookings
        tutor_role = session.get('tutor_role')
        if tutor_role == 'tutor_admin':
            if booking_to_update.get('tutor_id') != session.get('tutor_id'):
                return jsonify({'success': False, 'message': 'You can only update your own bookings'}), 403

        # Track changes for email notification
        old_slot = booking_to_update.get('slot_details', {})
        old_room = booking_to_update.get('selected_room')

        new_slot_id = data.get('selected_slot')
        new_room = data.get('selected_room')

        # Extract old slot ID - handle both old (object) and new (string) formats
        old_slot_id = booking_to_update.get('selected_slot')
        if isinstance(old_slot_id, dict):
            old_slot_id = old_slot_id.get('id')

        # Fallback to slot_details if old_slot_id is still not available
        if not old_slot_id and old_slot:
            old_slot_id = old_slot.get('id')

        # Handle slot change
        if new_slot_id and new_slot_id != old_slot_id:
            print(f"Slot change detected: {old_slot_id} -> {new_slot_id}")

            # Unbook old slot
            if old_slot_id:
                print(f"Unbooking old slot {old_slot_id}")
                db.unbook_slot(old_slot_id)

            # Book new slot
            slots = db.get_all_slots()
            new_slot_data = None

            for slot in slots:
                if str(slot.get('id')) == new_slot_id or str(slot.get('doc_id')) == new_slot_id:
                    if slot.get('booked'):
                        return jsonify({'success': False, 'message': 'New slot is already booked'}), 400
                    new_slot_data = slot
                    break

            if not new_slot_data:
                return jsonify({'success': False, 'message': 'New slot not found'}), 404

            print(f"Booking new slot {new_slot_id}")
            db.book_slot(new_slot_id, booking_to_update['email'], new_room or old_room)

        # Update booking data
        updates = {}
        if 'full_name' in data:
            updates['full_name'] = data['full_name']
        if new_room:
            updates['selected_room'] = new_room
        if new_slot_id:
            # Get updated slot details
            slots = db.get_all_slots()
            for slot in slots:
                if str(slot.get('id')) == new_slot_id:
                    updates['slot_details'] = slot
                    updates['selected_slot'] = new_slot_id  # Store as string ID
                    break

        success = db.update_booking(booking_id, updates)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update booking'}), 500

        # Send update notification email
        try:
            booking_to_update.update(updates)
            new_slot_details = updates.get('slot_details', old_slot)
            send_email_sync(
                EmailService.send_booking_update,
                booking_to_update,
                old_slot,
                new_slot_details,
                old_room,
                new_room
            )
        except Exception as e:
            print(f"[ERROR] Update email failed: {e}")

        return jsonify({'success': True, 'message': 'Booking updated successfully'})

    except Exception as e:
        print(f"[ERROR] {request.path}: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again.'}), 500


@booking_bp.route('/api/booking/lookup', methods=['POST'])
def booking_lookup():
    """DEPRECATED: Booking lookup is no longer supported."""
    return jsonify({
        'success': False,
        'message': 'This endpoint is deprecated.'
    }), 410


@booking_bp.route('/api/booking/verify', methods=['POST'])
def booking_verify():
    """DEPRECATED: Booking verification is no longer supported."""
    return jsonify({
        'success': False,
        'message': 'This endpoint is deprecated.'
    }), 410


@booking_bp.route('/api/booking/delete-by-email', methods=['POST'])
def delete_booking_by_email():
    """DEPRECATED: Use OAuth-authenticated delete instead."""
    return jsonify({
        'success': False,
        'message': 'This endpoint is deprecated. Please sign in to manage your bookings.'
    }), 410


@booking_bp.route('/api/user-booking', methods=['GET'])
def get_user_booking():
    """Get the current user's booking (authenticated users only)"""
    try:
        # Check if user is authenticated
        if not session.get('authenticated'):
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'success': False, 'message': 'User email not found'}), 401
        
        # Get all bookings and find one for this user (most recent/upcoming)
        bookings = db.get_all_bookings()
        
        # Find all bookings for this user
        user_bookings = []
        for booking in bookings:
            if booking.get('email', '').lower() == user_email.lower():
                user_bookings.append(booking)
        
        if not user_bookings:
            return jsonify({'success': False, 'message': 'No booking found'}), 404
        
        # If multiple bookings, return the most recent one
        # (sort by datetime and return the last one)
        from utils.datetime_utils import get_eastern_datetime
        
        sorted_bookings = []
        for booking in user_bookings:
            slot_details = booking.get('slot_details', {})
            slot_datetime = slot_details.get('datetime', '')
            try:
                slot_datetime_eastern = get_eastern_datetime(slot_datetime)
                sorted_bookings.append((slot_datetime_eastern, booking))
            except:
                sorted_bookings.append((None, booking))
        
        # Sort by datetime, most recent first
        sorted_bookings.sort(key=lambda x: x[0] if x[0] else datetime.min, reverse=True)
        
        if sorted_bookings:
            return jsonify({
                'success': True,
                'booking': sorted_bookings[0][1]
            })
        
        # Fallback: return first booking if no datetime
        return jsonify({
            'success': True,
            'booking': user_bookings[0]
        })
        
    except Exception as e:
        print(f"[ERROR] {request.path}: {e}")
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again.'}), 500


@booking_bp.route('/api/booking/update-by-email', methods=['POST'])
def update_booking_by_email():
    """Update a user's booking - requires OAuth authentication"""
    try:
        # Check if user is authenticated via OAuth
        if not session.get('authenticated'):
            return jsonify({
                'success': False,
                'message': 'Please sign in to update your booking.'
            }), 401

        # Get authenticated email from session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({
                'success': False,
                'message': 'Session expired. Please sign in again.'
            }), 401

        data = request.json
        new_slot_id = data.get('selected_slot')
        new_building = data.get('selected_building', '')
        new_room_number = data.get('room_number', '')

        # Find the user's booking
        user_bookings = db.get_user_bookings(user_email)
        if not user_bookings:
            return jsonify({'success': False, 'message': 'No booking found for your account'}), 404

        # Get the most recent booking
        booking = user_bookings[0]
        booking_id = booking.get('id')

        if not booking_id:
            return jsonify({'success': False, 'message': 'Booking ID not found'}), 404

        # Prepare updates
        updates = {}

        # Handle slot change
        if new_slot_id:
            old_slot_id = booking.get('selected_slot')
            if isinstance(old_slot_id, dict):
                old_slot_id = old_slot_id.get('id')

            if new_slot_id != old_slot_id:
                # Unbook old slot
                if old_slot_id:
                    db.unbook_slot(old_slot_id)

                # Get new slot data and book it
                slots = db.get_all_slots()
                new_slot_data = None
                for slot in slots:
                    if slot.get('id') == new_slot_id:
                        new_slot_data = slot
                        break

                if not new_slot_data:
                    return jsonify({'success': False, 'message': 'Selected time slot not found'}), 404

                if new_slot_data.get('is_booked'):
                    return jsonify({'success': False, 'message': 'Selected time slot is no longer available'}), 400

                # Book new slot
                db.book_slot(new_slot_id, user_email)
                updates['selected_slot'] = new_slot_id
                updates['slot_details'] = new_slot_data

        # Handle room change
        if new_building or new_room_number:
            if new_building == 'Zoom':
                updates['selected_room'] = 'Zoom - Online'
                updates['meeting_type'] = 'zoom'
            else:
                new_room = f"{new_building} - {new_room_number}" if new_building and new_room_number else booking.get('selected_room')
                updates['selected_room'] = new_room
                updates['meeting_type'] = 'in-person'

        if not updates:
            return jsonify({'success': False, 'message': 'No changes to update'}), 400

        # Update the booking
        success = db.update_booking(booking_id, updates)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update booking'}), 500

        # Get updated booking
        booking.update(updates)

        # Send update notification email
        try:
            old_slot = booking.get('slot_details', {})
            new_slot = updates.get('slot_details', old_slot)
            old_room = booking.get('selected_room', '')
            new_room = updates.get('selected_room', old_room)
            send_email_sync(
                EmailService.send_booking_update,
                booking,
                old_slot,
                new_slot,
                old_room,
                new_room
            )
        except Exception as e:
            print(f"[ERROR] Update email failed: {e}")

        return jsonify({
            'success': True,
            'message': 'Booking updated successfully',
            'booking': booking
        })

    except Exception as e:
        print(f"Error updating booking by email: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'An internal error occurred. Please try again.'}), 500
