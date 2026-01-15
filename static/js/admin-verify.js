// Admin Password Verification Handler

async function verifyPassword(event) {
    event.preventDefault();

    const password = document.getElementById('password').value;
    const button = document.getElementById('verifyButton');
    const errorMessage = document.getElementById('errorMessage');

    // Reset error
    errorMessage.style.display = 'none';
    errorMessage.textContent = '';

    // Validate input
    if (!password) {
        showVerifyError(errorMessage, 'Please enter your password');
        return;
    }

    // Disable button and show loading
    button.disabled = true;
    button.textContent = 'Verifying...';

    try {
        const response = await fetch('/admin/verify-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ password }),
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Show success and redirect
            button.textContent = 'Verified! Redirecting...';
            window.location.href = '/admin';
        } else if (response.status === 401) {
            // Wrong password
            showVerifyError(errorMessage, result.message || 'Incorrect password. Please try again.');
            resetVerifyButton(button);
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        } else if (response.status === 400) {
            // Missing data
            showVerifyError(errorMessage, result.message || 'Password is required.');
            resetVerifyButton(button);
        } else {
            // Other error
            showVerifyError(errorMessage, result.message || 'Verification failed. Please try again.');
            resetVerifyButton(button);
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        }
    } catch (error) {
        console.error('Verification error:', error);
        showVerifyError(errorMessage, 'Unable to connect to the server. Please check your connection and try again.');
        resetVerifyButton(button);
    }
}

function showVerifyError(errorEl, message) {
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    // Scroll into view if needed
    errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function resetVerifyButton(btn) {
    btn.disabled = false;
    btn.textContent = 'Verify & Continue';
}
