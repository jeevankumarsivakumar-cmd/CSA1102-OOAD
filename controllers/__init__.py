from .auth_controller import auth_bp, login_required, role_required
from .admin_controller import admin_bp
from .faculty_controller import faculty_bp
from .student_controller import student_bp
from .analytics_controller import analytics_bp
from .report_controller import report_bp

__all__ = [
    'auth_bp', 'login_required', 'role_required',
    'admin_bp', 'faculty_bp', 'student_bp',
    'analytics_bp', 'report_bp'
]
