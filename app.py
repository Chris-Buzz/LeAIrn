from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from datetime import datetime, timedelta
from functools import wraps
import json
import csv
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import google.generativeai as genai
from dotenv import load_dotenv

# Import Firestore database functions
import firestore_db as db

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-CHANGE-IN-PRODUCTION')

# Initialize Firestore
print("Initializing Firestore...")
db.initialize_firestore()

# Admin credentials - Multiple accounts supported
ADMIN_ACCOUNTS = {
    # Your account
    os.getenv('ADMIN1_USERNAME'): os.getenv('ADMIN1_PASSWORD'),
    # Professor account
    os.getenv('ADMIN2_USERNAME'): os.getenv('ADMIN2_PASSWORD'),
}

# Email configuration from environment variables
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USER = os.getenv('EMAIL_USER', 'your-email@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'AI Mentor Hub <your-email@gmail.com>')
EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', 'cjpbuzaid@gmail.com')

# Gemini AI configuration from environment variables
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"OK: Gemini AI configured successfully (Key: ...{GEMINI_API_KEY[-8:]})")
else:
    print("WARNING: GEMINI_API_KEY not set. AI insights will not work.")

# Track last auto-cleanup time
last_auto_cleanup = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def periodic_maintenance():
    """Run automatic cleanup and slot generation periodically"""
    global last_auto_cleanup

    # Only run cleanup once per hour
    now = datetime.now()
    if last_auto_cleanup is None or (now - last_auto_cleanup) > timedelta(hours=1):
        print("Running periodic maintenance...")
        auto_cleanup_and_generate_slots()
        last_auto_cleanup = now

def send_confirmation_email(user_data, slot_data):
    """Send booking confirmation email to user"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your AI Learning Session is Confirmed - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = user_data['email']

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">You're All Set!</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>Your AI learning session with Christopher Buzaid has been confirmed. I'm looking forward to meeting you and helping you discover the best way to use AI for your goals!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data['day']}, {slot_data['date']} at {slot_data['time']}</p>
                        <p><strong>Location:</strong> {user_data['selected_room']}</p>
                        <p><strong>Duration:</strong> 30 minutes</p>
                        <p><strong>Your AI Mentor:</strong> Christopher Buzaid</p>
                    </div>

                    <h3>What to Bring:</h3>
                    <ul>
                        <li>Any specific questions or topics you'd like to cover</li>
                        <li>Your laptop if you want hands-on practice</li>
                        <li>An open mind and curiosity!</li>
                    </ul>

                    <p style="margin-top: 30px;">See you soon!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn</p>
                </div>
            </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        # Send email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def get_gemini_teaching_insights(user_data):
    """Use Gemini AI to generate personalized teaching recommendations"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
You are an AI education expert preparing teaching notes for a 30-minute learning session. Analyze this student's profile and provide concise, actionable teaching recommendations.

Student Profile:
- Name: {user_data['full_name']}
- Role: {user_data['role']}
- AI Familiarity: {user_data.get('ai_familiarity', 'Not specified')}
- Current Tools: {user_data.get('ai_tools', 'None')}
- Primary Interest: {user_data.get('primary_use', 'Not specified')}
- Learning Goal: {user_data.get('learning_goal', 'Not specified')}
- Confidence Level: {user_data.get('confidence_level', 'Not specified')}/5

Provide practical teaching guidance in plain text format (no markdown, no special formatting):

TEACHING APPROACH:
Write 3-4 sentences explaining the best teaching style for this learner based on their experience level and goals.

RECOMMENDED AI TOOLS:
List 3-5 specific AI tools they should learn, with one brief sentence per tool explaining why it fits their interests.

30-MINUTE SESSION PLAN:
Provide a clear outline of what to cover in the session:
- Introduction (5 min): What to demonstrate
- Hands-on Practice (15 min): Specific exercises or examples to work through
- Next Steps (10 min): What they should practice after the session

ACTIONABLE TAKEAWAYS:
List 2-3 concrete things they can start doing immediately to build their AI skills for their specific use case.

