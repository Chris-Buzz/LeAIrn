// Admin Login Form Handler

async function handleLogin(event) {
    event.preventDefault();

    const errorEl = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginBtn');
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    errorEl.classList.remove('show');
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
            window.location.href = '/admin';
        } else {
            throw new Error(result.message || 'Invalid credentials');
        }
    } catch (error) {
        errorEl.textContent = error.message;
        errorEl.classList.add('show');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Sign In';
    }
}
