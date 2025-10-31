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
import threading
import time

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
    os.getenv('ADMIN1_USERNAME', 'christopher'): os.getenv('ADMIN1_PASSWORD', 'ChangeThisPassword123!'),
    # Professor account
    os.getenv('ADMIN2_USERNAME', 'professor'): os.getenv('ADMIN2_PASSWORD', 'ProfessorPassword123!'),
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

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.9rem; color: #9CA3AF; text-align: center;">
                            <strong>Need to cancel or reschedule?</strong><br>
                            Visit <a href="https://uleairn.com" style="color: #6366F1;">uleairn.com</a>, click the "View My Booking" button, and you can manage your booking from there.
                        </p>
                    </div>
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

def send_admin_notification_email(user_data, slot_data):
    """Send booking notification email to admin"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'New Booking: {user_data["full_name"]} - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_RECIPIENT
        msg['Reply-To'] = user_data['email']

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">New AI Learning Session Booked</h1>
                    <p>A new session has been scheduled on LeAIrn.</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Participant Information</h2>
                        <p><strong>Name:</strong> {user_data['full_name']}</p>
                        <p><strong>Email:</strong> <a href="mailto:{user_data['email']}">{user_data['email']}</a></p>
                        <p><strong>Role:</strong> {user_data.get('role', 'N/A').capitalize()}</p>
                        <p><strong>Department/Major:</strong> {user_data.get('department', 'Not specified')}</p>
                    </div>

                    <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data['day']}, {slot_data['date']} at {slot_data['time']}</p>
                        <p><strong>Location:</strong> {user_data['selected_room']}</p>
                        <p><strong>Duration:</strong> 30 minutes</p>
                    </div>

                    <div style="background: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">AI Experience Profile</h2>
                        <p><strong>Experience Level:</strong> {user_data.get('ai_familiarity', 'Not specified')}</p>
                        <p><strong>Tools Used:</strong> {user_data.get('ai_tools', 'None')}</p>
                        <p><strong>Primary Interests:</strong> {user_data.get('primary_use', 'Not specified')}</p>
                        <p><strong>Learning Goals:</strong> {user_data.get('learning_goal', 'Not specified')}</p>
                        {f"<p><strong>Personal Comments:</strong> {user_data.get('personal_comments')}</p>" if user_data.get('personal_comments') else ""}
                    </div>

                    <p style="margin-top: 30px; color: #6B7280; font-size: 0.9rem;">
                        This is an automated notification from LeAIrn. You can view and manage all bookings in your
                        <a href="https://uleairn.com/admin" style="color: #6366F1;">admin dashboard</a>.
                    </p>
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

        print(f"OK: Admin notification email sent for booking by {user_data['full_name']}")
        return True
    except Exception as e:
        print(f"Error sending admin notification email: {e}")
        return False

def send_booking_update_email(user_data, old_slot_data=None, new_slot_data=None, old_room=None, new_room=None):
    """Send email to user when their booking is updated"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your AI Learning Session Has Been Updated - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = user_data['email']

        # Determine what changed
        changes = []
        if old_slot_data and new_slot_data:
            changes.append(f"<li><strong>Time Changed:</strong> From {old_slot_data['day']}, {old_slot_data['date']} at {old_slot_data['time']} → To {new_slot_data['day']}, {new_slot_data['date']} at {new_slot_data['time']}</li>")
        if old_room and new_room and old_room != new_room:
            changes.append(f"<li><strong>Location Changed:</strong> From {old_room} → To {new_room}</li>")

        changes_html = ''.join(changes) if changes else '<li>Booking details updated</li>'
        current_slot = new_slot_data if new_slot_data else old_slot_data
        current_room = new_room if new_room else old_room

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #F59E0B;">Your Session Has Been Updated</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>Your AI learning session with Christopher Buzaid has been updated by an administrator.</p>

                    <div style="background: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">What Changed</h2>
                        <ul style="margin: 0; padding-left: 20px;">
                            {changes_html}
                        </ul>
                    </div>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Updated Session Details</h2>
                        <p><strong>Date & Time:</strong> {current_slot['day']}, {current_slot['date']} at {current_slot['time']}</p>
                        <p><strong>Location:</strong> {current_room}</p>
                        <p><strong>Duration:</strong> 30 minutes</p>
                        <p><strong>Your AI Mentor:</strong> Christopher Buzaid</p>
                    </div>

                    <p style="margin-top: 30px;">If you have any questions or concerns about this change, please contact me directly.</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com">cjpbuzaid@gmail.com</a></p>
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

        print(f"OK: Booking update email sent to {user_data['email']}")
        return True
    except Exception as e:
        print(f"Error sending booking update email: {e}")
        return False

