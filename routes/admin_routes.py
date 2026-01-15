"""
Admin Routes Blueprint
Handles admin dashboard, login, session management, and insights generation.
"""

from flask import Blueprint, request, session, render_template, redirect, url_for, jsonify
from datetime import datetime
import firestore_db as db
from middleware.auth import login_required
from services.email_service import EmailService
from services.ai_service import AIService
from routes.auth_routes import get_authorized_admin_info  # Database-driven admin config

admin_bp = Blueprint('admin', __name__)

# REMOVED: Environment variable admin accounts no longer supported
# All admin authentication now goes through:
# 1. OAuth SSO (which creates/uses database accounts)
# 2. Direct database username/password login
print(f"[OK] Admin system ready - OAuth SSO and database authentication enabled")


@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page and authentication with database and environment variable support"""

    # If already logged in, redirect to admin dashboard
    if session.get('logged_in') and session.get('admin_username'):
        return redirect('/admin')

    if request.method == 'POST':
        data = request.json
        username_or_email = data.get('username', '').strip()
        password = data.get('password')
        client_ip = request.remote_addr
        is_email = '@' in username_or_email

        print(f"Login attempt - {'Email' if is_email else 'Username'}: '{username_or_email}' - IP: {client_ip}")

        # Check rate limit on failed attempts (5 per hour)
        rate_limit_check = db.check_admin_login_rate_limit(client_ip)
        if not rate_limit_check['allowed']:
            print(f"[ERROR] Login attempt blocked - IP {client_ip} exceeded rate limit")
            return jsonify({
                'success': False,
                'message': f'Too many failed login attempts. Please wait {rate_limit_check["wait_minutes"]} minutes.'
            }), 429

        # Method 1: Try database-stored admin account first
        if is_email:
            # Email login - check database
            admin_account = db.get_admin_by_email(username_or_email)
            if admin_account and password:
                # Verify password
                verified_admin = db.verify_admin_password(admin_account.get('username'), password)
                if verified_admin:
                    db.reset_admin_login_attempts(client_ip)

                    # Get authorized admin info from database for fallback values
                    admin_email = verified_admin.get('email', '').lower()
                    admin_oauth_info = get_authorized_admin_info(admin_email) or {}

                    # Ensure session persists across requests
                    session.permanent = True
                    session['logged_in'] = True
                    session['authenticated'] = True  # Allow access to home page
                    session['admin_username'] = verified_admin.get('username')
                    session['tutor_id'] = verified_admin.get('tutor_id') or admin_oauth_info.get('tutor_id')
                    session['tutor_role'] = verified_admin.get('role', 'tutor_admin')
                    # Use database tutor_name, fall back to authorized_admins config
                    session['tutor_name'] = verified_admin.get('tutor_name') or admin_oauth_info.get('tutor_name', 'Admin')
                    session['tutor_email'] = verified_admin.get('email', '')
                    session['user_email'] = verified_admin.get('email', '')  # For home page
                    session['user_name'] = verified_admin.get('tutor_name') or admin_oauth_info.get('tutor_name', 'Admin')
                    session['auth_method'] = 'database'
                    session.modified = True  # Force session save

                    # Update last password verification
                    db.update_admin_last_password_verification(verified_admin.get('username'))

                    print(f"[OK] Database login successful for: {verified_admin.get('email')} (Role: {session.get('tutor_role')})")
                    return jsonify({'success': True})
        else:
            # Username login - try database first
            admin_account = db.get_admin_by_username(username_or_email)
            if admin_account and password:
                verified_admin = db.verify_admin_password(username_or_email, password)
                if verified_admin:
                    db.reset_admin_login_attempts(client_ip)

                    # Get authorized admin info from database for fallback values
                    admin_email = verified_admin.get('email', '').lower()
                    admin_oauth_info = get_authorized_admin_info(admin_email) or {}

                    # Ensure session persists across requests
                    session.permanent = True
                    session['logged_in'] = True
                    session['authenticated'] = True  # Allow access to home page
                    session['admin_username'] = verified_admin.get('username')
                    session['tutor_id'] = verified_admin.get('tutor_id') or admin_oauth_info.get('tutor_id')
                    session['tutor_role'] = verified_admin.get('role', 'tutor_admin')
                    # Use database tutor_name, fall back to authorized_admins config
                    session['tutor_name'] = verified_admin.get('tutor_name') or admin_oauth_info.get('tutor_name', 'Admin')
                    session['tutor_email'] = verified_admin.get('email', '')
                    session['user_email'] = verified_admin.get('email', '')  # For home page
                    session['user_name'] = verified_admin.get('tutor_name') or admin_oauth_info.get('tutor_name', 'Admin')
                    session['auth_method'] = 'database'
                    session.modified = True  # Force session save

                    # Update last password verification
                    db.update_admin_last_password_verification(username_or_email)

                    print(f"[OK] Database login successful for: {username_or_email} (Role: {session.get('tutor_role')})")
                    return jsonify({'success': True})

        # REMOVED: Environment variable login no longer supported
        # All admins must use OAuth SSO or create a database account

        print(f"[ERROR] Login failed for: {username_or_email}")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    return render_template('admin_login.html')


@admin_bp.route('/admin/setup')
def admin_setup():
    """Admin account setup page - shown when admin needs to complete registration"""
    # Check if user is logged in via OAuth but needs to complete registration
    if not session.get('logged_in') and not session.get('needs_registration'):
        return redirect(url_for('admin.admin_login'))

    needs_registration = session.get('needs_registration', False)
    if not needs_registration:
        # Already registered, go to admin page
        return redirect(url_for('admin.admin'))

    pending_email = session.get('pending_registration_email', session.get('user_email', ''))
    admin_info = get_authorized_admin_info(pending_email)
    tutor_name = admin_info.get('tutor_name', '') if admin_info else ''

    return render_template('admin_setup.html',
                         pending_email=pending_email,
                         tutor_name=tutor_name)


@admin_bp.route('/admin/register', methods=['POST'])
def admin_register():
    """Register a new admin account with username and password"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()

        # Validation
        if not email or not username or not password:
            return jsonify({
                'success': False,
                'message': 'Email, username, and password are required.'
            }), 400

        if password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'Passwords do not match.'
            }), 400

        if len(password) < 8:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters long.'
            }), 400

        if len(username) < 3:
            return jsonify({
                'success': False,
                'message': 'Username must be at least 3 characters long.'
            }), 400

        # Verify email is an authorized admin (from database)
        admin_email_info = get_authorized_admin_info(email.lower())

        if not admin_email_info:
            return jsonify({
                'success': False,
                'message': 'Email is not authorized for admin access.'
            }), 403

        # Generate verification token
        import secrets
        verification_token = secrets.token_urlsafe(32)

        # Store pending account in database
        success = db.store_pending_account_verification(
            email=email,
            username=username,
            password=password,
            verification_token=verification_token,
            role=admin_email_info.get('tutor_role', 'tutor_admin'),
            tutor_id=admin_email_info.get('tutor_id', username),
            tutor_name=admin_email_info.get('tutor_name', username.capitalize())
        )

        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to initiate account creation. Username may already be taken.'
            }), 500

        # Generate verification link
        # Use request.host_url to get the base URL (e.g., http://localhost:5000/)
        base_url = request.host_url.rstrip('/')
        verification_link = f"{base_url}/admin/verify-account?token={verification_token}"

        # Send verification email
        admin_name = admin_email_info.get('tutor_name', username.capitalize())
        email_sent = EmailService.send_account_verification_link(
            email=email,
            verification_link=verification_link,
            admin_name=admin_name
        )

        if not email_sent:
            print(f"[CRITICAL ERROR] Failed to send verification email to {email}")
            print(f"[CRITICAL ERROR] Email service is not configured correctly")
            print(f"[CRITICAL ERROR] Check EMAIL_USER and EMAIL_PASSWORD in .env")

            # Clean up pending account since we can't verify
            db.delete_pending_account_verification(verification_token)

            return jsonify({
                'success': False,
                'message': 'Failed to send verification email. Email service is not configured correctly. Please contact the administrator to fix email settings.'
            }), 500

        print(f"[OK] Verification email sent to: {email} (username: {username})")

        return jsonify({
            'success': True,
            'message': f'Verification email sent! Please check {email} and click the verification link to complete your account setup. The link expires in 1 hour.'
        })

    except Exception as e:
        print(f"Error in admin registration: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration.'
        }), 500