Keep all text conversational, practical, and focused on helping them build real solutions. No jargon unless necessary.
        """

        response = model.generate_content(prompt)
        print(f"OK: AI insights generated successfully for {user_data['full_name']}")
        return response.text.strip()
    except Exception as e:
        print(f"ERROR: Error generating Gemini insights: {e}")
        import traceback
        traceback.print_exc()
        return f"AI insights generation failed: {str(e)}. Manual assessment recommended."

# Initialize database with time slots if needed
def init_time_slots():
    """Check if time slots exist - admin controls generation now"""
    slots = db.get_all_slots()
    if len(slots) == 0:
        print("No time slots found. Admin can generate slots from dashboard.")

def auto_cleanup_and_generate_slots():
    """
    Automatic maintenance: Clean up past slots and ensure future slots exist.
    This runs periodically to keep the database clean and slots up to date.
    """
    try:
        all_slots = db.get_all_slots()
        now = datetime.now()
        now_iso = now.isoformat()

        # Count past and future slots
        past_slots = [s for s in all_slots if s.get('datetime', '') < now_iso]
        future_slots = [s for s in all_slots if s.get('datetime', '') >= now_iso]

        # Delete all past slots (both booked and unbooked)
        deleted_count = 0
        for slot in past_slots:
            success = db.delete_slot(slot['id'])
            if success:
                deleted_count += 1

        if deleted_count > 0:
            print(f"AUTO-CLEANUP: Deleted {deleted_count} past time slots")

        # Check if we need to generate more slots
        # Generate if we have less than 2 weeks of future slots
        if len(future_slots) < 20:  # Roughly 2 weeks worth of slots
            print("AUTO-GENERATE: Low on future slots, generating more...")
            generated_slots = generate_time_slots(weeks_ahead=6)

            added_count = 0
            for slot in generated_slots:
                slot_id = db.add_time_slot(slot)
                if slot_id:
                    added_count += 1

            if added_count > 0:
                print(f"AUTO-GENERATE: Added {added_count} new slots")

        return True

    except Exception as e:
        print(f"ERROR in auto_cleanup_and_generate_slots: {e}")
        return False

def generate_time_slots(weeks_ahead=6):
    """Generate ONLY the specific weekly time slots you requested"""
    slots = []
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # ONLY your specific requested times
    weekly_schedule = {
        1: [(11, 0), (12, 0), (13, 0)],  # Tuesday: 11:00, 12:00, 13:00
        2: [(14, 0), (15, 0)],            # Wednesday: 14:00, 15:00
        3: [(12, 0), (13, 0)],            # Thursday: 12:00, 13:00
        4: [(11, 0), (12, 0), (13, 0)]   # Friday: same as Tuesday
    }

    # Generate slots for specified number of weeks ahead
    for week in range(weeks_ahead):
        for day in range(7):
            current_date = start_date + timedelta(days=(week * 7 + day))
            weekday = current_date.weekday()

            if weekday in weekly_schedule:
                for hour_entry in weekly_schedule[weekday]:
                    if isinstance(hour_entry, (tuple, list)):
                        h = int(hour_entry[0])
                        m = int(hour_entry[1]) if len(hour_entry) > 1 else 0
                    else:
                        h = int(hour_entry)
                        m = 0

                    slot_time = current_date.replace(hour=h, minute=m, second=0, microsecond=0)

                    # Only add future slots
                    if slot_time > datetime.now():
                        slots.append({
                            'id': slot_time.strftime('%Y%m%d%H%M'),
                            'datetime': slot_time.isoformat(),
                            'day': slot_time.strftime('%A'),
                            'date': slot_time.strftime('%B %d, %Y'),
                            'time': slot_time.strftime('%I:%M %p'),
                            'booked': False,
                            'booked_by': None,
                            'room': None
                        })

    return slots

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/submit', methods=['POST'])
def submit_data():
    try:
        data = request.json

        # Validate required fields (phone is optional)
        required_fields = ['full_name', 'email', 'role', 'selected_slot', 'selected_room']

        for field in required_fields:
            if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                return jsonify({'success': False, 'message': f'Missing required field: {field}'}), 400

        # Add timestamp
        data['submission_date'] = datetime.now().isoformat()

        # Get all slots from Firestore
        slots = db.get_all_slots()

        slot_found = False
        selected_slot_data = None

        requested_slot = (data.get('selected_slot') or '').strip()
        print(f"Debug: Requested selected_slot='{requested_slot}'")

        for slot in slots:
            # slots from DB may store primary id under 'id' or use Firestore 'doc_id'
            slot_ids = [str(slot.get('id') or ''), str(slot.get('doc_id') or '')]
            if requested_slot in slot_ids:
                if slot.get('booked'):
                    return jsonify({'success': False, 'message': 'This slot has already been booked', 'requested_slot': requested_slot}), 400

                # Book in Firestore (db.book_slot will actually update DB)
                success = db.book_slot(slot.get('id') or slot.get('doc_id'), data['email'], data['selected_room'])
                if not success:
                    return jsonify({'success': False, 'message': 'Failed to book slot', 'requested_slot': requested_slot}), 500

                # Build local copy of slot for response
                selected_slot_data = slot.copy()
                selected_slot_data['booked'] = True
                selected_slot_data['booked_by'] = data['email']
                selected_slot_data['room'] = data['selected_room']
                slot_found = True
                break

        if not slot_found:
            return jsonify({'success': False, 'message': 'Invalid time slot', 'requested_slot': requested_slot}), 400

        # AI insights will be generated on-demand in admin dashboard
        data['ai_insights'] = None

        # Add slot info to user data
        data['slot_details'] = selected_slot_data

        # Add booking to Firestore
        booking_id = db.add_booking(data)

        if not booking_id:
            return jsonify({'success': False, 'message': 'Failed to save booking'}), 500

        # Send confirmation email
        print(f"Sending confirmation email to {data['email']}...")
        email_sent = send_confirmation_email(data, selected_slot_data)

        return jsonify({
            'success': True,
            'message': 'Booking confirmed!',
            'data': {
                'name': data['full_name'],
                'slot': selected_slot_data,
                'room': data['selected_room'],
                'email_sent': email_sent
            }
        })

    except Exception as e:
        print(f"Error in submit_data: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots', methods=['GET'])
def get_slots():
    try:
        # Get available slots from Firestore
        available_slots = db.get_available_slots()
        return jsonify(available_slots)
    except Exception as e:
        print(f"Error in get_slots: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')

        # Debug logging
        print(f"Login attempt - Username: '{username}'")
        print(f"Available accounts: {list(ADMIN_ACCOUNTS.keys())}")
        print(f"Password received: '{password}'")

        # Check if username exists and password matches
        if username in ADMIN_ACCOUNTS and ADMIN_ACCOUNTS[username] == password:
            session['logged_in'] = True
            session['admin_username'] = username  # Store which admin logged in
            print(f"✓ Login successful for: {username}")
            return jsonify({'success': True})

        print(f"✗ Login failed for: {username}")
        if username in ADMIN_ACCOUNTS:
            print(f"  Expected password: '{ADMIN_ACCOUNTS[username]}'")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    try:
        # Get all bookings from Firestore
        users = db.get_all_bookings()
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv', methods=['GET'])
@login_required
def export_csv():
    try:
        # Get all bookings from Firestore
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
            download_name=f'ai_scheduler_data_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/booking/<booking_id>', methods=['DELETE'])
@login_required
def delete_booking(booking_id):
    """Delete a booking and free up the time slot"""
    try:
        # Get all bookings
        users = db.get_all_bookings()

        # Find the booking by index or ID
        deleted_user = None
        for user in users:
            if user.get('id') == booking_id:
                deleted_user = user
                break

        if not deleted_user:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        slot_id = deleted_user.get('selected_slot')

        # Delete from Firestore
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Free up the time slot
        if slot_id:
            db.unbook_slot(slot_id)

        return jsonify({'success': True, 'message': 'Booking deleted successfully'})

    except Exception as e:
        print(f"Error deleting booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/<booking_id>', methods=['PUT'])
@login_required
def update_booking(booking_id):
    """Update a booking"""
    try:
        data = request.json

        # Get the existing booking
        booking = db.get_booking_by_id(booking_id)
        if not booking:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        old_slot = booking.get('selected_slot')
        new_slot = data.get('selected_slot', old_slot)

        # Prepare update data
        update_data = {
            'full_name': data.get('full_name', booking['full_name']),
            'email': data.get('email', booking['email']),
            'phone': data.get('phone', booking['phone']),
            'selected_room': data.get('selected_room', booking['selected_room'])
        }

        # If time slot changed, update slots
        if new_slot != old_slot:
            # Free old slot
            db.unbook_slot(old_slot)

            # Book new slot
            success = db.book_slot(new_slot, update_data['email'], update_data['selected_room'])
            if not success:
                # Re-book the old slot since new one failed
                db.book_slot(old_slot, booking['email'], booking['selected_room'])
                return jsonify({'success': False, 'message': 'New time slot already booked'}), 400

            update_data['selected_slot'] = new_slot

        # Update booking in Firestore
        success = db.update_booking(booking_id, update_data)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update booking'}), 500

        # Get updated booking
        updated_booking = db.get_booking_by_id(booking_id)

        return jsonify({'success': True, 'message': 'Booking updated successfully', 'data': updated_booking})

    except Exception as e:
        print(f"Error updating booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/manage', methods=['GET'])
@login_required
def get_all_slots():
    """Get all time slots including booked ones for admin management"""
    try:
        slots = db.get_all_slots()
        return jsonify(slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/slots/add', methods=['POST'])
@login_required
def add_time_slot():
    """Add a new time slot"""
    try:
        data = request.json
        slot_datetime = datetime.fromisoformat(data['datetime'])

        new_slot = {
            'id': slot_datetime.strftime('%Y%m%d%H%M'),
            'datetime': slot_datetime.isoformat(),
            'day': slot_datetime.strftime('%A'),
            'date': slot_datetime.strftime('%B %d, %Y'),
            'time': slot_datetime.strftime('%I:%M %p'),
            'booked': False,
            'booked_by': None,
            'room': None
        }

        # Add to Firestore
        slot_id = db.add_time_slot(new_slot)
        if not slot_id:
            return jsonify({'success': False, 'message': 'Time slot already exists or failed to add'}), 400

        return jsonify({'success': True, 'message': 'Time slot added successfully', 'slot': new_slot})

    except Exception as e:
        print(f"Error adding time slot: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/cleanup', methods=['POST'])
@login_required
def cleanup_old_slots():
    """Delete ALL old time slots from the database (including past booked slots)"""
    try:
        all_slots = db.get_all_slots()
        now = datetime.now().isoformat()

        deleted_count = 0
        for slot in all_slots:
            # Delete ALL past slots (both booked and unbooked)
            if slot.get('datetime', '') < now:
                success = db.delete_slot(slot['id'])
                if success:
                    deleted_count += 1

        print(f"OK: Cleaned up {deleted_count} old time slots")
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} old time slots',
            'deleted': deleted_count
        })

    except Exception as e:
        print(f"ERROR: Error cleaning up slots: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/auto-maintain', methods=['POST'])
@login_required
def trigger_auto_maintenance():
    """Manually trigger automatic cleanup and slot generation"""
    try:
        all_slots_before = db.get_all_slots()
        now = datetime.now().isoformat()

        past_count = len([s for s in all_slots_before if s.get('datetime', '') < now])
        future_count = len([s for s in all_slots_before if s.get('datetime', '') >= now])

        # Run the auto-maintenance
        auto_cleanup_and_generate_slots()

        all_slots_after = db.get_all_slots()
        new_future_count = len([s for s in all_slots_after if s.get('datetime', '') >= now])

        return jsonify({
            'success': True,
            'message': f'Maintenance completed: Removed {past_count} past slots, now have {new_future_count} future slots',
            'past_deleted': past_count,
            'future_before': future_count,
            'future_after': new_future_count
        })

    except Exception as e:
        print(f"ERROR: Error in auto-maintenance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/generate', methods=['POST'])
@login_required
def generate_slots_bulk():
    """Generate recurring time slots for the next N weeks"""
    try:
        data = request.json
        weeks_ahead = data.get('weeks_ahead', 6)
        cleanup_old = data.get('cleanup_old', True)

        # First, clean up ONLY past slots (NOT future slots)
        deleted_count = 0
        if cleanup_old:
            all_slots = db.get_all_slots()
            now = datetime.now().isoformat()

            for slot in all_slots:
                # Delete ONLY past slots (keep all future slots even if we're regenerating)
                if slot.get('datetime', '') < now:
                    success = db.delete_slot(slot['id'])
                    if success:
                        deleted_count += 1

            print(f"OK: Cleaned up {deleted_count} past time slots before generating new ones")

        # Generate the slots
        generated_slots = generate_time_slots(weeks_ahead)

        # Add only new slots (skip duplicates - this preserves existing future slots)
        added_count = 0
        skipped_count = 0

        for slot in generated_slots:
            slot_id = db.add_time_slot(slot)
            if slot_id:
                added_count += 1
            else:
                skipped_count += 1

        message = f'Generated {added_count} new slots for the next {weeks_ahead} weeks'
        if skipped_count > 0:
            message += f' ({skipped_count} already exist)'
        if deleted_count > 0:
            message += f'. Cleaned up {deleted_count} past slots'

        return jsonify({
            'success': True,
            'message': message,
            'added': added_count,
            'skipped': skipped_count,
            'deleted': deleted_count
        })

    except Exception as e:
        print(f"Error generating slots: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/<slot_id>', methods=['DELETE'])
@login_required
def delete_time_slot(slot_id):
    """Delete a time slot (only if not booked)"""
    try:
        # Get all slots
        slots = db.get_all_slots()

        # Find the slot
        slot_to_delete = None
        for slot in slots:
            if slot['id'] == slot_id:
                if slot['booked']:
                    return jsonify({'success': False, 'message': 'Cannot delete a booked time slot'}), 400
                slot_to_delete = slot
                break

        if slot_to_delete is None:
            return jsonify({'success': False, 'message': 'Time slot not found'}), 404

        # Delete from Firestore
        success = db.delete_slot(slot_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete slot'}), 500

        return jsonify({'success': True, 'message': 'Time slot deleted successfully'})

    except Exception as e:
        print(f"Error deleting time slot: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_slots():
    """Delete multiple slots at once"""
    try:
        data = request.json
        slot_ids = data.get('slot_ids', [])

        if not slot_ids:
            return jsonify({'success': False, 'message': 'No slot IDs provided'}), 400

        deleted_count = 0
        failed_count = 0
        booked_count = 0

        for slot_id in slot_ids:
            # Check if slot is booked
            all_slots = db.get_all_slots()
            slot = next((s for s in all_slots if s['id'] == slot_id), None)

            if not slot:
                failed_count += 1
                continue

            if slot.get('booked'):
                booked_count += 1
                continue

            success = db.delete_slot(slot_id)
            if success:
                deleted_count += 1
            else:
                failed_count += 1

        message = f'Deleted {deleted_count} slot(s)'
        if booked_count > 0:
            message += f', skipped {booked_count} booked slot(s)'
        if failed_count > 0:
            message += f', {failed_count} failed'

        return jsonify({
            'success': True,
            'message': message,
            'deleted': deleted_count,
            'booked': booked_count,
            'failed': failed_count
        })

    except Exception as e:
        print(f"Error bulk deleting slots: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/slots/delete-range', methods=['POST'])
@login_required
def delete_slots_by_range():
    """Delete slots in a date range or last N weeks"""
    try:
        data = request.json
        mode = data.get('mode', 'last_weeks')  # 'last_weeks' or 'date_range'

        all_slots = db.get_all_slots()
        now = datetime.now()

        slots_to_delete = []

        if mode == 'last_weeks':
            weeks = int(data.get('weeks', 0))
            if weeks <= 0:
                return jsonify({'success': False, 'message': 'Invalid number of weeks'}), 400

            # Calculate cutoff date (now + weeks)
            cutoff_date = now + timedelta(weeks=weeks)
            cutoff_iso = cutoff_date.isoformat()

            # Get all future unbooked slots after the cutoff
            slots_to_delete = [
                s for s in all_slots
                if s.get('datetime', '') > cutoff_iso and not s.get('booked', False)
            ]

        elif mode == 'date_range':
            start_date = data.get('start_date')
            end_date = data.get('end_date')

            if not start_date or not end_date:
                return jsonify({'success': False, 'message': 'Start and end dates required'}), 400

            # Get unbooked slots in range
            slots_to_delete = [
                s for s in all_slots
                if start_date <= s.get('datetime', '') <= end_date and not s.get('booked', False)
            ]

        deleted_count = 0
        for slot in slots_to_delete:
            success = db.delete_slot(slot['id'])
            if success:
                deleted_count += 1

        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} slot(s)',
            'deleted': deleted_count
        })

    except Exception as e:
        print(f"Error deleting slots by range: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/generate-insights/<booking_id>', methods=['POST'])
@login_required
def generate_insights_for_booking(booking_id):
    """Generate AI insights on-demand for a specific booking"""
    try:
        # Get booking from Firestore
        user = db.get_booking_by_id(booking_id)
        if not user:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404

        # Generate insights
        print(f"Generating AI insights for {user['full_name']}...")
        ai_insights = get_gemini_teaching_insights(user)

        # Update booking with insights
        success = db.update_booking(booking_id, {'ai_insights': ai_insights})
        if not success:
            return jsonify({'success': False, 'message': 'Failed to save insights'}), 500

        return jsonify({'success': True, 'insights': ai_insights})

    except Exception as e:
        print(f"Error generating insights: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/lookup', methods=['GET'])
def lookup_booking():
    """Look up a booking by email address - only returns future bookings"""
    try:
        email = request.args.get('email', '').strip()

        if not email:
            return jsonify({'success': False, 'message': 'Email address required'}), 400

        # Get all bookings from Firestore
        bookings = db.get_all_bookings()

        # Get current time
        now = datetime.now().isoformat()

        # Find booking with matching email AND future booking
        user_booking = None
        for booking in bookings:
            if booking.get('email', '').lower() == email.lower():
                # Check if this booking is in the future
                slot_details = booking.get('slot_details', {})
                slot_datetime = slot_details.get('datetime', '')

                # Only return if the booking is in the future
                if slot_datetime and slot_datetime > now:
                    user_booking = booking
                    break

        if not user_booking:
            return jsonify({'success': False, 'message': 'No upcoming booking found'}), 404

        return jsonify({
            'success': True,
            'booking': user_booking
        })

    except Exception as e:
        print(f"Error looking up booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def contact_form():
    """Handle contact form submissions and send email"""
    try:
        data = request.get_json()

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        message = data.get('message', '').strip()

        if not all([name, email, message]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        # Send email notification
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'LeAIrn Contact Form: Message from {name}'
            msg['From'] = EMAIL_FROM
            msg['To'] = EMAIL_RECIPIENT
            msg['Reply-To'] = email

            # Create HTML email body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border-radius: 10px;">
                        <h2 style="color: #6366F1; border-bottom: 2px solid #6366F1; padding-bottom: 10px;">New Contact Form Submission</h2>

                        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p><strong>From:</strong> {name}</p>
                            <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
                            <p><strong>Message:</strong></p>
                            <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #6366F1; margin-top: 10px; border-radius: 4px;">
                                {message.replace(chr(10), '<br>')}
                            </div>
                        </div>

                        <p style="color: #666; font-size: 0.9em; margin-top: 20px;">
                            This message was sent via the LeAIrn contact form.
                        </p>
                    </div>
                </body>
            </html>
            """

            # Attach HTML part
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Send email
            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)

            print(f"OK: Contact form email sent from {name} ({email})")
            return jsonify({'success': True, 'message': 'Message sent successfully!'})

        except Exception as email_error:
            print(f"ERROR: Failed to send contact email: {email_error}")
            # Still return success to user, but log the error
            return jsonify({'success': True, 'message': 'Message received! We\'ll get back to you soon.'})

    except Exception as e:
        print(f"ERROR: Contact form error: {e}")
        return jsonify({'success': False, 'message': 'Failed to send message. Please try again.'}), 500

# Initialize time slots on startup
init_time_slots()

# Vercel serverless function handler
app = app

if __name__ == '__main__':
    # Check if running in production or development
    is_production = os.getenv('FLASK_ENV') == 'production'

    if is_production:
        # Production server
        print("Starting in PRODUCTION mode...")
        app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
    else:
        # Development server
        print("Starting in DEVELOPMENT mode...")
        app.run(debug=True, port=5000)
