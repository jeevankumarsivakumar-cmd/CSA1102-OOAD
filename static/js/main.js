// =====================================================================
// AI-POWERED STUDENT ATTENDANCE AND ACADEMIC ANALYTICS SYSTEM
// Core Client JavaScript Interactions
// =====================================================================

document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });
    }

    // 2. Auto-dismiss Bootstrap Alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // 3. Quick Role Autofill for Login Screen
    const roleButtons = document.querySelectorAll('.quick-role-btn');
    const identifierInput = document.getElementById('identifier');
    const passwordInput = document.getElementById('password');

    roleButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const role = this.getAttribute('data-role');
            if (role === 'admin') {
                if (identifierInput) identifierInput.value = 'admin';
                if (passwordInput) passwordInput.value = 'admin123';
            } else if (role === 'faculty') {
                if (identifierInput) identifierInput.value = 'faculty1';
                if (passwordInput) passwordInput.value = 'faculty123';
            } else if (role === 'student') {
                if (identifierInput) identifierInput.value = 'student1';
                if (passwordInput) passwordInput.value = 'student123';
            } else if (role === 'student_risk') {
                if (identifierInput) identifierInput.value = 'student3';
                if (passwordInput) passwordInput.value = 'student123';
            }
            // Highlight selected button
            roleButtons.forEach(b => b.classList.remove('border-primary', 'bg-light'));
            this.classList.add('border-primary', 'bg-light');
        });
    });

    // 4. Attendance Bulk Actions
    const markAllPresentBtn = document.getElementById('btnMarkAllPresent');
    const markAllAbsentBtn = document.getElementById('btnMarkAllAbsent');

    if (markAllPresentBtn) {
        markAllPresentBtn.addEventListener('click', function () {
            const presentRadios = document.querySelectorAll('input[type="radio"][value="Present"]');
            presentRadios.forEach(radio => radio.checked = true);
        });
    }

    if (markAllAbsentBtn) {
        markAllAbsentBtn.addEventListener('click', function () {
            const absentRadios = document.querySelectorAll('input[type="radio"][value="Absent"]');
            absentRadios.forEach(radio => radio.checked = true);
        });
    }

    // 5. In-App Notification Read Marker via Fetch
    const markReadButtons = document.querySelectorAll('.btn-mark-read');
    markReadButtons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const notifId = this.getAttribute('data-id');
            const card = document.getElementById(`notif-card-${notifId}`);
            
            fetch(`/student/notifications/read/${notifId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && card) {
                    card.classList.remove('border-primary');
                    card.classList.add('opacity-75');
                    btn.remove();
                }
            })
            .catch(err => console.error('Failed to mark notification read:', err));
        });
    });
});