@admin_bp.route('/admin/verify-account', methods=['GET'])
def verify_account():
    """Verify email and create admin account from verification link"""
    try:
        token = request.args.get('token')

        if not token:
            return render_template('admin_verify.html',
                                 error='Invalid verification link. No token provided.')

        # Get pending account data
        pending_account = db.get_pending_account_verification(token)

        if not pending_account:
            return render_template('admin_verify.html',
                                 error='Verification link is invalid or has expired. Please request a new verification email.')

        # Create the actual admin account with pre-hashed password
        from datetime import datetime, timezone

        client = db.get_firestore_client()
        if not client:
            return render_template('admin_verify.html',
                                 error='Database connection error. Please try again later.')

        admins_ref = client.collection('admin_accounts')

        # Check if admin already exists
        existing_email = admins_ref.where('email', '==', pending_account['email']).limit(1).get()
        existing_username = admins_ref.where('username', '==', pending_account['username']).limit(1).get()

        if existing_email or existing_username:
            db.delete_pending_account_verification(token)
            return render_template('admin_verify.html',
                                 error='Account could not be created. Email or username already exists.')

        # Create admin account with pre-hashed password from pending account
        admin_data = {
            'email': pending_account['email'],
            'username': pending_account['username'],
            'password_hash': pending_account['password_hash'],  # Already hashed
            'role': pending_account['role'],
            'tutor_id': pending_account['tutor_id'],
            'tutor_name': pending_account['tutor_name'],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_password_verification': datetime.now(timezone.utc).isoformat(),
            'active': True
        }

        admins_ref.document().set(admin_data)

        # Delete pending account
        db.delete_pending_account_verification(token)

        print(f"[OK] Admin account verified and created: {pending_account['email']} (username: {pending_account['username']})")

        # Log the user in by setting up their session
        session.clear()
        session.permanent = True
        session['logged_in'] = True
        session['authenticated'] = True
        session['is_admin'] = True
        session['admin_username'] = pending_account['username']
        session['tutor_id'] = pending_account['tutor_id']
        session['tutor_role'] = pending_account['role']
        session['tutor_name'] = pending_account['tutor_name']
        session['tutor_email'] = pending_account['email']
        session['user_email'] = pending_account['email']
        session['user_name'] = pending_account['tutor_name']
        session['auth_method'] = 'database'
        session['needs_registration'] = False
        session.modified = True

        # Redirect to admin dashboard
        return redirect(url_for('admin.admin'))

    except Exception as e:
        print(f"ERROR in account verification: {e}")
        return render_template('admin_verify.html',
                             error='An error occurred during verification. Please try again or contact support.')