def send_booking_deletion_email(user_data, slot_data):
    """Send email to user when their booking is deleted"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your AI Learning Session Has Been Cancelled - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = user_data['email']

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #EF4444;">Your Session Has Been Cancelled</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>Your AI learning session with Christopher Buzaid has been cancelled.</p>

                    <div style="background: #fee2e2; border-left: 4px solid #EF4444; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Cancelled Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data['day']}, {slot_data['date']} at {slot_data['time']}</p>
                        <p><strong>Location:</strong> {user_data['selected_room']}</p>
                    </div>

                    <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Want to Reschedule?</h2>
                        <p>I'd still love to meet with you! You can book a new session anytime that works for you.</p>
                        <p style="margin-top: 15px;">
                            <a href="https://uleairn.com" style="display: inline-block; padding: 12px 24px; background: #6366F1; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                Book a New Session
                            </a>
                        </p>
                    </div>

                    <p style="margin-top: 30px;">If you have any questions, please don't hesitate to reach out.</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com">cjpbuzaid@gmail.com</a></p>
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

        print(f"OK: Booking deletion email sent to {user_data['email']}")
        return True
    except Exception as e:
        print(f"Error sending booking deletion email: {e}")
        return False

def send_feedback_request_email(user_data):
    """Send feedback request email to user after completing session"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'How Was Your AI Learning Session? Share Your Feedback - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = user_data['email']

        # Generate a unique feedback token (using booking ID)
        feedback_token = user_data['id']

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Thanks for Your Session!</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>I hope you enjoyed our AI learning session! Your feedback helps me improve and provide better experiences for future students.</p>

                    <div style="background: #f0f9ff; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0; color: #6366F1;">Share Your Feedback</h2>
                        <p>It'll only take a minute - rate your experience and optionally share any comments.</p>
                        <p style="margin-top: 20px; margin-bottom: 0;">
                            <a href="https://uleairn.com/feedback?token={feedback_token}" style="display: inline-block; padding: 14px 28px; background: #6366F1; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.5); border: 2px solid #4F46E5;">
                                Leave Feedback
                            </a>
                        </p>
                    </div>

                    <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Want to Learn More?</h2>
                        <p>Feel free to book another session anytime. I'm always happy to help you dive deeper into AI!</p>
                        <p style="margin-top: 15px;">
                            <a href="https://uleairn.com" style="display: inline-block; padding: 12px 24px; background: #10B981; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                Book Another Session
                            </a>
                        </p>
                    </div>

                    <p style="margin-top: 30px;">Thank you for taking the time to learn with me!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com">cjpbuzaid@gmail.com</a></p>
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

        print(f"OK: Feedback request email sent to {user_data['email']}")
        return True
    except Exception as e:
        print(f"Error sending feedback request email: {e}")
        return False

def send_verification_email(email: str, code: str) -> bool:
    """Send verification code email for booking lookup"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Verification Code - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = email

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Verify Your Email</h1>
                    <p>Hi there,</p>
                    <p>Someone requested to view a booking associated with this email address. To continue, please use the verification code below:</p>

                    <div style="background: #f0f9ff; border: 2px solid #6366F1; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                        <h2 style="margin: 0; color: #6366F1; font-size: 32px; letter-spacing: 8px; font-weight: 700;">{code}</h2>
                    </div>

                    <p style="color: #6B7280; font-size: 14px;">This code will expire in 10 minutes.</p>
                    <p style="color: #6B7280; font-size: 14px;">If you didn't request this, you can safely ignore this email.</p>

                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="color: #6B7280; font-size: 14px; margin: 0;">
                            - LeAIrn Team<br>
                            <a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a>
                        </p>
                    </div>
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

        print(f"OK: Verification email sent to {email}")
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False

def enhance_session_notes_with_ai(notes: str, user_data: dict) -> str:
    """Use Gemini AI to enhance and format session notes"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        prompt = f"""
You are helping format session notes from an AI teaching session. Take the raw notes provided and create a professional, well-organized summary that the student can use as a reference.

STUDENT INFO:
- Name: {user_data.get('full_name', 'Student')}
- Role: {user_data.get('role', 'N/A')}

RAW SESSION NOTES:
{notes}

Create a clean, organized summary in plain text (no markdown) with these sections:

SESSION OVERVIEW
Brief summary of what was covered in the session (2-3 sentences).

TOOLS INTRODUCED
List the specific AI tools that were demonstrated or discussed.

