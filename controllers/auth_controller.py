from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.user import User, Admin, Faculty, Student
from models.notification import Notification

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash("Access denied: You do not have permission to view this resource.", "danger")
                # Redirect to appropriate role dashboard
                if user_role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user_role == 'faculty':
                    return redirect(url_for('faculty.dashboard'))
                elif user_role == 'student':
                    return redirect(url_for('student.dashboard'))
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'faculty':
            return redirect(url_for('faculty.dashboard'))
        elif role == 'student':
            return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template('auth/login.html')

        user = User.get_by_username_or_email(identifier)
        if not user or not user.verify_password(password):
            flash("Invalid credentials. Please verify your username and password.", "danger")
            return render_template('auth/login.html')

        if not user.is_active:
            flash("Your account has been deactivated. Please contact administrator.", "danger")
            return render_template('auth/login.html')

        # Set session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['full_name'] = user.full_name
        session['email'] = user.email

        flash(f"Welcome back, {user.full_name}!", "success")

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        return redirect(url_for(user.get_dashboard_route()))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))
