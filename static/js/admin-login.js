// Admin Login Form Handler

async function handleLogin(event) {
    event.preventDefault();

    const errorEl = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginBtn');
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // Hide any previous errors
    errorEl.classList.remove('show');
    errorEl.textContent = '';

    // Validate inputs
    if (!username) {
        showError(errorEl, 'Please enter your username or email');
        return;
    }
    if (!password) {
        showError(errorEl, 'Please enter your password');
        return;
    }

    // Show loading state
    loginBtn.disabled = true;
    loginBtn.textContent = 'Signing in...';

    try {
        const response = await fetch('/admin/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Show success feedback briefly
            loginBtn.textContent = 'Success! Redirecting...';
            window.location.href = '/admin';
        } else if (response.status === 429) {
            // Rate limited
            showError(errorEl, result.message || 'Too many login attempts. Please wait a few minutes before trying again.');
            resetButton(loginBtn);
        } else if (response.status === 401) {
            // Invalid credentials
            showError(errorEl, result.message || 'Invalid username or password. Please check your credentials and try again.');
            resetButton(loginBtn);
            // Clear password field for security
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        } else {
            // Other errors
            showError(errorEl, result.message || 'Login failed. Please try again.');
            resetButton(loginBtn);
        }
    } catch (error) {
        console.error('Login error:', error);
        // Network or server error
        showError(errorEl, 'Unable to connect to the server. Please check your internet connection and try again.');
        resetButton(loginBtn);
    }
}

function showError(errorEl, message) {
    errorEl.textContent = message;
    errorEl.classList.add('show');
    // Scroll error into view if needed
    errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function resetButton(btn) {
    btn.disabled = false;
    btn.textContent = 'Sign In';
}
