// Admin theme toggle
        function initAdminTheme() {
            const savedTheme = localStorage.getItem('admin-theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateThemeIcons(savedTheme);
        }

        function toggleAdminTheme() {
            const current = document.documentElement.getAttribute('data-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('admin-theme', newTheme);
            updateThemeIcons(newTheme);
        }

        function updateThemeIcons(theme) {
            const lightIcon = document.getElementById('admin-theme-light');
            const darkIcon = document.getElementById('admin-theme-dark');
            const label = document.getElementById('theme-label');
            if (lightIcon && darkIcon) {
                lightIcon.style.display = theme === 'dark' ? 'none' : 'block';
                darkIcon.style.display = theme === 'dark' ? 'block' : 'none';
            }
            if (label) label.textContent = theme === 'dark' ? 'Light' : 'Dark';
        }

        // Initialize theme immediately
        initAdminTheme();

        // Helper: check if a fetch response is an auth error (401) and redirect if needed
        function handleAuthError(response) {
            if (response.status === 401) {
                response.json().then(data => {
                    alert(data.message || 'Session expired. Please log in again.');
                    window.location.href = data.redirect || '/admin/login';
                }).catch(() => {
                    alert('Session expired. Please log in again.');
                    window.location.href = '/admin/login';
                });
                return true; // Was an auth error
            }
            return false; // Not an auth error
        }

        // Safe JSON parser: handles auth errors and non-JSON responses gracefully
        async function safeJson(response) {
            if (handleAuthError(response)) return null;
            const text = await response.text();
            try {
                return JSON.parse(text);
            } catch {
                console.error('Non-JSON response:', text.substring(0, 200));
                throw new Error(`Server error (${response.status})`);
            }
        }

        // Registration Modal Functions
        function checkAndShowRegistrationModal() {
            // Check if the user needs to register (server sets this in session)
            fetch('/api/check-registration-needed')
                .then(res => { if (handleAuthError(res)) throw new Error('auth'); return res.json(); })
                .then(data => {
                    if (data.needs_registration) {
                        document.getElementById('registrationEmail').textContent = data.email || 'Unknown';
                        document.getElementById('registrationModal').style.display = 'flex';
                    }
                })
                .catch(err => console.error('Error checking registration status:', err));
        }

        document.getElementById('registrationForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('regUsername').value.trim();
            const password = document.getElementById('regPassword').value;
            const confirmPassword = document.getElementById('regConfirmPassword').value;
            const email = document.getElementById('registrationEmail').textContent;
            const errorDiv = document.getElementById('registrationError');
            const successDiv = document.getElementById('registrationSuccess');
            const submitBtn = document.getElementById('regSubmitBtn');

            // Clear previous messages
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';

            // Validation
            if (password !== confirmPassword) {
                errorDiv.textContent = 'Passwords do not match';
                errorDiv.style.display = 'block';
                return;
            }

            if (password.length < 8) {
                errorDiv.textContent = 'Password must be at least 8 characters';
                errorDiv.style.display = 'block';
                return;
            }

            if (username.length < 3) {
                errorDiv.textContent = 'Username must be at least 3 characters';
                errorDiv.style.display = 'block';
                return;
            }

            // Disable button with loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 18px; height: 18px;"></span>Sending Verification Email...</span>';

            try {
                const response = await fetch('/admin/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        email: email,
                        username: username,
                        password: password,
                        confirm_password: confirmPassword
                    })
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    // Email verification flow - SECURE (no bypass)
                    successDiv.innerHTML = `
                        <div style="display: flex; gap: 0.625rem; align-items: start;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="color: #059669; flex-shrink: 0; margin-top: 0.125rem;">
                                <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                                <polyline points="22 4 12 14.01 9 11.01"/>
                            </svg>
                            <div>
                                <strong style="display: block; margin-bottom: 0.25rem; font-size: 0.9rem;">Verification Email Sent!</strong>
                                <span style="font-size: 0.85rem;">${result.message}</span><br><br>
                                <strong style="font-size: 0.875rem;">Next Steps:</strong><br>
                                <span style="font-size: 0.85rem;">
                                1. Check ${email}<br>
                                2. Click verification link<br>
                                3. Auto-login to dashboard
                                </span>
                            </div>
                        </div>
                    `;
                    successDiv.style.display = 'block';

                    // Hide form fields after success
                    document.getElementById('regUsername').disabled = true;
                    document.getElementById('regPassword').disabled = true;
                    document.getElementById('regConfirmPassword').disabled = true;
                    submitBtn.style.display = 'none';
                } else {
                    errorDiv.textContent = result.message || 'Failed to send verification email';
                    errorDiv.style.display = 'block';
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>Create Account';
                }
            } catch (error) {
                console.error('Registration error:', error);
                errorDiv.textContent = 'Network error. Please try again.';
                errorDiv.style.display = 'block';
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>Send Verification Email';
            }
        });

        document.addEventListener('DOMContentLoaded', () => {
            checkAndShowRegistrationModal();
            loadUsers();
        });

        function formatSlotId(slotId) {
            // Handle null, undefined, or non-string values
            if (!slotId || typeof slotId !== 'string') {
                return 'Not specified';
            }

            // If slotId is too short, return as is
            if (slotId.length < 12) {
                return slotId;
            }

            const year = slotId.substring(0, 4);
            const month = slotId.substring(4, 6);
            const day = slotId.substring(6, 8);
            const hour = slotId.substring(8, 10);
            const minute = slotId.substring(10, 12);

            const date = new Date(year, month - 1, day, hour, minute);
            return date.toLocaleString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
            });
        }

        function exportCSV() {
            window.location.href = '/api/export/csv';
        }

        function logout() {
            if (confirm('Are you sure you want to logout?')) {
                window.location.href = '/admin/logout';
            }
        }

        let allUsers = [];

        async function loadUsers() {
            try {
                const response = await fetch('/api/users');
                if (handleAuthError(response)) return;
                if (!response.ok) throw new Error('Failed to load data');

                allUsers = await safeJson(response);
                displayUsers(allUsers);
            } catch (error) {
                console.error('Error loading users:', error);
                document.getElementById('bookingsTable').innerHTML = `
                    <tr>
                        <td colspan="9" class="empty-state" style="color: var(--error);">
                            <p>Error loading bookings. Please try again.</p>
                        </td>
                    </tr>
                `;
            }
        }

        async function displayUsers(users) {
            // Update current bookings count
            document.getElementById('totalBookings').textContent = users.length;
            document.getElementById('totalStudents').textContent = users.filter(u => u.role === 'student').length;

            // Fetch and update all-time statistics
            try {
                const statsResponse = await fetch('/api/statistics');
                if (handleAuthError(statsResponse)) return;
                if (statsResponse.ok) {
                    const stats = await statsResponse.json();
                    console.log('[STATS] Response:', JSON.stringify(stats));

                    // Check if this is a super_admin (Master) or tutor_admin
                    if (stats.role === 'super_admin' && stats.master_total) {
                        // Master admin - show master totals
                        document.getElementById('totalBookingsAllTime').textContent = stats.master_total.total_bookings || 0;
                        document.getElementById('uniqueClients').textContent = stats.master_total.unique_clients || 0;

                        // Show per-tutor breakdown if available
                        if (stats.tutor_stats) {
                            displayTutorBreakdown(stats.tutor_stats);
                        }
                    } else {
                        // Tutor admin - show their own stats
                        document.getElementById('totalBookingsAllTime').textContent = stats.total_bookings || 0;
                        document.getElementById('uniqueClients').textContent = stats.unique_clients || 0;
                    }
                } else {
                    // Fallback to calculating from users array
                    document.getElementById('totalBookingsAllTime').textContent = users.length;
                    const uniqueEmails = new Set(users.map(u => (u.email || '').toLowerCase().trim()).filter(e => e));
                    document.getElementById('uniqueClients').textContent = uniqueEmails.size;
                }
            } catch (error) {
                console.error('Error fetching statistics:', error);
                // Fallback to calculating from users array
                document.getElementById('totalBookingsAllTime').textContent = users.length;
                const uniqueEmails = new Set(users.map(u => (u.email || '').toLowerCase().trim()).filter(e => e));
                document.getElementById('uniqueClients').textContent = uniqueEmails.size;
            }

            function displayTutorBreakdown(tutorStats) {
                // Find or create tutor breakdown section
                let breakdownSection = document.getElementById('tutor-breakdown-section');

                if (!breakdownSection) {
                    // Create breakdown section after the statistics cards
                    const statsSection = document.querySelector('.stats-grid');
                    if (statsSection && statsSection.parentElement) {
                        breakdownSection = document.createElement('div');
                        breakdownSection.id = 'tutor-breakdown-section';
                        breakdownSection.style.marginTop = '2rem';
                        statsSection.parentElement.insertBefore(breakdownSection, statsSection.nextSibling);
                    }
                }

                if (!breakdownSection) return;

                // Build tutor breakdown HTML
                let html = '<h3 style="color: var(--text-primary); margin-bottom: 1rem; font-size: 1.25rem;">Per-Tutor Statistics</h3>';
                html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">';

                for (const [tutorId, stats] of Object.entries(tutorStats)) {
                    html += `
                        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.5rem;">
                            <div style="color: var(--primary); font-weight: 600; margin-bottom: 0.75rem; font-size: 1.125rem;">${stats.tutor_name}</div>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: var(--text-secondary);">Total Sessions:</span>
                                    <span style="color: var(--text-primary); font-weight: 600;">${stats.total_bookings}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between;">
                                    <span style="color: var(--text-secondary);">Unique Clients:</span>
                                    <span style="color: var(--text-primary); font-weight: 600;">${stats.unique_clients}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }

                html += '</div>';
                breakdownSection.innerHTML = html;
            }

            const now = new Date();
            const weekStart = new Date(now.setDate(now.getDate() - now.getDay()));
            const thisWeekCount = users.filter(u => {
                const submissionDate = new Date(u.submission_date);
                return submissionDate >= weekStart;
            }).length;
            document.getElementById('thisWeek').textContent = thisWeekCount;

            // Populate table
            const tbody = document.getElementById('bookingsTable');

            if (users.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="9" class="empty-state">
                            <p>No bookings yet</p>
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = '';
            users.forEach((user, index) => {
                const row = document.createElement('tr');

                const aiLevel = user.ai_familiarity || 'N/A';
                const primaryUse = user.primary_use || 'N/A';
                const department = user.department || 'N/A';

                // Format location with meeting type badge
                const meetingType = user.meeting_type || 'in-person';
                const attendeeCount = user.attendee_count || 1;
                const meetingTypeBadge = meetingType === 'zoom'
                    ? '<span style="display: inline-block; background: linear-gradient(135deg, #2D8CFF, #0B5CFF); color: white; font-size: 0.65rem; padding: 0.15rem 0.4rem; border-radius: 0.25rem; margin-right: 0.25rem;">ZOOM</span>'
                    : '';
                const attendeeBadge = attendeeCount > 1
                    ? `<span style="display: inline-block; background: rgba(16, 185, 129, 0.1); color: #10B981; font-size: 0.7rem; padding: 0.15rem 0.4rem; border-radius: 0.25rem; margin-left: 0.25rem;">${attendeeCount} people</span>`
                    : '';

                // Format booked at timestamp
                const bookedAt = user.timestamp || user.submission_date;
                let bookedAtFormatted = 'N/A';
                if (bookedAt) {
                    const bookedDate = new Date(bookedAt);
                    bookedAtFormatted = bookedDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' ' + bookedDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
                }

                row.innerHTML = `
                    <td><strong>${user.full_name}</strong></td>
                    <td>${user.email}</td>
                    <td><span class="badge badge-role">${user.role}</span></td>
                    <td>${department}</td>
                    <td><span class="badge" style="background: rgba(139, 92, 246, 0.1); color: #8B5CF6;">${aiLevel}</span></td>
                    <td title="${primaryUse}">${primaryUse}</td>
                    <td style="white-space: nowrap;">${user.slot_details && user.slot_details.day && user.slot_details.date && user.slot_details.time ? `${user.slot_details.day}, ${user.slot_details.date} at ${user.slot_details.time}` : formatSlotId(user.selected_slot)}</td>
                    <td>${meetingTypeBadge}${user.selected_room || 'Not specified'}${attendeeBadge}</td>
                    <td style="white-space: nowrap; font-size: 0.8rem; color: var(--text-secondary);">${bookedAtFormatted}</td>
                    <td>
                        <div style="display: flex; gap: 0.25rem; flex-wrap: nowrap;">
                            <button data-action="viewUserDetails" data-index="${index}" title="View Details" style="flex: 1; min-width: 50px; padding: 0.45rem 0.5rem; background: var(--primary); color: white; border: none; border-radius: 0.375rem; cursor: pointer; font-size: 0.75rem; font-weight: 600; white-space: nowrap; transition: all 0.2s;">
                                View
                            </button>
                            <button data-action="editBooking" data-index="${index}" title="Edit Booking" style="flex: 1; min-width: 45px; padding: 0.45rem 0.5rem; background: #F59E0B; color: white; border: none; border-radius: 0.375rem; cursor: pointer; font-size: 0.75rem; font-weight: 600; white-space: nowrap; transition: all 0.2s;">
                                Edit
                            </button>
                            <button data-action="markComplete" data-index="${index}" title="Mark Complete & Send Feedback" style="flex: 1; min-width: 40px; padding: 0.5rem; background: #10B981; color: white; border: none; border-radius: 0.375rem; cursor: pointer; font-size: 1.25rem; font-weight: 600; white-space: nowrap; transition: all 0.2s;">
                                ✓
                            </button>
                            <button data-action="deleteBooking" data-index="${index}" title="Delete Booking" style="flex: 1; min-width: 55px; padding: 0.45rem 0.5rem; background: var(--error); color: white; border: none; border-radius: 0.375rem; cursor: pointer; font-size: 0.75rem; font-weight: 600; white-space: nowrap; transition: all 0.2s;">
                                Delete
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        function markComplete(index) {
            const user = allUsers[index];
            showSessionNotesModal(user, index);
        }

        function showSessionNotesModal(user, index) {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                padding: 1rem;
            `;

            modal.innerHTML = `
                <div style="background: var(--surface); border-radius: 1rem; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 2rem;">
                    <h2 style="margin-bottom: 0.5rem; color: var(--text-primary);">Complete Session: ${user.full_name}</h2>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">Add session notes for your records and send a summary to the student.</p>

                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Session Notes (Optional)</label>
                        <textarea id="sessionNotes" placeholder="What did you cover? What tools did you teach? What prompting techniques? What should they practice?..." style="width: 100%; min-height: 200px; padding: 1rem; border: 2px solid var(--border); border-radius: 0.75rem; font-family: inherit; font-size: 0.95rem; resize: vertical; background: var(--bg); color: var(--text-primary);"></textarea>
                        <small style="display: block; margin-top: 0.5rem; color: var(--text-tertiary);">Notes will be formatted and sent to the student.</small>

                        <label style="display: flex; align-items: center; gap: 0.5rem; margin-top: 1rem; cursor: pointer;">
                            <input type="checkbox" id="skipAI" style="width: 18px; height: 18px; cursor: pointer;">
                            <span style="color: var(--text-primary); font-weight: 500;">Send without AI enhancement (use raw notes as-is)</span>
                        </label>
                    </div>

                    <div style="background: rgba(139, 92, 246, 0.05); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 0.75rem; padding: 1rem; margin-bottom: 1.5rem;">
                        <strong style="color: var(--primary);">What happens next:</strong>
                        <ul style="margin: 0.5rem 0 0 1.5rem; color: var(--text-secondary);">
                            <li id="aiEnhanceText">Session notes will be enhanced with AI and emailed to student</li>
                            <li>Feedback request will be sent to student</li>
                            <li>Notes will be saved to your records</li>
                            <li>Booking will be marked complete and removed</li>
                        </ul>
                    </div>

                    <div style="display: flex; gap: 0.75rem;">
                        <button data-action="closeModal" style="flex: 1; padding: 0.875rem; background: var(--bg); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; color: var(--text-primary);">
                            Cancel
                        </button>
                        <button data-action="previewSessionOverview" data-index="${index}" id="previewBtn" style="flex: 1; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Preview & Edit
                        </button>
                        <button data-action="submitSessionComplete" data-index="${index}" id="submitCompleteBtn" style="flex: 1; padding: 0.875rem; background: linear-gradient(135deg, #10B981, #059669); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Complete Without Preview
                        </button>
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);
            document.getElementById('sessionNotes').focus();

            // Update text when checkbox changes
            document.getElementById('skipAI').addEventListener('change', function() {
                const textElement = document.getElementById('aiEnhanceText');
                if (this.checked) {
                    textElement.textContent = 'Raw notes will be sent to student as-is (no AI formatting)';
                } else {
                    textElement.textContent = 'Session notes will be enhanced with AI and emailed to student';
                }
            });
        }

        async function previewSessionOverview(index, modal) {
            const user = allUsers[index];
            const notes = document.getElementById('sessionNotes').value.trim();
            const skipAI = document.getElementById('skipAI').checked;
            const previewBtn = document.getElementById('previewBtn');

            if (!notes && !skipAI) {
                alert('Please enter session notes to preview');
                return;
            }

            // Disable button
            previewBtn.disabled = true;
            previewBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 16px; height: 16px;"></span>Generating...</span>';

            try {
                const response = await fetch('/api/session-overviews/preview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        notes: notes,
                        user_name: user.full_name,
                        user_role: user.role,
                        skip_ai: skipAI
                    })
                });

                if (handleAuthError(response)) return;
                const result = await response.json();

                if (response.ok && result.success) {
                    // Show preview modal
                    showPreviewModal(index, modal, notes, result.enhanced_notes, skipAI);
                } else {
                    alert('Error: ' + (result.message || 'Failed to generate preview'));
                }
            } catch (error) {
                console.error('Error generating preview:', error);
                alert('Failed to generate preview: ' + error.message);
            } finally {
                previewBtn.disabled = false;
                previewBtn.textContent = 'Preview & Edit';
            }
        }

        function showPreviewModal(index, originalModal, rawNotes, enhancedNotes, skipAI) {
            const user = allUsers[index];

            const previewModal = document.createElement('div');
            previewModal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10001;
                padding: 1rem;
            `;

            previewModal.innerHTML = `
                <div style="background: var(--surface); border-radius: 1rem; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 2rem;">
                    <h2 style="margin-bottom: 0.5rem; color: var(--text-primary);">Preview: ${user.full_name}'s Session Overview</h2>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">${skipAI ? 'Review your raw notes before sending' : 'Review and edit the AI-enhanced overview before sending'}</p>

                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">${skipAI ? 'Your Notes' : 'AI-Enhanced Overview'}</label>
                        <textarea id="editableOverview" style="width: 100%; min-height: 300px; padding: 1rem; border: 2px solid var(--border); border-radius: 0.75rem; font-family: inherit; font-size: 0.95rem; resize: vertical; background: var(--bg); color: var(--text-primary); line-height: 1.6;">${enhancedNotes}</textarea>
                        <small style="display: block; margin-top: 0.5rem; color: var(--text-tertiary);">You can edit the text above before sending</small>
                    </div>

                    ${!skipAI ? `
                    <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg); border-radius: 0.75rem; border: 1px solid var(--border);">
                        <strong style="display: block; margin-bottom: 0.5rem; color: var(--text-secondary);">Original Notes:</strong>
                        <p style="color: var(--text-secondary); margin: 0; white-space: pre-wrap; font-size: 0.9rem;">${rawNotes}</p>
                    </div>
                    ` : ''}

                    <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                        <button data-action="closeModal" style="flex: 1; min-width: 120px; padding: 0.875rem; background: var(--bg); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; color: var(--text-primary);">
                            Back to Edit
                        </button>
                        ${!skipAI ? `
                        <button data-action="regenerateOverview" data-index="${index}" data-notes="${rawNotes.replace(/"/g, '&quot;').replace(/'/g, '&#39;')}" style="flex: 1; min-width: 120px; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Regenerate
                        </button>
                        ` : ''}
                        <button data-action="submitWithEditedOverview" data-index="${index}" id="submitEditedBtn" style="flex: 1; min-width: 120px; padding: 0.875rem; background: linear-gradient(135deg, #10B981, #059669); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Send & Complete
                        </button>
                    </div>
                </div>
            `;

            previewModal.classList.add('dynamic-modal');
            document.body.appendChild(previewModal);
            document.getElementById('editableOverview').focus();

            // Store reference to original modal
            previewModal.originalModal = originalModal;
        }

        async function regenerateOverview(index, rawNotes, previewModal) {
            const user = allUsers[index];
            const btn = event.target;
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 16px; height: 16px;"></span>Regenerating...</span>';

            try {
                const response = await fetch('/api/session-overviews/preview', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        notes: rawNotes,
                        user_name: user.full_name,
                        user_role: user.role,
                        skip_ai: false
                    })
                });

                if (handleAuthError(response)) return;
                const result = await response.json();

                if (response.ok && result.success) {
                    document.getElementById('editableOverview').value = result.enhanced_notes;
                    alert('Overview regenerated! Review the new version above.');
                } else {
                    alert('Error: ' + (result.message || 'Failed to regenerate'));
                }
            } catch (error) {
                console.error('Error regenerating:', error);
                alert('Failed to regenerate: ' + error.message);
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        }

        async function submitWithEditedOverview(index, previewModal) {
            const user = allUsers[index];
            const editedNotes = document.getElementById('editableOverview').value.trim();
            const submitBtn = document.getElementById('submitEditedBtn');

            if (!editedNotes) {
                alert('Overview cannot be empty');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 16px; height: 16px;"></span>Completing...</span>';

            try {
                const response = await fetch(`/api/booking/${user.id}/complete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        notes: editedNotes,
                        skip_ai: true  // Already processed, send as-is
                    })
                });

                if (handleAuthError(response)) return;
                const result = await response.json();

                if (response.ok && result.success) {
                    previewModal.remove();
                    if (previewModal.originalModal) {
                        previewModal.originalModal.remove();
                    }
                    alert(`Session completed!\\n\\n✓ Session overview sent to student\\n✓ Feedback request sent\\n✓ Booking removed`);
                    loadUsers();
                } else {
                    alert('Error: ' + (result.message || 'Failed to complete'));
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Send & Complete';
                }
            } catch (error) {
                console.error('Error completing:', error);
                alert('Failed to complete: ' + error.message);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send & Complete';
            }
        }

        async function submitSessionComplete(index, modal) {
            const user = allUsers[index];
            const notes = document.getElementById('sessionNotes').value.trim();
            const skipAI = document.getElementById('skipAI').checked;
            const submitBtn = document.getElementById('submitCompleteBtn');

            // Disable button
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 16px; height: 16px;"></span>Processing...</span>';

            try {
                const response = await fetch(`/api/booking/${user.id}/complete`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        notes: notes,
                        skip_ai: skipAI
                    })
                });

                if (handleAuthError(response)) return;
                const result = await response.json();

                if (response.ok && result.success) {
                    modal.remove();
                    alert(`Session completed!\\n\\n${notes ? '✓ Session overview sent to student\\n' : ''}✓ Feedback request sent\\n✓ Booking removed`);
                    loadUsers();
                    loadTimeSlots();
                } else {
                    alert('Error: ' + (result.message || 'Failed to mark complete'));
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Complete Session';
                }
            } catch (error) {
                console.error('Error marking complete:', error);
                alert('Failed to mark session complete: ' + error.message);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Complete Session';
            }
        }

        async function deleteBooking(index) {
            const user = allUsers[index];
            if (!confirm(`Are you sure you want to delete the booking for ${user.full_name}?`)) {
                return;
            }

            try {
                const response = await fetch(`/api/booking/${user.id}`, {
                    method: 'DELETE'
                });

                const result = await safeJson(response); if (!result) return;

                console.log('Delete response:', response.ok, result);

                if (response.ok) {
                    if (result.success) {
                        alert('Booking deleted successfully!');
                        loadUsers();
                        loadTimeSlots();
                    } else {
                        alert('Error: ' + (result.message || 'Unknown error'));
                    }
                } else {
                    alert('Error: ' + (result.message || 'Failed to delete booking'));
                }
            } catch (error) {
                console.error('Error deleting booking:', error);
                alert('Failed to delete booking: ' + error.message);
            }
        }

        async function editBooking(index) {
            const user = allUsers[index];

            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0, 0, 0, 0.7); display: flex;
                align-items: center; justify-content: center; z-index: 10000;
            `;

            modal.innerHTML = `
                <div style="background: var(--surface); border-radius: 1rem; max-width: 600px; width: 90%; max-height: 90vh; overflow-y: auto; padding: 2rem; position: relative;">
                    <h2 style="margin-bottom: 1.5rem;">Edit Booking - ${user.full_name}</h2>

                    <div style="display: grid; gap: 1rem; margin-bottom: 2rem;">
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Name</label>
                            <input id="edit_name" type="text" value="${user.full_name}" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Email</label>
                            <input id="edit_email" type="email" value="${user.email}" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Location</label>
                            <input id="edit_room" type="text" value="${user.selected_room}" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary);">
                        </div>
                        <div>
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Change Time Slot (Current: ${formatSlotId(user.selected_slot)})</label>
                            <select id="edit_slot" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary);">
                                <option value="${user.selected_slot}">Keep current time</option>
                            </select>
                            <small style="color: var(--text-tertiary); display: block; margin-top: 0.25rem;">Loading available time slots...</small>
                        </div>
                    </div>

                    <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                        <button data-action="closeModal" style="padding: 0.75rem 1.5rem; background: var(--bg); color: var(--text-primary); border: 2px solid var(--border); border-radius: 0.5rem; cursor: pointer; font-weight: 600;">
                            Cancel
                        </button>
                        <button data-action="saveBookingEdit" data-id="${user.id}" style="padding: 0.75rem 1.5rem; background: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600;">
                            Save Changes
                        </button>
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);

            // Load available time slots
            try {
                const response = await fetch('/api/slots');
                const slots = await safeJson(response); if (!slots) return;
                const select = document.getElementById('edit_slot');
                const small = select.nextElementSibling;

                slots.forEach(slot => {
                    const option = document.createElement('option');
                    option.value = slot.id;
                    option.textContent = `${slot.day}, ${slot.date} at ${slot.time}`;
                    select.appendChild(option);
                });

                small.textContent = `${slots.length} available time slots`;
            } catch (error) {
                console.error('Error loading slots:', error);
            }
        }

        async function saveBookingEdit(bookingId, modal) {
            const updatedData = {
                full_name: document.getElementById('edit_name').value,
                email: document.getElementById('edit_email').value,
                selected_room: document.getElementById('edit_room').value,
                selected_slot: document.getElementById('edit_slot').value
            };

            try {
                const response = await fetch(`/api/booking/${bookingId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updatedData)
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    alert('Booking updated successfully!');
                    modal.remove();
                    loadUsers();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                console.error('Error updating booking:', error);
                alert('Failed to update booking');
            }
        }

        // Helper functions to format user data for display
        function formatExperienceLevel(value) {
            const levels = {
                'new': "I'm completely new to AI",
                'casual': "I've tried AI a few times",
                'basic': 'I use AI sometimes',
                'practical': 'I use AI regularly',
                'advanced': "I'm very experienced with AI"
            };
            return levels[value] || value;
        }

        function formatAITools(tools) {
            if (!tools) return 'None';
            const toolNames = {
                'chatgpt': 'ChatGPT',
                'gemini': 'Google Gemini',
                'claude': 'Claude',
                'image_gen': 'Image Generators',
                'coding': 'Coding Assistants',
                'research': 'Research & Search',
                'video': 'Video & Audio',
                'writing': 'Writing Assistants',
                'productivity': 'Productivity Tools',
                'none': 'None yet'
            };
            return tools.split(', ').map(tool => toolNames[tool] || tool).join(', ');
        }

        function formatPrimaryUse(uses) {
            if (!uses) return 'N/A';
            const useNames = {
                'writing': 'Writing & Content',
                'coding': 'Coding & Programming',
                'research': 'Research & Analysis',
                'creative': 'Creative Projects',
                'productivity': 'Productivity & Organization',
                'education': 'School & Studying',
                'business': 'Work & Professional',
                'not_sure': 'Not sure yet'
            };
            return uses.split(', ').map(use => useNames[use] || use).join(', ');
        }

        function formatLearningGoals(goals) {
            if (!goals) return 'N/A';
            const goalNames = {
                'use_tools': 'Get better at using AI',
                'understand': 'Understand how AI works',
                'build': 'Build my own AI projects',
                'integrate': 'Add AI to my projects',
                'career': 'Build career skills',
                'productivity': 'Work more efficiently',
                'explore': 'Just curious to learn'
            };
            return goals.split(', ').map(goal => goalNames[goal] || goal).join(', ');
        }

        function formatConfidenceLevel(value) {
            const levels = {
                '1': 'Not confident',
                '2': 'A little comfortable',
                '3': 'Somewhat comfortable',
                '4': 'Very comfortable',
                '5': 'Expert level'
            };
            return levels[value] || value;
        }

        function formatCodingSetupResponse(value) {
            const responses = {
                'viewed_full': '<span style="color: var(--success);">✓ Viewed full setup guide</span>',
                'ready': '<span style="color: var(--success);">✓ Ready to continue</span>',
                'skip': '<span style="color: var(--warning);">⚠ Skipped from STOP screen</span>',
                'no_time': '<span style="color: var(--warning);">⚠ No time to set up</span>',
                'close': '<span style="color: var(--text-secondary);">ⓘ Closed without response</span>',
                'dismissed': '<span style="color: var(--text-secondary);">ⓘ Dismissed</span>'
            };
            return responses[value] || value;
        }

        async function viewUserDetails(index) {
            const user = allUsers[index];

            // Create modal HTML
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                animation: fadeIn 0.3s ease;
            `;

            const insightsContent = user.ai_insights || `
<div style="display: flex; align-items: center; gap: 0.75rem; justify-content: flex-start;">
    <div style="width: 20px; height: 20px; border: 2.5px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0;"></div>
    <div style="font-weight: 600; color: var(--text-primary); font-size: 0.95rem;">Generating AI insights...</div>
</div>
            `;

            modal.classList.add('dynamic-modal');
            modal.innerHTML = `
                <div style="background: var(--surface); border-radius: 1rem; max-width: 800px; width: 90%; max-height: 90vh; overflow-y: auto; padding: 2rem; position: relative; box-shadow: var(--shadow-lg);">
                    <button data-action="closeModal" style="position: absolute; top: 1rem; right: 1rem; background: var(--bg); border: 2px solid var(--border); border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 1.5rem; color: var(--text-secondary);">×</button>

                    <h2 style="margin-bottom: 1.5rem; color: var(--text-primary);">${user.full_name} - Session Details</h2>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <div style="background: var(--bg); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">Email</div>
                            <div style="font-weight: 600;">${user.email}</div>
                        </div>
                        <div style="background: var(--bg); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">Role</div>
                            <div style="font-weight: 600; text-transform: capitalize;">${user.role}</div>
                        </div>
                        <div style="background: var(--bg); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">${user.role === 'student' ? 'Major' : 'Department'}</div>
                            <div style="font-weight: 600;">${user.department || 'Not specified'}</div>
                        </div>
                        <div style="background: var(--bg); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">Booking Time</div>
                            <div style="font-weight: 600;">${user.slot_details && user.slot_details.day && user.slot_details.date && user.slot_details.time ? `${user.slot_details.day}, ${user.slot_details.date} at ${user.slot_details.time}` : formatSlotId(user.selected_slot)}</div>
                        </div>
                        <div style="background: var(--bg); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">Location</div>
                            <div style="font-weight: 600;">
                                ${user.meeting_type === 'zoom' ? '<span style="display: inline-block; background: linear-gradient(135deg, #2D8CFF, #0B5CFF); color: white; font-size: 0.7rem; padding: 0.2rem 0.5rem; border-radius: 0.25rem; margin-right: 0.35rem;">ZOOM</span>' : ''}${user.selected_room}
                            </div>
                        </div>
                        <div style="background: var(--bg); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                            <div style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 0.5rem;">Attendees</div>
                            <div style="font-weight: 600; display: flex; align-items: center; gap: 0.5rem;">
                                <span style="font-size: 1.25rem;">${user.attendee_count || 1}</span>
                                <span style="color: var(--text-secondary);">${(user.attendee_count || 1) === 1 ? 'person' : 'people'}</span>
                            </div>
                        </div>
                    </div>

                    <h3 style="margin: 2rem 0 1rem; color: var(--text-primary);">AI Experience Profile</h3>
                    <div style="background: rgba(99, 102, 241, 0.05); padding: 1.5rem; border-radius: 0.75rem; border: 1px solid rgba(99, 102, 241, 0.2); margin-bottom: 2rem;">
                        <div style="display: grid; gap: 1rem;">
                            <div><strong>Experience Level:</strong> ${formatExperienceLevel(user.ai_familiarity)}</div>
                            <div><strong>AI Tools Used:</strong> ${formatAITools(user.ai_tools)}</div>
                            <div><strong>Primary Use:</strong> ${formatPrimaryUse(user.primary_use)}</div>
                            <div><strong>Learning Goals:</strong> ${formatLearningGoals(user.learning_goal)}</div>
                            ${user.research_consent !== undefined && user.research_consent !== null ? `<div><strong>Research Consent:</strong> <span style="color: ${user.research_consent ? 'var(--success)' : 'var(--error)'}; font-weight: 600;">${user.research_consent ? '✓ Accepted' : '✗ Declined'}</span></div>` : `<div><strong>Research Consent:</strong> <span style="color: var(--text-tertiary);">Not recorded</span></div>`}
                        </div>
                    </div>

                    ${user.personal_comments ? `
                    <h3 style="margin: 2rem 0 1rem; color: var(--text-primary);">${user.role === 'student' ? "Student's" : user.role === 'teacher' ? "Teacher's" : user.role === 'advisor' ? "Advisor's" : "User's"} Comments</h3>
                    <div style="background: rgba(245, 158, 11, 0.05); padding: 1.5rem; border-radius: 0.75rem; border: 1px solid rgba(245, 158, 11, 0.2); margin-bottom: 2rem;">
                        <div style="line-height: 1.6; white-space: pre-wrap; color: var(--text-primary);">${user.personal_comments}</div>
                    </div>
                    ` : ''}

                    <div style="display: flex; align-items: center; justify-content: space-between; margin: 2rem 0 1rem;">
                        <h3 style="margin: 0; color: var(--text-primary); display: flex; align-items: center; gap: 0.75rem;">
                            AI Teaching Insights
                            <span style="background: linear-gradient(135deg, #6366F1, #8B5CF6); padding: 0.25rem 0.75rem; border-radius: 0.5rem; font-size: 0.75rem; color: white; font-weight: 700;">Powered by Gemini</span>
                        </h3>
                        <button id="refresh-insights-btn" data-action="regenerateInsights" data-index="${index}" style="padding: 0.5rem 1rem; background: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600; font-size: 0.875rem; display: flex; align-items: center; gap: 0.5rem; transition: all 0.3s;" title="Generate new insights">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
                            </svg>
                            Refresh
                        </button>
                    </div>
                    <div id="insights-container" style="background: var(--bg); padding: 1.5rem; border-radius: 0.75rem; border: 2px solid var(--border); line-height: 1.8; font-size: 0.95rem; ${user.ai_insights ? 'white-space: pre-wrap;' : ''}">
                        ${insightsContent}
                    </div>

                    <div style="margin-top: 2rem; text-align: right;">
                        <button data-action="closeModal" style="padding: 0.75rem 2rem; background: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Close
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Generate insights if they don't exist
            if (!user.ai_insights) {
                try {
                    const response = await fetch(`/api/generate-insights/${user.id}`, {
                        method: 'POST'
                    });

                    const result = await safeJson(response); if (!result) return;

                    if (response.ok && result.success) {
                        const insightsContainer = document.getElementById('insights-container');
                        if (insightsContainer) {
                            insightsContainer.style.whiteSpace = 'pre-wrap';
                            insightsContainer.textContent = result.insights;
                        }
                        // Update local cache
                        allUsers[index].ai_insights = result.insights;
                    } else {
                        const insightsContainer = document.getElementById('insights-container');
                        if (insightsContainer) {
                            insightsContainer.innerHTML = '<span style="color: var(--error);">Failed to generate AI insights. Please try again.</span>';
                        }
                    }
                } catch (error) {
                    console.error('Error generating insights:', error);
                    const insightsContainer = document.getElementById('insights-container');
                    if (insightsContainer) {
                        insightsContainer.innerHTML = '<span style="color: var(--error);">Error generating insights: ' + error.message + '</span>';
                    }
                }
            }
        }

        // Regenerate insights function
        async function regenerateInsights(index) {
            const user = allUsers[index];
            const refreshBtn = document.getElementById('refresh-insights-btn');
            const insightsContainer = document.getElementById('insights-container');

            if (!refreshBtn || !insightsContainer) return;

            // Disable button and show loading state
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation: spin 1s linear infinite;">
                    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
                </svg>
                Generating...
            `;
            insightsContainer.innerHTML = '<div style="text-align: center; color: var(--text-secondary); padding: 2rem;">Generating new insights...</div>';

            try {
                const response = await fetch(`/api/generate-insights/${user.id}`, {
                    method: 'POST'
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    insightsContainer.style.whiteSpace = 'pre-wrap';
                    insightsContainer.textContent = result.insights;
                    // Update local cache
                    allUsers[index].ai_insights = result.insights;
                } else {
                    insightsContainer.innerHTML = '<span style="color: var(--error);">Failed to generate AI insights. Please try again.</span>';
                }
            } catch (error) {
                console.error('Error regenerating insights:', error);
                insightsContainer.innerHTML = '<span style="color: var(--error);">Error generating insights: ' + error.message + '</span>';
            } finally {
                // Re-enable button
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
                    </svg>
                    Refresh
                `;
            }
        }

        // Time Slot Management Functions
        let allSlots = [];
        let slotsExpanded = false;

        function toggleSlotsSection() {
            const slotsContent = document.getElementById('slotsManagement');
            const chevron = document.getElementById('slotsChevron');

            slotsExpanded = !slotsExpanded;

            if (slotsExpanded) {
                slotsContent.style.maxHeight = '800px';
                slotsContent.style.overflowY = 'auto';
                slotsContent.style.opacity = '1';
                chevron.style.transform = 'rotate(180deg)';
                // Load slots when expanded for the first time
                if (allSlots.length === 0) {
                    loadTimeSlots();
                }
            } else {
                slotsContent.style.maxHeight = '0';
                slotsContent.style.overflowY = 'hidden';
                slotsContent.style.opacity = '0';
                chevron.style.transform = 'rotate(0deg)';
            }
        }

        async function loadTimeSlots() {
            try {
                const response = await fetch('/api/slots/manage');
                if (handleAuthError(response)) return;
                if (!response.ok) throw new Error('Failed to load slots');

                allSlots = await safeJson(response);
                displayTimeSlots(allSlots);
            } catch (error) {
                console.error('Error loading time slots:', error);
                document.getElementById('slotsManagement').innerHTML = `
                    <div style="padding: 2rem;">
                        <p style="color: var(--error); text-align: center;">Error loading time slots</p>
                    </div>
                `;
            }
        }

        function displayTimeSlots(slots) {
            const container = document.getElementById('slotsManagement');

            if (slots.length === 0) {
                container.innerHTML = '<div style="padding: 2rem;"><p style="text-align: center; color: var(--text-tertiary);">No time slots available</p></div>';
                return;
            }

            // Separate upcoming and past slots
            // Use UTC time for accurate comparison regardless of browser timezone
            const now = new Date();
            const nowUTC = now.getTime(); // Get milliseconds since epoch for accurate comparison

            const upcoming = slots.filter(s => {
                try {
                    const slotTime = new Date(s.datetime).getTime();
                    return slotTime > nowUTC;
                } catch (e) {
                    return false;
                }
            }).sort((a, b) => new Date(a.datetime) - new Date(b.datetime));

            const past = slots.filter(s => {
                try {
                    const slotTime = new Date(s.datetime).getTime();
                    return slotTime <= nowUTC;
                } catch (e) {
                    return true; // Treat parse errors as past slots
                }
            });

            const pastUnbooked = past.filter(s => !s.booked).length;

            container.innerHTML = `
                <div style="padding: 2rem;">
                    <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--surface); border-radius: 0.75rem; border: 1px solid var(--border);">
                        <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
                            <div>
                                <div style="font-size: 0.85rem; color: var(--text-tertiary);">Total Slots</div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">${slots.length}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.85rem; color: var(--text-tertiary);">Upcoming</div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #10B981;">${upcoming.length}</div>
                            </div>
                            <div>
                                <div style="font-size: 0.85rem; color: var(--text-tertiary);">Past Slots</div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-tertiary);">${past.length}</div>
                            </div>
                            ${pastUnbooked > 0 ? `
                            <div style="flex: 1; display: flex; align-items: center; justify-content: flex-end;">
                                <button data-action="cleanupOldSlots" style="padding: 0.75rem 1.5rem; background: #F59E0B; color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600;">
                                    Clean Up ${pastUnbooked} Old Slots
                                </button>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    <h3 style="margin-bottom: 1rem; color: var(--text-primary);">Upcoming Time Slots (${upcoming.length})</h3>
                    <div class="slots-grid-container">
                        ${upcoming.map((slot, index) => `
                            <div class="slot-card slot-card-hover ${slot.booked ? 'booked' : 'available'}" data-action="viewSlotDetails" data-index="${index}" style="cursor: pointer; transition: all 0.3s;">
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
                                    <span class="slot-status ${slot.booked ? 'booked' : 'available'}">
                                        ${slot.booked ? 'Booked' : 'Available'}
                                    </span>
                                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity: 0.5;">
                                        <circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>
                                    </svg>
                                </div>
                                <div class="slot-info">
                                    <div class="slot-day">${slot.day}</div>
                                    <div class="slot-date">${slot.date}</div>
                                    <div class="slot-time">${slot.time}</div>
                                    ${slot.booked ? `<div class="slot-booked-by">Booked by: ${slot.booked_by}</div>` : ''}
                                </div>
                                ${!slot.booked ? `
                                    <div class="slot-actions">
                                        <button data-action="deleteSlot" data-id="${slot.id}">
                                            Delete Slot
                                        </button>
                                    </div>
                                ` : ''}
                                <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--text-tertiary); text-align: center;">
                                    Click for details
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        function viewSlotDetails(index) {
            const slot = allSlots[index];

            // Create modal
            const modal = document.createElement('div');
            modal.className = 'admin-modal';
            modal.style.cssText = 'animation: fadeIn 0.3s ease;';

            // Format booking timestamp
            const bookingTimeDisplay = slot.booking_timestamp ?
                new Date(slot.booking_timestamp).toLocaleString('en-US', {
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }) : 'N/A';

            modal.innerHTML = `
                <div class="admin-modal-content" style="max-width: 600px;">
                    <div class="admin-modal-header">
                        <h2>Time Slot Details</h2>
                        <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary); font-size: 0.95rem;">
                            Complete slot information
                        </p>
                    </div>

                    <div class="admin-modal-body">
                        <!-- Status Banner -->
                        <div style="padding: 1rem; background: ${slot.booked ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%)' : 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)'}; border-radius: 0.75rem; margin-bottom: 1.5rem; border: 2px solid ${slot.booked ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'};">
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div style="width: 40px; height: 40px; border-radius: 50%; background: ${slot.booked ? 'linear-gradient(135deg, #EF4444, #DC2626)' : 'linear-gradient(135deg, #10B981, #059669)'}; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                                    ${slot.booked ?
                                        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><path d="M20 8v6M23 11h-6"></path></svg>' :
                                        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>'
                                    }
                                </div>
                                <div>
                                    <div style="font-weight: 700; font-size: 1.1rem; color: var(--text-primary); margin-bottom: 0.25rem;">
                                        ${slot.booked ? 'Booked' : 'Available'}
                                    </div>
                                    <div style="font-size: 0.85rem; color: var(--text-secondary);">
                                        ${slot.booked ? 'This slot is currently reserved' : 'This slot is open for booking'}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Date & Time Info -->
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1.5rem;">
                            <div style="background: var(--surface); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                                <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Day</div>
                                <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-primary);">${slot.day || 'N/A'}</div>
                            </div>
                            <div style="background: var(--surface); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                                <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Date</div>
                                <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-primary);">${slot.date || 'N/A'}</div>
                            </div>
                            <div style="background: var(--surface); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                                <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Time</div>
                                <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-primary);">${slot.time || 'N/A'}</div>
                            </div>
                            <div style="background: var(--surface); padding: 1rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                                <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Location</div>
                                <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-primary);">${slot.selected_room || slot.location || 'Not specified'}</div>
                            </div>
                        </div>

                        <!-- Tutor Info -->
                        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%); padding: 1rem; border-radius: 0.75rem; margin-bottom: 1.5rem; border: 1px solid rgba(99, 102, 241, 0.3);">
                            <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Tutor</div>
                            <div style="font-weight: 600; font-size: 1.1rem; color: var(--text-primary); margin-bottom: 0.25rem;">${slot.tutor_name || 'Unknown'}</div>
                            <div style="font-size: 0.85rem; color: var(--text-secondary);">ID: ${slot.tutor_id || 'N/A'}</div>
                        </div>

                        ${slot.booked ? `
                            <!-- Booking Details -->
                            <div style="background: var(--surface); padding: 1.25rem; border-radius: 0.75rem; border: 1px solid var(--border);">
                                <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-primary); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                        <circle cx="8.5" cy="7" r="4"></circle>
                                        <path d="M20 8v6M23 11h-6"></path>
                                    </svg>
                                    Booking Information
                                </div>
                                <div style="display: grid; gap: 0.75rem;">
                                    <div style="display: flex; justify-content: space-between; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);">
                                        <span style="color: var(--text-tertiary); font-size: 0.9rem;">Booked by:</span>
                                        <span style="font-weight: 600; color: var(--text-primary);">${slot.booked_by || 'Unknown'}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);">
                                        <span style="color: var(--text-tertiary); font-size: 0.9rem;">Booked email:</span>
                                        <span style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${slot.booked_by_email || 'N/A'}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="color: var(--text-tertiary); font-size: 0.9rem;">Booking time:</span>
                                        <span style="font-weight: 600; color: var(--text-primary); font-size: 0.85rem;">${bookingTimeDisplay}</span>
                                    </div>
                                </div>
                            </div>
                        ` : `
                            <div style="background: rgba(245, 158, 11, 0.05); padding: 1rem; border-radius: 0.75rem; border: 1px solid rgba(245, 158, 11, 0.3); text-align: center;">
                                <div style="font-size: 0.9rem; color: var(--text-secondary);">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline-block; vertical-align: middle; margin-right: 0.5rem;">
                                        <circle cx="12" cy="12" r="10"></circle>
                                        <line x1="12" y1="8" x2="12" y2="12"></line>
                                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                                    </svg>
                                    This slot is available for students to book
                                </div>
                            </div>
                        `}
                    </div>

                    <div class="admin-modal-footer">
                        <button class="btn-modal-cancel" data-action="closeModal">
                            Close
                        </button>
                        ${!slot.booked ? `
                            <button class="btn-modal-primary" style="background: linear-gradient(135deg, #EF4444, #DC2626);" data-action="confirmDeleteSlot" data-id="${slot.id}">
                                Delete Slot
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);
        }

        // Cache admin role and tutors list for instant modal loading
        let cachedAdminData = null;

        async function loadAdminDataIfNeeded() {
            if (cachedAdminData) return cachedAdminData;

            try {
                const statsResponse = await fetch('/api/statistics');
                const stats = await safeJson(statsResponse); if (!stats) return;

                const data = {
                    isSuperAdmin: stats.role === 'super_admin',
                    tutorName: stats.tutor_name || 'Tutor',
                    tutorsList: []
                };

                if (data.isSuperAdmin) {
                    const tutorsResponse = await fetch('/api/tutors');
                    const tutorsData = await safeJson(tutorsResponse); if (!tutorsData) return;
                    if (tutorsData.success) {
                        data.tutorsList = tutorsData.tutors;
                    }
                }

                cachedAdminData = data;
                return data;
            } catch (error) {
                console.error('Error loading admin data:', error);
                return {
                    isSuperAdmin: false,
                    tutorName: 'Tutor',
                    tutorsList: []
                };
            }
        }

        async function showGenerateSlotsModal() {
            // INSTANT: Show modal immediately with loading skeleton
            const modal = document.createElement('div');
            modal.className = 'admin-modal';

            modal.innerHTML = `
                <div class="admin-modal-content" style="max-width: 700px;">
                    <div class="admin-modal-header">
                        <h2>Generate Recurring Time Slots</h2>
                        <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary); font-size: 0.95rem;">
                            <div class="spinner" style="width: 16px; height: 16px; display: inline-block; vertical-align: middle;"></div>
                            Loading...
                        </p>
                    </div>
                    <div class="admin-modal-body" style="max-height: 70vh; overflow-y: auto; min-height: 200px; display: flex; align-items: center; justify-content: center;">
                        <div style="text-align: center;">
                            <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto 1rem;"></div>
                            <p style="color: var(--text-secondary);">Preparing form...</p>
                        </div>
                    </div>
                    <div class="admin-modal-footer">
                        <button class="btn-modal-cancel" data-action="closeModal">
                            Cancel
                        </button>
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);

            // BACKGROUND: Load data and update modal
            try {
                const data = await loadAdminDataIfNeeded();
                const { isSuperAdmin, tutorName, tutorsList } = data;

                const tutorSelectionHTML = isSuperAdmin ? `
                    <div class="admin-form-group" style="margin-bottom: 1.5rem;">
                        <label>Select Tutor</label>
                        <select id="selected_tutor" style="width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary); font-family: inherit; font-size: 1rem; cursor: pointer;">
                            <option value="">-- Select a tutor --</option>
                            ${tutorsList.map(tutor => `<option value="${tutor.id}">${tutor.name || tutor.id}</option>`).join('')}
                        </select>
                        <small class="admin-form-hint">Choose which tutor to generate slots for</small>
                    </div>
                ` : '';

                const modalTitle = isSuperAdmin ? 'Generate Recurring Time Slots' : 'Generate Your Recurring Time Slots';
                const modalSubtitle = isSuperAdmin ? 'Weekly Schedule Builder' : `${tutorName}'s Weekly Schedule Builder`;
                const modalDescription = isSuperAdmin ? 'Select a tutor and configure their weekly schedule.' : 'Select the days and times you\'re available for tutoring sessions.';

                modal.innerHTML = `
                    <div class="admin-modal-content" style="max-width: 700px;">
                        <div class="admin-modal-header">
                            <h2>${modalTitle}</h2>
                            <p style="margin: 0.5rem 0 0 0; color: var(--text-secondary); font-size: 0.95rem;">
                                ${modalSubtitle}
                            </p>
                        </div>

                        <div class="admin-modal-body" style="max-height: 70vh; overflow-y: auto;">
                            ${tutorSelectionHTML}

                            <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">
                                ${modalDescription}
                            </p>

                            <div style="display: flex; flex-direction: column; gap: 1.25rem; margin-bottom: 1.5rem;">
                                ${['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day, index) => `
                                    <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1rem;">
                                        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                                            <input type="checkbox" id="day_${index}" style="width: 18px; height: 18px; cursor: pointer;" data-action="toggleDayTimes" data-index="${index}">
                                            <label for="day_${index}" style="font-weight: 600; font-size: 1rem; color: var(--text-primary); cursor: pointer; flex: 1;">${day}</label>
                                        </div>
                                        <div id="times_${index}" style="display: none; padding-left: 1.75rem;">
                                            <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.75rem;" id="time_chips_${index}"></div>
                                            <div style="display: flex; gap: 0.5rem; align-items: center;">
                                                <input type="time" id="time_input_${index}" style="flex: 1; padding: 0.5rem; border: 1px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary); font-family: inherit;">
                                                <button data-action="addTimeSlot" data-index="${index}" type="button" style="padding: 0.5rem 1rem; background: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600; white-space: nowrap;">
                                                    + Add Time
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>

                            <div class="admin-form-group">
                                <label>How many weeks ahead?</label>
                                <input id="weeks_ahead" type="number" value="6" min="1" max="52" style="width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary); font-family: inherit;">
                                <small class="admin-form-hint">Generates slots for the next N weeks. Existing future slots will be preserved.</small>
                            </div>
                        </div>

                        <div class="admin-modal-footer">
                            <button class="btn-modal-cancel" data-action="closeModal">
                                Cancel
                            </button>
                            <button class="btn-modal-primary" data-action="generateRecurringSlots">
                                Generate Slots
                            </button>
                        </div>
                    </div>
                `;

                // Initialize time slot storage
                window.dayTimeslots = [[], [], [], [], [], [], []];  // One array for each day

            } catch (error) {
                console.error('Error loading generate slots modal:', error);
                modal.innerHTML = `
                    <div class="admin-modal-content">
                        <div class="admin-modal-header">
                            <h2>Error</h2>
                        </div>
                        <div class="admin-modal-body">
                            <p style="color: var(--danger);">Failed to load form. Please try again.</p>
                        </div>
                        <div class="admin-modal-footer">
                            <button class="btn-modal-cancel" data-action="closeModal">
                                Close
                            </button>
                        </div>
                    </div>
                `;
            }
        }

        function toggleDayTimes(dayIndex) {
            const checkbox = document.getElementById(`day_${dayIndex}`);
            const timesContainer = document.getElementById(`times_${dayIndex}`);

            if (checkbox.checked) {
                timesContainer.style.display = 'block';
            } else {
                timesContainer.style.display = 'none';
                // Clear times for this day
                window.dayTimeslots[dayIndex] = [];
                document.getElementById(`time_chips_${dayIndex}`).innerHTML = '';
            }
        }

        function addTimeSlot(dayIndex) {
            const timeInput = document.getElementById(`time_input_${dayIndex}`);
            const timeValue = timeInput.value;

            if (!timeValue) {
                alert('Please select a time');
                return;
            }

            // Parse time (format: HH:MM)
            const [hours, minutes] = timeValue.split(':').map(Number);

            // Check for duplicates
            const isDuplicate = window.dayTimeslots[dayIndex].some(([h, m]) => h === hours && m === minutes);
            if (isDuplicate) {
                alert('This time slot already exists for this day');
                return;
            }

            // Add to storage
            window.dayTimeslots[dayIndex].push([hours, minutes]);

            // Sort times chronologically
            window.dayTimeslots[dayIndex].sort((a, b) => {
                if (a[0] !== b[0]) return a[0] - b[0];
                return a[1] - b[1];
            });

            // Update display
            updateTimeChips(dayIndex);

            // Clear input
            timeInput.value = '';
        }

        function removeTimeSlot(dayIndex, timeIndex) {
            window.dayTimeslots[dayIndex].splice(timeIndex, 1);
            updateTimeChips(dayIndex);
        }

        function updateTimeChips(dayIndex) {
            const container = document.getElementById(`time_chips_${dayIndex}`);
            const times = window.dayTimeslots[dayIndex];

            container.innerHTML = times.map(([h, m], idx) => {
                const displayTime = formatTime12Hour(h, m);
                return `
                    <div style="display: inline-flex; align-items: center; gap: 0.5rem; background: var(--primary); color: white; padding: 0.4rem 0.75rem; border-radius: 1rem; font-size: 0.875rem; font-weight: 500;">
                        <span>${displayTime}</span>
                        <button data-action="removeTimeSlot" data-day-index="${dayIndex}" data-time-index="${idx}" type="button" class="remove-time-btn" style="background: none; border: none; color: white; cursor: pointer; padding: 0; width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; line-height: 1; opacity: 0.8;">
                            ×
                        </button>
                    </div>
                `;
            }).join('');
        }

        function formatTime12Hour(hours, minutes) {
            const period = hours >= 12 ? 'PM' : 'AM';
            const displayHours = hours % 12 || 12;
            const displayMinutes = minutes.toString().padStart(2, '0');
            return `${displayHours}:${displayMinutes} ${period}`;
        }

        async function generateRecurringSlots(modal) {
            const weeksAhead = parseInt(document.getElementById('weeks_ahead').value);

            if (weeksAhead < 1 || weeksAhead > 52) {
                alert('Please enter a number between 1 and 52 weeks');
                return;
            }

            // Build custom schedule from selected days and times
            const customSchedule = {};
            let hasAnySlots = false;

            for (let i = 0; i < 7; i++) {
                const checkbox = document.getElementById(`day_${i}`);
                if (checkbox && checkbox.checked) {
                    const times = window.dayTimeslots[i];
                    if (times && times.length > 0) {
                        customSchedule[i] = times;  // Monday=0, Tuesday=1, ..., Sunday=6
                        hasAnySlots = true;
                    }
                }
            }

            if (!hasAnySlots) {
                alert('Please select at least one day and add at least one time slot');
                return;
            }

            // Get the button and show loading state
            const button = modal.querySelector('.btn-modal-primary');
            const originalContent = button.innerHTML;
            button.classList.add('btn-loading');
            button.innerHTML = '<span style="display: inline-flex; align-items: center;"><span class="spinner"></span>Generating...</span>';

            try {
                // Get selected tutor if super_admin is using the modal
                const tutorSelect = document.getElementById('selected_tutor');
                const selectedTutorId = tutorSelect ? tutorSelect.value : null;
                const selectedTutorName = tutorSelect && tutorSelect.selectedIndex > 0
                    ? tutorSelect.options[tutorSelect.selectedIndex].text
                    : null;

                // If tutor selection exists but no tutor selected, show error
                if (tutorSelect && !selectedTutorId) {
                    alert('Please select a tutor to generate slots for');
                    button.classList.remove('btn-loading');
                    button.innerHTML = originalContent;
                    return;
                }

                const requestBody = {
                    weeks_ahead: weeksAhead,
                    schedule: customSchedule
                };

                // Add tutor_id and tutor_name if selected (for super_admin)
                if (selectedTutorId) {
                    requestBody.tutor_id = selectedTutorId;
                    requestBody.tutor_name = selectedTutorName;
                }

                const response = await fetch('/api/slots/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    alert(result.message || 'Slots generated successfully!');
                    modal.remove();
                    loadTimeSlots();
                } else {
                    alert('Error: ' + (result.message || 'Failed to generate slots'));
                    button.classList.remove('btn-loading');
                    button.innerHTML = originalContent;
                }
            } catch (error) {
                console.error('Error generating slots:', error);
                alert('Failed to generate time slots. Please try again.');
                button.classList.remove('btn-loading');
                button.innerHTML = originalContent;
            }
        }

        async function showAddSlotModal() {
            // INSTANT: Show modal immediately with loading skeleton
            const modal = document.createElement('div');
            modal.className = 'admin-modal';

            const now = new Date();
            const minDatetime = now.toISOString().slice(0, 16);

            modal.innerHTML = `
                <div class="admin-modal-content">
                    <div class="admin-modal-header">
                        <h2>Add New Time Slot</h2>
                    </div>
                    <div class="admin-modal-body" style="min-height: 150px; display: flex; align-items: center; justify-content: center;">
                        <div style="text-align: center;">
                            <div class="spinner" style="width: 32px; height: 32px; margin: 0 auto 0.75rem;"></div>
                            <p style="color: var(--text-secondary); font-size: 0.9rem;">Loading...</p>
                        </div>
                    </div>
                    <div class="admin-modal-footer">
                        <button class="btn-modal-cancel" data-action="closeModal">
                            Cancel
                        </button>
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);

            // BACKGROUND: Load data and update modal
            try {
                const data = await loadAdminDataIfNeeded();
                const { isSuperAdmin, tutorsList } = data;

                const tutorSelectionHTML = isSuperAdmin ? `
                    <div class="admin-form-group">
                        <label>Select Tutor</label>
                        <select id="selected_tutor_single" style="width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; background: var(--bg); color: var(--text-primary); font-family: inherit; font-size: 1rem; cursor: pointer;">
                            <option value="">-- Select a tutor --</option>
                            ${tutorsList.map(tutor => `<option value="${tutor.id}">${tutor.name || tutor.id}</option>`).join('')}
                        </select>
                        <small class="admin-form-hint">Choose which tutor to create this slot for</small>
                    </div>
                ` : '';

                modal.innerHTML = `
                    <div class="admin-modal-content">
                        <div class="admin-modal-header">
                            <h2>Add New Time Slot</h2>
                        </div>

                        <div class="admin-modal-body">
                            ${tutorSelectionHTML}

                            <div class="admin-form-group">
                                <label>Date and Time</label>
                                <input id="new_slot_datetime" type="datetime-local" min="${minDatetime}">
                                <small class="admin-form-hint">Select the date and time for the new time slot</small>
                            </div>
                        </div>

                        <div class="admin-modal-footer">
                            <button class="btn-modal-cancel" data-action="closeModal">
                                Cancel
                            </button>
                            <button class="btn-modal-primary" data-action="addNewSlot">
                                Add Time Slot
                            </button>
                        </div>
                    </div>
                `;
            } catch (error) {
                console.error('Error loading add slot modal:', error);
                modal.innerHTML = `
                    <div class="admin-modal-content">
                        <div class="admin-modal-header">
                            <h2>Error</h2>
                        </div>
                        <div class="admin-modal-body">
                            <p style="color: var(--danger);">Failed to load form. Please try again.</p>
                        </div>
                        <div class="admin-modal-footer">
                            <button class="btn-modal-cancel" data-action="closeModal">
                                Close
                            </button>
                        </div>
                    </div>
                `;
            }
        }

        async function addNewSlot(modal) {
            const datetimeElement = document.getElementById('new_slot_datetime');
            console.log('[ADD SLOT] Datetime element:', datetimeElement);
            console.log('[ADD SLOT] Datetime value:', datetimeElement ? datetimeElement.value : 'ELEMENT NOT FOUND');

            const datetimeInput = datetimeElement ? datetimeElement.value : '';

            if (!datetimeInput || datetimeInput.trim() === '') {
                console.error('[ADD SLOT] No datetime input provided');
                alert('Please select a date and time');
                return;
            }

            console.log('[ADD SLOT] Processing datetime:', datetimeInput);

            // Parse the datetime input
            // The datetime-local input format is: YYYY-MM-DDTHH:MM
            const [datePart, timePart] = datetimeInput.split('T');
            const [year, month, day] = datePart.split('-');
            const [hours, minutes] = timePart.split(':');
            
            const slotId = `${year}${month}${day}${hours}${minutes}`;
            
            // For display, create a Date object to get day name
            const slotDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), parseInt(hours), parseInt(minutes));
            const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            
            const dayName = dayNames[slotDate.getDay()];
            const monthName = monthNames[slotDate.getMonth()];
            const dateStr = `${monthName} ${day}, ${year}`;
            
            // Format time as 12-hour format
            const hourNum = parseInt(hours);
            const period = hourNum >= 12 ? 'PM' : 'AM';
            const display12Hour = hourNum === 0 ? 12 : (hourNum > 12 ? hourNum - 12 : hourNum);
            const timeStr = `${String(display12Hour).padStart(2, '0')}:${minutes} ${period}`;

            // Send the raw components to the server; server will interpret as Eastern time
            const slotData = {
                id: slotId,
                datetime: datetimeInput,  // Send in format YYYY-MM-DDTHH:MM
                day: dayName,
                date: dateStr,
                time: timeStr,
                booked: false,
                booked_by: null,
                room: null
            };

            // Get selected tutor if super_admin is using the modal
            const tutorSelect = document.getElementById('selected_tutor_single');
            if (tutorSelect) {
                const selectedTutorId = tutorSelect.value;
                if (!selectedTutorId) {
                    alert('Please select a tutor to create this slot for');
                    return;
                }
                slotData.tutor_id = selectedTutorId;
                // Get the tutor name from the selected option text
                if (tutorSelect.selectedIndex > 0) {
                    slotData.tutor_name = tutorSelect.options[tutorSelect.selectedIndex].text;
                }
            }

            // Get the button and show loading state
            const button = modal.querySelector('.btn-modal-primary');
            const originalContent = button.innerHTML;
            button.classList.add('btn-loading');
            button.innerHTML = '<span style="display: inline-flex; align-items: center;"><span class="spinner"></span>Adding...</span>';

            try {
                const response = await fetch('/api/slots/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(slotData)
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    alert('Time slot added successfully!');
                    modal.remove();
                    loadTimeSlots();
                } else {
                    alert('Error: ' + result.message);
                    button.classList.remove('btn-loading');
                    button.innerHTML = originalContent;
                }
            } catch (error) {
                console.error('Error adding time slot:', error);
                alert('Failed to add time slot');
                button.classList.remove('btn-loading');
                button.innerHTML = originalContent;
            }
        }

        async function cleanupOldSlots(event) {
            if (!confirm('This will delete ALL past time slots (both booked and unbooked). Continue?')) {
                return;
            }

            // Get the button and show loading state
            const button = event.target;
            const originalContent = button.innerHTML;
            button.classList.add('btn-loading');
            button.innerHTML = '<span style="display: inline-flex; align-items: center;"><span class="spinner" style="border-color: rgba(0, 0, 0, 0.3); border-top-color: #F59E0B;"></span>Cleaning...</span>';

            try {
                const response = await fetch('/api/slots/cleanup', {
                    method: 'POST'
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    alert(result.message);
                    loadTimeSlots();
                } else {
                    alert('Error: ' + result.message);
                    button.classList.remove('btn-loading');
                    button.innerHTML = originalContent;
                }
            } catch (error) {
                console.error('Error cleaning up slots:', error);
                alert('Failed to clean up slots');
                button.classList.remove('btn-loading');
                button.innerHTML = originalContent;
            }
        }

        async function deleteSlot(slotId) {
            if (!confirm('Are you sure you want to delete this time slot?')) {
                return;
            }

            try {
                const response = await fetch(`/api/slots/${slotId}`, {
                    method: 'DELETE'
                });

                const result = await safeJson(response); if (!result) return;

                if (response.ok && result.success) {
                    alert('Time slot deleted successfully!');
                    loadTimeSlots();
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                console.error('Error deleting time slot:', error);
                alert('Failed to delete time slot');
            }
        }

        // Bulk Delete Modal Functions
        function showBulkDeleteModal() {
            const modal = document.createElement('div');
            modal.className = 'admin-modal';

            modal.innerHTML = `
                <div class="admin-modal-content">
                    <div class="admin-modal-header">
                        <h2>Bulk Delete Time Slots</h2>
                    </div>

                    <div class="admin-modal-body">
                        <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">
                            Choose how you want to delete multiple slots:
                        </p>

                        <div style="display: flex; gap: 1rem; margin-bottom: 2rem;">
                            <button data-action="switchDeleteMode" data-mode="last_weeks" id="btn-last-weeks" style="flex: 1; padding: 1rem; border: 2px solid var(--primary); background: var(--primary); color: white; border-radius: 0.75rem; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                                Delete Last N Weeks
                            </button>
                            <button data-action="switchDeleteMode" data-mode="select" id="btn-select" style="flex: 1; padding: 1rem; border: 2px solid var(--border); background: transparent; color: var(--text-primary); border-radius: 0.75rem; cursor: pointer; font-weight: 600; transition: all 0.3s;">
                                Select Individually
                            </button>
                        </div>

                        <div id="delete-mode-content">
                            <div id="last-weeks-mode">
                                <div class="admin-form-group">
                                    <label>Delete slots after how many weeks from now?</label>
                                    <input id="delete_weeks" type="number" value="6" min="1" max="52">
                                    <small class="admin-form-hint">Example: Enter "6" to delete all slots that are more than 6 weeks away</small>
                                </div>
                            </div>

                            <div id="select-mode" style="display: none;">
                                <p style="margin-bottom: 1rem; color: var(--text-secondary);">Loading available slots...</p>
                                <div id="selectable-slots" style="max-height: 400px; overflow-y: auto; border: 2px solid var(--border); border-radius: 0.75rem; padding: 1rem;">
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="admin-modal-footer">
                        <button class="btn-modal-cancel" data-action="closeModal">
                            Cancel
                        </button>
                        <button class="btn-modal-primary" style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);" data-action="executeBulkDelete">
                            Delete Slots
                        </button>
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);
            loadSelectableSlots();
        }

        let currentDeleteMode = 'last_weeks';

        function switchDeleteMode(mode) {
            currentDeleteMode = mode;

            const btnLastWeeks = document.getElementById('btn-last-weeks');
            const btnSelect = document.getElementById('btn-select');
            const lastWeeksDiv = document.getElementById('last-weeks-mode');
            const selectDiv = document.getElementById('select-mode');

            if (mode === 'last_weeks') {
                btnLastWeeks.style.background = 'var(--primary)';
                btnLastWeeks.style.color = 'white';
                btnSelect.style.background = 'transparent';
                btnSelect.style.color = 'var(--text-primary)';
                lastWeeksDiv.style.display = 'block';
                selectDiv.style.display = 'none';
            } else {
                btnSelect.style.background = 'var(--primary)';
                btnSelect.style.color = 'white';
                btnLastWeeks.style.background = 'transparent';
                btnLastWeeks.style.color = 'var(--text-primary)';
                selectDiv.style.display = 'block';
                lastWeeksDiv.style.display = 'none';
            }
        }

        async function loadSelectableSlots() {
            try {
                const response = await fetch('/api/slots/manage');
                const slots = await safeJson(response); if (!slots) return;

                const now = new Date();
                const availableSlots = slots.filter(s => !s.booked && new Date(s.datetime) > now)
                    .sort((a, b) => new Date(a.datetime) - new Date(b.datetime));

                const container = document.getElementById('selectable-slots');

                if (availableSlots.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: var(--text-tertiary);">No available slots to delete</p>';
                    return;
                }

                container.innerHTML = availableSlots.map(slot => `
                    <div style="padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.5rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.75rem; transition: all 0.3s;">
                        <input type="checkbox" value="${slot.id}" class="slot-checkbox" style="width: 18px; height: 18px; cursor: pointer;">
                        <div style="flex: 1;">
                            <div style="font-weight: 600;">${slot.day}, ${slot.date}</div>
                            <div style="font-size: 0.9rem; color: var(--text-secondary);">${slot.time}</div>
                        </div>
                    </div>
                `).join('');

            } catch (error) {
                console.error('Error loading slots:', error);
                document.getElementById('selectable-slots').innerHTML = '<p style="color: var(--error);">Error loading slots</p>';
            }
        }

        async function executeBulkDelete(modal) {
            // Get the button and prepare loading state
            const button = modal.querySelector('.btn-modal-primary');
            const originalContent = button.innerHTML;

            if (currentDeleteMode === 'last_weeks') {
                const weeks = parseInt(document.getElementById('delete_weeks').value);

                if (weeks < 1) {
                    alert('Please enter a valid number of weeks');
                    return;
                }

                if (!confirm(`This will delete all unbooked slots that are more than ${weeks} weeks from now. Continue?`)) {
                    return;
                }

                // Show loading state
                button.classList.add('btn-loading');
                button.innerHTML = '<span style="display: inline-flex; align-items: center;"><span class="spinner"></span>Deleting...</span>';

                try {
                    const response = await fetch('/api/slots/delete-range', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: 'last_weeks', weeks: weeks })
                    });

                    const result = await safeJson(response); if (!result) return;

                    if (response.ok && result.success) {
                        alert(result.message);
                        modal.remove();
                        loadTimeSlots();
                    } else {
                        alert('Error: ' + result.message);
                        button.classList.remove('btn-loading');
                        button.innerHTML = originalContent;
                    }
                } catch (error) {
                    console.error('Error deleting slots:', error);
                    alert('Failed to delete slots');
                    button.classList.remove('btn-loading');
                    button.innerHTML = originalContent;
                }

            } else {
                const checkboxes = document.querySelectorAll('.slot-checkbox:checked');
                const slotIds = Array.from(checkboxes).map(cb => cb.value);

                if (slotIds.length === 0) {
                    alert('Please select at least one slot to delete');
                    return;
                }

                if (!confirm(`Delete ${slotIds.length} selected slot(s)?`)) {
                    return;
                }

                // Show loading state
                button.classList.add('btn-loading');
                button.innerHTML = '<span style="display: inline-flex; align-items: center;"><span class="spinner"></span>Deleting...</span>';

                try {
                    console.log('[BULK DELETE] Sending request with slot_ids:', slotIds);

                    const response = await fetch('/api/slots/bulk-delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ slot_ids: slotIds })
                    });

                    const result = await safeJson(response); if (!result) return;
                    console.log('[BULK DELETE] Response:', result);

                    if (response.ok && result.success) {
                        const msg = `✓ Successfully deleted ${result.deleted_count} of ${slotIds.length} slots`;
                        console.log('[BULK DELETE]', msg);
                        alert(msg);
                        modal.remove();
                        loadTimeSlots();
                    } else {
                        console.error('[BULK DELETE] Error:', result);
                        alert('Error: ' + (result.message || 'Failed to delete slots'));
                        button.classList.remove('btn-loading');
                        button.innerHTML = originalContent;
                    }
                } catch (error) {
                    console.error('Error deleting slots:', error);
                    alert('Failed to delete slots');
                    button.classList.remove('btn-loading');
                    button.innerHTML = originalContent;
                }
            }
        }

        async function loadFeedback() {
            try {
                const response = await fetch('/api/feedback');
                if (handleAuthError(response)) return;
                const feedbackList = await response.json();

                const tbody = document.getElementById('feedbackTable');
                tbody.innerHTML = '';

                if (feedbackList.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><p>No feedback received yet</p></td></tr>';
                    document.getElementById('feedbackSummary').innerHTML = '<div style="text-align: center; color: var(--text-tertiary); padding: 1rem;">No feedback data yet</div>';
                    return;
                }

                // Calculate and display summary stats
                displayFeedbackSummary(feedbackList);

                // Sort by timestamp, newest first
                feedbackList.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

                feedbackList.forEach((feedback, index) => {
                    const row = document.createElement('tr');

                    // Format rating as stars
                    const stars = '⭐'.repeat(feedback.rating);

                    // Format date
                    const date = new Date(feedback.timestamp);
                    const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});

                    // Truncate comments if too long
                    let comments = feedback.comments || 'No comments';
                    const fullComments = comments;
                    const maxLength = 100;
                    let isTruncated = false;
                    if (comments.length > maxLength) {
                        comments = comments.substring(0, maxLength) + '...';
                        isTruncated = true;
                    }

                    // Get user info
                    const userName = feedback.user_name || 'Unknown User';
                    const userEmail = feedback.user_email || 'N/A';

                    // Store feedback data for modal
                    row.dataset.feedbackIndex = index;

                    row.innerHTML = `
                        <td>
                            <div style="font-weight: 600; margin-bottom: 0.25rem;">${userName}</div>
                            <div style="font-size: 0.85rem; color: var(--text-secondary);">${userEmail}</div>
                        </td>
                        <td>
                            <span style="font-size: 1.25rem;">${stars}</span>
                            <span style="margin-left: 0.5rem; font-weight: 600;">${feedback.rating}/5</span>
                        </td>
                        <td style="max-width: 400px;">
                            <div style="white-space: normal; line-height: 1.5; ${isTruncated ? 'cursor: pointer; color: var(--primary);' : ''}" ${isTruncated ? `data-action="showFeedbackModal" data-feedback="${JSON.stringify(feedback).replace(/"/g, '&quot;')}" title="Click to view full feedback"` : ''}>${comments}${isTruncated ? ' <span style="color: var(--primary); font-weight: 600;">(click to view)</span>' : ''}</div>
                        </td>
                        <td style="white-space: nowrap;">${formattedDate}</td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading feedback:', error);
                const tbody = document.getElementById('feedbackTable');
                tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><p>Error loading feedback</p></td></tr>';
            }
        }

        // Display feedback summary statistics
        function displayFeedbackSummary(feedbackList) {
            const summaryDiv = document.getElementById('feedbackSummary');

            // Calculate stats
            const totalFeedback = feedbackList.length;
            const totalRating = feedbackList.reduce((sum, f) => sum + f.rating, 0);
            const averageRating = (totalRating / totalFeedback).toFixed(1);

            // Count by rating
            const ratingCounts = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
            feedbackList.forEach(f => {
                if (ratingCounts.hasOwnProperty(f.rating)) {
                    ratingCounts[f.rating]++;
                }
            });

            const fiveStarCount = ratingCounts[5];
            const fourStarCount = ratingCounts[4];
            const positiveCount = fiveStarCount + fourStarCount;
            const positivePercent = ((positiveCount / totalFeedback) * 100).toFixed(0);

            summaryDiv.innerHTML = `
                <div style="background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%); padding: 1.5rem; border-radius: 0.75rem; color: white;">
                    <div style="font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem;">Average Rating</div>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <div style="font-size: 2.5rem; font-weight: 700;">${averageRating}</div>
                        <div>
                            <div style="font-size: 1.5rem;">⭐</div>
                            <div style="font-size: 0.85rem; opacity: 0.9;">out of 5</div>
                        </div>
                    </div>
                </div>

                <div style="background: var(--bg); padding: 1.5rem; border-radius: 0.75rem; border: 2px solid var(--border);">
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Total Feedback</div>
                    <div style="font-size: 2rem; font-weight: 700; color: var(--text-primary);">${totalFeedback}</div>
                    <div style="font-size: 0.9rem; color: var(--text-tertiary); margin-top: 0.25rem;">sessions reviewed</div>
                </div>

                <div style="background: var(--bg); padding: 1.5rem; border-radius: 0.75rem; border: 2px solid var(--border);">
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">Positive Feedback</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #10B981;">${positivePercent}%</div>
                    <div style="font-size: 0.9rem; color: var(--text-tertiary); margin-top: 0.25rem;">${positiveCount} of ${totalFeedback} (4-5 stars)</div>
                </div>

                <div style="background: var(--bg); padding: 1.5rem; border-radius: 0.75rem; border: 2px solid var(--border);">
                    <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem;">Rating Breakdown</div>
                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                        ${[5, 4, 3, 2, 1].map(rating => {
                            const count = ratingCounts[rating];
                            const percentage = totalFeedback > 0 ? ((count / totalFeedback) * 100).toFixed(0) : 0;
                            return `
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    <div style="min-width: 60px; font-size: 0.9rem;">${'⭐'.repeat(rating)}</div>
                                    <div style="flex: 1; background: var(--border); height: 8px; border-radius: 4px; overflow: hidden;">
                                        <div style="background: linear-gradient(90deg, #6366F1, #8B5CF6); height: 100%; width: ${percentage}%; transition: width 0.3s;"></div>
                                    </div>
                                    <div style="min-width: 50px; text-align: right; font-size: 0.85rem; color: var(--text-secondary);">${count} (${percentage}%)</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
        }

        // Feedback modal functions
        function showFeedbackModal(feedback) {
            const modal = document.getElementById('feedbackModal');
            const userName = feedback.user_name || 'Unknown User';
            const userEmail = feedback.user_email || 'N/A';
            const stars = '⭐'.repeat(feedback.rating);
            const date = new Date(feedback.timestamp);
            const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            const comments = feedback.comments || 'No comments provided';

            document.getElementById('feedbackModalContent').innerHTML = `
                <div class="feedback-modal-header">
                    <div>
                        <h2 style="margin: 0 0 0.5rem 0; color: var(--text-primary);">Feedback Details</h2>
                        <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">${formattedDate}</p>
                    </div>
                    <button class="feedback-modal-close" data-action="closeFeedbackModal">×</button>
                </div>

                <div style="background: var(--bg); padding: 1.5rem; border-radius: 0.75rem; margin-bottom: 1.5rem;">
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">USER</label>
                        <div style="font-weight: 600; font-size: 1.1rem;">${userName}</div>
                        <div style="color: var(--text-secondary); font-size: 0.9rem;">${userEmail}</div>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">RATING</label>
                        <div>
                            <span style="font-size: 1.5rem;">${stars}</span>
                            <span style="margin-left: 0.75rem; font-weight: 700; font-size: 1.25rem; color: var(--primary);">${feedback.rating}/5</span>
                        </div>
                    </div>

                    <div>
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">COMMENTS</label>
                        <div style="line-height: 1.8; white-space: pre-wrap; color: var(--text-primary);">${comments}</div>
                    </div>
                </div>

                <button data-action="closeFeedbackModal" style="width: 100%; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                    Close
                </button>
            `;

            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeFeedbackModal() {
            const modal = document.getElementById('feedbackModal');
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }

        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('feedbackModal');
            if (e.target === modal) {
                closeFeedbackModal();
            }
        });

        // Load session overviews
        // Store overviews globally so we can access them by index
        let allOverviews = [];

        async function loadSessionOverviews() {
            try {
                const response = await fetch('/api/session-overviews');
                if (handleAuthError(response)) return;
                const overviews = await response.json();

                const tbody = document.getElementById('overviewsTable');
                tbody.innerHTML = '';

                if (overviews.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" class="empty-state"><p>No session overviews yet</p></td></tr>';
                    allOverviews = [];
                    return;
                }

                // Sort by created date, newest first
                overviews.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                allOverviews = overviews;

                overviews.forEach((overview, index) => {
                    const row = document.createElement('tr');

                    const userName = overview.user_name || 'Unknown';
                    const userEmail = overview.user_email || '';
                    const sessionDate = overview.session_date || 'N/A';

                    // Preview of notes
                    const notes = overview.enhanced_notes || overview.notes || 'No notes';
                    const maxLength = 80;
                    const preview = notes.length > maxLength ? notes.substring(0, maxLength) + '...' : notes;

                    const createdDate = new Date(overview.created_at);
                    const formattedCreated = createdDate.toLocaleDateString() + ' ' + createdDate.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});

                    row.innerHTML = `
                        <td>
                            <div style="font-weight: 600; margin-bottom: 0.25rem;">${userName}</div>
                            ${userEmail ? `<div style="font-size: 0.85rem; color: var(--text-secondary);">${userEmail}</div>` : ''}
                        </td>
                        <td style="white-space: nowrap;">${sessionDate}</td>
                        <td style="max-width: 300px;">
                            <div style="white-space: normal; line-height: 1.5;">${preview}</div>
                        </td>
                        <td style="white-space: nowrap;">${formattedCreated}</td>
                        <td>
                            <div style="display: flex; gap: 0.5rem;">
                                <button data-action="showOverviewModalByIndex" data-index="${index}" style="padding: 0.5rem 1rem; background: var(--primary); color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600; font-size: 0.85rem;">
                                    View Full
                                </button>
                                <button data-action="deleteOverview" data-booking-id="${overview.booking_id}" data-user-name="${userName}" style="padding: 0.5rem 1rem; background: #EF4444; color: white; border: none; border-radius: 0.5rem; cursor: pointer; font-weight: 600; font-size: 0.85rem;">
                                    Delete
                                </button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading session overviews:', error);
                const tbody = document.getElementById('overviewsTable');
                tbody.innerHTML = '<tr><td colspan="5" class="empty-state"><p>Error loading overviews</p></td></tr>';
            }
        }

        // Show overview modal by index
        function showOverviewModalByIndex(index) {
            if (allOverviews[index]) {
                showOverviewModal(allOverviews[index]);
            }
        }

        // Show overview modal
        function showOverviewModal(overview) {
            const modal = document.getElementById('overviewModal');
            const userName = overview.user_name || 'Unknown';
            const userEmail = overview.user_email || '';
            const sessionDate = overview.session_date || 'N/A';
            const createdDate = new Date(overview.created_at);
            const formattedCreated = createdDate.toLocaleDateString() + ' ' + createdDate.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});

            const rawNotes = overview.notes || '';
            const enhancedNotes = overview.enhanced_notes || '';

            document.getElementById('overviewModalContent').innerHTML = `
                <div class="feedback-modal-header">
                    <div>
                        <h2 style="margin: 0 0 0.5rem 0; color: var(--text-primary);">Session Overview</h2>
                        <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">${sessionDate}</p>
                    </div>
                    <button class="feedback-modal-close" data-action="closeOverviewModal">×</button>
                </div>

                <div style="background: var(--bg); padding: 1.5rem; border-radius: 0.75rem; margin-bottom: 1.5rem;">
                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">PARTICIPANT</label>
                        <div style="font-weight: 600; font-size: 1.1rem;">${userName}</div>
                        ${userEmail ? `<div style="color: var(--text-secondary); font-size: 0.9rem;">${userEmail}</div>` : ''}
                    </div>

                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">CREATED</label>
                        <div style="color: var(--text-primary);">${formattedCreated}</div>
                    </div>

                    ${enhancedNotes ? `
                    <div style="margin-bottom: ${rawNotes ? '1.5rem' : '0'};">
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">AI-ENHANCED SUMMARY (Sent to Student)</label>
                        <div style="background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); padding: 1rem; border-radius: 0.5rem; line-height: 1.8; white-space: pre-wrap; color: var(--text-primary);">${enhancedNotes}</div>
                    </div>
                    ` : ''}

                    ${rawNotes ? `
                    <div>
                        <label style="display: block; font-weight: 600; color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">RAW NOTES</label>
                        <div style="background: var(--bg); border: 1px solid var(--border); padding: 1rem; border-radius: 0.5rem; line-height: 1.8; white-space: pre-wrap; color: var(--text-primary);">${rawNotes}</div>
                    </div>
                    ` : ''}

                    ${!enhancedNotes && !rawNotes ? '<div style="color: var(--text-secondary); font-style: italic;">No notes recorded for this session</div>' : ''}
                </div>

                <button data-action="closeOverviewModal" style="width: 100%; padding: 0.875rem; background: var(--primary); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                    Close
                </button>
            `;

            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeOverviewModal() {
            const modal = document.getElementById('overviewModal');
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }

        // Delete overview
        async function deleteOverview(bookingId, userName) {
            if (!confirm(`Delete session overview for ${userName}?\n\nThis action cannot be undone.`)) {
                return;
            }

            try {
                const response = await fetch(`/api/session-overviews/${bookingId}`, {
                    method: 'DELETE'
                });

                if (handleAuthError(response)) return;
                const result = await response.json();

                if (response.ok && result.success) {
                    alert('Session overview deleted successfully');
                    loadSessionOverviews(); // Reload the list
                } else {
                    alert('Error: ' + (result.message || 'Failed to delete overview'));
                }
            } catch (error) {
                console.error('Error deleting overview:', error);
                alert('Error deleting overview. Please try again.');
            }
        }

        // Manual overview modal
        function showManualOverviewModal() {
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.7);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                padding: 1rem;
            `;

            modal.innerHTML = `
                <div style="background: var(--surface); border-radius: 1rem; max-width: 700px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 2rem;">
                    <h2 style="margin-bottom: 0.5rem; color: var(--text-primary);">Add Manual Session Overview</h2>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">For sessions you've already completed but didn't record at the time.</p>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Name *</label>
                        <input type="text" id="manualUserName" placeholder="John Doe" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.75rem; font-family: inherit; font-size: 0.95rem; background: var(--bg); color: var(--text-primary);">
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Email *</label>
                        <input type="email" id="manualUserEmail" placeholder="john@example.com" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.75rem; font-family: inherit; font-size: 0.95rem; background: var(--bg); color: var(--text-primary);">
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Session Date</label>
                        <input type="text" id="manualSessionDate" placeholder="Monday, Dec 18 at 2:00 PM" style="width: 100%; padding: 0.75rem; border: 2px solid var(--border); border-radius: 0.75rem; font-family: inherit; font-size: 0.95rem; background: var(--bg); color: var(--text-primary);">
                    </div>

                    <div style="margin-bottom: 1.5rem;">
                        <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">Session Notes *</label>
                        <textarea id="manualNotes" placeholder="What did you cover? What tools did you teach? What prompting techniques? What should they practice?..." style="width: 100%; min-height: 200px; padding: 1rem; border: 2px solid var(--border); border-radius: 0.75rem; font-family: inherit; font-size: 0.95rem; resize: vertical; background: var(--bg); color: var(--text-primary);"></textarea>
                    </div>

                    <div style="background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 0.75rem; padding: 1rem; margin-bottom: 1rem;">
                        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; margin: 0;">
                            <input type="checkbox" id="manualSkipAI" style="width: 18px; height: 18px; cursor: pointer;">
                            <span style="color: var(--text-primary); font-weight: 500;">Send without AI enhancement (use raw notes as-is)</span>
                        </label>
                        <small style="display: block; margin-top: 0.5rem; margin-left: 1.75rem; color: var(--text-tertiary);" id="manualAiEnhanceText">Notes will be enhanced with AI for better formatting</small>
                    </div>

                    <div style="background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 0.75rem; padding: 1rem; margin-bottom: 1.5rem;">
                        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; margin: 0;">
                            <input type="checkbox" id="manualSendEmail" style="width: 18px; height: 18px; cursor: pointer;">
                            <span style="color: var(--text-primary); font-weight: 500;">Send overview email to participant</span>
                        </label>
                        <small style="display: block; margin-top: 0.5rem; margin-left: 1.75rem; color: var(--text-tertiary);">If checked, the notes will be sent to their email</small>
                    </div>

                    <div style="display: flex; gap: 0.75rem;">
                        <button data-action="closeModal" style="flex: 1; padding: 0.875rem; background: var(--bg); border: 2px solid var(--border); border-radius: 0.75rem; cursor: pointer; font-weight: 600; color: var(--text-primary);">
                            Cancel
                        </button>
                        <button data-action="submitManualOverview" id="submitManualBtn" style="flex: 1; padding: 0.875rem; background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: white; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600; font-size: 1rem;">
                            Save Overview
                        </button>
                    </div>
                </div>
            `;

            modal.classList.add('dynamic-modal');
            document.body.appendChild(modal);
            document.getElementById('manualUserName').focus();

            // Add event listener for AI checkbox toggle
            document.getElementById('manualSkipAI').addEventListener('change', function() {
                const textElement = document.getElementById('manualAiEnhanceText');
                if (this.checked) {
                    textElement.textContent = 'Raw notes will be saved as-is (no AI formatting)';
                } else {
                    textElement.textContent = 'Notes will be enhanced with AI for better formatting';
                }
            });
        }

        async function submitManualOverview(modal) {
            const userName = document.getElementById('manualUserName').value.trim();
            const userEmail = document.getElementById('manualUserEmail').value.trim();
            const sessionDate = document.getElementById('manualSessionDate').value.trim();
            const notes = document.getElementById('manualNotes').value.trim();
            const sendEmail = document.getElementById('manualSendEmail').checked;
            const skipAI = document.getElementById('manualSkipAI').checked;
            const submitBtn = document.getElementById('submitManualBtn');

            // Validation
            if (!userName) {
                alert('Please enter student name');
                return;
            }
            if (!userEmail) {
                alert('Please enter student email');
                return;
            }
            if (!notes) {
                alert('Please enter session notes');
                return;
            }

            // Disable button
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span style="display: inline-flex; align-items: center; gap: 0.5rem;"><span class="spinner" style="border-width: 2px; width: 16px; height: 16px;"></span>Saving...</span>';

            try {
                const response = await fetch('/api/session-overviews/manual', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        user_name: userName,
                        user_email: userEmail,
                        session_date: sessionDate || 'Not specified',
                        notes: notes,
                        send_email: sendEmail,
                        skip_ai: skipAI
                    })
                });

                if (handleAuthError(response)) return;
                const result = await response.json();

                if (response.ok && result.success) {
                    modal.remove();
                    alert(`Overview saved successfully!${sendEmail ? '\\n✓ Email sent to student' : ''}`);
                    loadSessionOverviews();
                } else {
                    alert('Error: ' + (result.message || 'Failed to save overview'));
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Save Overview';
                }
            } catch (error) {
                console.error('Error saving manual overview:', error);
                alert('Failed to save overview: ' + error.message);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Save Overview';
            }
        }

        // Load everything on page load
        document.addEventListener('DOMContentLoaded', () => {
            loadUsers();
            // loadTimeSlots(); // Now loads only when section is expanded
            loadFeedback();
            loadSessionOverviews();
        });