PROMPTING TECHNIQUES TAUGHT
List the key prompting strategies and techniques covered.

KEY CONCEPTS
Main ideas and concepts explained during the session.

ACTION ITEMS
What the student should practice or work on next.

Keep it concise, professional, and easy to read. Focus on the practical takeaways.
"""

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"ERROR: Error enhancing notes with AI: {e}")
        return notes  # Return original notes if AI fails

def send_session_overview_email(user_data: dict, overview: str) -> bool:
    """Send session overview email to user"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your AI Learning Session Summary - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = user_data['email']

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Your Session Summary</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>Here's a summary of what we covered in your AI learning session. Keep this for your reference!</p>

                    <div style="background: #f0f9ff; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; font-size: 14px; line-height: 1.8; margin: 0;">{overview}</pre>
                    </div>

                    <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Keep Learning!</h2>
                        <p>Feel free to book another session anytime if you have questions or want to dive deeper.</p>
                        <p style="margin-top: 15px;">
                            <a href="https://uleairn.com" style="display: inline-block; padding: 12px 24px; background: #10B981; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                                Book Another Session
                            </a>
                        </p>
                    </div>

                    <p style="margin-top: 30px;">Happy learning!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com">cjpbuzaid@gmail.com</a></p>
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

        print(f"OK: Session overview email sent to {user_data['email']}")
        return True
    except Exception as e:
        print(f"Error sending session overview email: {e}")
        return False

