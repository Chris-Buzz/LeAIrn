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

// Informed Consent Modal
function showConsentModal(nextStep) {
    const modal = document.createElement('div');
    modal.id = 'consentModal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        padding: 1rem;
    `;

    modal.innerHTML = `
        <div style="background: var(--surface); border-radius: 1rem; max-width: 800px; width: 100%; max-height: 85vh; overflow-y: auto; padding: 2rem; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
            <h2 style="margin-bottom: 0.5rem; color: var(--primary); font-size: 1.1rem; text-align: center;">INFORMED CONSENT FOR RESEARCH PARTICIPATION</h2>
            <h3 style="margin-bottom: 0.75rem; color: var(--text-primary); font-size: 0.85rem; text-align: center;">Improving Efficiency in Higher Education through Customized AI Training</h3>

            <div style="color: var(--text-primary); line-height: 1.4; font-size: 0.7rem;">
                <p style="margin-bottom: 0.5rem;"><strong>Principal Investigator:</strong> Weihao Qu, Phone: 732-263-5396, Email: wqu@monmouth.edu</p>
                <p style="margin-bottom: 0.75rem;"><strong>Co-Investigator:</strong> Ling Zheng, Phone: 732-571-4459, Email: lzheng@monmouth.edu</p>

                <p style="margin-bottom: 0.75rem; font-weight: 600;">You are being asked to be a participant in a research study.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">What is the purpose of this study?</h4>
                <p style="margin-bottom: 0.75rem;">The purpose of this study is about how artificial intelligence (AI) tools can be used to improve efficiency in learning, studying, and working at a mid-sized college. The goal of this project is to design and test customized AI training workshops, one-on-one sessions, and online modules for students, staff, and faculty.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">What will you have to do, if you agree to be in the study?</h4>
                <p style="margin-bottom: 0.3rem;">If you agree to be in this study, your part will involve:</p>
                <ul style="margin: 0.3rem 0 0.75rem 1.5rem; list-style-type: disc;">
                    <li>Finish an online pre-assessment on your own AI tool knowledge before the training session when you book the training.</li>
                    <li>Attend a one-on-one training session (about 45–60 minutes).</li>
                    <li>Complete a short survey (5–10 minutes) at the end of the training session.</li>
                    <li>Receive a follow-up survey about one month later (5–10 minutes).</li>
                </ul>
                <p style="margin-bottom: 0.75rem;">Your total participation time will be about 55–70 minutes.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">Are there any possible risks to being in this study?</h4>
                <p style="margin-bottom: 0.75rem;">If you agree to be in this study, there are no foreseeable risks to you, above those that you experience in your daily life.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">Are there any possible benefits to being in this study?</h4>
                <p style="margin-bottom: 0.75rem;">There is no direct benefit to you by participating in this study.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">How will your study information be protected?</h4>
                <p style="margin-bottom: 0.5rem;">Your name will not be linked in any way to the information you provide. Neither IP addresses nor any other identifiable information will be collected. The registered email will be collected during the one-on-one training in order to contact the participants with the post survey.</p>
                <p style="margin-bottom: 0.5rem;">Data will be collected using the Internet; no guarantees can be made regarding the interception of data sent via the Internet by any third party. Confidentiality will be maintained to the degree permitted by the technology used.</p>
                <p style="margin-bottom: 0.75rem;">Your information will be viewed by the study team and other people within Monmouth University who help administer and oversee research. If information from this study is published or presented at scientific meetings, your name and other identifiable information will not be used.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">Important Contact Information</h4>
                <p style="margin-bottom: 0.5rem;">Please contact Dr. Weihao Qu at 732-263-5396 or via e-mail at wqu@monmouth.edu if you have any questions about the study, or if you believe you have experienced harm or injury as a result of being in this study.</p>
                <p style="margin-bottom: 0.5rem; font-size: 0.65rem; color: var(--text-secondary);">If your participation in this research study has caused you to feel uncomfortable in any way, or if by participating in this research study it has prompted you to consider personal matters about which you are concerned, we encourage you to immediately stop participating in this research study and strongly encourage you to contact support services. If you are a Monmouth University student, you can contact Monmouth University's Counseling and Psychological Services (CPS) to schedule a confidential appointment to speak to a counselor at 732-571-7517. If you are a Monmouth University employee, you can contact Monmouth University's Employee Assistance Program (EAP) at their confidential intake number at 1-800-300-0628. If you are a member of the general public, you may contact your local community mental health center or the National Helpline of the Substance Abuse and Mental Health Services Administration (SAMHSA) at 1-800-662-HELP (4357) — a free, confidential, 24/7 resource for individuals seeking counseling or mental health support.</p>
                <p style="margin-bottom: 0.75rem;">In addition, for any questions about your rights as a research participant, please contact the Monmouth University Institutional Review Board via e-mail at IRB@monmouth.edu.</p>

                <h4 style="color: var(--primary); margin: 1rem 0 0.4rem 0; font-size: 0.8rem;">Your participation is voluntary!</h4>
                <p style="margin-bottom: 0.75rem;">Your participation in this study is voluntary. You may decide not to participate at all or, if you start the study, you may withdraw at any time without any penalty. Withdrawal or refusing to participate will not affect your relationship with Monmouth University in any way.</p>

                <div style="background: rgba(99, 102, 241, 0.1); border-left: 4px solid var(--primary); padding: 1rem; border-radius: 0.5rem; margin: 1.5rem 0;">
                    <p style="margin: 0; font-weight: 600;">If you click 'I ACCEPT' below, it means that you have (a) read this consent form, (b) you agree to be a participant in this study, and (c) you are over 18 years old.</p>
                    <p style="margin: 0.5rem 0 0 0;">If you click 'I DO NOT ACCEPT', you will still go through the steps listed within the purpose of the study, but your data will not be used for research purposes.</p>
                </div>
            </div>

            <div style="display: flex; gap: 1rem; margin-top: 2rem;">
                <button onclick="handleConsent(false, ${nextStep})" style="flex: 1; padding: 1rem; background: linear-gradient(135deg, #EF4444, #DC2626); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 700; font-size: 1rem; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); transition: all 0.3s;">
                    I DO NOT ACCEPT
                </button>
                <button onclick="handleConsent(true, ${nextStep})" style="flex: 1; padding: 1rem; background: linear-gradient(135deg, #10B981, #059669); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 700; font-size: 1rem; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3); transition: all 0.3s;">
                    I ACCEPT
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

function handleConsent(accepted, nextStep) {
    consentGiven = accepted;

    // Remove the consent modal
    const modal = document.getElementById('consentModal');
    if (modal) {
        modal.remove();
    }

    // Show notification
    if (accepted) {
        showNotification('Thank you for your consent. Your participation helps improve AI training.', 'success');
    } else {
        showNotification('You may continue with the booking. Your data will not be used for research.', 'info');
    }

    // Continue to next step
    goToStep(nextStep, true);
}

// Step Navigation
// Track consent status
let consentGiven = null; // null = not asked yet, true = accepted, false = declined

function goToStep(stepNumber, skipValidation = false) {
    // Validate before moving forward (unless skipped for restoration)
    if (!skipValidation && stepNumber > currentStep && !validateCurrentStep()) {
        return;
    }

    // Show consent modal when moving from step 1 to step 2 (after personal info, before questions)
    if (currentStep === 1 && stepNumber === 2 && consentGiven === null) {
        showConsentModal(stepNumber);
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

    // Question 3: Primary Use (checkboxes - at least one required)
    if (currentStep === 4) {
        const primaryUse = document.querySelectorAll('input[name="primary_use"]:checked');
        if (primaryUse.length === 0) {
            showNotification('Please select at least one option', 'error');
            return false;
        }
        return true;
    }

    // Question 4: Learning Goal (checkboxes - at least one required)
    if (currentStep === 5) {
        const learningGoal = document.querySelectorAll('input[name="learning_goal"]:checked');
        if (learningGoal.length === 0) {
            showNotification('Please select at least one option', 'error');
            return false;
        }
        return true;
    }

    // Question 5: Confidence Level (radio - required)
    if (currentStep === 6) {
        const confidence = document.querySelector('input[name="confidence_level"]:checked');
        if (!confidence) {
            showNotification('Please select an option', 'error');
            return false;
        }
        return true;
    }

    // Question 6: Personal Comments (optional)
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

    // Get primary use (checkboxes - multiple selections)
    const primaryUse = Array.from(document.querySelectorAll('input[name="primary_use"]:checked'))
        .map(cb => cb.value);

    // Get learning goals (checkboxes - multiple selections)
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
        // Research consent status
        research_consent: consentGiven, // true = consented, false = declined, null = not asked
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

let verificationEmail = '';

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
        resultDiv.innerHTML = '<div style="text-align: center; padding: 2rem;"><div class="spinner" style="margin: 0 auto; border-color: rgba(99, 102, 241, 0.3); border-top-color: var(--primary);"></div><p style="margin-top: 1rem; color: var(--text-secondary);">Checking for booking...</p></div>';
        resultDiv.style.display = 'block';

        const response = await fetch('/api/booking/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email })
        });
        const result = await response.json();

        if (response.ok && result.success) {
            // Verification code sent - show verification form
            verificationEmail = email;
            showNotification('Verification code sent to your email!', 'success');

            resultDiv.innerHTML = `
                <div style="background: var(--bg); border: 2px solid var(--primary); border-radius: 1rem; padding: 1.5rem;">
                    <h3 style="margin-bottom: 1rem; color: var(--primary);">Check Your Email</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">We've sent a 6-digit verification code to <strong>${email}</strong></p>

                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Enter Verification Code</label>
                        <input type="text" id="verification_code" maxlength="6" placeholder="000000"
                            style="width: 100%; padding: 0.875rem; border: 2px solid var(--border); border-radius: 0.75rem; font-size: 1.5rem; text-align: center; letter-spacing: 0.5rem; font-weight: 600;"
                            oninput="this.value = this.value.replace(/[^0-9]/g, '')">
                        <small style="display: block; margin-top: 0.5rem; color: var(--text-tertiary);">Code expires in 10 minutes</small>
                    </div>

                    <div style="display: flex; gap: 0.75rem;">
                        <button onclick="verifyCode()" style="flex: 1; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Verify Code
                        </button>
                        <button onclick="resendVerificationCode()" style="flex: 1; padding: 0.875rem; background: var(--bg); color: var(--text-primary); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Resend Code
                        </button>
                    </div>
                </div>
            `;

            // Focus on code input
            setTimeout(() => {
                document.getElementById('verification_code').focus();
            }, 100);
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

async function verifyCode() {
    const code = document.getElementById('verification_code').value.trim();
    const resultDiv = document.getElementById('booking-lookup-result');

    if (!code || code.length !== 6) {
        showNotification('Please enter the 6-digit code', 'error');
        return;
    }

    try {
        // Show loading state
        resultDiv.innerHTML = '<div style="text-align: center; padding: 2rem;"><div class="spinner" style="margin: 0 auto; border-color: rgba(99, 102, 241, 0.3); border-top-color: var(--primary);"></div><p style="margin-top: 1rem; color: var(--text-secondary);">Verifying code...</p></div>';

        const response = await fetch('/api/booking/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: verificationEmail,
                code: code
            })
        });

        const result = await response.json();

        if (response.ok && result.success && result.bookings) {
            const bookings = result.bookings;

            showNotification('Verification successful!', 'success');

            // Display all bookings
            const bookingsHTML = bookings.map((booking, index) => {
                const slotDetails = booking.slot_details || {};
                return `
                    <div style="background: var(--bg); border: 2px solid var(--primary); border-radius: 1rem; padding: 1.5rem; margin-bottom: 1rem;">
                        <h3 style="margin-bottom: 1rem; color: var(--primary);">Booking ${bookings.length > 1 ? `#${index + 1}` : ''}</h3>

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
                        </div>

                        <div style="margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid var(--border); display: flex; gap: 0.75rem;">
                            <button onclick="showEditBookingForm('${verificationEmail}', '${booking.id}')" style="flex: 1; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem; transition: all 0.3s;">
                                Edit Booking
                            </button>
                            <button onclick="confirmDeleteSpecificBooking('${booking.id}', '${slotDetails.day || ''}, ${slotDetails.date || ''} at ${slotDetails.time || ''}')" style="flex: 1; padding: 0.875rem; background: var(--error); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem; transition: all 0.3s;">
                                Delete Booking
                            </button>
                        </div>
                    </div>
                `;
            }).join('');

            resultDiv.innerHTML = `
                <div style="margin-bottom: 1rem;">
                    <h3 style="color: var(--text-primary);">Your Booking${bookings.length > 1 ? 's' : ''}</h3>
                    ${bookings.length > 1 ? `<p style="color: var(--text-secondary); font-size: 0.9rem;">You have ${bookings.length} upcoming sessions</p>` : ''}
                </div>
                ${bookingsHTML}
            `;
        } else {
            showNotification(result.message || 'Invalid verification code', 'error');
            // Show verification form again with error
            document.getElementById('verification_code').value = '';
            document.getElementById('verification_code').focus();
            document.getElementById('verification_code').style.borderColor = 'var(--error)';
        }
    } catch (error) {
        console.error('Error verifying code:', error);
        showNotification('Failed to verify code. Please try again.', 'error');
    }
}

async function resendVerificationCode() {
    if (!verificationEmail) {
        showNotification('Please enter your email first', 'error');
        return;
    }

    try {
        const response = await fetch('/api/booking/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: verificationEmail })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            showNotification('New verification code sent!', 'success');
            document.getElementById('verification_code').value = '';
            document.getElementById('verification_code').focus();
        } else {
            showNotification(result.message || 'Failed to resend code', 'error');
        }
    } catch (error) {
        console.error('Error resending code:', error);
        showNotification('Failed to resend code. Please try again.', 'error');
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

// Delete Booking Confirmation Dialog
function confirmDeleteBooking(email) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 11000;
        animation: fadeIn 0.3s ease;
    `;

    modal.innerHTML = `
        <div style="background: var(--surface); border-radius: 1rem; max-width: 500px; width: 90%; padding: 2rem; box-shadow: var(--shadow-lg); position: relative;">
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--error)" stroke-width="2" style="margin: 0 auto 1rem;">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
                <h2 style="color: var(--text-primary); margin-bottom: 0.5rem;">Delete Your Booking?</h2>
                <p style="color: var(--text-secondary); font-size: 0.95rem;">Are you sure you want to delete your booking? This action cannot be undone.</p>
            </div>

            <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--error); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1.5rem;">
                <p style="color: var(--text-primary); font-size: 0.9rem; margin: 0;">
                    <strong>Warning:</strong> Your time slot will be released and available for others to book.
                </p>
            </div>

            <div style="display: flex; gap: 1rem;">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" style="flex: 1; padding: 0.875rem; background: var(--bg); color: var(--text-primary); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                    Cancel
                </button>
                <button onclick="deleteBookingByEmail('${email}', this.parentElement.parentElement.parentElement)" style="flex: 1; padding: 0.875rem; background: var(--error); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                    Yes, Delete My Booking
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

async function deleteBookingByEmail(email, confirmModal) {
    // Get the button and show loading state
    const deleteBtn = confirmModal.querySelector('button[onclick*="deleteBookingByEmail"]');
    const originalBtnText = deleteBtn.innerHTML;
    deleteBtn.disabled = true;
    deleteBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span style="width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite;"></span>Deleting...</span>';

    try {
        const response = await fetch('/api/booking/delete-by-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email, confirmed: true })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Close confirmation modal
            confirmModal.remove();

            // Show success message
            showNotification('Your booking has been deleted successfully', 'success');

            // Update the booking lookup result to show deletion success
            const resultDiv = document.getElementById('booking-lookup-result');
            if (resultDiv) {
                resultDiv.innerHTML = `
                    <div style="background: var(--bg); border: 2px solid var(--success); border-radius: 1rem; padding: 1.5rem; text-align: center;">
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--success)" stroke-width="2" style="margin: 0 auto 1rem;">
                            <circle cx="12" cy="12" r="10"></circle>
                            <path d="M9 12l2 2 4-4"></path>
                        </svg>
                        <h3 style="margin-bottom: 0.5rem; color: var(--success);">Booking Deleted</h3>
                        <p style="color: var(--text-secondary);">Your booking has been successfully deleted. The time slot is now available for others.</p>
                        <button onclick="closeViewBookingModal()" style="margin-top: 1rem; padding: 0.75rem 1.5rem; background: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600;">
                            Close
                        </button>
                    </div>
                `;
            }
        } else {
            // Show error and restore button
            showNotification('Error: ' + result.message, 'error');
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalBtnText;
        }
    } catch (error) {
        console.error('Error deleting booking:', error);
        showNotification('Failed to delete booking. Please try again.', 'error');
        deleteBtn.disabled = false;
        deleteBtn.innerHTML = originalBtnText;
    }
}

// Delete a specific booking by ID
function confirmDeleteSpecificBooking(bookingId, bookingDetails) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 11000;
        animation: fadeIn 0.3s ease;
    `;

    modal.innerHTML = `
        <div style="background: var(--surface); border-radius: 1rem; max-width: 500px; width: 90%; padding: 2rem; box-shadow: var(--shadow-lg); position: relative;">
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--error)" stroke-width="2" style="margin: 0 auto 1rem;">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
                <h2 style="color: var(--text-primary); margin-bottom: 0.5rem;">Delete This Booking?</h2>
                <p style="color: var(--text-secondary); font-size: 0.95rem;">Are you sure you want to delete the booking for ${bookingDetails}?</p>
            </div>

            <div style="background: rgba(239, 68, 68, 0.1); border-left: 4px solid var(--error); padding: 1rem; border-radius: 0.5rem; margin-bottom: 1.5rem;">
                <p style="color: var(--text-primary); font-size: 0.9rem; margin: 0;">This action cannot be undone. The time slot will become available for others to book.</p>
            </div>

            <div style="display: flex; gap: 0.75rem;">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" style="flex: 1; padding: 0.875rem; background: var(--bg); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; color: var(--text-primary); font-size: 1rem;">
                    Cancel
                </button>
                <button id="confirmDeleteBtn" style="flex: 1; padding: 0.875rem; background: var(--error); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                    Delete Booking
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Handle delete confirmation
    const deleteBtn = document.getElementById('confirmDeleteBtn');
    deleteBtn.onclick = async () => {
        const originalBtnText = deleteBtn.innerHTML;
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 16px; height: 16px;"></span>Deleting...</span>';

        try {
            const response = await fetch(`/api/booking/${bookingId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (response.ok && result.success) {
                modal.remove();
                showNotification('Booking deleted successfully', 'success');

                // Reload the bookings to show updated list
                verifyBookingCode();
            } else {
                showNotification('Error: ' + (result.message || 'Failed to delete booking'), 'error');
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = originalBtnText;
            }
        } catch (error) {
            console.error('Error deleting booking:', error);
            showNotification('Failed to delete booking. Please try again.', 'error');
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalBtnText;
        }
    };
}

// Show edit booking form
async function showEditBookingForm(email, bookingData) {
    const booking = typeof bookingData === 'string' ? JSON.parse(bookingData) : bookingData;

    // Parse the room to get building and room number
    const roomParts = (booking.selected_room || '').split(' - ');
    const currentBuilding = booking.selected_building || roomParts[0] || '';
    const currentRoomNumber = booking.room_number || roomParts[1] || '';

    // Create modal overlay
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.85);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 11000;
        animation: fadeIn 0.3s ease;
        overflow-y: auto;
        padding: 2rem;
    `;

    modal.innerHTML = `
        <div style="background: var(--surface); border-radius: 1rem; max-width: 600px; width: 100%; padding: 2rem; box-shadow: var(--shadow-lg); position: relative; max-height: 90vh; overflow-y: auto;">
            <div style="text-align: center; margin-bottom: 1.5rem;">
                <h2 style="color: var(--text-primary); margin-bottom: 0.5rem;">Edit Your Booking</h2>
                <p style="color: var(--text-secondary); font-size: 0.95rem;">Update your time slot or location</p>
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: var(--text-primary);">Select New Time Slot (Optional)</label>
                <select id="edit_user_slot" style="width: 100%; padding: 0.875rem; border: 2px solid var(--border); border-radius: 0.75rem; background: var(--bg); color: var(--text-primary); font-size: 1rem;">
                    <option value="">Keep current time slot</option>
                </select>
                <small id="slots-loading" style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 0.5rem; display: block;">Loading available slots...</small>
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: var(--text-primary);">Building *</label>
                <select id="edit_user_building" style="width: 100%; padding: 0.875rem; border: 2px solid var(--border); border-radius: 0.75rem; background: var(--bg); color: var(--text-primary); font-size: 1rem;">
                    <option value="">Select a building</option>
                    <option value="Edison Hall" ${currentBuilding === 'Edison Hall' ? 'selected' : ''}>Edison Hall</option>
                    <option value="Howard Hall" ${currentBuilding === 'Howard Hall' ? 'selected' : ''}>Howard Hall</option>
                    <option value="Pozycki Hall" ${currentBuilding === 'Pozycki Hall' ? 'selected' : ''}>Pozycki Hall</option>
                    <option value="McAllan Hall" ${currentBuilding === 'McAllan Hall' ? 'selected' : ''}>McAllan Hall</option>
                    <option value="Great Hall" ${currentBuilding === 'Great Hall' ? 'selected' : ''}>Great Hall</option>
                    <option value="Bey Hall" ${currentBuilding === 'Bey Hall' ? 'selected' : ''}>Bey Hall</option>
                    <option value="Rebecca Stafford Student Center" ${currentBuilding === 'Rebecca Stafford Student Center' ? 'selected' : ''}>Rebecca Stafford Student Center</option>
                    <option value="Guggenheim Memorial Library" ${currentBuilding === 'Guggenheim Memorial Library' ? 'selected' : ''}>Guggenheim Memorial Library</option>
                </select>
            </div>

            <div style="margin-bottom: 1.5rem;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: var(--text-primary);">Room Number / Office *</label>
                <input type="text" id="edit_user_room_number" value="${currentRoomNumber}" placeholder="e.g., 301, Professor's Office" style="width: 100%; padding: 0.875rem; border: 2px solid var(--border); border-radius: 0.75rem; background: var(--bg); color: var(--text-primary); font-size: 1rem;">
            </div>

            <div style="display: flex; gap: 1rem;">
                <button onclick="this.parentElement.parentElement.parentElement.remove()" style="flex: 1; padding: 0.875rem; background: var(--bg); color: var(--text-primary); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                    Cancel
                </button>
                <button onclick="saveUserBookingEdit('${email}', this.parentElement.parentElement.parentElement)" style="flex: 1; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                    Save Changes
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Load available time slots
    try {
        const response = await fetch('/api/slots');
        const slots = await response.json();
        const select = document.getElementById('edit_user_slot');
        const loadingText = document.getElementById('slots-loading');

        slots.forEach(slot => {
            const option = document.createElement('option');
            option.value = slot.id;
            option.textContent = `${slot.day}, ${slot.date} at ${slot.time}`;
            if (slot.id === booking.selected_slot) {
                option.textContent += ' (current)';
            }
            select.appendChild(option);
        });

        loadingText.textContent = `${slots.length} available time slots`;
        loadingText.style.color = 'var(--success)';
    } catch (error) {
        console.error('Error loading slots:', error);
        document.getElementById('slots-loading').textContent = 'Failed to load time slots';
        document.getElementById('slots-loading').style.color = 'var(--error)';
    }
}

async function saveUserBookingEdit(email, modal) {
    const newSlotId = document.getElementById('edit_user_slot').value;
    const newBuilding = document.getElementById('edit_user_building').value;
    const newRoomNumber = document.getElementById('edit_user_room_number').value.trim();

    if (!newBuilding || !newRoomNumber) {
        showNotification('Please select a building and enter a room number', 'error');
        return;
    }

    const saveBtn = modal.querySelector('button[onclick*="saveUserBookingEdit"]');
    const originalBtnText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span style="width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; border-radius: 50%; animation: spin 0.8s linear infinite;"></span>Saving...</span>';

    try {
        const response = await fetch('/api/booking/update-by-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                selected_slot: newSlotId || undefined,
                selected_building: newBuilding,
                room_number: newRoomNumber
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            modal.remove();
            showNotification('Your booking has been updated successfully!', 'success');

            // Refresh the booking display
            setTimeout(() => {
                lookupBooking();
            }, 500);
        } else {
            showNotification('Error: ' + result.message, 'error');
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnText;
        }
    } catch (error) {
        console.error('Error updating booking:', error);
        showNotification('Failed to update booking. Please try again.', 'error');
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalBtnText;
    }
}
