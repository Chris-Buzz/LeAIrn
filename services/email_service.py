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

            print(f"✓ Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            print(f"✗ Email failed to {to_email}: {e}")
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
                    <h1 style="color: #6366F1;">✓ Your Booking is Confirmed!</h1>
                    <p>Hi {name},</p>
                    <p>Great news! Your AI learning session booking has been confirmed. We look forward to meeting you!</p>

                    <div style="background: #f0fdf4; border: 2px solid #22c55e; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #16a34a;">Session Details</h3>
                        <p style="margin: 5px 0;"><strong>Date & Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                        <p style="margin: 5px 0;"><strong>Duration:</strong> 30 minutes</p>
                        <p style="margin: 5px 0;"><strong>Location:</strong> {slot_data.get('location', 'To be confirmed')}</p>
                    </div>

                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #111827;">What to Expect</h3>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>Introduction to AI tools and concepts</li>
                            <li>Hands-on demonstration of relevant AI applications</li>
                            <li>Q&A and personalized guidance</li>
                            <li>Resources for continued learning</li>
                        </ul>
                    </div>

                    <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #92400e;">Important Reminders</h3>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>Please arrive 5 minutes early</li>
                            <li>Bring any specific questions or projects you'd like to discuss</li>
                            <li>You'll receive a reminder email 1 hour before your session</li>
                        </ul>
                    </div>

                    <p>If you need to reschedule or cancel, please contact me as soon as possible.</p>
                    <p style="margin-top: 30px;">Looking forward to working with you!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com" style="color: #6366F1;">cjpbuzaid@gmail.com</a></p>

                    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB;">
                        <p style="font-size: 0.85rem; color: #9CA3AF;">
                            <strong>✓ Verified via Monmouth University SSO</strong><br>
                            This booking was created using your verified @monmouth.edu email address.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=email,
            subject='Booking Confirmed - LeAIrn',
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
        admin_email = os.getenv('ADMIN_EMAIL', EMAIL_USER)
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">🎓 New Booking</h1>
                    <p><strong>Name:</strong> {user_data.get('full_name', 'N/A')}</p>
                    <p><strong>Email:</strong> {user_data.get('email', 'N/A')}</p>
                    <p><strong>Role:</strong> {user_data.get('role', 'N/A')}</p>
                    <p><strong>Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                    <p><strong>Location:</strong> {user_data.get('selected_room', 'Not specified')}</p>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=admin_email,
            subject=f'New Booking: {user_data.get("full_name", "Student")}',
            html_content=html
        )

    @staticmethod
    def send_meeting_reminder(user_data: Dict) -> bool:
        """
        Send meeting reminder email 1 hour before session
        
        Args:
            user_data: Dictionary containing booking information
            
        Returns:
            bool: True if email sent successfully
        """
        slot_details = user_data.get('slot_details', {})
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">⏰ Your Session Starts Soon!</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>This is a friendly reminder that your AI learning session with Christopher Buzaid is coming up in <strong>1 hour</strong>!</p>

                    <div style="background: #f0f9ff; border: 2px solid #0ea5e9; border-radius: 8px; padding: 20px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #0c4a6e;">Session Details</h3>
                        <p style="margin: 5px 0;"><strong>Time:</strong> {slot_details.get('day', '')}, {slot_details.get('date', '')} at {slot_details.get('time', '')}</p>
                        <p style="margin: 5px 0;"><strong>Location:</strong> {user_data.get('selected_room', 'Check your confirmation email')}</p>
                        <p style="margin: 5px 0;"><strong>Duration:</strong> 30 minutes</p>
                    </div>

                    <p><strong>Quick Tips:</strong></p>
                    <ul>
                        <li>Arrive 5 minutes early</li>
                        <li>Bring any questions or projects you'd like to discuss</li>
                        <li>Have a notebook or laptop ready for notes</li>
                    </ul>

                    <p>See you soon!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn</p>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='⏰ Reminder: Your AI Session Starts in 1 Hour',
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
            changes.append(f"<li><strong>Time:</strong> {old_slot_data.get('day')} {old_slot_data.get('time')} → {new_slot_data.get('day')} {new_slot_data.get('time')}</li>")
        if old_room and new_room:
            changes.append(f"<li><strong>Location:</strong> {old_room} → {new_room}</li>")

        changes_html = "".join(changes) if changes else "<li>Booking details updated</li>"
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #f59e0b;">📝 Booking Updated</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Your AI learning session booking has been updated:</p>
                    <ul style="background: #fef3c7; padding: 15px; border-radius: 8px;">
                        {changes_html}
                    </ul>
                    <p>All other details remain the same. See you soon!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn</p>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Booking Updated - LeAIrn',
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
                    <h1 style="color: #ef4444;">❌ Booking Cancelled</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Your AI learning session booking has been cancelled:</p>
                    <div style="background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
                        <p style="margin: 5px 0;"><strong>Time:</strong> {slot_data.get('day', '')}, {slot_data.get('date', '')} at {slot_data.get('time', '')}</p>
                    </div>
                    <p>If you'd like to reschedule, please visit <a href="https://uleairn.com">uleairn.com</a> to book a new session.</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn</p>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Booking Cancelled - LeAIrn',
            html_content=html
        )

    @staticmethod
    def send_feedback_request(user_data: Dict) -> bool:
        """
        Send feedback request email after session
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            bool: True if email sent successfully
        """
        feedback_link = "https://uleairn.com/feedback"
        
        html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #6366F1;">📝 How Was Your Session?</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Thank you for attending your AI learning session! I'd love to hear your feedback.</p>
                    <p>Your input helps me improve future sessions and better serve the Monmouth University community.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{feedback_link}" style="display: inline-block; background: #6366F1; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold;">Share Your Feedback</a>
                    </div>
                    <p>It only takes 2 minutes and your responses are anonymous.</p>
                    <p>Thank you!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn</p>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Share Your Feedback - LeAIrn',
            html_content=html
        )

    @staticmethod
    def send_session_overview(user_data: Dict, overview: str) -> bool:
        """
        Send AI-generated session overview to student
        
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
                    <h1 style="color: #6366F1;">📄 Your Session Summary</h1>
                    <p>Hi {user_data.get('full_name', 'there')},</p>
                    <p>Here's a summary of your AI learning session:</p>
                    <div style="background: #f9fafb; border-left: 4px solid #6366F1; padding: 20px; margin: 20px 0; white-space: pre-wrap;">
                        {overview}
                    </div>
                    <p>Feel free to reach out if you have any follow-up questions!</p>
                    <p style="color: #6B7280;">- Christopher Buzaid<br>LeAIrn<br><a href="mailto:cjpbuzaid@gmail.com">cjpbuzaid@gmail.com</a></p>
                </div>
            </body>
        </html>
        """

        return EmailService._send_email(
            to_email=user_data.get('email', ''),
            subject='Your Session Summary - LeAIrn',
            html_content=html
        )
