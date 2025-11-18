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
    recaptcha_site_key = os.getenv('RECAPTCHA_SITE_KEY')
    is_authenticated = session.get('authenticated', False)
    user_email = session.get('user_email', '')
    user_name = session.get('user_name', '')

    return render_template('index.html',
                         recaptcha_site_key=recaptcha_site_key,
                         authenticated=is_authenticated,
                         user_email=user_email,
                         user_name=user_name)


@api_bp.route('/projects')
def projects():
    """AI Projects Gallery page"""
    return render_template('projects.html')


@api_bp.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files (images, GIFs) from the media directory"""
    try:
        media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media')
        return send_from_directory(media_dir, filename)
    except Exception as e:
        print(f"Error serving media file {filename}: {e}")
        return "File not found", 404


@api_bp.route('/feedback')
def feedback_page():
    """Feedback submission page"""
    return render_template('feedback.html')


@api_bp.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files"""
    media_folder = os.path.join(os.path.dirname(__file__), '..', 'static', 'images')
    return send_from_directory(media_folder, filename)


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
    """Get all slots for admin management"""
    try:
        slots = db.get_all_slots()
        return jsonify(slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/add', methods=['POST'])
@login_required
def add_slot():
    """Add a new time slot"""
    try:
        data = request.json
        slot_id = db.add_time_slot(data)
        if slot_id:
            return jsonify({'success': True, 'message': 'Slot added', 'id': slot_id})
        else:
            return jsonify({'success': False, 'message': 'Failed to add slot'}), 500
    except Exception as e:
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
    """Generate new time slots"""
    try:
        data = request.json
        weeks_ahead = data.get('weeks_ahead', 6)
        
        generated_slots = slot_service.generate_slots(weeks_ahead)
        added_count = 0

        for slot in generated_slots:
            slot_id = db.add_time_slot(slot)
            if slot_id:
                added_count += 1

        return jsonify({
            'success': True,
            'message': f'Generated {added_count} new slots',
            'added_count': added_count
        })
    except Exception as e:
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
    try:
        data = request.json
        slot_ids = data.get('slot_ids', [])
        
        deleted_count = 0
        for slot_id in slot_ids:
            success = db.delete_slot(slot_id)
            if success:
                deleted_count += 1

        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} slots',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/api/slots/delete-range', methods=['POST'])
@login_required
def delete_slots_range():
    """Delete slots within a date range"""
    try:
        data = request.json
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        all_slots = db.get_all_slots()
        deleted_count = 0

        for slot in all_slots:
            slot_date = slot.get('datetime', '')
            if start_date <= slot_date <= end_date:
                success = db.delete_slot(slot['id'])
                if success:
                    deleted_count += 1

        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} slots',
            'deleted_count': deleted_count
        })
    except Exception as e:
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

        success = db.store_feedback(booking_id, feedback_data)
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
        # Process contact form
        return jsonify({'success': True, 'message': 'Message sent successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
