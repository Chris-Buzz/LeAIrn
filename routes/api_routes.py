"""
API Routes Blueprint
Handles slots management, feedback, exports, cron jobs, and public pages.
"""

from flask import Blueprint, request, session, render_template, jsonify, send_file, send_from_directory
from datetime import datetime
import os
import csv
import io
import firestore_db as db
from middleware.auth import login_required, cron_auth_required
from utils import get_eastern_now
from services.slot_service import SlotService
from services.email_service import EmailService
from utils.datetime_utils import get_eastern_now as tz_get_eastern_now, get_eastern_datetime

# Initialize timezone utility wrapper
class TimezoneUtil:
    @staticmethod
    def get_eastern_now():
        return tz_get_eastern_now()
    
    @staticmethod
    def get_eastern_datetime(dt_str):
        return get_eastern_datetime(dt_str)

# Initialize slot service
tz_util = TimezoneUtil()
slot_service = SlotService(db, tz_util)

api_bp = Blueprint('api', __name__)


# ============================================================================
# PUBLIC PAGES
# ============================================================================

@api_bp.route('/')
def index():
    """Home page"""
    from routes.auth_routes import is_authorized_admin
    from datetime import datetime

    recaptcha_site_key = os.getenv('RECAPTCHA_SITE_KEY')
    is_authenticated = session.get('authenticated', False)
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')
    user_type = session.get('user_type', '')

    # Debug: Log session state for troubleshooting
    print(f"[HOME PAGE] Session state:")
    print(f"  authenticated: {is_authenticated}")
    print(f"  user_email: {user_email}")
    print(f"  user_name: {user_name}")
    print(f"  user_type: {user_type}")
    print(f"  logged_in: {session.get('logged_in')}")
    print(f"  admin_username: {session.get('admin_username')}")

    # Check if user is an authorized admin (only show admin button to authorized emails)
    is_admin = is_authorized_admin(user_email) if user_email else False

    # Check if user is external (non-Monmouth) - show pricing button
    is_external_user = is_authenticated and user_type == 'external'

    return render_template('index.html',
                         recaptcha_site_key=recaptcha_site_key,
                         authenticated=is_authenticated,
                         user_email=user_email,
                         user_name=user_name,
                         is_admin=is_admin,
                         is_external_user=is_external_user,
                         current_year=datetime.now().year)


@api_bp.route('/projects')
def projects():
    """AI Projects Gallery page"""
    return render_template('projects.html')


@api_bp.route('/ai-tools')
def ai_tools():
    """Free AI Tools for Students page"""
    return render_template('ai_tools.html')


@api_bp.route('/pricing')
def pricing():
    """Pricing page for external users"""
    from datetime import datetime
    return render_template('pricing.html', current_year=datetime.now().year)


