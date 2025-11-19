"""
Email Service Module
Handles all email functionality for the LeAIrn booking system.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional

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
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = EMAIL_FROM
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)

            print(f"[OK] Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            print(f"[ERROR] Email failed to {to_email}: {e}")
            return False

    @staticmethod
    def send_booking_confirmation(email: str, name: str, slot_data: Dict) -> bool:
        """
        Send booking confirmation email (OAuth verified users)
        
        Args:
            email: User's verified @monmouth.edu email
            name: User's full name
            slot_data: Dictionary containing slot details (day, date, time, location)
            
        Returns:
            bool: True if email sent successfully
        """
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">You're All Set!</h1>
                    <p>Hi {name},</p>
                    <p>Your AI learning session with Christopher Buzaid has been confirmed. I'm looking forward to meeting you and helping you discover the best way to use AI for your goals!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p><strong>Location:</strong> {slot_data.get('location', 'To be confirmed')}</p>
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
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.9rem; color: #9CA3AF;">
                            <strong>Need to cancel or reschedule?</strong><br>
                            Visit <a href="https://uleairn.com" style="color: #6366F1;">uleairn.com</a>, click the "View My Booking" button, and you can manage your booking from there.
                        </p>
                        <p style="font-size: 0.85rem; color: #9CA3AF; margin-top: 20px;">
                            <strong>🔒 Security Notice:</strong> LeAIrn will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=email,
            subject='Your AI Learning Session is Confirmed - LeAIrn',
            html_content=html
        )

    @staticmethod
    def send_admin_notification(user_data: Dict, slot_data: Dict) -> bool:
        """
        Send booking notification to admin
        
        Args:
            user_data: Dictionary containing user information
            slot_data: Dictionary containing slot details
            
        Returns:
            bool: True if email sent successfully
        """
        admin_email = os.getenv('EMAIL_RECIPIENT', os.getenv('EMAIL_USER'))
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">New AI Learning Session Booked</h1>
                    <p>A new session has been scheduled on LeAIrn.</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Participant Information</h2>
                        <p><strong>Name:</strong> {user_data.get('full_name', 'N/A')}</p>
                        <p><strong>Email:</strong> <a href="mailto:{user_data.get('email', '')}">{user_data.get('email', 'N/A')}</a></p>
                        <p><strong>Role:</strong> {user_data.get('role', 'N/A').capitalize() if user_data.get('role') else 'N/A'}</p>
                        <p><strong>Department/Major:</strong> {user_data.get('department', 'Not specified')}</p>
                    </div>

                    <div style="background: #f0fdf4; border-left: 4px solid #10B981; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p><strong>Location:</strong> {user_data.get('selected_room', 'Not specified')}</p>
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

        return EmailService._send_email(
            to_email=admin_email,
            subject=f'New Booking: {user_data.get("full_name", "Student")} - LeAIrn',
            html_content=html
        )

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
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Your AI Learning Session is Today!</h1>
                    <p>Hi {user_name},</p>
                    <p>Just a friendly reminder that your AI learning session with Christopher Buzaid is happening today!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Session Details</h2>
                        <p style="margin: 10px 0;"><strong>📅 Date:</strong> {session_date}</p>
                        <p style="margin: 10px 0;"><strong>⏰ Time:</strong> {session_time}</p>
                        <p style="margin: 10px 0;"><strong>📍 Location:</strong> {session_location}</p>
                        <p style="margin: 10px 0;"><strong>⏱️ Duration:</strong> 30 minutes</p>
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
                            <a href="https://uleairn.com" style="color: #F59E0B; font-weight: 600;">Visit LeAIrn to manage your booking</a>
                        </p>
                    </div>

                    <p style="margin-top: 30px;">Looking forward to seeing you today!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LeAIrn will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_email,
            subject=f"Reminder: Your AI Learning Session with Christopher Today! - LeAIrn",
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
        changes = []
        if old_slot_data and new_slot_data:
            changes.append(f"<li><strong>Time Changed:</strong> From {old_slot_data.get('day', '')}, {old_slot_data.get('date', '')} at {old_slot_data.get('time', '')} → To {new_slot_data.get('day', '')}, {new_slot_data.get('date', '')} at {new_slot_data.get('time', '')}</li>")
        if old_room and new_room and old_room != new_room:
            changes.append(f"<li><strong>Location Changed:</strong> From {old_room} → To {new_room}</li>")

        changes_html = ''.join(changes) if changes else '<li>Booking details updated</li>'
        current_slot = new_slot_data if new_slot_data else old_slot_data
        current_room = new_room if new_room else old_room
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #F59E0B;">Your Session Has Been Updated</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Your AI learning session with Christopher Buzaid has been updated by an administrator.</p>

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
                        <p><strong>Duration:</strong> 30 minutes</p>
                        <p><strong>Your AI Mentor:</strong> Christopher Buzaid</p>
                    </div>

                    <p style="margin-top: 30px;">If you have any questions or concerns about this change, please contact me directly.</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LeAIrn will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your AI Learning Session Has Been Updated - LeAIrn',
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
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #EF4444;">Your Session Has Been Cancelled</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Your AI learning session with Christopher Buzaid has been cancelled.</p>

                    <div style="background: #fee2e2; border-left: 4px solid #EF4444; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Cancelled Session Details</h2>
                        <p><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p><strong>Location:</strong> {user_data.get('selected_room', 'N/A')}</p>
                    </div>

                    <h3>Want to Reschedule?</h3>
                    <p>I'd still love to meet with you! You can book a new session anytime that works for you.</p>
                    <p style="margin-top: 15px;">
                        <a href="https://uleairn.com" style="display: inline-block; padding: 12px 24px; background: #6366F1; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Book a New Session
                        </a>
                    </p>

                    <p style="margin-top: 30px;">If you have any questions, please don't hesitate to reach out.</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LeAIrn will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your AI Learning Session Has Been Cancelled - LeAIrn',
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
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Thanks for Your Session!</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>I hope you enjoyed our AI learning session! Your feedback helps me improve and provide better experiences for future students.</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <h2 style="margin-top: 0;">Share Your Feedback</h2>
                        <p>It'll only take a minute - rate your experience and optionally share any comments.</p>
                        <p style="margin-top: 20px; margin-bottom: 0;">
                            <a href="https://uleairn.com/feedback?token={feedback_token}" style="display: inline-block; padding: 14px 28px; background: #6366F1; color: #ffffff !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                                Leave Feedback
                            </a>
                        </p>
                    </div>

                    <h3>Want to Learn More?</h3>
                    <p>Feel free to book another session anytime. I'm always happy to help you dive deeper into AI!</p>
                    <p style="margin-top: 15px;">
                        <a href="https://uleairn.com" style="display: inline-block; padding: 12px 24px; background: #10B981; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Book Another Session
                        </a>
                    </p>

                    <p style="margin-top: 30px;">Thank you for taking the time to learn with me!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LeAIrn will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='How Was Your AI Learning Session? Share Your Feedback - LeAIrn',
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
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">Your Session Summary</h1>
                    <p>Hi {user_data['full_name']},</p>
                    <p>Here's a summary of what we covered in your AI learning session. Keep this for your reference!</p>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0;">
                        <pre style="white-space: pre-wrap; font-family: Arial, sans-serif; font-size: 14px; line-height: 1.8; margin: 0;">{overview}</pre>
                    </div>

                    <h3>Keep Learning!</h3>
                    <p>Feel free to book another session anytime if you have questions or want to dive deeper.</p>
                    <p style="margin-top: 15px;">
                        <a href="https://uleairn.com" style="display: inline-block; padding: 12px 24px; background: #10B981; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                            Book Another Session
                        </a>
                    </p>

                    <p style="margin-top: 30px;">Happy learning!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>🔒 Security Notice:</strong> LeAIrn will NEVER ask for your password. Always verify this email came from <strong>leairn.notifications@gmail.com</strong>
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your AI Learning Session Summary - LeAIrn',
            html_content=html
        )
