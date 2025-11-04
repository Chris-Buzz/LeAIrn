import os
import sys
from datetime import datetime, time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import firestore_db as db
from app import send_booking_reminder_email, initialize_email_config


def send_daily_reminders():
    """
    Check for bookings scheduled for today and send reminder emails at 8:30 AM.
    """
    try:
        initialize_email_config()
        print(f"\n{'='*60}")
        print(f"Daily Reminder Email Job - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # Get all bookings
        bookings = db.get_all_bookings()
        print(f"Found {len(bookings)} total bookings")

        # Get today's date for comparison
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"Looking for bookings scheduled for: {today}\n")

        # Track reminders sent
        reminders_sent = 0
        reminders_skipped = 0

        # Check each booking
        for booking in bookings:
            try:
                slot_details = booking.get('slot_details', {})
                booking_datetime_str = slot_details.get('datetime', '')
                
                if not booking_datetime_str:
                    print(f"⚠️  Skipping booking (no datetime): {booking.get('id')}")
                    reminders_skipped += 1
                    continue

                # Parse the booking datetime
                booking_date = booking_datetime_str[:10]  # Extract YYYY-MM-DD
                booking_id = booking.get('id', 'unknown')
                user_name = booking.get('full_name', 'User')
                user_email = booking.get('email', '')

                # Check if booking is for today
                if booking_date == today:
                    print(f"📧 Found booking for today: {booking_id}")
                    print(f"   Name: {user_name}")
                    print(f"   Email: {user_email}")
                    print(f"   Time: {slot_details.get('time', 'N/A')}")

                    # Send reminder email
                    try:
                        email_sent = send_booking_reminder_email(booking)
                        if email_sent:
                            print(f"   ✅ Reminder email sent successfully\n")
                            reminders_sent += 1
                        else:
                            print(f"   ❌ Failed to send reminder email\n")
                            reminders_skipped += 1
                    except Exception as email_error:
                        print(f"   ❌ Exception sending reminder: {email_error}\n")
                        reminders_skipped += 1

            except Exception as booking_error:
                print(f"❌ Error processing booking: {booking_error}")
                reminders_skipped += 1
                continue

        # Print summary
        print(f"{'='*60}")
        print(f"Summary:")
        print(f"  ✅ Reminders sent: {reminders_sent}")
        print(f"  ⚠️  Reminders skipped: {reminders_skipped}")
        print(f"{'='*60}\n")

        return reminders_sent, reminders_skipped

    except Exception as e:
        print(f"❌ ERROR: Failed to send daily reminders: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


if __name__ == '__main__':
    send_daily_reminders()
