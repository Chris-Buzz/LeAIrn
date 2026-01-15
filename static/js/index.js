/**
 * Index Page Specific JavaScript
 * Handles authentication UI, pricing panel, AI tools panel, and admin registration modal
 */

// ============================================================================
// DEBUG & AUTHENTICATION STATUS
// ============================================================================

/**
 * Log authentication status on page load for debugging (disabled in production)
 */
function logAuthenticationStatus() {
    // Debug logging disabled for security - do not expose auth status in console
}

// ============================================================================
// RECAPTCHA INITIALIZATION
// ============================================================================

/**
 * Initialize reCAPTCHA if the site key is provided
 * Site key is passed via body data-recaptcha-key attribute
 */
function initializeRecaptcha() {
    // reCAPTCHA key is read from document.body.dataset.recaptchaKey
    // reCAPTCHA will auto-initialize when site key is present in data attribute
}

// ============================================================================
// UI PANEL CONTROLS
// ============================================================================

/**
 * Toggle AI Tools Panel visibility
 */
function toggleAITools() {
    const panel = document.getElementById('aiToolsPanel');
    const btn = document.querySelector('.ai-tools-btn');

    if (!panel || !btn) return;

    if (panel.classList.contains('visible')) {
        panel.classList.remove('visible');
        panel.classList.add('hidden');
        btn.style.display = 'flex';
    } else {
        panel.classList.remove('hidden');
        panel.classList.add('visible');
        btn.style.display = 'none';
    }
}

/**
 * Open Pricing Info Panel
 */
function openPricingInfo() {
    const panel = document.getElementById('pricingPanel');
    const btn = document.querySelector('.pricing-btn');

    if (!panel) return;

    panel.classList.remove('hidden');
    panel.classList.add('visible');
    if (btn) btn.style.display = 'none';
}

/**
 * Close Pricing Info Panel
 */
function closePricingInfo() {
    const panel = document.getElementById('pricingPanel');
    const btn = document.querySelector('.pricing-btn');

    if (!panel) return;

    panel.classList.remove('visible');
    panel.classList.add('hidden');
    if (btn) btn.style.display = 'flex';
}

/**
 * Logout user - redirect to logout route
 */
function logout() {
    window.location.href = '/logout';
}

// ============================================================================
// AUTHENTICATION GATE
// ============================================================================

/**
 * Handle authentication gate display based on user status
 */
function handleAuthenticationGate() {
    const loadingScreen = document.getElementById('loadingScreen');
    const authGate = document.getElementById('authGate');
    const mainContent = document.getElementById('mainContent');
    const isAuthenticated = document.body.dataset.authenticated === 'true';


    // Hide loading screen after a brief moment
    setTimeout(() => {
        if (loadingScreen) {
            loadingScreen.style.display = 'none';
        }

        if (isAuthenticated) {
            // User is authenticated - show main content
            if (mainContent) {
                mainContent.style.display = 'block';
            }
            if (authGate) {
                authGate.style.pointerEvents = 'none';
                authGate.style.opacity = '0';
            }
        } else {
            // Not authenticated - show invite gate
            if (authGate) {
                authGate.style.display = 'flex';
                authGate.style.pointerEvents = 'all';
                setTimeout(() => {
                    authGate.style.opacity = '1';
                }, 50);
            }
            if (mainContent) {
                mainContent.style.display = 'none';
            }
        }
    }, 500);
}

// ============================================================================
// ADMIN REGISTRATION MODAL
// ============================================================================

/**
 * Show admin registration modal if triggered by URL parameter
 */
function showAdminRegistrationModal() {
    const modal = document.getElementById('adminRegistrationModal');
    const emailDisplay = document.getElementById('adminEmailDisplay');

    if (!modal || !emailDisplay) return;

    // Get email from session (passed via URL parameter)
    const urlParams = new URLSearchParams(window.location.search);
    const showReg = urlParams.get('show_admin_registration');

    if (showReg === 'true') {
        // Fetch session data to get pending email
        fetch('/api/admin/pending-registration')
            .then(response => response.json())
            .then(data => {
                if (data.pending && data.email) {
                    emailDisplay.textContent = data.email;
                    modal.style.display = 'flex';
                }
            })
            .catch(error => {
                console.error('Error fetching pending registration:', error);
            });
    }
}

/**
 * Close admin registration modal
 */
function closeAdminRegistrationModal() {
    const modal = document.getElementById('adminRegistrationModal');
    if (!modal) return;

    modal.style.display = 'none';
    
    // Clear URL parameter
    const url = new URL(window.location);
    url.searchParams.delete('show_admin_registration');
    window.history.replaceState({}, '', url);
}

/**
 * Submit admin registration form
 * @param {Event} event - Form submit event
 */
async function submitAdminRegistration(event) {
    event.preventDefault();

    const username = document.getElementById('admin_username')?.value.trim();
    const password = document.getElementById('admin_password')?.value;
    const confirmPassword = document.getElementById('admin_confirm_password')?.value;
    const emailDisplay = document.getElementById('adminEmailDisplay')?.textContent;
    const submitBtn = document.getElementById('adminRegSubmitBtn');
    const errorDiv = document.getElementById('adminRegError');

    if (!username || !password || !confirmPassword || !emailDisplay || !submitBtn || !errorDiv) {
        console.error('Missing required form elements');
        return;
    }

    // Reset error
    errorDiv.style.display = 'none';

    // Validate passwords match
    if (password !== confirmPassword) {
        errorDiv.textContent = 'Passwords do not match.';
        errorDiv.style.display = 'block';
        return;
    }

    // Show loading state
    submitBtn.disabled = true;
    const btnText = submitBtn.querySelector('.btn-text');
    const btnSpinner = submitBtn.querySelector('.btn-spinner');
    
    if (btnText) btnText.style.display = 'none';
    if (btnSpinner) btnSpinner.classList.remove('hidden');

    try {
        const response = await fetch('/admin/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: emailDisplay,
                username: username,
                password: password,
                confirm_password: confirmPassword
            })
        });

        const result = await response.json();

        if (result.success) {
            // Success - redirect to admin dashboard
            window.location.href = '/admin/login';
        } else {
            // Show error
            errorDiv.textContent = result.message || 'Failed to create account.';
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            if (btnText) btnText.style.display = 'inline';
            if (btnSpinner) btnSpinner.classList.add('hidden');
        }
    } catch (error) {
        console.error('Registration error:', error);
        errorDiv.textContent = 'An error occurred. Please try again.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
        if (btnText) btnText.style.display = 'inline';
        if (btnSpinner) btnSpinner.classList.add('hidden');
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize all index page functionality
 */
function initializeIndexPage() {
    logAuthenticationStatus();
    initializeRecaptcha();
    handleAuthenticationGate();
    showAdminRegistrationModal();
}

// Run on DOM ready
document.addEventListener('DOMContentLoaded', initializeIndexPage);
