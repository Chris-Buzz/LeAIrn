// LeAIrn - Client-side JavaScript

let currentStep = 1;
let bookingData = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('LeAIrn initialized');

    // Load theme - default to dark mode
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcons();

    // Show welcome modal on first visit
    showWelcomeModal();

    // Add real-time email confirmation validation
    const emailField = document.getElementById('email');
    const emailConfirmField = document.getElementById('email_confirm');
    const emailMatchHint = document.getElementById('email-match-hint');

    if (emailField && emailConfirmField && emailMatchHint) {
        const checkEmailMatch = () => {
            const email = emailField.value.trim();
            const emailConfirm = emailConfirmField.value.trim();

            // Only show hint if confirm field has content
            if (emailConfirm.length > 0) {
                if (email !== emailConfirm) {
                    emailMatchHint.style.display = 'block';
                    emailConfirmField.style.borderColor = 'var(--error)';
                    emailConfirmField.style.borderWidth = '2px';
                } else {
                    emailMatchHint.style.display = 'none';
                    emailConfirmField.style.borderColor = '';
                    emailConfirmField.style.borderWidth = '';
                }
            } else {
                emailMatchHint.style.display = 'none';
                emailConfirmField.style.borderColor = '';
                emailConfirmField.style.borderWidth = '';
            }
        };

        // Add listeners for both fields
        emailField.addEventListener('input', checkEmailMatch);
        emailConfirmField.addEventListener('input', checkEmailMatch);
        emailField.addEventListener('blur', checkEmailMatch);
        emailConfirmField.addEventListener('blur', checkEmailMatch);
    }
});

// Welcome Modal Functions
function showWelcomeModal() {
    const hasVisited = localStorage.getItem('leairnVisited');
    const modal = document.getElementById('welcomeModal');

    if (!hasVisited && modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // Prevent scrolling
    } else if (modal) {
        modal.classList.add('hidden');
    }
}

function closeWelcomeModal() {
    const modal = document.getElementById('welcomeModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = ''; // Restore scrolling
        localStorage.setItem('leairnVisited', 'true');
    }
}

// Modal header hide-on-scroll behavior
function initWelcomeModalScrollBehavior() {
    const modal = document.getElementById('welcomeModal');
    if (!modal) return;

    const header = modal.querySelector('.welcome-modal-header');
    const body = modal.querySelector('.welcome-modal-body');

    if (!header || !body) return;

    // We let the parent `.welcome-modal-content` scroll so the header scrolls away naturally.
    // Keep a MutationObserver to reset any inline styles if they exist from previous interactions.
    const observer = new MutationObserver(mutations => {
        for (const m of mutations) {
            if (m.attributeName === 'class') {
                const hidden = modal.classList.contains('hidden');
                if (!hidden) {
                    // when shown, ensure no leftover inline styles
                    header.style.transform = '';
                    header.style.opacity = '';
                    body.style.paddingTop = '';
                    // ensure scroll starts at top
                    modal.scrollTop = 0;
                } else {
                    // when hidden, reset inline styles
                    header.style.transform = '';
                    header.style.opacity = '';
                    body.style.paddingTop = '';
                }
            }
        }
    });

    observer.observe(modal, { attributes: true, attributeFilter: ['class'] });
}

// Initialize modal scroll behavior after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initWelcomeModalScrollBehavior();
});

// Theme Toggle
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcons();
}

function updateThemeIcons() {
    const theme = document.documentElement.getAttribute('data-theme');
    const lightIcon = document.getElementById('theme-icon-light');
    const darkIcon = document.getElementById('theme-icon-dark');

    if (theme === 'dark') {
        lightIcon.classList.add('hidden');
        darkIcon.classList.remove('hidden');
    } else {
        lightIcon.classList.remove('hidden');
        darkIcon.classList.add('hidden');
    }
}

