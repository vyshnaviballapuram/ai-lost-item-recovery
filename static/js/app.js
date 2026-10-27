/**
 * AI-Based Campus Lost-Item Recovery System
 * Frontend UI JavaScript Client
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Bootstrap Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map((el) => new bootstrap.Tooltip(el));

    // 2. Auto-dismiss flash messages after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // 3. Mark notification as read via AJAX
    document.querySelectorAll('.btn-mark-notification-read').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const notifId = btn.getAttribute('data-notif-id');
            const targetUrl = btn.getAttribute('href');

            try {
                const response = await fetch(`/notifications/read/${notifId}/`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                if (response.ok) {
                    const row = document.getElementById(`notif-row-${notifId}`);
                    if (row) {
                        row.classList.remove('bg-surface-elevated');
                        row.style.opacity = '0.7';
                    }
                    if (targetUrl && targetUrl !== '#') {
                        window.location.href = targetUrl;
                    }
                }
            } catch (err) {
                console.error("Failed to mark notification read", err);
            }
        });
    });
});