@api_bp.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files (images, GIFs) from the media directory"""
    try:
        # Get the media directory path
        media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media')
        
        # Security: prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            return "Access denied", 403
        
        # Check if file exists
        file_path = os.path.join(media_dir, filename)
        if not os.path.isfile(file_path):
            print(f"Media file not found: {filename} (looked in {media_dir})")
            return "File not found", 404
        
        # Serve the file with caching headers for production
        response = send_from_directory(media_dir, filename)
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
        return response
    except Exception as e:
        print(f"Error serving media file {filename}: {e}")
        import traceback
        traceback.print_exc()
        return "Error serving file", 500


@api_bp.route('/feedback')
def feedback_page():
    """Feedback submission page"""
    return render_template('feedback.html')


# ============================================================================
# SLOTS MANAGEMENT
# ============================================================================

@api_bp.route('/api/slots', methods=['GET'])
def get_slots():
    """Get all available time slots"""
    try:
        available_slots = db.get_available_slots()
        return jsonify(available_slots)
    except Exception as e:
        print(f"Error in get_slots: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/manage', methods=['GET'])
@login_required
def manage_slots():
    """Get slots for admin management (filtered by tutor, only future slots in Eastern time)"""
    try:
        from utils.datetime_utils import get_eastern_now, get_eastern_datetime
        from flask import session

        tutor_role = session.get('tutor_role', 'admin')
        tutor_id = session.get('tutor_id')

        all_slots = db.get_all_slots()
        now_eastern = get_eastern_now()

        # Filter to only show future slots in Eastern time
        future_slots = []
        for slot in all_slots:
            slot_datetime_str = slot.get('datetime', '')
            try:
                slot_datetime_eastern = get_eastern_datetime(slot_datetime_str)
                if slot_datetime_eastern and slot_datetime_eastern > now_eastern:
                    # Filter by tutor if not super_admin
                    if tutor_role == 'super_admin':
                        future_slots.append(slot)
                    elif tutor_role == 'tutor_admin' and tutor_id:
                        if slot.get('tutor_id') == tutor_id:
                            future_slots.append(slot)
                    else:
                        # Legacy admin - show all
                        future_slots.append(slot)
            except:
                # If can't parse datetime, skip this slot
                pass

        return jsonify(future_slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/add', methods=['POST'])
@login_required
def add_slot():
    """Add a new time slot with tutor assignment"""
    try:
        from datetime import datetime, timezone
        from flask import session

        data = request.json
        datetime_str = data.get('datetime')
        requested_tutor_id = data.get('tutor_id')  # Optional: for super_admin to create slots for specific tutors
        requested_tutor_name = data.get('tutor_name')  # Optional: tutor name from frontend dropdown
        location_type = data.get('location_type', 'user_choice')  # zoom, room, user_choice
        location_value = data.get('location_value', '')  # Zoom link or room name

        if not datetime_str:
            return jsonify({'success': False, 'message': 'Datetime is required'}), 400

        # Get tutor information
        # If a specific tutor_id is requested and user is super_admin, use that
        # Otherwise, use the session tutor info
        tutor_role = session.get('tutor_role', 'tutor_admin')

        if requested_tutor_id and tutor_role == 'super_admin':
            # Super admin is creating a slot for a specific tutor
            tutor_info = db.get_tutor_by_id(requested_tutor_id)
            if not tutor_info:
                return jsonify({'success': False, 'message': f'Tutor not found: {requested_tutor_id}'}), 400
            tutor_id = tutor_info['id']
            # Use tutor_name from request if provided, otherwise from database
            tutor_name = requested_tutor_name or tutor_info.get('name') or tutor_info.get('tutor_name') or 'Unknown'
        else:
            # Use session tutor info (normal tutor creating their own slot)
            tutor_id = session.get('tutor_id')
            # Fallback chain: tutor_name -> user_name -> lookup from database
            tutor_name = session.get('tutor_name') or session.get('user_name')

            # DEBUG: Print what we have so far
            print(f"\n{'='*60}")
            print(f"[ADD_SLOT DEBUG] Initial values:")
            print(f"  tutor_id from session: {repr(tutor_id)}")
            print(f"  tutor_name from session: {repr(tutor_name)}")
            print(f"  admin_username: {repr(session.get('admin_username'))}")
            print(f"  tutor_email: {repr(session.get('tutor_email'))}")
            print(f"  user_email: {repr(session.get('user_email'))}")

            # If still no tutor_name, try to get it from the database
            if not tutor_name:
                admin_username = session.get('admin_username')
                tutor_email = session.get('tutor_email') or session.get('user_email')

                if admin_username:
                    # Try database first
                    print(f"  Looking up admin by username: {admin_username}")
                    db_admin = db.get_admin_by_username(admin_username)
                    print(f"  Database result: {db_admin}")
                    if db_admin:
                        tutor_name = db_admin.get('tutor_name')
                        print(f"  Got tutor_name from DB: {repr(tutor_name)}")

                # If still no name, try authorized_admins collection by email
                if not tutor_name and tutor_email:
                    from routes.auth_routes import get_authorized_admin_info
                    admin_info = get_authorized_admin_info(tutor_email.lower())
                    print(f"  authorized_admins lookup for {tutor_email}: {admin_info}")
                    if admin_info:
                        tutor_name = admin_info.get('tutor_name')
                        print(f"  Got tutor_name from authorized_admins: {repr(tutor_name)}")

            # Final fallback
            if not tutor_name:
                tutor_name = tutor_id.replace('_', ' ').title() if tutor_id else 'Unknown'
                print(f"  Using final fallback tutor_name: {repr(tutor_name)}")

            print(f"[ADD_SLOT DEBUG] Final tutor_name: {repr(tutor_name)}")
            print(f"{'='*60}\n")

        # Convert the datetime-local format to ISO format and parse it
        try:
            # datetime-local format: "2025-11-18T14:30"
            dt = datetime.fromisoformat(datetime_str)
            iso_datetime = dt.isoformat()
        except:
            iso_datetime = datetime_str
            dt = datetime.fromisoformat(datetime_str)

        # Generate slot ID in format: YYYYMMDDHHMI_tutorID
        base_slot_id = datetime_str.replace('-', '').replace(':', '').replace('T', '')
        slot_id = f"{base_slot_id}_{tutor_id}" if tutor_id else base_slot_id

        # Format date components for display
        day_name = dt.strftime('%A')  # e.g., "Friday"
        date_str = dt.strftime('%B %d, %Y')  # e.g., "December 05, 2025"
        time_str = dt.strftime('%I:%M %p')  # e.g., "01:00 PM"

        # Prepare slot data
        slot_data = {
            'id': slot_id,
            'datetime': iso_datetime,
            'day': day_name,
            'date': date_str,
            'time': time_str,
            'booked': False,
            'booking_id': None,
            'booked_by': None,
            'room': None,
            'tutor_id': tutor_id,
            'tutor_name': tutor_name,
            'location_type': location_type,  # zoom, room, user_choice
            'location_value': location_value,  # Zoom link or room name
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        result_id = db.add_time_slot(slot_data)
        if result_id:
            return jsonify({'success': True, 'message': 'Slot added successfully', 'id': result_id})
        else:
            return jsonify({'success': False, 'message': 'Failed to add slot. Slot may already exist.'}), 500
    except Exception as e:
        print(f'Error adding slot: {e}')
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/cleanup', methods=['POST'])
@login_required
def cleanup_slots():
    """Clean up past time slots"""
    try:
        all_slots = db.get_all_slots()
        now_eastern = get_eastern_now()
        deleted_count = 0

        for slot in all_slots:
            slot_datetime_str = slot.get('datetime', '')
            try:
                slot_datetime_eastern = get_eastern_datetime(slot_datetime_str)
                if slot_datetime_eastern and slot_datetime_eastern < now_eastern:
                    success = db.delete_slot(slot['id'])
                    if success:
                        deleted_count += 1
            except:
                pass

        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} past slots',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/auto-maintain', methods=['POST'])
@login_required
def auto_maintain_slots():
    """Run automatic cleanup and slot generation"""
    try:
        success = slot_service.auto_cleanup_and_generate()
        if success:
            return jsonify({
                'success': True,
                'message': 'Automatic maintenance completed'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Maintenance failed'
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/generate', methods=['POST'])
@login_required
def generate_slots():
    """Generate new time slots with tutor-specific parameters"""
    try:
        from flask import session

        # Get request data
        data = request.json or {}
        weeks_ahead = data.get('weeks_ahead', 6)
        custom_schedule = data.get('schedule')  # Optional custom schedule
        requested_tutor_id = data.get('tutor_id')  # Optional: for super_admin to create slots for specific tutors
        requested_tutor_name = data.get('tutor_name')  # Optional: tutor name from frontend dropdown
        location_type = data.get('location_type', 'user_choice')  # zoom, room, user_choice
        location_value = data.get('location_value', '')  # Zoom link or room name

        # Get tutor information
        tutor_role = session.get('tutor_role', 'tutor_admin')

        if requested_tutor_id and tutor_role == 'super_admin':
            # Super admin is creating slots for a specific tutor
            tutor_info = db.get_tutor_by_id(requested_tutor_id)
            if not tutor_info:
                return jsonify({
                    'success': False,
                    'message': f'Tutor not found: {requested_tutor_id}'
                }), 400
            tutor_id = tutor_info['id']
            # Use tutor_name from request if provided, otherwise from database
            tutor_name = requested_tutor_name or tutor_info.get('name') or tutor_info.get('tutor_name') or 'Unknown'
            tutor_email = tutor_info.get('email', '')
        elif tutor_role == 'super_admin':
            # Super admin without specifying a tutor - not allowed
            return jsonify({
                'success': False,
                'message': 'Please select a tutor to generate slots for.'
            }), 400
        else:
            # Normal tutor creating their own slots
            tutor_id = session.get('tutor_id')
            # Fallback chain: tutor_name -> user_name -> lookup from database by admin_username
            tutor_name = session.get('tutor_name') or session.get('user_name')
            tutor_email = session.get('tutor_email') or session.get('user_email') or ''

            # If still no tutor_name, try to get it from the database
            if not tutor_name:
                admin_username = session.get('admin_username')
                if admin_username:
                    # Try database first
                    db_admin = db.get_admin_by_username(admin_username)
                    if db_admin:
                        tutor_name = db_admin.get('tutor_name')
                        tutor_email = tutor_email or db_admin.get('email', '')

                # If still no name, try authorized_admins collection by email
                if not tutor_name and tutor_email:
                    from routes.auth_routes import get_authorized_admin_info
                    admin_info = get_authorized_admin_info(tutor_email.lower())
                    if admin_info:
                        tutor_name = admin_info.get('tutor_name')

            # Final fallback to avoid 'Unknown'
            if not tutor_name:
                tutor_name = tutor_id.replace('_', ' ').title() if tutor_id else 'Unknown'

            # DEBUG: Print ALL session variables to diagnose issue
            import sys
            print(f"\n{'='*80}", flush=True)
            print(f"[DEBUG] === COMPLETE SESSION DATA FOR SLOT GENERATION ===", flush=True)
            print(f"{'='*80}", flush=True)
            for key, value in session.items():
                print(f"[DEBUG]   session['{key}'] = {repr(value)}", flush=True)
            print(f"{'='*80}", flush=True)
            print(f"[DEBUG] EXTRACTED VALUES:", flush=True)
            print(f"[DEBUG]   tutor_id: {tutor_id}", flush=True)
            print(f"[DEBUG]   tutor_name: {tutor_name}", flush=True)
            print(f"[DEBUG]   tutor_email: {tutor_email}", flush=True)
            print(f"[DEBUG]   admin_username: {session.get('admin_username')}", flush=True)
            print(f"[DEBUG]   auth_method: {session.get('auth_method')}", flush=True)
            print(f"{'='*80}\n", flush=True)
            sys.stdout.flush()

        # Generate slots with tutor information
        generated_slots = slot_service.generate_slots(
            weeks_ahead=weeks_ahead,
            weekly_schedule=custom_schedule,
            tutor_id=tutor_id,
            tutor_name=tutor_name,
            tutor_email=tutor_email,
            location_type=location_type,
            location_value=location_value
        )

        added_count = 0
        for slot in generated_slots:
            slot_id = db.add_time_slot(slot)
            if slot_id:
                added_count += 1

        print(f"[OK] {tutor_name} generated {added_count} new slots")

        return jsonify({
            'success': True,
            'message': f'Generated {added_count} new slots for {tutor_name}',
            'added_count': added_count,
            'tutor_name': tutor_name
        })
    except Exception as e:
        print(f"[ERROR] Slot generation failed: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/<slot_id>', methods=['DELETE'])
@login_required
def delete_slot(slot_id):
    """Delete a specific time slot"""
    try:
        success = db.delete_slot(slot_id)
        if success:
            return jsonify({'success': True, 'message': 'Slot deleted'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete slot'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/<slot_id>/unbook', methods=['POST'])
@login_required
def unbook_slot(slot_id):
    """Mark a slot as available again"""
    try:
        success = db.unbook_slot(slot_id)
        if success:
            return jsonify({'success': True, 'message': 'Slot marked as available'})
        else:
            return jsonify({'success': False, 'message': 'Failed to unbook slot'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_slots():
    """Delete multiple slots at once"""
    import sys
    try:
        data = request.json
        print(f"\n[DEBUG] ========== BULK DELETE STARTED ==========", flush=True)
        print(f"[DEBUG] Request data: {data}", flush=True)
        print(f"[DEBUG] Request headers: {dict(request.headers)}", flush=True)
        sys.stdout.flush()

        if not data:
            print(f"[ERROR] No data provided in request", flush=True)
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        slot_ids = data.get('slot_ids', [])
        print(f"[DEBUG] Extracted slot_ids: {slot_ids}", flush=True)
        print(f"[DEBUG] Type of slot_ids: {type(slot_ids)}", flush=True)
        print(f"[DEBUG] Length of slot_ids: {len(slot_ids) if isinstance(slot_ids, list) else 'N/A'}", flush=True)
        sys.stdout.flush()

        if not slot_ids or len(slot_ids) == 0:
            print(f"[ERROR] No slots selected for deletion", flush=True)
            return jsonify({
                'success': False,
                'message': 'No slots selected for deletion'
            }), 400

        deleted_count = 0
        failed_slots = []

        for i, slot_id in enumerate(slot_ids):
            print(f"[DEBUG] [{i+1}/{len(slot_ids)}] Attempting to delete slot: '{slot_id}'", flush=True)
            success = db.delete_slot(slot_id)
            if success:
                deleted_count += 1
                print(f"[OK] ✓ Deleted slot: {slot_id}", flush=True)
            else:
                failed_slots.append(slot_id)
                print(f"[ERROR] ✗ Failed to delete slot: {slot_id}", flush=True)
            sys.stdout.flush()

        print(f"\n[DEBUG] ========== BULK DELETE COMPLETE ==========", flush=True)
        print(f"[DEBUG] Deleted: {deleted_count}/{len(slot_ids)}", flush=True)
        print(f"[DEBUG] Failed: {len(failed_slots)}", flush=True)
        sys.stdout.flush()

        if deleted_count > 0:
            return jsonify({
                'success': True,
                'message': f'Deleted {deleted_count} of {len(slot_ids)} slots',
                'deleted_count': deleted_count,
                'failed_count': len(failed_slots),
                'failed_slots': failed_slots
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to delete any slots',
                'failed_slots': failed_slots
            }), 500

    except Exception as e:
        print(f"\n[ERROR] ========== BULK DELETE EXCEPTION ==========", flush=True)
        print(f"[ERROR] Exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred during bulk deletion'
        }), 500


@api_bp.route('/api/slots/delete-range', methods=['POST'])
@login_required
def delete_slots_range():
    """Delete slots within a date range or based on weeks"""
    try:
        from datetime import timedelta
        import pytz
        
        data = request.json
        mode = data.get('mode', 'date_range')
        
        all_slots = db.get_all_slots()
        deleted_count = 0

        if mode == 'last_weeks':
            # Delete slots that are further than N weeks in the future
            weeks = data.get('weeks', 6)
            
            eastern = pytz.timezone('America/New_York')
            now = datetime.now(eastern)
            cutoff_date = now + timedelta(weeks=weeks)
            
            for slot in all_slots:
                try:
                    slot_datetime_str = slot.get('datetime', '')
                    if slot_datetime_str:
                        # Parse the slot datetime
                        slot_dt = datetime.fromisoformat(slot_datetime_str)
                        if slot_dt.tzinfo is None:
                            slot_dt = pytz.utc.localize(slot_dt)
                        slot_dt_eastern = slot_dt.astimezone(eastern)
                        
                        # Only delete unbooked slots that are beyond the cutoff
                        if not slot.get('booked', False) and slot_dt_eastern > cutoff_date:
                            success = db.delete_slot(slot['id'])
                            if success:
                                deleted_count += 1
                except:
                    pass
        else:
            # Delete by date range
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            
            for slot in all_slots:
                slot_date = slot.get('datetime', '')
                if start_date and end_date and start_date <= slot_date <= end_date:
                    success = db.delete_slot(slot['id'])
                    if success:
                        deleted_count += 1

        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} slots',
            'deleted_count': deleted_count
        })
    except Exception as e:
        print(f"Error in delete_slots_range: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# FEEDBACK
# ============================================================================

@api_bp.route('/api/feedback', methods=['GET'])
@login_required
def get_all_feedback():
    """Get all feedback for admin view"""
    try:
        feedback_list = db.get_all_feedback()
        return jsonify(feedback_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a completed session"""
    try:
        data = request.json

        if not data.get('token'):
            return jsonify({'success': False, 'message': 'Invalid feedback link'}), 400

        if not data.get('rating') or not isinstance(data.get('rating'), int) or data.get('rating') < 1 or data.get('rating') > 5:
            return jsonify({'success': False, 'message': 'Please provide a rating between 1 and 5'}), 400

        # Get user metadata from token (booking ID)
        booking_id = data.get('token')
        user_metadata = db.get_feedback_metadata(booking_id)

        feedback_data = {
            'booking_id': booking_id,
            'rating': data['rating'],
            'comments': data.get('comments', '').strip(),
            'user_name': user_metadata.get('user_name', 'Anonymous') if user_metadata else 'Anonymous',
            'user_email': user_metadata.get('user_email', 'unknown') if user_metadata else 'unknown',
            'timestamp': datetime.now().isoformat(),
            'submitted': True
        }

        success = db.add_feedback(feedback_data)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to submit feedback'}), 500

        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        })

    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'message': 'Failed to submit feedback'}), 500


