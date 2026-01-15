"""
Slot Service Module
Handles time slot management, generation, cleanup, and reminders.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from .email_service import EmailService


class SlotService:
    """Service for managing booking time slots"""

    def __init__(self, db, timezone_util):
        """
        Initialize slot service with database and timezone utility
        
        Args:
            db: Database instance (firestore_db)
            timezone_util: Timezone utility for Eastern time conversion
        """
        self.db = db
        self.tz = timezone_util
        self.last_auto_cleanup = None

    def init_slots(self) -> None:
        """Check if time slots exist - admin controls generation now"""
        slots = self.db.get_all_slots()
        if len(slots) == 0:
            print("No time slots found. Admin can generate slots from dashboard.")

    def generate_slots(self, weeks_ahead: int = 6, weekly_schedule: Optional[Dict] = None,
                      tutor_id: str = None, tutor_name: str = None, tutor_email: str = None,
                      location_type: str = 'user_choice', location_value: str = '') -> List[Dict]:
        """
        Generate time slots in Eastern time with optional tutor-specific parameters

        Args:
            weeks_ahead: Number of weeks to generate slots for
            weekly_schedule: Optional custom schedule {weekday: [(hour, minute), ...]}
                           If None, uses default schedule
            tutor_id: Tutor ID to assign slots to
            tutor_name: Tutor name to assign slots to
            tutor_email: Tutor email to assign slots to
            location_type: Meeting location type (zoom, room, user_choice)
            location_value: Zoom link or room name if applicable

        Returns:
            List of slot dictionaries with datetime, day, date, time, tutor info, etc.
        """
        # DEBUG: Log received parameters
        print(f"[DEBUG] SlotService.generate_slots called with:")
        print(f"[DEBUG]   tutor_id: {tutor_id}")
        print(f"[DEBUG]   tutor_name: {tutor_name}")
        print(f"[DEBUG]   tutor_email: {tutor_email}")

        slots = []

        # Start from today in Eastern time
        start_date = self.tz.get_eastern_now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Use custom schedule if provided, otherwise use default
        if weekly_schedule is None:
            # Default schedule (backward compatibility)
            weekly_schedule = {
                1: [(11, 0), (12, 0), (13, 0)],  # Tuesday
                2: [(14, 0), (15, 0)],            # Wednesday
                3: [(12, 0), (13, 0)],            # Thursday
                4: [(11, 0), (12, 0), (13, 0)]   # Friday
            }
        else:
            # Convert string keys to integers (JSON converts dict keys to strings)
            weekly_schedule = {int(k): v for k, v in weekly_schedule.items()}

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

                        # Only add future slots (compare in Eastern time)
                        if slot_time > self.tz.get_eastern_now():
                            # Generate slot ID with tutor_id to prevent conflicts
                            base_slot_id = slot_time.strftime('%Y%m%d%H%M')
                            slot_id = f"{base_slot_id}_{tutor_id}" if tutor_id else base_slot_id

                            slot_data = {
                                'id': slot_id,
                                'datetime': slot_time.isoformat(),
                                'day': slot_time.strftime('%A'),
                                'date': slot_time.strftime('%B %d, %Y'),
                                'time': slot_time.strftime('%I:%M %p'),
                                'booked': False,
                                'booked_by': None,
                                'room': None,
                                'location_type': location_type,
                                'location_value': location_value
                            }

                            # Add tutor information if provided
                            if tutor_id:
                                slot_data['tutor_id'] = tutor_id
                            if tutor_name:
                                slot_data['tutor_name'] = tutor_name
                                print(f"[DEBUG] Setting tutor_name to: {tutor_name} for slot {slot_id}")
                            if tutor_email:
                                slot_data['tutor_email'] = tutor_email

                            slots.append(slot_data)

        return slots

    def auto_cleanup_and_generate(self) -> bool:
        """
        Automatic maintenance: Clean up past slots ONLY.
        Does NOT auto-generate - admin must manually add slots.
        Uses Eastern time to determine what's "past".
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            all_slots = self.db.get_all_slots()
            now_eastern = self.tz.get_eastern_now()

            # Count past and future slots (based on Eastern time)
            past_slots = []
            future_slots = []
            
            for slot in all_slots:
                slot_datetime_str = slot.get('datetime', '')
                try:
                    # Convert slot time to Eastern
                    slot_datetime_eastern = self.tz.get_eastern_datetime(slot_datetime_str)
                    
                    if slot_datetime_eastern and slot_datetime_eastern < now_eastern:
                        past_slots.append(slot)
                    else:
                        future_slots.append(slot)
                except:
                    # If parsing fails, treat as past (safe deletion)
                    past_slots.append(slot)

            # Delete all past slots (both booked and unbooked)
            deleted_count = 0
            for slot in past_slots:
                success = self.db.delete_slot(slot['id'])
                if success:
                    deleted_count += 1

            if deleted_count > 0:
                print(f"AUTO-CLEANUP: Deleted {deleted_count} past time slots (Eastern time)")

            # DO NOT auto-generate slots - admin must manually add via dashboard
            if len(future_slots) < 10:
                print(f"WARNING: Only {len(future_slots)} future slots remaining. Admin should add more from dashboard.")

            return True

        except Exception as e:
            print(f"ERROR in auto_cleanup_and_generate: {e}")
            return False

    def periodic_maintenance(self) -> None:
        """Run automatic cleanup and slot generation periodically (Eastern time)"""
        # Only run cleanup once per hour
        now = self.tz.get_eastern_now()
        if self.last_auto_cleanup is None or (now - self.last_auto_cleanup) > timedelta(hours=1):
            print(f"Running periodic maintenance at {now.strftime('%Y-%m-%d %I:%M %p %Z')}...")
            self.auto_cleanup_and_generate()
            self.last_auto_cleanup = now

    def check_and_send_meeting_reminders(self) -> int:
        """
        Check for bookings today (Eastern time) and send reminder emails
        
        Returns:
            int: Number of reminders sent successfully
        """
        try:
            print("Checking for meetings today to send reminders...")

            # Get all bookings
            bookings = self.db.get_all_bookings()

            # Get today's date in Eastern time
            today = self.tz.get_eastern_now().date()

            reminders_sent = 0
            for booking in bookings:
                slot_details = booking.get('slot_details', {})
                slot_datetime_str = slot_details.get('datetime', '')

                if not slot_datetime_str:
                    continue

                # Parse the slot datetime and convert to Eastern
                try:
                    slot_datetime_eastern = self.tz.get_eastern_datetime(slot_datetime_str)
                    if not slot_datetime_eastern:
                        continue
                        
                    slot_date = slot_datetime_eastern.date()

                    # Check if booking is today (Eastern time)
                    if slot_date == today:
                        # Send reminder email
                        print(f"Sending reminder to {booking['full_name']} for session at {slot_details.get('time')} Eastern")
                        success = EmailService.send_meeting_reminder(booking)
                        if success:
                            reminders_sent += 1
                            print(f"[OK] Reminder sent to {booking['email']}")
                        else:
                            print(f"[ERROR] Failed to send reminder to {booking['email']}")
                except Exception as e:
                    print(f"Error parsing datetime for booking {booking.get('id')}: {e}")
                    continue

            print(f"Meeting reminder check complete. Sent {reminders_sent} reminder(s).")
            return reminders_sent

        except Exception as e:
            print(f"ERROR: Error in check_and_send_meeting_reminders: {e}")
            return 0

    def morning_reminder_scheduler(self) -> None:
        """Background thread that sends reminders at 8:30 AM Eastern every day"""
        while True:
            try:
                # Get Eastern time
                now = self.tz.get_eastern_now()

                # Check if it's 8:30 AM Eastern (or between 8:30-8:31)
                if now.hour == 8 and now.minute == 30:
                    print(f"=== Running morning reminder scheduler at 8:30 AM Eastern (actual time: {now}) ===")
                    self.check_and_send_meeting_reminders()

                    # Sleep for 60 seconds to avoid sending multiple times
                    time.sleep(60)

                # Check every 30 seconds
                time.sleep(30)

            except Exception as e:
                print(f"ERROR: Exception in morning_reminder_scheduler: {e}")
                time.sleep(60)  # Sleep for a minute before retrying

    def get_available_slots(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all available (unbooked) slots
        
        Args:
            limit: Optional maximum number of slots to return
            
        Returns:
            List of available slot dictionaries
        """
        all_slots = self.db.get_all_slots()
        available = [s for s in all_slots if not s.get('booked', False)]
        
        # Sort by datetime
        available.sort(key=lambda x: x.get('datetime', ''))
        
        if limit:
            return available[:limit]
        return available

    def get_slot_by_id(self, slot_id: str) -> Optional[Dict]:
        """
        Get slot details by ID
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            Slot dictionary or None if not found
        """
        slots = self.db.get_all_slots()
        for slot in slots:
            if slot.get('id') == slot_id:
                return slot
        return None

    def book_slot(self, slot_id: str, user_email: str, room: str) -> bool:
        """
        Mark a slot as booked
        
        Args:
            slot_id: Slot identifier
            user_email: User's email address
            room: Selected room/location
            
        Returns:
            bool: True if successfully booked
        """
        return self.db.book_slot(slot_id, user_email, room)

    def unbook_slot(self, slot_id: str) -> bool:
        """
        Mark a slot as available again
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            bool: True if successfully unbooked
        """
        return self.db.unbook_slot(slot_id)

    def delete_slot(self, slot_id: str) -> bool:
        """
        Delete a slot permanently
        
        Args:
            slot_id: Slot identifier
            
        Returns:
            bool: True if successfully deleted
        """
        return self.db.delete_slot(slot_id)

    def get_slots_summary(self) -> Dict:
        """
        Get summary statistics about slots
        
        Returns:
            Dictionary with total, available, booked counts
        """
        all_slots = self.db.get_all_slots()
        total = len(all_slots)
        booked = sum(1 for s in all_slots if s.get('booked', False))
        available = total - booked
        
        return {
            'total': total,
            'available': available,
            'booked': booked
        }
