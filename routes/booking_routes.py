"""
Booking Routes Blueprint
Handles all booking-related operations (create, update, delete, lookup).
"""

from flask import Blueprint, request, session, jsonify
from datetime import datetime
import firestore_db as db
from utils import get_client_ip, verify_recaptcha
from services.email_service import EmailService

booking_bp = Blueprint('booking', __name__)


@booking_bp.route('/api/booking/request-verification', methods=['POST'])
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

        # Validate required fields
        required_fields = ['full_name', 'role', 'selected_slot', 'selected_room']
        for field in required_fields:
            if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

        # Verify reCAPTCHA (optional for OAuth-authenticated users)
        # OAuth provides strong authentication, so reCAPTCHA is an additional layer
        recaptcha_token = data.get('recaptcha_token')
        if recaptcha_token:
            success, score, error = verify_recaptcha(recaptcha_token)
            if success is False:
                # reCAPTCHA explicitly failed - log but continue (OAuth is strong enough)
                print(f"[WARNING] reCAPTCHA failed: {error} (score: {score}) - allowing authenticated user")
            elif success is True:
                # reCAPTCHA passed
                print(f"[OK] reCAPTCHA verification passed (score: {score})")
            else:
                # reCAPTCHA returned None (optional/misconfigured)
                print(f"[INFO] reCAPTCHA skipped - optional for authenticated users")
        else:
            print(f"[INFO] No reCAPTCHA token provided - user authenticated via OAuth")
        
        print(f"[OK] Proceeding with booking - user authenticated via OAuth ({email})")

        # Check device-based rate limiting (2 bookings/24hrs per device)
        device_id = data.get('device_id')
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

        # Validate the slot exists and is available
        slots = db.get_all_slots()
        requested_slot = (data.get('selected_slot') or '').strip()

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

        # Create booking data
        booking_data = {
            'full_name': data['full_name'].strip(),
            'email': email,
            'phone': data.get('phone', '').strip(),
            'role': data['role'].strip(),
            'department': data.get('department', '').strip(),
            'ai_familiarity': data.get('ai_familiarity', '').strip(),
            'ai_tools': data.get('ai_tools', '').strip(),
            'primary_use': data.get('primary_use', '').strip(),
            'learning_goal': data.get('learning_goal', '').strip(),
            'confidence_level': data.get('confidence_level', 3),
            'personal_comments': data.get('personal_comments', '').strip(),
            'selected_slot': selected_slot_data,
            'selected_room': data['selected_room'].strip(),
            'timestamp': datetime.now().isoformat(),
            'status': 'confirmed',
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

        # Send confirmation emails
        try:
            slot_data = {
                'day': selected_slot_data.get('day', ''),
                'date': selected_slot_data.get('date', ''),
                'time': selected_slot_data.get('time', ''),
                'location': data['selected_room']
            }
            
            user_data = {
                'email': email,
                'full_name': data['full_name'],
                'role': data['role'],
                'selected_room': data['selected_room'],
                'department': data.get('department', ''),
                'ai_familiarity': data.get('ai_familiarity', ''),
                'ai_tools': data.get('ai_tools', ''),
                'primary_use': data.get('primary_use', ''),
                'learning_goal': data.get('learning_goal', ''),
                'personal_comments': data.get('personal_comments', '')
            }
            
            EmailService.send_booking_confirmation(email, data['full_name'], slot_data)
            EmailService.send_admin_notification(user_data, slot_data)
        except Exception as e:
            print(f"Email sending error: {e}")

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
def delete_booking(booking_id):
    """Delete a booking and free up the time slot"""
    try:
        users = db.get_all_bookings()
        deleted_user = None
        
        for user in users:
            if user.get('id') == booking_id:
                deleted_user = user
                break

        if not deleted_user:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        slot_id = deleted_user.get('selected_slot')
        slot_details = deleted_user.get('slot_details', {})

        # Delete from Firestore
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Free up the time slot
        if slot_id:
            db.unbook_slot(slot_id)

        # Send deletion notification email
        try:
            EmailService.send_booking_deletion(deleted_user, slot_details)
        except Exception as e:
            print(f"Email error: {e}")

        return jsonify({'success': True, 'message': 'Booking deleted successfully'})

    except Exception as e:
        print(f"Error deleting booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@booking_bp.route('/api/booking/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update an existing booking"""
    try:
        data = request.json
        users = db.get_all_bookings()
        
        booking_to_update = None
        for user in users:
            if user.get('id') == booking_id:
                booking_to_update = user
                break

        if not booking_to_update:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        # Track changes for email notification
        old_slot = booking_to_update.get('slot_details', {})
        old_room = booking_to_update.get('selected_room')
        
        new_slot_id = data.get('selected_slot')
        new_room = data.get('selected_room')

        # Handle slot change
        if new_slot_id and new_slot_id != booking_to_update.get('selected_slot'):
            old_slot_id = booking_to_update.get('selected_slot')
            
            # Unbook old slot
            if old_slot_id:
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
                    updates['selected_slot'] = new_slot_id
                    break

        success = db.update_booking(booking_id, updates)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update booking'}), 500

        # Send update notification email
        try:
            booking_to_update.update(updates)
            new_slot_details = updates.get('slot_details', old_slot)
            EmailService.send_booking_update(
                booking_to_update,
                old_slot,
                new_slot_details,
                old_room,
                new_room
            )
        except Exception as e:
            print(f"Email error: {e}")

        return jsonify({'success': True, 'message': 'Booking updated successfully'})

    except Exception as e:
        print(f"Error updating booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


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


@booking_bp.route('/api/booking/update-by-email', methods=['POST'])
def update_booking_by_email():
    """DEPRECATED: Use OAuth-authenticated update instead."""
    return jsonify({
        'success': False,
        'message': 'This endpoint is deprecated. Please sign in to manage your bookings.'
    }), 410