def send_meeting_reminder_email(user_data: dict) -> bool:
    """Send meeting reminder email to user the morning of their session"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Reminder: Your AI Learning Session Today - LeAIrn'
        msg['From'] = EMAIL_FROM
        msg['To'] = user_data['email']

        slot_details = user_data.get('slot_details', {})
        day = slot_details.get('day', 'Today')
        date = slot_details.get('date', '')
        time = slot_details.get('time', 'your scheduled time')
        location = user_data.get('selected_room', 'the scheduled location')

        # Create HTML email
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Your Session is Today!</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>This is a friendly reminder that your AI learning session is scheduled for today.</p>

                    <div style="background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white; border-radius: 12px; padding: 25px; margin: 25px 0; text-align: center;">
                        <h2 style="margin: 0 0 15px 0; font-size: 24px;">Session Details</h2>
                        <div style="background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">TIME</div>
                            <div style="font-size: 22px; font-weight: 700;">{time}</div>
                        </div>
                        <div style="background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 15px;">
                            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 5px;">LOCATION</div>
                            <div style="font-size: 20px; font-weight: 700;">{location}</div>
                        </div>
                    </div>

                    <div style="background: #f0f9ff; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #6366F1;">What to Bring</h3>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>Your laptop or device</li>
                            <li>Any specific questions or topics you want to cover</li>
                            <li>An open mind and eagerness to learn!</li>
                        </ul>
                    </div>

                    <div style="background: #fff7ed; border-left: 4px solid #F59E0B; padding: 20px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #F59E0B;">Need to Reschedule?</h3>
                        <p style="margin: 10px 0;">If something came up, please let me know as soon as possible.</p>
                        <p style="margin: 10px 0;">
                            <a href="https://uleairn.com" style="color: #F59E0B; font-weight: 600;">Visit LeAIrn to manage your booking</a>
                        </p>
                    </div>

                    <p style="margin-top: 30px;">Looking forward to seeing you today!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>
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

        print(f"OK: Meeting reminder email sent to {user_data['email']}")
        return True
    except Exception as e:
        print(f"Error sending meeting reminder email: {e}")
        return False

def check_and_send_meeting_reminders():
    """Check for bookings today and send reminder emails"""
    try:
        print("Checking for meetings today to send reminders...")

        # Get all bookings
        bookings = db.get_all_bookings()

        # Get today's date
        today = datetime.now().date()

        reminders_sent = 0
        for booking in bookings:
            slot_details = booking.get('slot_details', {})
            slot_datetime_str = slot_details.get('datetime', '')

            if not slot_datetime_str:
                continue

            # Parse the slot datetime
            try:
                slot_datetime = datetime.fromisoformat(slot_datetime_str)
                slot_date = slot_datetime.date()

                # Check if booking is today
                if slot_date == today:
                    # Send reminder email
                    print(f"Sending reminder to {booking['full_name']} for session at {slot_details.get('time')}")
                    success = send_meeting_reminder_email(booking)
                    if success:
                        reminders_sent += 1
                        print(f"✓ Reminder sent to {booking['email']}")
                    else:
                        print(f"✗ Failed to send reminder to {booking['email']}")
            except Exception as e:
                print(f"Error parsing datetime for booking {booking.get('id')}: {e}")
                continue

        print(f"Meeting reminder check complete. Sent {reminders_sent} reminder(s).")
        return reminders_sent

    except Exception as e:
        print(f"ERROR: Error in check_and_send_meeting_reminders: {e}")
        return 0

def morning_reminder_scheduler():
    """Background thread that sends reminders at 8:30 AM every day"""
    while True:
        try:
            now = datetime.now()

            # Check if it's 8:30 AM (or between 8:30-8:31 to allow for execution time)
            if now.hour == 8 and now.minute == 30:
                print("=== Running morning reminder scheduler at 8:30 AM ===")
                check_and_send_meeting_reminders()

                # Sleep for 60 seconds to avoid sending multiple times in the same minute
                time.sleep(60)

            # Check every 30 seconds
            time.sleep(30)

        except Exception as e:
            print(f"ERROR: Exception in morning_reminder_scheduler: {e}")
            time.sleep(60)  # Sleep for a minute before retrying

def get_gemini_teaching_insights(user_data):
    """Use Gemini AI to generate personalized teaching recommendations"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')

        # Include personal comments if available
        comments_section = ""
        if user_data.get('personal_comments'):
            comments_section = f"\n- Student's Comments: {user_data.get('personal_comments')}"

        prompt = f"""
You are preparing a 30-minute personalized AI Teaching Guide for an instructor. The instructor’s job is to teach the student how to USE AI tools to solve their own problems effectively — not to solve the problems for them. 

The guide should be practical, tool-specific, and centered around showing the student how to think, prompt, and experiment with AI.

STUDENT PROFILE:
- Name: {user_data['full_name']}
- Role: {user_data['role']}
- Department/Major: {user_data.get('department', 'Not specified')}
- AI Experience: {user_data.get('ai_familiarity', 'Not specified')}
- Tools Used: {user_data.get('ai_tools', 'None')}
- Interested In: {user_data.get('primary_use', 'Not specified')}
- Goals: {user_data.get('learning_goal', 'Not specified')}
- Confidence Level: {user_data.get('confidence_level', 'Not specified')}/5
{comments_section}

TASK:
Generate a concise, practical teaching guide that helps the instructor run a 30-minute session tailored to this student. 
The instructor should walk away knowing exactly how to:
1. Identify the student’s biggest real-world challenges.
2. Match them with relevant AI tools that can genuinely help them.
3. Teach them how to use those tools step-by-step.
4. Help them refine their prompts to get useful results.
5. Equip them with a repeatable method for solving future problems independently.

STRUCTURE OF OUTPUT:

THEIR PROBLEMS/NEEDS (2–3 sentences):
Describe what kinds of problems or challenges this student likely faces in their role, based on their profile and goals.

AI TOOLS THAT CAN HELP THEM (2–3 tools):
List AI tools most relevant to this person’s work or goals. Choose tools across different categories (e.g., productivity, creativity, coding, analysis, research, communication, planning). For each tool, briefly explain what specific problem it helps them solve and how.

SESSION OUTLINE — Teaching Them to Fish (Total: 30 min):
1. Opening (0–5 min): Discuss their daily challenges or frustrations. Show one quick example of AI solving a relevant problem.
2. Core Skills (5–15 min): Demonstrate how to ask AI for help effectively. Show 2–3 example prompts tailored to their field.
3. Practice (15–25 min): Let the student use AI to solve one of their actual problems. Guide them on refining their prompts, comparing outputs, and verifying accuracy.
4. Wrap-up (25–30 min): Give them a framework for solving future problems using AI tools. Reinforce the process of experimenting, iterating, and validating results.

PROMPTING TECHNIQUES FOR THEIR PROBLEMS (3–4 techniques):
Provide 3–4 prompting strategies that are directly relevant to this student’s typical problems. Include clear examples such as:
- “How to ask AI for help when stuck on [specific type of task].”
- “How to get AI to break down complex [field-related] problems.”
- “How to iterate with AI to refine solutions and check accuracy.”

HOW TO HELP THEM SOLVE THEIR OWN PROBLEMS:
Provide the instructor with a simple framework for teaching the student to become self-sufficient with AI. Focus on:
- What kinds of questions to ask to uncover their real pain points.
- How to demonstrate AI solving a similar or smaller problem first.
- How to guide the student to prompt and explore on their own.
- How to teach them to evaluate, refine, and verify AI responses.

IMPORTANT:
- The AI must recommend tools and strategies that *genuinely fit the student’s needs and experience level.*
- Avoid generic or overly broad suggestions — make them actionable and relevant.
- If personal comments or special context are included, use them to make the guide more human and personalized.

{f"Address their comment: {user_data.get('personal_comments')}" if user_data.get('personal_comments') else ""}

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

@app.route('/feedback')
def feedback():
    """Feedback page for users to rate their session"""
    return render_template('feedback.html')

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

        # Store research consent status (true = consented, false = declined, null = not asked)
        data['research_consent'] = data.get('research_consent', None)

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

        # Send confirmation email to user
        print(f"Sending confirmation email to {data['email']}...")
        email_sent = send_confirmation_email(data, selected_slot_data)

        # Send notification email to admin
        print(f"Sending admin notification email...")
        admin_email_sent = send_admin_notification_email(data, selected_slot_data)

        return jsonify({
            'success': True,
            'message': 'Booking confirmed!',
            'data': {
                'name': data['full_name'],
                'slot': selected_slot_data,
                'room': data['selected_room'],
                'email_sent': email_sent,
                'admin_notified': admin_email_sent
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

@app.route('/api/feedback', methods=['GET'])
@login_required
def get_all_feedback():
    """Get all feedback for admin view"""
    try:
        feedback_list = db.get_all_feedback()
        return jsonify(feedback_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session-overviews', methods=['GET'])
@login_required
def get_session_overviews():
    """Get all session overviews for admin view"""
    try:
        overviews = db.get_all_session_overviews()
        return jsonify(overviews)
    except Exception as e:
        print(f"Error getting session overviews: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session-overviews/<booking_id>', methods=['DELETE'])
@login_required
def delete_session_overview(booking_id):
    """Delete a session overview"""
    try:
        success = db.delete_session_overview(booking_id)
        if success:
            return jsonify({'success': True, 'message': 'Overview deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete overview'}), 500
    except Exception as e:
        print(f"Error deleting session overview: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/send-reminders', methods=['POST'])
@login_required
def manual_send_reminders():
    """Manually trigger reminder emails for testing"""
    try:
        count = check_and_send_meeting_reminders()
        return jsonify({
            'success': True,
            'message': f'Sent {count} reminder email(s)',
            'reminders_sent': count
        })
    except Exception as e:
        print(f"Error sending reminders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/session-overviews/manual', methods=['POST'])
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

        # Validation
        if not user_name or not user_email or not notes:
            return jsonify({'success': False, 'message': 'Name, email, and notes are required'}), 400

        # Generate a unique booking ID for this manual overview
        import uuid
        booking_id = f"manual_{uuid.uuid4().hex[:12]}"

        # Enhance notes with AI if requested
        enhanced_notes = notes
        if not skip_ai:
            print(f"Enhancing manual session notes with AI...")
            user_data = {
                'full_name': user_name,
                'role': 'N/A'
            }
            enhanced_notes = enhance_session_notes_with_ai(notes, user_data)
        else:
            print(f"Skipping AI enhancement for manual overview")

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
            print(f"Sending manual overview email to {user_email}...")
            user_data = {
                'full_name': user_name,
                'email': user_email
            }
            email_sent = send_session_overview_email(user_data, enhanced_notes)
            if not email_sent:
                print(f"WARNING: Failed to send overview email")

        return jsonify({
            'success': True,
            'message': 'Overview saved successfully',
            'email_sent': send_email
        })

    except Exception as e:
        print(f"Error creating manual overview: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/session-overviews/preview', methods=['POST'])
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
            user_data = {
                'full_name': user_name,
                'role': user_role
            }
            enhanced_notes = enhance_session_notes_with_ai(notes, user_data)

        return jsonify({
            'success': True,
            'enhanced_notes': enhanced_notes
        })

    except Exception as e:
        print(f"Error previewing session overview: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
        slot_details = deleted_user.get('slot_details', {})

        # Delete from Firestore
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Free up the time slot
        if slot_id:
            db.unbook_slot(slot_id)

        # Send deletion notification email to user
        print(f"Sending deletion notification email to {deleted_user['email']}...")
        try:
            email_sent = send_booking_deletion_email(deleted_user, slot_details)
            if email_sent:
                print(f"OK: Deletion notification email sent successfully")
            else:
                print(f"WARNING: Deletion notification email failed to send")
        except Exception as email_error:
            print(f"ERROR: Exception while sending deletion email: {email_error}")

        return jsonify({'success': True, 'message': 'Booking deleted successfully'})

    except Exception as e:
        print(f"Error deleting booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/<booking_id>/complete', methods=['POST'])
@login_required
def mark_booking_complete(booking_id):
    """Mark a booking as complete, send feedback request and session overview, then delete it"""
    try:
        data = request.json or {}
        session_notes = data.get('notes', '').strip()
        skip_ai = data.get('skip_ai', False)

        # Get all bookings
        users = db.get_all_bookings()

        # Find the booking
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
                print(f"Skipping AI enhancement, using raw notes...")
                enhanced_notes = session_notes
            else:
                print(f"Enhancing session notes with AI...")
                enhanced_notes = enhance_session_notes_with_ai(session_notes, completed_user)

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
            print(f"Sending session overview email to {completed_user['email']}...")
            try:
                overview_sent = send_session_overview_email(completed_user, enhanced_notes)
                if overview_sent:
                    print(f"OK: Session overview email sent successfully")
                else:
                    print(f"WARNING: Session overview email failed to send")
            except Exception as email_error:
                print(f"ERROR: Exception while sending overview email: {email_error}")

        # Send feedback request email
        print(f"Sending feedback request email to {completed_user['email']}...")
        try:
            email_sent = send_feedback_request_email(completed_user)
            if email_sent:
                print(f"OK: Feedback request email sent successfully")
            else:
                print(f"WARNING: Feedback request email failed to send")
        except Exception as email_error:
            print(f"ERROR: Exception while sending feedback email: {email_error}")

        # Store user info for feedback association (before deleting booking)
        db.store_feedback_metadata(booking_id, {
            'user_name': completed_user.get('full_name', 'Unknown'),
            'user_email': completed_user.get('email', 'Unknown')
        })

        # Delete the booking
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Free up the time slot
        if slot_id:
            db.unbook_slot(slot_id)

        return jsonify({'success': True, 'message': 'Session marked complete and feedback email sent'})

    except Exception as e:
        print(f"Error marking booking complete: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a completed session"""
    try:
        data = request.json

        # Validate required fields
        if not data.get('token'):
            return jsonify({'success': False, 'message': 'Invalid feedback link'}), 400

        if not data.get('rating') or not isinstance(data.get('rating'), int) or data.get('rating') < 1 or data.get('rating') > 5:
            return jsonify({'success': False, 'message': 'Please provide a rating between 1 and 5'}), 400

        booking_id = data['token']
        rating = data['rating']
        comments = data.get('comments', '').strip()

        # Check if feedback already exists for this booking
        existing_feedback = db.get_feedback_by_booking_id(booking_id)
        if existing_feedback:
            return jsonify({'success': False, 'message': 'Feedback has already been submitted for this session'}), 400

        # Get user metadata for this booking
        user_metadata = db.get_feedback_metadata(booking_id)

        # Create feedback document
        feedback_data = {
            'booking_id': booking_id,
            'rating': rating,
            'comments': comments,
            'timestamp': datetime.now().isoformat(),
            'user_name': user_metadata.get('user_name', 'Unknown') if user_metadata else 'Unknown',
            'user_email': user_metadata.get('user_email', 'Unknown') if user_metadata else 'Unknown'
        }

        # Save to Firestore
        feedback_id = db.add_feedback(feedback_data)

        if feedback_id:
            print(f"OK: Feedback submitted - Rating: {rating}/5, Booking ID: {booking_id}")
            return jsonify({'success': True, 'message': 'Thank you for your feedback!', 'feedback_id': feedback_id})
        else:
            return jsonify({'success': False, 'message': 'Failed to save feedback'}), 500

    except Exception as e:
        print(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while submitting feedback'}), 500

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
        old_room = booking.get('selected_room')
        new_room = data.get('selected_room', old_room)

        # Track if anything changed
        slot_changed = new_slot != old_slot
        room_changed = new_room != old_room

        # Prepare update data
        update_data = {
            'full_name': data.get('full_name', booking['full_name']),
            'email': data.get('email', booking['email']),
            'selected_room': new_room
        }

        # Get slot details for email
        old_slot_data = None
        new_slot_data = None

        if slot_changed:
            # Get old slot details
            old_slot_data = booking.get('slot_details', {})

            # Free old slot
            db.unbook_slot(old_slot)

            # Book new slot
            success = db.book_slot(new_slot, update_data['email'], update_data['selected_room'])
            if not success:
                # Re-book the old slot since new one failed
                db.book_slot(old_slot, booking['email'], booking['selected_room'])
                return jsonify({'success': False, 'message': 'New time slot already booked'}), 400

            update_data['selected_slot'] = new_slot

            # Get new slot details
            all_slots = db.get_all_slots()
            for slot in all_slots:
                if slot.get('id') == new_slot:
                    new_slot_data = slot
                    update_data['slot_details'] = slot
                    break

        # Update booking in Firestore
        success = db.update_booking(booking_id, update_data)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update booking'}), 500

        # Send update notification email if something changed
        if slot_changed or room_changed:
            print(f"Sending update notification email to {booking['email']}...")
            send_booking_update_email(
                booking,
                old_slot_data=old_slot_data,
                new_slot_data=new_slot_data,
                old_room=old_room,
                new_room=new_room
            )

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

@app.route('/api/booking/lookup', methods=['POST'])
def lookup_booking():
    """Send verification code to email for booking lookup"""
    try:
        data = request.json
        email = data.get('email', '').strip()

        if not email:
            return jsonify({'success': False, 'message': 'Email address required'}), 400

        # Get all bookings from Firestore
        bookings = db.get_all_bookings()

        # Get current time
        now = datetime.now().isoformat()

        # Find all future bookings with matching email
        user_bookings = []
        for booking in bookings:
            if booking.get('email', '').lower() == email.lower():
                # Check if this booking is in the future
                slot_details = booking.get('slot_details', {})
                slot_datetime = slot_details.get('datetime', '')

                # Only include if the booking is in the future
                if slot_datetime and slot_datetime > now:
                    user_bookings.append(booking)

        if not user_bookings:
            return jsonify({'success': False, 'message': 'No upcoming bookings found'}), 404

        # Generate 6-digit verification code
        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Set expiration (10 minutes from now)
        expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()

        # Store verification code
        success = db.store_verification_code(email, code, expires_at)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to generate verification code'}), 500

        # Send verification email
        email_sent = send_verification_email(email, code)
        if not email_sent:
            return jsonify({'success': False, 'message': 'Failed to send verification email'}), 500

        return jsonify({
            'success': True,
            'message': 'Verification code sent to your email'
        })

    except Exception as e:
        print(f"Error in booking lookup: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/verify', methods=['POST'])
def verify_booking_code():
    """Verify code and return booking details"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        code = data.get('code', '').strip()

        if not email or not code:
            return jsonify({'success': False, 'message': 'Email and code required'}), 400

        # Get verification code from database
        verification = db.get_verification_code(email)

        if not verification:
            return jsonify({'success': False, 'message': 'Invalid or expired code'}), 400

        # Check if code was already used
        if verification.get('used'):
            return jsonify({'success': False, 'message': 'This code has already been used'}), 400

        # Verify code matches
        if verification.get('code') != code:
            return jsonify({'success': False, 'message': 'Invalid verification code'}), 400

        # Mark code as used
        db.mark_verification_code_used(email)

        # Get all bookings for this user
        bookings = db.get_all_bookings()
        now = datetime.now().isoformat()

        user_bookings = []
        for booking in bookings:
            if booking.get('email', '').lower() == email.lower():
                slot_details = booking.get('slot_details', {})
                slot_datetime = slot_details.get('datetime', '')
                if slot_datetime and slot_datetime > now:
                    user_bookings.append(booking)

        if not user_bookings:
            return jsonify({'success': False, 'message': 'No upcoming bookings found'}), 404

        # Sort bookings by datetime (earliest first)
        user_bookings.sort(key=lambda x: x.get('slot_details', {}).get('datetime', ''))

        return jsonify({
            'success': True,
            'bookings': user_bookings
        })

    except Exception as e:
        print(f"Error verifying code: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/delete-by-email', methods=['POST'])
def delete_booking_by_email():
    """Delete a booking by email address - for user self-deletion"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        confirmed = data.get('confirmed', False)

        if not email:
            return jsonify({'success': False, 'message': 'Email address required'}), 400

        if not confirmed:
            return jsonify({'success': False, 'message': 'Deletion not confirmed'}), 400

        # Get all bookings from Firestore
        bookings = db.get_all_bookings()

        # Get current time
        now = datetime.now().isoformat()

        # Find booking with matching email AND future booking
        booking_to_delete = None
        for booking in bookings:
            if booking.get('email', '').lower() == email.lower():
                # Check if this booking is in the future
                slot_details = booking.get('slot_details', {})
                slot_datetime = slot_details.get('datetime', '')

                # Only delete if the booking is in the future
                if slot_datetime and slot_datetime > now:
                    booking_to_delete = booking
                    break

        if not booking_to_delete:
            return jsonify({'success': False, 'message': 'No upcoming booking found to delete'}), 404

        # Get the booking ID and slot ID
        booking_id = booking_to_delete.get('id')
        slot_id = booking_to_delete.get('selected_slot')
        slot_details = booking_to_delete.get('slot_details', {})

        # Delete from Firestore
        success = db.delete_booking(booking_id)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to delete booking'}), 500

        # Free up the time slot
        if slot_id:
            db.unbook_slot(slot_id)

        # Send deletion notification email to user
        print(f"Sending deletion notification email to {booking_to_delete['email']}...")
        try:
            email_sent = send_booking_deletion_email(booking_to_delete, slot_details)
            if email_sent:
                print(f"OK: Deletion notification email sent successfully")
            else:
                print(f"WARNING: Deletion notification email failed to send")
        except Exception as email_error:
            print(f"ERROR: Exception while sending deletion email: {email_error}")

        return jsonify({'success': True, 'message': 'Booking deleted successfully'})

    except Exception as e:
        print(f"Error deleting booking: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/booking/update-by-email', methods=['POST'])
def update_booking_by_email():
    """Update a booking by email address - for user self-edit"""
    try:
        data = request.json
        email = data.get('email', '').strip()
        new_slot_id = data.get('selected_slot')
        new_building = data.get('selected_building')
        new_room_number = data.get('room_number', '').strip()

        if not email:
            return jsonify({'success': False, 'message': 'Email address required'}), 400

        # Get all bookings from Firestore
        bookings = db.get_all_bookings()

        # Get current time
        now = datetime.now().isoformat()

        # Find booking with matching email AND future booking
        booking_to_update = None
        for booking in bookings:
            if booking.get('email', '').lower() == email.lower():
                # Check if this booking is in the future
                slot_details = booking.get('slot_details', {})
                slot_datetime = slot_details.get('datetime', '')

                # Only update if the booking is in the future
                if slot_datetime and slot_datetime > now:
                    booking_to_update = booking
                    break

        if not booking_to_update:
            return jsonify({'success': False, 'message': 'No upcoming booking found to update'}), 404

        booking_id = booking_to_update.get('id')
        old_slot_id = booking_to_update.get('selected_slot')
        old_room = booking_to_update.get('selected_room')
        old_slot_data = booking_to_update.get('slot_details', {})

        # Prepare update data
        new_room = f"{new_building} - {new_room_number}" if new_building and new_room_number else old_room
        update_data = {
            'selected_room': new_room,
            'selected_building': new_building,
            'room_number': new_room_number
        }

        # Track changes
        slot_changed = False
        room_changed = new_room != old_room
        new_slot_data = None

        # If time slot changed, update slots
        if new_slot_id and new_slot_id != old_slot_id:
            # Free old slot
            db.unbook_slot(old_slot_id)

            # Book new slot
            success = db.book_slot(new_slot_id, email, new_room)
            if not success:
                # Re-book the old slot since new one failed
                db.book_slot(old_slot_id, email, old_room)
                return jsonify({'success': False, 'message': 'New time slot already booked'}), 400

            update_data['selected_slot'] = new_slot_id
            slot_changed = True

            # Get new slot details
            all_slots = db.get_all_slots()
            for slot in all_slots:
                if slot.get('id') == new_slot_id:
                    new_slot_data = slot
                    update_data['slot_details'] = slot
                    break

        # Update booking in Firestore
        success = db.update_booking(booking_id, update_data)
        if not success:
            return jsonify({'success': False, 'message': 'Failed to update booking'}), 500

        # Send update notification email if something changed
        if slot_changed or room_changed:
            print(f"Sending update notification email to {email}...")
            try:
                email_sent = send_booking_update_email(
                    booking_to_update,
                    old_slot_data=old_slot_data if slot_changed else None,
                    new_slot_data=new_slot_data if slot_changed else None,
                    old_room=old_room if room_changed else None,
                    new_room=new_room if room_changed else None
                )
                if email_sent:
                    print(f"OK: Update notification email sent successfully")
            except Exception as email_error:
                print(f"ERROR: Exception while sending update email: {email_error}")

        # Get updated booking
        updated_booking = db.get_booking_by_id(booking_id)

        return jsonify({'success': True, 'message': 'Booking updated successfully', 'booking': updated_booking})

    except Exception as e:
        print(f"Error updating booking: {e}")
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
    # Start the morning reminder scheduler in a background thread
    print("Starting morning reminder scheduler...")
    reminder_thread = threading.Thread(target=morning_reminder_scheduler, daemon=True)
    reminder_thread.start()
    print("✓ Morning reminder scheduler started (runs at 8:30 AM daily)")

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
