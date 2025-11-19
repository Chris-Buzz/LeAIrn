"""
Admin Routes Blueprint
Handles admin dashboard, login, session management, and insights generation.
"""

from flask import Blueprint, request, session, render_template, redirect, url_for, jsonify
import os
import firestore_db as db
from middleware.auth import login_required
from services.email_service import EmailService
from services.ai_service import AIService

admin_bp = Blueprint('admin', __name__)

# Admin accounts configuration
ADMIN_ACCOUNTS = {}
admin_count = 1
while True:
    username = os.getenv(f'ADMIN{admin_count}_USERNAME')
    password = os.getenv(f'ADMIN{admin_count}_PASSWORD')
    if username and password:
        ADMIN_ACCOUNTS[username] = password
        admin_count += 1
    else:
        break


@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page and authentication"""
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        client_ip = request.remote_addr

        print(f"Login attempt - Username: '{username}' - IP: {client_ip}")

        # Check rate limit on failed attempts (5 per hour)
        rate_limit_check = db.check_admin_login_rate_limit(client_ip)
        if not rate_limit_check['allowed']:
            print(f"[ERROR] Login attempt blocked - IP {client_ip} exceeded rate limit")
            return jsonify({
                'success': False,
                'message': f'Too many failed login attempts. Please wait {rate_limit_check["wait_minutes"]} minutes.'
            }), 429

        # Check credentials
        if username in ADMIN_ACCOUNTS and ADMIN_ACCOUNTS[username] == password:
            db.reset_admin_login_attempts(client_ip)
            session['logged_in'] = True
            session['admin_username'] = username
            print(f"[OK] Login successful for: {username}")
            return jsonify({'success': True})

        print(f"[ERROR] Login failed for: {username}")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
    return render_template('admin_login.html')


@admin_bp.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/admin')
@login_required
def admin():
    """Admin dashboard"""
    return render_template('admin.html')


@admin_bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Get all bookings for admin dashboard (including past bookings)"""
    try:
        users = db.get_all_bookings()
        return jsonify(users)
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/booking/<booking_id>/complete', methods=['POST'])
@login_required
def mark_booking_complete(booking_id):
    """Mark a booking as complete, send feedback and session overview"""
    try:
        data = request.json or {}
        session_notes = data.get('notes', '').strip()
        skip_ai = data.get('skip_ai', False)

        users = db.get_all_bookings()
        completed_user = None
        
        for user in users:
            if user.get('id') == booking_id:
                completed_user = user
                break

        if not completed_user:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        slot_id = completed_user.get('selected_slot')
        slot_details = completed_user.get('slot_details', {})
        session_date = f"{slot_details.get('day', '')}, {slot_details.get('date', '')} at {slot_details.get('time', '')}"

        # Process session notes if provided
        enhanced_notes = ''
        if session_notes:
            if skip_ai:
                enhanced_notes = session_notes
            else:
                print(f"Enhancing session notes with AI...")
                enhanced_notes = AIService.enhance_session_notes(
                    session_notes,
                    completed_user.get('full_name', ''),
                    completed_user.get('role', '')
                )
                # Ensure we have something to send
                if not enhanced_notes:
                    enhanced_notes = session_notes

            # Store session overview
            overview_data = {
                'notes': session_notes,
                'enhanced_notes': enhanced_notes,
                'user_name': completed_user.get('full_name', ''),
                'user_email': completed_user.get('email', ''),
                'session_date': session_date,
                'created_by': 'admin'
            }
            db.store_session_overview(booking_id, overview_data)

            # Send session overview email
            try:
                EmailService.send_session_overview(completed_user, enhanced_notes)
            except Exception as e:
                print(f"Email error: {e}")

        # Send feedback request email
        try:
            EmailService.send_feedback_request(completed_user)
        except Exception as e:
            print(f"Email error: {e}")

        # Store user info for feedback association
        db.store_feedback_metadata(booking_id, {
            'user_name': completed_user.get('full_name', 'Unknown'),
            'user_email': completed_user.get('email', 'Unknown')
        })

        # Delete the booking
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Delete the time slot
        if slot_id:
            db.delete_slot(slot_id)

        return jsonify({'success': True, 'message': 'Session marked complete'})

    except Exception as e:
        print(f"Error marking booking complete: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/session-overviews', methods=['GET'])
@login_required
def get_session_overviews():
    """Get all session overviews for admin view"""
    try:
        overviews = db.get_all_session_overviews()
        return jsonify(overviews)
    except Exception as e:
        print(f"Error getting session overviews: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/session-overviews/<booking_id>', methods=['DELETE'])
@login_required
def delete_session_overview(booking_id):
    """Delete a session overview"""
    try:
        success = db.delete_session_overview(booking_id)
        if success:
            return jsonify({'success': True, 'message': 'Overview deleted'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete'}), 500
    except Exception as e:
        print(f"Error deleting session overview: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/session-overviews/manual', methods=['POST'])
@login_required
def create_manual_overview():
    """Create a manual session overview for past sessions"""
    try:
        data = request.json
        user_name = data.get('user_name', '').strip()
        user_email = data.get('user_email', '').strip()
        session_date = data.get('session_date', '').strip()
        notes = data.get('notes', '').strip()
        send_email = data.get('send_email', False)
        skip_ai = data.get('skip_ai', False)

        if not user_name or not user_email or not notes:
            return jsonify({'success': False, 'message': 'Name, email, and notes are required'}), 400

        # Generate unique booking ID
        import uuid
        booking_id = f"manual_{uuid.uuid4().hex[:12]}"

        # Enhance notes with AI if requested
        enhanced_notes = notes
        if not skip_ai:
            print(f"Enhancing manual session notes with AI...")
            enhanced_notes = AIService.enhance_session_notes(notes, user_name, 'N/A')
            # Ensure we have something to store
            if not enhanced_notes:
                enhanced_notes = notes

        # Store session overview
        overview_data = {
            'notes': notes,
            'enhanced_notes': enhanced_notes,
            'user_name': user_name,
            'user_email': user_email,
            'session_date': session_date or 'Not specified',
            'created_by': 'admin_manual'
        }
        success = db.store_session_overview(booking_id, overview_data)

        if not success:
            return jsonify({'success': False, 'message': 'Failed to save overview'}), 500

        # Send email if requested
        if send_email:
            user_data = {'full_name': user_name, 'email': user_email}
            EmailService.send_session_overview(user_data, enhanced_notes)

        return jsonify({
            'success': True,
            'message': 'Overview saved successfully',
            'email_sent': send_email
        })

    except Exception as e:
        print(f"Error creating manual overview: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/session-overviews/preview', methods=['POST'])
@login_required
def preview_session_overview():
    """Preview AI-enhanced session notes before completing"""
    try:
        data = request.json
        notes = data.get('notes', '').strip()
        user_name = data.get('user_name', '')
        user_role = data.get('user_role', '')
        skip_ai = data.get('skip_ai', False)

        if not notes:
            return jsonify({'success': False, 'message': 'Notes are required'}), 400

        if skip_ai:
            enhanced_notes = notes
        else:
            enhanced_notes = AIService.enhance_session_notes(notes, user_name, user_role)
            # Ensure we have something to return
            if not enhanced_notes:
                enhanced_notes = notes

        return jsonify({'success': True, 'enhanced_notes': enhanced_notes or notes})

    except Exception as e:
        print(f"Error previewing session overview: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/generate-insights/<booking_id>', methods=['POST'])
@login_required
def generate_insights_for_booking(booking_id):
    """Generate AI insights on-demand for a specific booking"""
    try:
        user = db.get_booking_by_id(booking_id)
        if not user:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        print(f"Generating AI insights for {user['full_name']}...")
        
        # Prepare session data for insights
        session_data = {
            'topics': [],  # Could be extracted from booking data
            'duration': 30,
            'student_questions': [],
            'difficulty_level': 3
        }
        
        ai_insights = AIService.get_teaching_insights(session_data)

        # Update booking with insights
        success = db.update_booking(booking_id, {'ai_insights': ai_insights})
        if not success:
            return jsonify({'success': False, 'message': 'Failed to save insights'}), 500

        return jsonify({'success': True, 'insights': ai_insights})

    except Exception as e:
        print(f"Error generating insights: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
