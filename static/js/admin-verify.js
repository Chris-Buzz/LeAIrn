// Admin Password Verification Handler

async function verifyPassword(event) {
    event.preventDefault();

    const password = document.getElementById('password').value;
    const button = document.getElementById('verifyButton');
    const errorMessage = document.getElementById('errorMessage');

    // Reset error
    errorMessage.style.display = 'none';
    errorMessage.textContent = '';

    // Disable button
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

        if (result.success) {
            // Redirect to admin dashboard
            window.location.href = '/admin';
        } else {
            // Show error
            errorMessage.textContent = result.message || 'Verification failed. Please try again.';
            errorMessage.style.display = 'block';
            button.disabled = false;
            button.textContent = 'Verify & Continue';
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        }
    } catch (error) {
        console.error('Verification error:', error);
        errorMessage.textContent = 'An error occurred. Please try again.';
        errorMessage.style.display = 'block';
        button.disabled = false;
        button.textContent = 'Verify & Continue';
    }
}