@admin_bp.route('/admin/verify-password', methods=['GET', 'POST'])
def admin_verify_password():
    """Password re-verification page for admins (required every 3 days)"""
    # Check if user has a session
    if 'logged_in' not in session or 'admin_username' not in session:
        return redirect(url_for('admin.admin_login'))

    if request.method == 'POST':
        data = request.json
        password = data.get('password')
        username = session.get('admin_username')

        if not password or not username:
            return jsonify({
                'success': False,
                'message': 'Password is required.'
            }), 400

        # Verify password
        verified_admin = db.verify_admin_password(username, password)
        if verified_admin:
            # Update last password verification timestamp
            db.update_admin_last_password_verification(username)
            print(f"[OK] Password re-verified for admin: {username}")
            return jsonify({'success': True})
        else:
            print(f"[ERROR] Password re-verification failed for: {username}")
            return jsonify({
                'success': False,
                'message': 'Incorrect password.'
            }), 401

    # GET request - show verification form
    return render_template('admin_verify.html',
                         username=session.get('admin_username'),
                         tutor_name=session.get('tutor_name'))


@admin_bp.route('/admin/logout')
def admin_logout():
    """Admin logout - clear all admin session data"""
    session.pop('logged_in', None)
    session.pop('admin_username', None)
    session.pop('tutor_id', None)
    session.pop('tutor_role', None)
    session.pop('tutor_name', None)
    session.pop('auth_method', None)
    return redirect(url_for('admin.admin_login'))


@admin_bp.route('/admin')
@login_required
def admin():
    """Admin dashboard"""
    # Check if user needs to complete registration - redirect to setup page
    needs_registration = session.get('needs_registration', False)
    if needs_registration:
        return redirect(url_for('admin.admin_setup'))

    return render_template('admin.html',
                         needs_registration=False,
                         pending_email='')


@admin_bp.route('/api/check-registration-needed', methods=['GET'])
@login_required
def check_registration_needed():
    """Check if user needs to complete database account registration"""
    needs_registration = session.get('needs_registration', False)
    pending_email = session.get('pending_registration_email', session.get('user_email', ''))

    return jsonify({
        'needs_registration': needs_registration,
        'email': pending_email
    })