# ============================================================================
# EXPORT & DATA
# ============================================================================

@api_bp.route('/api/export/csv', methods=['GET'])
@login_required
def export_csv():
    """Export all bookings to CSV"""
    try:
        users = db.get_all_bookings()

        if not users:
            return jsonify({'error': 'No data to export'}), 404

        # Create CSV in memory
        output = io.StringIO()
        fieldnames = ['full_name', 'email', 'phone', 'role', 'selected_room', 'selected_slot', 'submission_date']

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for user in users:
            writer.writerow({k: user.get(k, '') for k in fieldnames})

        # Convert to bytes
        output.seek(0)
        byte_output = io.BytesIO()
        byte_output.write(output.getvalue().encode('utf-8'))
        byte_output.seek(0)

        return send_file(
            byte_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'leairn_bookings_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CRON JOBS & REMINDERS
# ============================================================================

@api_bp.route('/api/send-reminders', methods=['POST'])
@login_required
def manual_send_reminders():
    """Manually trigger reminder emails for testing"""
    try:
        count = slot_service.check_and_send_meeting_reminders()
        return jsonify({
            'success': True,
            'message': f'Sent {count} reminder email(s)',
            'reminders_sent': count
        })
    except Exception as e:
        print(f"Error sending reminders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/api/cron/send-reminders', methods=['GET', 'POST'])
def cron_send_reminders():
    """Cron endpoint to send morning reminders (8:30 AM EST)"""
    try:
        # Check if this is an external cron request
        api_key = request.headers.get('X-Cron-API-Key') or request.args.get('api_key')
        
        # If API key is provided, validate it
        if api_key is not None:
            cron_api_key = os.getenv('CRON_API_KEY')
            if not cron_api_key or api_key != cron_api_key:
                return jsonify({
                    'success': False,
                    'message': 'Unauthorized - Invalid cron API key'
                }), 401

        # Send reminders
        count = slot_service.check_and_send_meeting_reminders()
        
        return jsonify({
            'success': True,
            'message': f'Sent {count} reminder(s)',
            'reminders_sent': count
        })

    except Exception as e:
        print(f"Error in cron_send_reminders: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'error': 'Failed to process cron job'
        }), 500


@api_bp.route('/api/send-daily-reminders', methods=['POST', 'GET'])
@cron_auth_required
def send_daily_reminders():
    """Send daily booking reminders at 8:30 AM (alternative cron endpoint)"""
    try:
        count = slot_service.check_and_send_meeting_reminders()
        return jsonify({
            'success': True,
            'reminders_sent': count,
            'message': f'Successfully sent {count} reminder email(s)'
        })
    except Exception as e:
        print(f"Error in send_daily_reminders: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================================
# CONTACT & SUBMISSIONS
# ============================================================================

@api_bp.route('/api/submit', methods=['POST'])
def submit_form():
    """Handle general form submissions"""
    try:
        data = request.json
        # Process form submission
        return jsonify({'success': True, 'message': 'Form submitted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/contact', methods=['POST'])
def contact_form():
    """Handle contact form submissions"""
    try:
        data = request.json

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()

        if not name or not email or not message:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        # Send the contact message email
        from services.email_service import EmailService
        success = EmailService.send_contact_message(name, email, message)

        if success:
            return jsonify({'success': True, 'message': 'Message sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send message. Please try again.'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/admin/pending-registration', methods=['GET'])
def get_pending_admin_registration():
    """Get pending admin registration data from session"""
    try:
        pending = session.get('pending_admin_registration', False)
        email = session.get('pending_admin_email', '')
        name = session.get('pending_admin_name', '')

        return jsonify({
            'pending': pending,
            'email': email,
            'name': name
        })
    except Exception as e:
        return jsonify({'pending': False}), 500


@api_bp.route('/api/payment/status', methods=['GET'])
def get_payment_status():
    """Get current user's payment status"""
    try:
        if not session.get('authenticated'):
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        email = session.get('user_email')
        if not email:
            return jsonify({'success': False, 'message': 'User email not found'}), 401

        payment_status = db.get_user_payment_status(email)

        return jsonify({
            'success': True,
            'payment_status': payment_status
        })

    except Exception as e:
        print(f"Error getting payment status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/payment/create-session', methods=['POST'])
def create_payment_session():
    """Payment information endpoint - no automated payment, handled via email"""
    try:
        if not session.get('authenticated'):
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401

        email = session.get('user_email')
        if not email:
            return jsonify({'success': False, 'message': 'User email not found'}), 401

        # Check if user is Monmouth (shouldn't need to pay)
        if email.endswith('@monmouth.edu'):
            return jsonify({
                'success': False,
                'message': 'Monmouth students get free access - no payment required!'
            }), 400

        # Payment is handled manually via email (Venmo, Zelle, PayPal, etc.)
        return jsonify({
            'success': True,
            'message': 'After booking, payment details will be sent to your email. You can pay before or after your session using Venmo, Zelle, PayPal, or other convenient methods.',
            'payment_methods': ['Venmo', 'Zelle', 'PayPal', 'Cash'],
            'amount': 50,
            'session_duration': '30-90 minutes',
            'manual_payment': True
        }), 200

    except Exception as e:
        print(f"Error in payment info endpoint: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/slots/<slot_id>/location', methods=['PUT'])
@login_required
def update_slot_location(slot_id):
    """Update meeting location for a specific slot"""
    try:
        data = request.json or {}
        location_type = data.get('location_type', 'user_choice')
        location_value = data.get('location_value', '')

        # Validate location_type
        valid_types = ['zoom', 'room', 'user_choice']
        if location_type not in valid_types:
            return jsonify({
                'success': False,
                'message': f'Invalid location_type. Must be one of: {", ".join(valid_types)}'
            }), 400

        # Update the slot
        success = db.update_slot(slot_id, {
            'location_type': location_type,
            'location_value': location_value
        })

        if not success:
            return jsonify({'success': False, 'message': 'Failed to update slot location'}), 500

        return jsonify({
            'success': True,
            'message': 'Slot location updated successfully'
        })

    except Exception as e:
        print(f"Error updating slot location: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
