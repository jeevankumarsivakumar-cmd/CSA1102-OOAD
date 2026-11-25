import os
from flask import Flask, redirect, url_for, session, render_template
from config import Config
from database.db import db
from models.user import User
from models.notification import Notification

from controllers.auth_controller import auth_bp
from controllers.admin_controller import admin_bp
from controllers.faculty_controller import faculty_bp
from controllers.student_controller import student_bp
from controllers.analytics_controller import analytics_bp
from controllers.report_controller import report_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure required directories exist
    os.makedirs(Config.REPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static', 'images'), exist_ok=True)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(report_bp)

    @app.route('/')
    def index():
        if 'user_id' in session:
            role = session.get('role')
            if role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif role == 'faculty':
                return redirect(url_for('faculty.dashboard'))
            elif role == 'student':
                return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    # Context processors for global template access
    @app.context_processor
    def inject_global_context():
        user = None
        unread_count = 0
        if 'user_id' in session:
            user = User.get_by_id(session['user_id'])
            unread_count = Notification.get_unread_count(session['user_id'])

        return {
            'current_user': user,
            'unread_notif_count': unread_count,
            'active_role': session.get('role'),
            'db_engine': db.get_engine_name()
        }

    # Template filters
    @app.template_filter('badge_status')
    def badge_status_filter(status):
        if status == 'Present':
            return '<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-check-circle-fill me-1"></i>Present</span>'
        elif status == 'Absent':
            return '<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1"><i class="bi bi-x-circle-fill me-1"></i>Absent</span>'
        elif status == 'On Duty':
            return '<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1"><i class="bi bi-briefcase-fill me-1"></i>On Duty</span>'
        return f'<span class="badge bg-secondary">{status}</span>'

    @app.template_filter('badge_risk')
    def badge_risk_filter(category):
        if category == 'Good Performance':
            return '<span class="badge bg-success-subtle text-success border border-success-subtle px-3 py-1 fw-semibold"><i class="bi bi-shield-check me-1"></i>Good Performance</span>'
        elif category == 'Average Performance':
            return '<span class="badge bg-warning-subtle text-warning border border-warning-subtle px-3 py-1 fw-semibold"><i class="bi bi-exclamation-triangle me-1"></i>Average Performance</span>'
        elif category == 'Needs Improvement':
            return '<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-1 fw-semibold"><i class="bi bi-exclamation-diamond me-1"></i>Needs Improvement</span>'
        return f'<span class="badge bg-secondary">{category}</span>'

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', not_found=True), 404

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    print(f"[*] Starting AI-Powered Student Attendance and Academic Analytics System on {host}:{port}...")
    print(f"[*] Database Engine: {db.get_engine_name()}")
    app.run(host=host, port=port, debug=debug)