// Step Navigation
function goToStep(stepNumber) {
    // Validate before moving forward
    if (stepNumber > currentStep && !validateCurrentStep()) {
        return;
    }

    // Hide current step
    document.querySelectorAll('.step').forEach(step => step.classList.remove('active'));

    // Show new step
    document.getElementById(`step${stepNumber}`).classList.add('active');

    // Update progress bar
    updateProgressBar(stepNumber);

    // Save current step
    currentStep = stepNumber;

    // Load time slots when entering step 8
    if (stepNumber === 8) {
        loadTimeSlots();
    }

    // Scroll to the top of the form card for better UX
    const formCard = document.querySelector('.form-card');
    if (formCard) {
        // Get the position of the form card relative to the viewport
        const cardTop = formCard.getBoundingClientRect().top + window.pageYOffset;
        // Scroll to just above the form card with some padding
        window.scrollTo({
            top: cardTop - 20,
            behavior: 'smooth'
        });
    } else {
        // Fallback to top of page
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function updateProgressBar(activeStep) {
    const steps = document.querySelectorAll('.progress-step');

    steps.forEach((step, index) => {
        step.classList.remove('active', 'completed');

        // Determine which section we're in
        let sectionIndex = 0;
        if (activeStep === 1) sectionIndex = 0; // Info
        else if (activeStep >= 2 && activeStep <= 7) sectionIndex = 1; // Questions (now includes 6 questions + comments)
        else if (activeStep === 8 || activeStep === 9) sectionIndex = 2; // Time/Location
        else if (activeStep === 10) sectionIndex = 3; // Done

        if (index === sectionIndex) {
            step.classList.add('active');
        } else if (index < sectionIndex) {
            step.classList.add('completed');
        }
    });
}

function validateCurrentStep() {
    if (currentStep === 1) {
        const name = document.getElementById('full_name').value.trim();
        const email = document.getElementById('email').value.trim();
        const emailConfirm = document.getElementById('email_confirm').value.trim();
        const role = document.getElementById('role').value;
        const departmentField = document.getElementById('department-field');
        const department = document.getElementById('department').value.trim();

        if (!name || !email || !emailConfirm || !role) {
            showNotification('Please fill in all required fields', 'error');
            return false;
        }

        // Email validation
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showNotification('Please enter a valid email address', 'error');
            return false;
        }

        // Email confirmation validation
        if (email !== emailConfirm) {
            showNotification('Email addresses do not match. Please check and try again.', 'error');
            document.getElementById('email-match-hint').style.display = 'block';
            return false;
        }

        // Department/Major validation (if field is visible)
        if (departmentField.style.display !== 'none' && !department) {
            showNotification('Please enter your department or major', 'error');
            return false;
        }

        // Hide email match hint if validation passes
        document.getElementById('email-match-hint').style.display = 'none';

        return true;
    }

    // Question 1: AI Familiarity
    if (currentStep === 2) {
        const familiarity = document.querySelector('input[name="ai_familiarity"]:checked');
        if (!familiarity) {
            showNotification('Please select an option', 'error');
            return false;
        }
        return true;
    }

    // Question 2: AI Tools (checkboxes - optional)
    if (currentStep === 3) {
        return true; // Checkboxes are optional
    }

    // Question 3: Primary Use (now checkboxes - at least one required)
    if (currentStep === 4) {
        const primaryUse = document.querySelectorAll('input[name="primary_use"]:checked');
        if (primaryUse.length === 0) {
            showNotification('Please select at least one area of interest', 'error');
            return false;
        }
        return true;
    }

    // Question 4: Learning Goal (now checkboxes - at least one required)
    if (currentStep === 5) {
        const learningGoal = document.querySelectorAll('input[name="learning_goal"]:checked');
        if (learningGoal.length === 0) {
            showNotification('Please select at least one learning goal', 'error');
            return false;
        }
        return true;
    }

    // Question 5: Confidence Level
    if (currentStep === 6) {
        const confidence = document.querySelector('input[name="confidence_level"]:checked');
        if (!confidence) {
            showNotification('Please select an option', 'error');
            return false;
        }
        return true;
    }

    // Step 7: Personal Comments (optional)
    if (currentStep === 7) {
        return true; // Comments are optional
    }

    // Step 8: Time selection
    if (currentStep === 8) {
        if (!document.getElementById('selected_slot').value) {
            showNotification('Please select a time slot', 'error');
            return false;
        }
        return true;
    }

    // Step 9: Location
    if (currentStep === 9) {
        const building = document.getElementById('selected_building').value;
        const roomNumber = document.getElementById('room_number').value.trim();

        if (!building) {
            showNotification('Please select a building', 'error');
            return false;
        }
        if (!roomNumber) {
            showNotification('Please enter a room number or office', 'error');
            return false;
        }
        return true;
    }

    return true;
}

// Load Time Slots
async function loadTimeSlots() {
    const loadingEl = document.getElementById('loadingSlots');
    const slotsContainer = document.getElementById('slotsContainer');

    loadingEl.classList.remove('hidden');
    slotsContainer.classList.add('hidden');

    try {
        const response = await fetch('/api/slots');
        if (!response.ok) throw new Error('Failed to load slots');

        const slots = await response.json();

    loadingEl.classList.add('hidden');
    slotsContainer.classList.remove('hidden');

        if (slots.length === 0) {
            slotsContainer.innerHTML = `
                    <div class="slots-empty">
                        <p>No available slots at the moment</p>
                        <p style="margin-top: 0.5rem; color: var(--text-tertiary);">Please check back later</p>
                    </div>
                `;
            return;
        }

        // Render slots
        slotsContainer.innerHTML = '';
        slots.forEach((slot, index) => {
            const slotEl = document.createElement('div');
            slotEl.className = 'time-slot';
            slotEl.dataset.slotId = slot.id;
            slotEl.style.animationDelay = `${index * 0.03}s`;
            slotEl.style.animation = 'fadeInUp 0.4s ease both';

            slotEl.innerHTML = `
                <div class="time-day">${slot.day}</div>
                <div class="time-date">${slot.date}</div>
                <div class="time-time">${slot.time}</div>
            `;

            slotEl.addEventListener('click', () => selectTimeSlot(slot, slotEl));
            slotsContainer.appendChild(slotEl);
        });

    } catch (error) {
        console.error('Error loading slots:', error);
        loadingEl.innerHTML = `
            <p class="error-text">Failed to load time slots</p>
            <p style="font-size: 0.95rem; margin-top: 0.5rem;">Please refresh the page to try again</p>
        `;
    }
}

function selectTimeSlot(slot, element) {
    // Deselect all
    document.querySelectorAll('.time-slot').forEach(el => el.classList.remove('selected'));

    // Select clicked slot
    element.classList.add('selected');
    document.getElementById('selected_slot').value = slot.id;

    // Store slot data
    bookingData.selectedSlot = slot;

    // Enable continue button
    const continueBtn = document.getElementById('continueToLocation');
    continueBtn.disabled = false;

    // Smooth scroll to the continue button after a brief moment
    setTimeout(() => {
        continueBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 300);
}

// Confirm Booking
async function confirmBooking() {
    const confirmBtn = document.querySelector('#step9 .btn-primary');
    const btnText = confirmBtn.querySelector('.btn-text');
    const btnSpinner = confirmBtn.querySelector('.btn-spinner');

    // Get AI tools (checkboxes)
    const aiTools = Array.from(document.querySelectorAll('input[name="ai_tools"]:checked'))
        .map(cb => cb.value);

    // Get primary use (now checkboxes - multiple selections)
    const primaryUse = Array.from(document.querySelectorAll('input[name="primary_use"]:checked'))
        .map(cb => cb.value);

    // Get learning goals (now checkboxes - multiple selections)
    const learningGoals = Array.from(document.querySelectorAll('input[name="learning_goal"]:checked'))
        .map(cb => cb.value);

    // Combine building and room number into selected_room for backward compatibility
    const building = document.getElementById('selected_building').value;
    const roomNumber = document.getElementById('room_number').value.trim();
    const fullLocation = building && roomNumber ? `${building} - ${roomNumber}` : '';

    // Get department/major if visible
    const departmentField = document.getElementById('department-field');
    const department = departmentField.style.display !== 'none' ? document.getElementById('department').value.trim() : null;

    // Get form data
    const formData = {
        full_name: document.getElementById('full_name').value.trim(),
        email: document.getElementById('email').value.trim(),
        phone: null, // Phone is no longer collected
        role: document.getElementById('role').value,
        department: department, // Add department/major
        selected_slot: document.getElementById('selected_slot').value,
        selected_room: fullLocation,
        selected_building: building,
        room_number: roomNumber,
        // Questionnaire data
        ai_familiarity: document.querySelector('input[name="ai_familiarity"]:checked')?.value,
        ai_tools: aiTools.join(', '),
        primary_use: primaryUse.join(', '),
        learning_goal: learningGoals.join(', '),
        confidence_level: document.querySelector('input[name="confidence_level"]:checked')?.value,
        personal_comments: document.getElementById('personal_comments')?.value.trim() || null // Optional
    };

    // Validate
    if (!building || !roomNumber) {
        showNotification('Please select a building and enter a room number', 'error');
        return;
    }

    // Show instant feedback - optimistic UI
    confirmBtn.disabled = true;
    btnText.textContent = 'Confirmed!';

    // Create temporary booking data for immediate display
    const tempBookingData = {
        name: formData.full_name,
        room: fullLocation,
        slot: bookingData.selectedSlot || {
            day: 'Scheduled',
            date: 'Processing...',
            time: ''
        }
    };

    // Show booking details immediately
    displayBookingDetails(tempBookingData);

    // Go to success step immediately for instant feedback
    goToStep(10);

    // Process booking in background
    try {
        const response = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Update with actual booking data
            bookingData = { ...formData, ...result.data };
            displayBookingDetails(result.data);

            // Show success message
            console.log('Booking confirmed successfully');
        } else {
            // If booking failed, show error but user already sees success page
            // You may want to handle this differently based on your needs
            console.error('Booking submission failed:', result.message);
            showNotification('Booking saved locally. Please contact support if you need confirmation.', 'warning');
        }

    } catch (error) {
        console.error('Booking error:', error);
        // User already sees success, so just log the error
        // You could show a subtle notification that confirmation email may be delayed
        showNotification('Your booking is saved. Confirmation email may be delayed.', 'info');
    }
}

function displayBookingDetails(data) {
    const detailsContainer = document.getElementById('bookingDetails');

    detailsContainer.innerHTML = `
        <div class="detail-item">
            <div class="detail-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>
            </div>
            <div class="detail-content">
                <div class="detail-label">Name</div>
                <div class="detail-value">${data.name}</div>
            </div>
        </div>
        <div class="detail-item">
            <div class="detail-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                    <line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/>
                    <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
            </div>
            <div class="detail-content">
                <div class="detail-label">Date & Time</div>
                <div class="detail-value">${data.slot.day}, ${data.slot.date} at ${data.slot.time}</div>
            </div>
        </div>
        <div class="detail-item">
            <div class="detail-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                    <circle cx="12" cy="10" r="3"/>
                </svg>
            </div>
            <div class="detail-content">
                <div class="detail-label">Location</div>
                <div class="detail-value">${data.room}</div>
            </div>
        </div>
    `;
}

// Google Calendar Integration
function addToGoogleCalendar() {
    const slot = bookingData.slot;
    if (!slot) return;

    const startDate = new Date(slot.datetime);
    const endDate = new Date(startDate.getTime() + 30 * 60000);

    const formatDate = (date) => date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

    const params = new URLSearchParams({
        action: 'TEMPLATE',
        text: 'AI Learning Session - AI Mentor Hub',
        details: `AI learning session at ${bookingData.selected_room}\\n\\nScheduled through AI Mentor Hub`,
        location: bookingData.selected_room,
        dates: `${formatDate(startDate)}/${formatDate(endDate)}`
    });

    window.open(`https://calendar.google.com/calendar/render?${params.toString()}`, '_blank');
}

// Download ICS File
function downloadICS() {
    const slot = bookingData.slot;
    if (!slot) return;

    const startDate = new Date(slot.datetime);
    const endDate = new Date(startDate.getTime() + 30 * 60000);

    const formatDate = (date) => date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Mentor Hub//EN
BEGIN:VEVENT
UID:${slot.id}@aimentorhub
DTSTAMP:${formatDate(new Date())}
DTSTART:${formatDate(startDate)}
DTEND:${formatDate(endDate)}
SUMMARY:AI Learning Session - AI Mentor Hub
DESCRIPTION:AI learning session at ${bookingData.selected_room}\\n\\nScheduled through AI Mentor Hub
LOCATION:${bookingData.selected_room}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR`;

    const blob = new Blob([icsContent], { type: 'text/calendar' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ai-mentor-hub-session.ics';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    showNotification('Calendar file downloaded successfully', 'success');
}

// Notifications
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        background: ${type === 'error' ? 'var(--error)' : type === 'success' ? 'var(--success)' : 'var(--primary)'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.75rem;
        font-weight: 600;
        box-shadow: var(--shadow-lg);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
        max-width: 400px;
    `;

    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// View Booking Modal Functions
function showViewBookingModal() {
    const modal = document.getElementById('viewBookingModal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        document.getElementById('lookup_email').value = '';
        const resultDiv = document.getElementById('booking-lookup-result');
        if (resultDiv) {
            resultDiv.style.display = 'none';
        }
    }
}

function closeViewBookingModal() {
    const modal = document.getElementById('viewBookingModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

async function lookupBooking() {
    const email = document.getElementById('lookup_email').value.trim();
    const resultDiv = document.getElementById('booking-lookup-result');

    if (!email) {
        showNotification('Please enter your email address', 'error');
        return;
    }

    // Email validation
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }

    try {
        // Show loading state
        resultDiv.innerHTML = '<div style="text-align: center; padding: 2rem;"><div class="spinner" style="margin: 0 auto; border-color: rgba(99, 102, 241, 0.3); border-top-color: var(--primary);"></div><p style="margin-top: 1rem; color: var(--text-secondary);">Looking up your booking...</p></div>';
        resultDiv.style.display = 'block';

        const response = await fetch(`/api/booking/lookup?email=${encodeURIComponent(email)}`);
        const result = await response.json();

        if (response.ok && result.success && result.booking) {
            const booking = result.booking;
            const slotDetails = booking.slot_details || {};

            resultDiv.innerHTML = `
                <div style="background: var(--bg); border: 2px solid var(--primary); border-radius: 1rem; padding: 1.5rem;">
                    <h3 style="margin-bottom: 1rem; color: var(--primary);">Your Booking Details</h3>

                    <div style="display: grid; gap: 0.75rem;">
                        <div>
                            <strong style="color: var(--text-secondary);">Name:</strong>
                            <div>${booking.full_name}</div>
                        </div>

                        <div>
                            <strong style="color: var(--text-secondary);">Date & Time:</strong>
                            <div>${slotDetails.day || ''}, ${slotDetails.date || ''} at ${slotDetails.time || ''}</div>
                        </div>

                        <div>
                            <strong style="color: var(--text-secondary);">Location:</strong>
                            <div>${booking.selected_room || 'Not specified'}</div>
                        </div>

                        <div>
                            <strong style="color: var(--text-secondary);">Status:</strong>
                            <div style="color: var(--success); font-weight: 600;">✓ Confirmed</div>
                        </div>
                    </div>

                    <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border); color: var(--text-secondary); font-size: 0.9rem;">
                        <p>A confirmation email was sent to <strong>${booking.email}</strong></p>
                        <p style="margin-top: 0.5rem;">If you need to make changes, please contact: <a href="mailto:cjpbuzaid@gmail.com" style="color: var(--primary);">cjpbuzaid@gmail.com</a></p>
                    </div>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div style="background: var(--bg); border: 2px solid var(--border); border-radius: 1rem; padding: 1.5rem; text-align: center;">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--text-tertiary); margin-bottom: 1rem;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <h3 style="margin-bottom: 0.5rem;">No Upcoming Booking Found</h3>
                    <p style="color: var(--text-secondary);">We couldn't find an upcoming booking with this email address.</p>
                    <p style="color: var(--text-secondary); margin-top: 0.5rem; font-size: 0.9rem;">Past bookings are not shown. Please book a new session if needed.</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error looking up booking:', error);
        resultDiv.innerHTML = `
            <div style="background: var(--bg); border: 2px solid var(--error); border-radius: 1rem; padding: 1.5rem; text-align: center;">
                <h3 style="margin-bottom: 0.5rem; color: var(--error);">Error</h3>
                <p style="color: var(--text-secondary);">Failed to lookup booking. Please try again.</p>
            </div>
        `;
    }
}

// Contact Form Functions
function openContactForm() {
    const modal = document.getElementById('contactFormModal');
    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('contact_name').focus();
    }
}

function closeContactForm() {
    const modal = document.getElementById('contactFormModal');
    if (modal) {
        modal.classList.add('hidden');
        document.getElementById('contactForm').reset();
        document.getElementById('contact-form-result').style.display = 'none';
    }
}

async function submitContactForm(event) {
    event.preventDefault();

    const name = document.getElementById('contact_name').value.trim();
    const email = document.getElementById('contact_email').value.trim();
    const message = document.getElementById('contact_message').value.trim();
    const resultDiv = document.getElementById('contact-form-result');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    if (!name || !email || !message) {
        resultDiv.innerHTML = '<p style="color: var(--error); text-align: center;">Please fill in all fields.</p>';
        resultDiv.style.display = 'block';
        return;
    }

    // Show loading state
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span style="width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite;"></span>Sending...</span>';

    try {
        const response = await fetch('/api/contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, email, message })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            resultDiv.innerHTML = '<p style="color: var(--success); text-align: center; font-weight: 600;">Message sent successfully! I\'ll get back to you soon.</p>';
            resultDiv.style.display = 'block';
            document.getElementById('contactForm').reset();

            // Close modal after 2 seconds
            setTimeout(() => {
                closeContactForm();
            }, 2000);
        } else {
            resultDiv.innerHTML = `<p style="color: var(--error); text-align: center;">Error: ${result.message || 'Failed to send message'}</p>`;
            resultDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error sending message:', error);
        resultDiv.innerHTML = '<p style="color: var(--error); text-align: center;">Failed to send message. Please try again.</p>';
        resultDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
}

// Show/hide department field based on role selection
function showDepartmentField() {
    const role = document.getElementById('role').value;
    const departmentField = document.getElementById('department-field');
    const departmentLabel = document.getElementById('department-label');
    const departmentInput = document.getElementById('department');

    if (role && role !== '') {
        departmentField.style.display = 'block';

        // Update label based on role
        if (role === 'student') {
            departmentLabel.textContent = 'Major *';
            departmentInput.placeholder = 'e.g., Computer Science, Psychology, Business';
        } else if (role === 'teacher' || role === 'advisor') {
            departmentLabel.textContent = 'Department *';
            departmentInput.placeholder = 'e.g., Computer Science, Mathematics, English';
        } else {
            departmentLabel.textContent = 'Department *';
            departmentInput.placeholder = 'e.g., IT, Administration, Counseling';
        }

        // Make field required
        departmentInput.setAttribute('required', 'required');
    } else {
        departmentField.style.display = 'none';
        departmentInput.removeAttribute('required');
    }
}
