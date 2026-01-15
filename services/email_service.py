"""
Email Service Module
Handles all email functionality for the LearnAI booking system.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables (must be before reading env vars)
load_dotenv()

# Email configuration
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_FROM = os.getenv('EMAIL_FROM', EMAIL_USER)


class EmailService:
    """Service for sending various types of emails"""

    @staticmethod
    def _send_email(to_email: str, subject: str, html_content: str) -> bool:
        """
        Internal method to send email via SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_content: HTML email body

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Check if email is configured
            if not EMAIL_USER or not EMAIL_PASSWORD:
                print(f"[CRITICAL ERROR] Email not configured!")
                print(f"[CRITICAL ERROR] EMAIL_USER: {'SET' if EMAIL_USER else 'NOT SET'}")
                print(f"[CRITICAL ERROR] EMAIL_PASSWORD: {'SET' if EMAIL_PASSWORD else 'NOT SET'}")
                print(f"[CRITICAL ERROR] Please set EMAIL_USER and EMAIL_PASSWORD in .env file")
                return False

            if EMAIL_USER == 'your-email@gmail.com' or EMAIL_PASSWORD == 'your-gmail-app-password':
                print(f"[CRITICAL ERROR] Email credentials are still default values!")
                print(f"[CRITICAL ERROR] EMAIL_USER: {EMAIL_USER}")
                print(f"[CRITICAL ERROR] Please update .env with real Gmail credentials")
                print(f"[CRITICAL ERROR] Get Gmail App Password from: https://myaccount.google.com/apppasswords")
                return False

            # Strip whitespace from credentials (common issue)
            email_user = EMAIL_USER.strip() if EMAIL_USER else None
            email_password = EMAIL_PASSWORD.strip() if EMAIL_PASSWORD else None

            if not email_user or not email_password:
                print(f"[ERROR] Email credentials not configured properly")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = EMAIL_FROM
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
                server.starttls()
                server.login(email_user, email_password)
                server.send_message(msg)

            print(f"[OK] Email sent successfully")
            return True

        except smtplib.SMTPAuthenticationError:
            print(f"[ERROR] SMTP authentication failed - check EMAIL_PASSWORD in .env")
            return False
        except Exception as e:
            print(f"[ERROR] Email send failed: {type(e).__name__}")
            return False

    @staticmethod
    def send_booking_confirmation(email: str, name: str, slot_data: Dict) -> bool:
        """
        Send booking confirmation email (OAuth verified users)

        Args:
            email: User's verified @monmouth.edu email
            name: User's full name
            slot_data: Dictionary containing slot details (day, date, time, location, tutor info)

        Returns:
            bool: True if email sent successfully
        """
        # Get tutor information from slot_data
        tutor_name = slot_data.get('tutor_name', 'Christopher Buzaid')
        tutor_email = slot_data.get('tutor_email', 'cjpbuzaid@gmail.com')

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">You're All Set!</h1>
                    <p>Hi {name},</p>
                    <p>Your AI learning session with {tutor_name} has been confirmed. I'm looking forward to meeting you and helping you discover the best way to use AI for your goals!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p><strong>Location:</strong> {slot_data.get('location', 'To be confirmed')}</p>
                        <p><strong>Duration:</strong> 30-90 minutes</p>
                        <p><strong>Your AI Mentor:</strong> {tutor_name}</p>
                    </div>

                    <h3>What to Bring:</h3>
                    <ul>
                        <li>Any specific questions or topics you'd like to cover</li>
                        <li>Your laptop if you want hands-on practice</li>
                        <li>An open mind and curiosity!</li>
                    </ul>

                    <p style="margin-top: 30px;">See you soon!</p>
                    <p style="color: #6B7280;">- {tutor_name}<br>LearnAI<br><a href="mailto:{tutor_email}" style="color: #6366F1;">{tutor_email}</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.9rem; color: #9CA3AF;">
                            <strong>Need to cancel or reschedule?</strong><br>
                            Visit <a href="https://lainow.com" style="color: #6366F1;">lainow.com</a>, click the "View My Booking" button, and you can manage your booking from there.
                        </p>
                        <p style="font-size: 0.85rem; color: #9CA3AF; margin-top: 20px;">
                            <strong>🔒 Security Notice:</strong> LearnAI will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=email,
            subject='Your AI Learning Session is Confirmed - LearnAI',
            html_content=html
        )

    @staticmethod
    def send_admin_notification(user_data: Dict, slot_data: Dict) -> bool:
        """
        Send booking notification to tutor and master admin

        Args:
            user_data: Dictionary containing user information
            slot_data: Dictionary containing slot details (including tutor info)

        Returns:
            bool: True if all emails sent successfully
        """
        # Get tutor email from slot_data, fallback to Christopher
        tutor_email = slot_data.get('tutor_email', 'cjpbuzaid@gmail.com')
        tutor_name = slot_data.get('tutor_name', 'Christopher Buzaid')

        # Master admin email (always receives notifications)
        master_email = 'cjpbuzaid@gmail.com'

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">New AI Learning Session Booked</h1>
                    <p>A new session has been scheduled on LearnAI with <strong>{tutor_name}</strong>.</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Participant Information</h2>
                        <p><strong>Name:</strong> {user_data.get('full_name', 'N/A')}</p>
                        <p><strong>Email:</strong> <a href="mailto:{user_data.get('email', '')}">{user_data.get('email', 'N/A')}</a></p>
                        <p><strong>Role:</strong> {user_data.get('role', 'N/A').capitalize() if user_data.get('role') else 'N/A'}</p>
                        <p><strong>Department/Major:</strong> {user_data.get('department', 'Not specified')}</p>
                    </div>

                    <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p><strong>Tutor:</strong> {tutor_name}</p>
                        <p><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p><strong>Location:</strong> {user_data.get('selected_room', 'Not specified')}</p>
                        <p><strong>Duration:</strong> 30-90 minutes</p>
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
                        This is an automated notification from LearnAI. You can view and manage all bookings in your
                        <a href="https://lainow.com/admin" style="color: #6366F1;">admin dashboard</a>.
                    </p>
                </div>
            </body>
        </html>
        """

        # Send to tutor
        tutor_success = EmailService._send_email(
            to_email=tutor_email,
            subject=f'New Booking: {user_data.get("full_name", "Student")} - LearnAI',
            html_content=html
        )

        # Also send to master admin if different from tutor
        master_success = True
        if tutor_email.lower() != master_email.lower():
            master_success = EmailService._send_email(
                to_email=master_email,
                subject=f'New Booking for {tutor_name}: {user_data.get("full_name", "Student")} - LearnAI',
                html_content=html
            )

        return tutor_success and master_success

    @staticmethod
    def send_meeting_reminder(user_data: Dict) -> bool:
        """
        Send meeting reminder email on day of session at 8:30 AM

        Args:
            user_data: Dictionary containing booking information

        Returns:
            bool: True if email sent successfully
        """
        slot_details = user_data.get('slot_details', {})
        user_email = user_data.get('email', '')
        user_name = user_data.get('full_name', 'Student')
        session_location = user_data.get('selected_room', 'TBD')
        session_time = slot_details.get('time', 'N/A')
        session_date = f"{slot_details.get('day', '')}, {slot_details.get('date', '')}"

        # Get tutor info from booking data or slot details
        tutor_name = user_data.get('tutor_name') or slot_details.get('tutor_name', 'Christopher Buzaid')
        tutor_email = user_data.get('tutor_email') or slot_details.get('tutor_email', 'cjpbuzaid@gmail.com')

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Your AI Learning Session is Today!</h1>
                    <p>Hi {user_name},</p>
                    <p>Just a friendly reminder that your AI learning session with {tutor_name} is happening today!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p style="margin: 10px 0;"><strong>📅 Date:</strong> {session_date}</p>
                        <p style="margin: 10px 0;"><strong>⏰ Time:</strong> {session_time}</p>
                        <p style="margin: 10px 0;"><strong>📍 Location:</strong> {session_location}</p>
                        <p style="margin: 10px 0;"><strong>⏱️ Duration:</strong> 30-90 minutes</p>
                        <p style="margin: 10px 0;"><strong>👤 Your AI Mentor:</strong> {tutor_name}</p>
                    </div>

                    <h3>📌 Tips Before You Come:</h3>
                    <ul>
                        <li>Arrive 5 minutes early</li>
                        <li>Bring any questions or projects you're working on</li>
                        <li>Have your laptop ready if we're doing hands-on work</li>
                        <li>Let me know if you need to reschedule</li>
                    </ul>

                    <div style="background: #fff7ed; border-left: 4px solid #F59E0B; padding: 20px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #F59E0B;">Need to Reschedule?</h3>
                        <p style="margin: 10px 0;">If something came up, please let me know as soon as possible.</p>
                        <p style="margin: 10px 0;">
                            <a href="https://lainow.com" style="color: #F59E0B; font-weight: 600;">Visit LearnAI to manage your booking</a>
                        </p>
                    </div>

                    <p style="margin-top: 30px;">Looking forward to seeing you today!</p>
                    <p style="color: #6B7280;">- {tutor_name}<br>LearnAI<br><a href="mailto:{tutor_email}" style="color: #6366F1;">{tutor_email}</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LearnAI will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_email,
            subject=f"Reminder: Your AI Learning Session with {tutor_name} Today! - LearnAI",
            html_content=html
        )

    @staticmethod
    def send_booking_update(user_data: Dict, old_slot_data: Optional[Dict] = None,
                           new_slot_data: Optional[Dict] = None,
                           old_room: Optional[str] = None,
                           new_room: Optional[str] = None) -> bool:
        """
        Send email notification when booking is updated

        Args:
            user_data: Dictionary containing user information
            old_slot_data: Previous slot details (if time changed)
            new_slot_data: New slot details (if time changed)
            old_room: Previous room (if location changed)
            new_room: New room (if location changed)

        Returns:
            bool: True if email sent successfully
        """
        # Get tutor info from user_data or slot details
        current_slot = new_slot_data if new_slot_data else old_slot_data or {}
        tutor_name = user_data.get('tutor_name') or current_slot.get('tutor_name', 'Christopher Buzaid')
        tutor_email = user_data.get('tutor_email') or current_slot.get('tutor_email', 'cjpbuzaid@gmail.com')

        changes = []
        if old_slot_data and new_slot_data:
            changes.append(f"<li><strong>Time Changed:</strong> From {old_slot_data.get('day', '')}, {old_slot_data.get('date', '')} at {old_slot_data.get('time', '')} → To {new_slot_data.get('day', '')}, {new_slot_data.get('date', '')} at {new_slot_data.get('time', '')}</li>")
        if old_room and new_room and old_room != new_room:
            changes.append(f"<li><strong>Location Changed:</strong> From {old_room} → To {new_room}</li>")

        changes_html = ''.join(changes) if changes else '<li>Booking details updated</li>'
        current_room = new_room if new_room else old_room

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #F59E0B;">Your Session Has Been Updated</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Your AI learning session with {tutor_name} has been updated by an administrator.</p>

                    <div style="background: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">What Changed</h2>
                        <ul style="margin: 0; padding-left: 20px;">
                            {changes_html}
                        </ul>
                    </div>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Updated Session Details</h2>
                        <p><strong>Date & Time:</strong> {current_slot.get('day', '')}, {current_slot.get('date', '')} at {current_slot.get('time', '')}</p>
                        <p><strong>Location:</strong> {current_room}</p>
                        <p><strong>Duration:</strong> 30-90 minutes</p>
                        <p><strong>Your AI Mentor:</strong> {tutor_name}</p>
                    </div>

                    <p style="margin-top: 30px;">If you have any questions or concerns about this change, please contact me directly.</p>
                    <p style="color: #6B7280;">- {tutor_name}<br>LearnAI<br><a href="mailto:{tutor_email}" style="color: #6366F1;">{tutor_email}</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LearnAI will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your AI Learning Session Has Been Updated - LearnAI',
            html_content=html
        )

    @staticmethod
    def send_booking_deletion(user_data: Dict, slot_data: Dict) -> bool:
        """
        Send email notification when booking is cancelled

        Args:
            user_data: Dictionary containing user information
            slot_data: Dictionary containing cancelled slot details

        Returns:
            bool: True if email sent successfully
        """
        # Get tutor info from user_data or slot_data
        tutor_name = user_data.get('tutor_name') or slot_data.get('tutor_name', 'Christopher Buzaid')
        tutor_email = user_data.get('tutor_email') or slot_data.get('tutor_email', 'cjpbuzaid@gmail.com')

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #EF4444;">Your Session Has Been Cancelled</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Your AI learning session with {tutor_name} has been cancelled.</p>

                    <div style="background: #fee2e2; border-left: 4px solid #EF4444; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Cancelled Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p><strong>Location:</strong> {user_data.get('selected_room', 'N/A')}</p>
                        <p><strong>AI Mentor:</strong> {tutor_name}</p>
                    </div>

                    <h3>Want to Reschedule?</h3>
                    <p>We'd still love to meet with you! You can book a new session anytime that works for you.</p>
                    <p style="margin-top: 15px;">
                        <a href="https://lainow.com" style="display: inline-block; padding: 12px 24px; background: #6366F1; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Book a New Session
                        </a>
                    </p>

                    <p style="margin-top: 30px;">If you have any questions, please don't hesitate to reach out.</p>
                    <p style="color: #6B7280;">- {tutor_name}<br>LearnAI<br><a href="mailto:{tutor_email}" style="color: #6366F1;">{tutor_email}</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LearnAI will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your AI Learning Session Has Been Cancelled - LearnAI',
            html_content=html
        )

    @staticmethod
    def send_feedback_request(user_data: Dict, booking_id: str = None) -> bool:
        """
        Send feedback request email after session

        Args:
            user_data: Dictionary containing user information
            booking_id: The booking ID to use as feedback token

        Returns:
            bool: True if email sent successfully
        """
        # Generate feedback token using booking ID
        feedback_token = booking_id if booking_id else user_data.get('id', '')

        # Get tutor info from user_data or slot_details
        slot_details = user_data.get('slot_details', {})
        tutor_name = user_data.get('tutor_name') or slot_details.get('tutor_name', 'Christopher Buzaid')
        tutor_email = user_data.get('tutor_email') or slot_details.get('tutor_email', 'cjpbuzaid@gmail.com')

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Thanks for Your Session!</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>I hope you enjoyed your AI learning session with {tutor_name}! Your feedback helps us improve and provide better experiences for future students.</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Share Your Feedback</h2>
                        <p>It'll only take a minute - rate your experience and optionally share any comments.</p>
                        <p style="margin-top: 20px; margin-bottom: 0;">
                            <a href="https://lainow.com/feedback?token={feedback_token}" style="display: inline-block; padding: 14px 28px; background: #6366F1; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                Leave Feedback
                            </a>
                        </p>
                    </div>

                    <h3>Want to Learn More?</h3>
                    <p>Feel free to book another session anytime. We're always happy to help you dive deeper into AI!</p>
                    <p style="margin-top: 15px;">
                        <a href="https://lainow.com" style="display: inline-block; padding: 12px 24px; background: #10B981; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Book Another Session
                        </a>
                    </p>

                    <p style="margin-top: 30px;">Thank you for taking the time to learn with us!</p>
                    <p style="color: #6B7280;">- {tutor_name}<br>LearnAI<br><a href="mailto:{tutor_email}" style="color: #6366F1;">{tutor_email}</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LearnAI will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='How Was Your AI Learning Session? Share Your Feedback - LearnAI',
            html_content=html
        )

    @staticmethod
    def send_session_overview(user_data: Dict, overview: str) -> bool:
        """
        Send session overview email to user

        Args:
            user_data: Dictionary containing user information
            overview: AI-generated session summary

        Returns:
            bool: True if email sent successfully
        """
        # Get tutor info from user_data or slot_details
        slot_details = user_data.get('slot_details', {})
        tutor_name = user_data.get('tutor_name') or slot_details.get('tutor_name', 'Christopher Buzaid')
        tutor_email = user_data.get('tutor_email') or slot_details.get('tutor_email', 'cjpbuzaid@gmail.com')

        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Your Session Summary</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>Here's a summary of what we covered in your AI learning session with {tutor_name}. Keep this for your reference!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; font-size: 14px; line-height: 1.8; margin: 0;">{overview}</pre>
                    </div>

                    <h3>Keep Learning!</h3>
                    <p>Feel free to book another session anytime if you have questions or want to dive deeper.</p>
                    <p style="margin-top: 15px;">
                        <a href="https://lainow.com" style="display: inline-block; padding: 12px 24px; background: #10B981; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Book Another Session
                        </a>
                    </p>

                    <p style="margin-top: 30px;">Happy learning!</p>
                    <p style="color: #6B7280;">- {tutor_name}<br>LearnAI<br><a href="mailto:{tutor_email}" style="color: #6366F1;">{tutor_email}</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LearnAI will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your AI Learning Session Summary - LearnAI',
            html_content=html
        )

    @staticmethod
    def send_admin_verification_code(email: str, code: str, admin_name: str = 'Admin') -> bool:
        """
        Send verification code to admin email for security verification

        Args:
            email: Admin's email address
            code: 6-digit verification code
            admin_name: Admin's display name

        Returns:
            bool: True if email sent successfully
        """
        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #11111B;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #11111B; padding: 40px 20px;">
                    <tr>
                        <td align="center">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #1E1E2E; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
                                <!-- Header with gradient -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #6366F1 0%, #818CF8 100%); padding: 40px 40px 30px; text-align: center;">
                                        <div style="width: 70px; height: 70px; background: rgba(255,255,255,0.2); border-radius: 50%; margin: 0 auto 20px; line-height: 70px;">
                                            <span style="font-size: 32px;">&#128274;</span>
                                        </div>
                                        <h1 style="color: #ffffff; font-size: 24px; font-weight: 700; margin: 0 0 8px;">Admin Verification Required</h1>
                                        <p style="color: rgba(255,255,255,0.8); font-size: 15px; margin: 0;">Security check for your account</p>
                                    </td>
                                </tr>

                                <!-- Body content -->
                                <tr>
                                    <td style="padding: 35px 40px;">
                                        <p style="color: #CDD6F4; font-size: 15px; line-height: 1.7; margin: 0 0 25px;">
                                            Hi <strong style="color: #A6E3A1;">{admin_name}</strong>, enter the verification code below to confirm your identity.
                                        </p>

                                        <!-- Code display box -->
                                        <div style="background: rgba(99, 102, 241, 0.1); border: 2px solid rgba(99, 102, 241, 0.3); border-radius: 16px; padding: 30px; margin: 25px 0; text-align: center;">
                                            <p style="color: #A6ADC8; margin: 0 0 12px; font-size: 13px;">Your verification code:</p>
                                            <p style="font-size: 40px; font-weight: 700; letter-spacing: 12px; color: #A6E3A1; margin: 15px 0; font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;">{code}</p>
                                            <p style="color: #6C7086; font-size: 12px; margin: 15px 0 0;">Expires in 10 minutes</p>
                                        </div>

                                        <!-- Security warning -->
                                        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #F59E0B; border-radius: 0 8px 8px 0; padding: 14px 16px; margin-top: 20px;">
                                            <p style="color: #FCD34D; font-size: 13px; margin: 0;">
                                                <strong>Security Notice:</strong> <span style="color: #A6ADC8;">If you didn't request this code, someone may have tried to access your account. Please ignore this email.</span>
                                            </p>
                                        </div>

                                        <p style="color: #6C7086; font-size: 12px; text-align: center; margin: 25px 0 0;">
                                            This verification is required periodically as a security measure.
                                        </p>
                                    </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                    <td style="background: #181825; padding: 25px 40px; text-align: center; border-top: 1px solid #313244;">
                                        <p style="color: #6C7086; font-size: 12px; margin: 0;">
                                            LearnAI Admin Security &bull; <a href="https://lainow.com" style="color: #818CF8; text-decoration: none;">lainow.com</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=email,
            subject='LearnAI Admin Verification Code',
            html_content=html
        )

    @staticmethod
    def send_account_verification_link(email: str, verification_link: str, admin_name: str = 'Admin') -> bool:
        """
        Send account creation verification link to admin email

        Args:
            email: Admin's email address
            verification_link: Full URL to verify and create account
            admin_name: Admin's display name

        Returns:
            bool: True if email sent successfully
        """
        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #11111B;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #11111B; padding: 40px 20px;">
                    <tr>
                        <td align="center">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #1E1E2E; border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
                                <!-- Header with gradient -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); padding: 40px 40px 30px; text-align: center;">
                                        <div style="width: 70px; height: 70px; background: rgba(255,255,255,0.2); border-radius: 50%; margin: 0 auto 20px; line-height: 70px;">
                                            <span style="font-size: 32px;">&#9989;</span>
                                        </div>
                                        <h1 style="color: #ffffff; font-size: 24px; font-weight: 700; margin: 0 0 8px;">Verify Your Admin Account</h1>
                                        <p style="color: rgba(255,255,255,0.8); font-size: 15px; margin: 0;">Complete your LearnAI admin setup</p>
                                    </td>
                                </tr>

                                <!-- Body content -->
                                <tr>
                                    <td style="padding: 35px 40px;">
                                        <p style="color: #CDD6F4; font-size: 15px; line-height: 1.7; margin: 0 0 25px;">
                                            Hi <strong style="color: #A6E3A1;">{admin_name}</strong>, you're almost there! Click the button below to verify your email and activate your admin account.
                                        </p>

                                        <!-- CTA Button -->
                                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 30px 0;">
                                            <tr>
                                                <td align="center">
                                                    <a href="{verification_link}" style="display: inline-block; padding: 16px 40px; background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); color: #ffffff; text-decoration: none; border-radius: 12px; font-weight: 700; font-size: 16px;">
                                                        Verify Email & Create Account
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>

                                        <p style="color: #A6ADC8; font-size: 13px; text-align: center; margin: 0 0 30px;">
                                            This link expires in 1 hour
                                        </p>

                                        <!-- Link fallback box -->
                                        <div style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 12px; padding: 16px 20px; margin-bottom: 20px;">
                                            <p style="color: #A6ADC8; font-size: 13px; margin: 0 0 8px;">
                                                <strong style="color: #CDD6F4;">Can't click the button?</strong> Copy and paste this link:
                                            </p>
                                            <p style="color: #818CF8; font-size: 12px; margin: 0; word-break: break-all;">
                                                {verification_link}
                                            </p>
                                        </div>

                                        <!-- Security warning -->
                                        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #F59E0B; border-radius: 0 8px 8px 0; padding: 14px 16px;">
                                            <p style="color: #FCD34D; font-size: 13px; margin: 0;">
                                                <strong>Security Notice:</strong> <span style="color: #A6ADC8;">If you didn't request this, ignore this email. No account will be created.</span>
                                            </p>
                                        </div>
                                    </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                    <td style="background: #181825; padding: 25px 40px; text-align: center; border-top: 1px solid #313244;">
                                        <p style="color: #6C7086; font-size: 12px; margin: 0 0 8px;">
                                            LearnAI will NEVER ask for your password in an email.
                                        </p>
                                        <p style="color: #6C7086; font-size: 12px; margin: 0;">
                                            LearnAI Admin Security &bull; <a href="https://lainow.com" style="color: #818CF8; text-decoration: none;">lainow.com</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=email,
            subject='Verify Your LearnAI Admin Account',
            html_content=html
        )

    @staticmethod
    def send_contact_message(sender_name: str, sender_email: str, message: str) -> bool:
        """
        Send contact form message to the admin/tutor

        Args:
            sender_name: Name of the person sending the message
            sender_email: Email of the person sending the message
            message: The message content
        """
        from datetime import datetime

        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
            </head>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1F2937; background-color: #f3f4f6; margin: 0; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #6366F1; margin-bottom: 10px;">New Contact Form Message</h1>
                        <p style="color: #6B7280; font-size: 0.95rem;">Received on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                    </div>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                        <h2 style="margin-top: 0; color: #374151;">Sender Information</h2>
                        <p><strong>Name:</strong> {sender_name}</p>
                        <p><strong>Email:</strong> <a href="mailto:{sender_email}" style="color: #6366F1;">{sender_email}</a></p>
                    </div>

                    <div style="background: #fefce8; border-left: 4px solid #EAB308; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                        <h2 style="margin-top: 0; color: #374151;">Message</h2>
                        <p style="white-space: pre-wrap; margin: 0;">{message}</p>
                    </div>

                    <p style="margin-top: 30px;">
                        <a href="mailto:{sender_email}?subject=Re: Your LearnAI Inquiry" style="display: inline-block; padding: 12px 24px; background: #6366F1; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Reply to {sender_name}
                        </a>
                    </p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB; text-align: center;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            LearnAI Contact Form &bull; <a href="https://lainow.com" style="color: #6366F1;">lainow.com</a>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email='cjpbuzaid@gmail.com',
            subject=f'LearnAI Contact Form: Message from {sender_name}',
            html_content=html
        )
