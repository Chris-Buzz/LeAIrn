// Theme Management
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    // Toggle icons
    document.getElementById('theme-icon-light').classList.toggle('hidden');
    document.getElementById('theme-icon-dark').classList.toggle('hidden');
}

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
if (savedTheme === 'dark') {
    document.getElementById('theme-icon-light').classList.add('hidden');
    document.getElementById('theme-icon-dark').classList.remove('hidden');
}

// Feedback Form Logic
let selectedRating = 0;
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

const ratingLabels = {
    1: 'Poor',
    2: 'Fair',
    3: 'Good',
    4: 'Very Good',
    5: 'Excellent'
};

function setRating(rating) {
    selectedRating = rating;

    // Update star display
    const stars = document.querySelectorAll('.star');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.classList.add('active');
        } else {
            star.classList.remove('active');
        }
    });

    // Update rating label
    document.getElementById('ratingLabel').textContent = ratingLabels[rating];

    // Clear error if it was showing
    document.getElementById('errorMessage').classList.add('hidden');
}

async function submitFeedback(event) {
    event.preventDefault();

    // Validate rating
    if (selectedRating === 0) {
        const errorMsg = document.getElementById('errorMessage');
        errorMsg.textContent = 'Please select a star rating before submitting.';
        errorMsg.classList.remove('hidden');
        return;
    }

    // Validate token
    if (!token) {
        const errorMsg = document.getElementById('errorMessage');
        errorMsg.textContent = 'Invalid feedback link. Please use the link from your email.';
        errorMsg.classList.remove('hidden');
        return;
    }

    const comments = document.getElementById('comments').value.trim();
    const submitBtn = document.getElementById('submitBtn');

    // Disable button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';

    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                token: token,
                rating: selectedRating,
                comments: comments
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            // Show success message
            document.getElementById('feedbackForm').classList.add('hidden');
            document.getElementById('successMessage').classList.remove('hidden');
        } else {
            const errorMsg = document.getElementById('errorMessage');
            errorMsg.textContent = result.message || 'Failed to submit feedback. Please try again.';
            errorMsg.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Feedback';
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        const errorMsg = document.getElementById('errorMessage');
        errorMsg.textContent = 'An error occurred. Please try again later.';
        errorMsg.classList.remove('hidden');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Feedback';
    }
}

// Check if token exists on page load
if (!token) {
    document.getElementById('errorMessage').textContent = 'Invalid feedback link. Please use the link from your email.';
    document.getElementById('errorMessage').classList.remove('hidden');
    document.getElementById('submitBtn').disabled = true;
}