@admin_bp.route('/api/admin-accounts/<email>', methods=['DELETE'])
@login_required
def delete_admin_account(email):
    """Delete an admin account by email (super_admin only)"""
    try:
        # Only super_admin can delete admin accounts
        tutor_role = session.get('tutor_role', '')
        if tutor_role != 'super_admin':
            return jsonify({
                'success': False,
                'message': 'Only super_admin can delete admin accounts'
            }), 403

        # Delete the admin account
        success = db.delete_admin_account_by_email(email)

        if success:
            return jsonify({
                'success': True,
                'message': f'Admin account {email} deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Admin account {email} not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@admin_bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Get all bookings for admin dashboard (filtered by tutor if not super_admin)"""
    try:
        tutor_role = session.get('tutor_role', 'admin')
        tutor_id = session.get('tutor_id')

        all_users = db.get_all_bookings()

        # If super_admin, return all bookings
        if tutor_role == 'super_admin':
            return jsonify(all_users)

        # If tutor_admin, only return their bookings
        if tutor_role == 'tutor_admin' and tutor_id:
            filtered_users = [
                user for user in all_users
                if user.get('tutor_id') == tutor_id
            ]
            return jsonify(filtered_users)

        # Default: return all (for legacy admin accounts)
        return jsonify(all_users)
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Get booking statistics: per-tutor breakdown + master total from persistent storage"""
    try:
        tutor_role = session.get('tutor_role', 'tutor_admin')
        tutor_id = session.get('tutor_id')

        # Get statistics from persistent storage (includes historical data)
        stats_summary = db.get_statistics_summary()

        # Also count current active bookings (not yet completed)
        current_bookings = db.get_all_bookings()
        active_count = len(current_bookings)

        # If tutor_admin, only return their own stats
        if tutor_role == 'tutor_admin':
            tutor_stats = stats_summary.get('tutors', {}).get(tutor_id, {})
            return jsonify({
                'success': True,
                'role': tutor_role,
                'tutor_id': tutor_id,
                'total_bookings': tutor_stats.get('total_bookings', 0),
                'unique_clients': tutor_stats.get('unique_clients', 0),
                'active_bookings': active_count,
                'tutor_name': session.get('tutor_name', 'Unknown')
            })

        # If super_admin (Master), return all tutor stats + master total
        return jsonify({
            'success': True,
            'role': tutor_role,
            'tutor_stats': stats_summary.get('tutors', {}),
            'master_total': stats_summary.get('master_total', {'total_bookings': 0, 'unique_clients': 0}),
            'active_bookings': active_count
        })

    except Exception as e:
        print(f"Error fetching statistics: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/tutors', methods=['GET'])
@login_required
def get_tutors():
    """Get list of all tutors for dropdown selection"""
    try:
        tutors = db.get_all_tutors()
        return jsonify({
            'success': True,
            'tutors': tutors
        })
    except Exception as e:
        print(f"Error fetching tutors: {e}")
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
        
        # Handle slot_details - could be stored directly or need to extract from slot_id
        slot_details = completed_user.get('slot_details', {})
        if not slot_details and isinstance(slot_id, dict):
            slot_details = slot_id
        
        session_date = f"{slot_details.get('day', '')}, {slot_details.get('date', '')} at {slot_details.get('time', '')}".strip()
        if not session_date or session_date == ',':
            session_date = 'Not specified'

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
            EmailService.send_feedback_request(completed_user, booking_id)
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
            # slot_id might be a dict with 'id' or 'doc_id' field, or a string ID
            if isinstance(slot_id, dict):
                actual_slot_id = slot_id.get('id') or slot_id.get('doc_id')
            else:
                actual_slot_id = slot_id
            
            if actual_slot_id:
                db.delete_slot(actual_slot_id)

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


@admin_bp.route('/api/users/missed-session', methods=['POST'])
@login_required
def record_user_missed_session():
    """Record a missed session for a user"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        excused = data.get('excused', False)
        reason = data.get('reason', '').strip()

        if not email:
            return jsonify({'success': False, 'message': 'Email is required'}), 400

        success = db.record_missed_session(email, excused, reason)

        if not success:
            return jsonify({'success': False, 'message': 'Failed to record missed session'}), 500

        # Get updated user data
        user = db.get_or_create_user(email)

        return jsonify({
            'success': True,
            'message': f"Recorded {'excused' if excused else 'unexcused'} miss for {email}",
            'user': user
        })

    except Exception as e:
        print(f"Error recording missed session: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/users/<email>/ban', methods=['POST'])
@login_required
def ban_user_endpoint(email):
    """Ban a user from the system"""
    try:
        data = request.json or {}
        reason = data.get('reason', 'Manually banned by administrator')

        success = db.ban_user(email, reason)

        if not success:
            return jsonify({'success': False, 'message': 'Failed to ban user (may be Monmouth user)'}), 400

        return jsonify({
            'success': True,
            'message': f'User {email} has been banned'
        })

    except Exception as e:
        print(f"Error banning user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/users/<email>/unban', methods=['POST'])
@login_required
def unban_user_endpoint(email):
    """Unban a user"""
    try:
        success = db.unban_user(email)

        if not success:
            return jsonify({'success': False, 'message': 'Failed to unban user'}), 400

        return jsonify({
            'success': True,
            'message': f'User {email} has been unbanned'
        })

    except Exception as e:
        print(f"Error unbanning user: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/users/<email>/reset-misses', methods=['POST'])
@login_required
def reset_user_misses_endpoint(email):
    """Reset missed session counters for a user"""
    try:
        success = db.reset_user_misses(email)

        if not success:
            return jsonify({'success': False, 'message': 'Failed to reset misses'}), 400

        return jsonify({
            'success': True,
            'message': f'Missed session counters reset for {email}'
        })

    except Exception as e:
        print(f"Error resetting misses: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/users/<email>/status', methods=['GET'])
@login_required
def get_user_status(email):
    """Get detailed status for a user (payment, bans, misses)"""
    try:
        user_data = db.get_or_create_user(email)
        payment_status = db.get_user_payment_status(email)
        is_banned, ban_reason = db.is_user_banned(email)

        return jsonify({
            'success': True,
            'user': user_data,
            'payment_status': payment_status,
            'is_banned': is_banned,
            'ban_reason': ban_reason
        })

    except Exception as e:
        print(f"Error getting user status: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/admin/test-email', methods=['POST'])
@login_required
def test_email_configuration():
    """
    Test email configuration by sending a test email.
    Only accessible by super_admin users.
    """
    try:
        # Only super_admin can test email
        if session.get('tutor_role') != 'super_admin':
            return jsonify({
                'success': False,
                'message': 'Only super admin can test email configuration'
            }), 403

        import os
        from services.email_service import EmailService

        # Get configuration status
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASSWORD')
        email_from = os.getenv('EMAIL_FROM', email_user)

        config_status = {
            'EMAIL_USER': 'SET' if email_user and email_user != 'your-email@gmail.com' else 'NOT SET or default',
            'EMAIL_PASSWORD': 'SET' if email_password and email_password != 'your-gmail-app-password' else 'NOT SET or default',
            'EMAIL_FROM': email_from if email_from else 'NOT SET',
            'email_user_value': email_user[:20] + '...' if email_user and len(email_user) > 20 else email_user,
            'password_length': len(email_password) if email_password else 0
        }

        # Get recipient from request or use admin's email
        data = request.get_json() or {}
        test_recipient = data.get('recipient', session.get('tutor_email', session.get('user_email')))

        if not test_recipient:
            return jsonify({
                'success': False,
                'message': 'No recipient email provided',
                'config': config_status
            }), 400

        # Try to send a test email
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #6366F1;">LearnAI Email Test</h1>
                <p>This is a test email from your LearnAI booking system.</p>
                <p><strong>If you received this email, your email configuration is working correctly!</strong></p>
                <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Sent at:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p style="margin: 5px 0 0 0;"><strong>From:</strong> {email_from}</p>
                </div>
                <p style="color: #6B7280; font-size: 0.9rem;">This test was initiated from the admin panel.</p>
            </body>
        </html>
        """

        success = EmailService._send_email(
            to_email=test_recipient,
            subject='LearnAI - Email Configuration Test',
            html_content=html_content
        )

        if success:
            return jsonify({
                'success': True,
                'message': f'Test email sent successfully to {test_recipient}',
                'config': config_status
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send test email. Check server logs for details.',
                'config': config_status,
                'troubleshooting': [
                    'Verify EMAIL_USER is set to your Gmail address',
                    'Verify EMAIL_PASSWORD is a valid Gmail App Password (16 characters, no spaces)',
                    'Generate new App Password at: https://myaccount.google.com/apppasswords',
                    'Ensure 2-Step Verification is enabled on your Google account',
                    'Check server logs for detailed SMTP error messages'
                ]
            }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error testing email: {str(e)}'
        }), 500
