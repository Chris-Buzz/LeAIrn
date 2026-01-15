/**
 * Admin Setup Form Handler
 * Handles form submission and password validation for admin account creation
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('setupForm');
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');
    const submitBtn = document.getElementById('submitBtn');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const passwordMatchStatus = document.getElementById('passwordMatchStatus');
    const pendingEmailEl = document.getElementById('pendingEmail');
    const pendingEmail = pendingEmailEl ? pendingEmailEl.dataset.email : '';

    // Check if we have a pending email
    if (!pendingEmail) {
        showError('Session expired. Please start the login process again.');
        submitBtn.disabled = true;
        return;
    }

    // Real-time password match validation
    function checkPasswordMatch() {
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        if (confirmPassword.length === 0) {
            passwordMatchStatus.textContent = '';
            passwordMatchStatus.style.color = '';
            return;
        }

        if (password === confirmPassword) {
            passwordMatchStatus.textContent = 'Passwords match';
            passwordMatchStatus.style.color = 'var(--success)';
        } else {
            passwordMatchStatus.textContent = 'Passwords do not match';
            passwordMatchStatus.style.color = 'var(--error)';
        }
    }

    passwordInput.addEventListener('input', checkPasswordMatch);
    confirmPasswordInput.addEventListener('input', checkPasswordMatch);

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        successMessage.style.display = 'none';
        // Scroll error into view
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    function hideError() {
        errorMessage.style.display = 'none';
        errorMessage.textContent = '';
    }

    function showSuccess(email) {
        document.querySelector('.setup-container').innerHTML =
            '<div style="text-align: center;">' +
                '<div class="setup-icon" style="width: 80px; height: 80px; background: linear-gradient(135deg, #A6E3A1 0%, #94E2D5 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1.5rem;">' +
                    '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                        '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>' +
                        '<polyline points="22,6 12,13 2,6"></polyline>' +
                    '</svg>' +
                '</div>' +
                '<h1 style="font-size: 1.75rem; font-weight: 700; margin-bottom: 0.75rem; color: var(--text-primary);">Check Your Email</h1>' +
                '<p style="color: var(--text-secondary); margin-bottom: 1.5rem; line-height: 1.6;">' +
                    'We\'ve sent a verification link to<br>' +
                    '<strong style="color: var(--primary);">' + escapeHtml(email) + '</strong>' +
                '</p>' +
                '<p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.5rem;">' +
                    'Click the link in the email to complete your account setup.<br>' +
                    'The link expires in 1 hour.' +
                '</p>' +
                '<div style="background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); padding: 1rem; border-radius: 0.75rem; text-align: left;">' +
                    '<p style="color: var(--text-secondary); font-size: 0.85rem; margin: 0;">' +
                        '<strong style="color: var(--text-primary);">Didn\'t receive the email?</strong><br>' +
                        'Check your spam folder or <a href="/admin/setup" style="color: var(--primary);">try again</a>.' +
                    '</p>' +
                '</div>' +
            '</div>';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function resetButton() {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Create Admin Account';
    }

    async function handleSubmit(e) {
        e.preventDefault();
        e.stopPropagation();

        const username = document.getElementById('username').value.trim();
        const password = passwordInput.value;
        const confirmPassword = confirmPasswordInput.value;

        // Clear any previous errors
        hideError();

        // Validation
        if (!username) {
            showError('Please enter a username');
            document.getElementById('username').focus();
            return false;
        }

        if (!/^[a-zA-Z0-9_]{3,20}$/.test(username)) {
            showError('Username must be 3-20 characters and contain only letters, numbers, and underscores');
            document.getElementById('username').focus();
            return false;
        }

        if (!password) {
            showError('Please enter a password');
            passwordInput.focus();
            return false;
        }

        if (password.length < 8) {
            showError('Password must be at least 8 characters');
            passwordInput.focus();
            return false;
        }

        if (password !== confirmPassword) {
            showError('Passwords do not match');
            confirmPasswordInput.focus();
            return false;
        }

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner"></span>Creating account...';

        try {
            const response = await fetch('/admin/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: pendingEmail,
                    username: username,
                    password: password,
                    confirm_password: confirmPassword
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showSuccess(pendingEmail);
            } else if (response.status === 400) {
                // Validation error
                showError(result.message || 'Please check your input and try again.');
                resetButton();
            } else if (response.status === 403) {
                // Not authorized
                showError(result.message || 'Your email is not authorized for admin access. Please contact an administrator.');
                resetButton();
            } else if (response.status === 500) {
                // Server error (often email sending failure)
                showError(result.message || 'Server error. This may be due to email configuration issues. Please contact an administrator.');
                resetButton();
            } else {
                showError(result.message || 'Failed to create account. Please try again.');
                resetButton();
            }
        } catch (error) {
            console.error('Registration error:', error);
            showError('Unable to connect to the server. Please check your connection and try again.');
            resetButton();
        }

        return false;
    }

    form.addEventListener('submit', handleSubmit);
});