// ============================================================================
// GLOBAL EVENT DELEGATION SYSTEM FOR CSP COMPLIANCE
// All dynamic buttons use data-action attributes instead of inline onclick
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Header Buttons
    document.getElementById('btn-home')?.addEventListener('click', function() {
        window.location.href = '/';
    });

    document.getElementById('btn-refresh')?.addEventListener('click', function() {
        loadUsers();
        loadTimeSlots();
    });

    document.getElementById('btn-export')?.addEventListener('click', function() {
        exportCSV();
    });

    document.getElementById('btn-logout')?.addEventListener('click', function() {
        logout();
    });

    // Slots Section
    document.getElementById('slots-header')?.addEventListener('click', function() {
        toggleSlotsSection();
    });

    document.getElementById('slotsActionButtons')?.addEventListener('click', function(event) {
        event.stopPropagation();
    });

    document.getElementById('btn-generate-slots')?.addEventListener('click', function() {
        showGenerateSlotsModal();
    });

    document.getElementById('btn-add-slot')?.addEventListener('click', function() {
        showAddSlotModal();
    });

    document.getElementById('btn-bulk-delete')?.addEventListener('click', function() {
        showBulkDeleteModal();
    });

    // Manual Overview
    document.getElementById('btn-manual-overview')?.addEventListener('click', function() {
        showManualOverviewModal();
    });

    // Global click event delegation for dynamically created elements
    document.body.addEventListener('click', function(e) {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        const index = target.dataset.index ? parseInt(target.dataset.index) : null;
        const id = target.dataset.id;
        const modal = target.closest('.dynamic-modal');

        switch (action) {
            // Booking actions
            case 'viewUserDetails':
                viewUserDetails(index);
                break;
            case 'editBooking':
                editBooking(index);
                break;
            case 'markComplete':
                markComplete(index);
                break;
            case 'deleteBooking':
                deleteBooking(index);
                break;

            // Modal close actions
            case 'closeModal':
                if (modal) modal.remove();
                break;

            // Session notes actions
            case 'previewSessionOverview':
                previewSessionOverview(index, modal);
                break;
            case 'submitSessionComplete':
                submitSessionComplete(index, modal);
                break;
            case 'regenerateOverview':
                const rawNotes = target.dataset.notes;
                regenerateOverview(index, rawNotes, modal);
                break;
            case 'submitWithEditedOverview':
                submitWithEditedOverview(index, modal);
                break;

            // Booking edit actions
            case 'saveBookingEdit':
                saveBookingEdit(id, modal);
                break;
            case 'closeDetailsModal':
                if (modal) modal.remove();
                break;
            case 'regenerateInsights':
                regenerateInsights(index);
                break;

            // Slot actions
            case 'viewSlotDetails':
                viewSlotDetails(index);
                break;
            case 'deleteSlot':
                deleteSlot(id);
                break;
            case 'confirmDeleteSlot':
                if (modal) modal.remove();
                deleteSlot(id);
                break;
            case 'cleanupOldSlots':
                cleanupOldSlots(e);
                break;
            case 'addTimeSlot':
                addTimeSlot(index);
                break;
            case 'removeTimeSlot':
                const dayIdx = parseInt(target.dataset.dayIndex);
                const timeIdx = parseInt(target.dataset.timeIndex);
                removeTimeSlot(dayIdx, timeIdx);
                break;
            case 'generateRecurringSlots':
                generateRecurringSlots(modal);
                break;
            case 'addNewSlot':
                addNewSlot(modal);
                break;
            case 'switchDeleteMode':
                const mode = target.dataset.mode;
                switchDeleteMode(mode);
                break;
            case 'executeBulkDelete':
                executeBulkDelete(modal);
                break;

            // Feedback actions
            case 'showFeedbackModal':
                const feedbackData = JSON.parse(target.dataset.feedback);
                showFeedbackModal(feedbackData);
                break;
            case 'closeFeedbackModal':
                closeFeedbackModal();
                break;

            // Overview actions
            case 'showOverviewModalByIndex':
                showOverviewModalByIndex(index);
                break;
            case 'deleteOverview':
                const bookingId = target.dataset.bookingId;
                const userName = target.dataset.userName;
                deleteOverview(bookingId, userName);
                break;
            case 'closeOverviewModal':
                closeOverviewModal();
                break;
            case 'submitManualOverview':
                submitManualOverview(modal);
                break;

            // Day time toggle
            case 'toggleDayTimes':
                toggleDayTimes(index);
                break;
        }
    });

    // Global change event delegation for checkboxes
    document.body.addEventListener('change', function(e) {
        const target = e.target;
        if (target.dataset.action === 'toggleDayTimes') {
            const index = parseInt(target.dataset.index);
            toggleDayTimes(index);
        }
    });

    // Global mouseover/mouseout for hover effects (slots)
    document.body.addEventListener('mouseover', function(e) {
        const slotCard = e.target.closest('.slot-card-hover');
        if (slotCard) {
            slotCard.style.transform = 'translateY(-4px)';
            slotCard.style.boxShadow = '0 8px 20px rgba(0,0,0,0.15)';
        }
        const removeBtn = e.target.closest('.remove-time-btn');
        if (removeBtn) {
            removeBtn.style.opacity = '1';
        }
    });

    document.body.addEventListener('mouseout', function(e) {
        const slotCard = e.target.closest('.slot-card-hover');
        if (slotCard) {
            slotCard.style.transform = 'none';
            slotCard.style.boxShadow = '';
        }
        const removeBtn = e.target.closest('.remove-time-btn');
        if (removeBtn) {
            removeBtn.style.opacity = '0.8';
        }
    });
});

