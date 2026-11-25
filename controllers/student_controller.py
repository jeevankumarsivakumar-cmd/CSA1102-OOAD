import math
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import db
from services.attendance_service import AttendanceService
from services.prediction_service import PredictionService
from services.notification_service import NotificationService
from models.notification import Notification
from models.intervention import FacultyIntervention
from models.improvement_plan import StudentImprovementGoal, AcademicImprovementService
from controllers.auth_controller import login_required, role_required

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
@login_required
@role_required(['student'])
def check_student_access():
    pass

def get_current_student():
    user_id = session.get('user_id')
    sql = """
        SELECT s.*, u.full_name, u.email, u.phone, u.avatar, c.class_code, c.room_number, c.semester
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN classes c ON s.class_id = c.id
        WHERE s.user_id = %s
    """
    return db.query(sql, (user_id,), fetchone=True)

@student_bp.route('/dashboard')
def dashboard():
    student = get_current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for('auth.login'))

    student_id = student['id']

    # 1. Overall attendance metrics
    att_stats = AttendanceService.calculate_student_attendance(student_id)

    # 2. Subject-wise attendance breakdown
    subject_attendance = AttendanceService.get_subject_wise_attendance(student_id)

    # 3. Academic marks summary
    academic_marks = db.query("""
        SELECT m.*, s.subject_code, s.subject_name
        FROM academic_marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = %s
        ORDER BY m.exam_date DESC
        LIMIT 6
    """, (student_id,))

    # 4. Absence history
    absence_history = AttendanceService.get_student_absence_history(student_id, limit=6)

    # 5. Recent notifications
    notifications = Notification.get_for_user(student['user_id'], limit=5)

    # 6. AI Performance Insights
    prediction = PredictionService.get_latest_student_prediction(student_id)

    # Generate tailored recommendations based on risk classification
    recommendations = []
    category = prediction.get('risk_category')
    att_pct = att_stats['attendance_percentage']
    
    if att_pct < 75.0:
        recommendations.append("Priority: Attend all upcoming classes without absence to restore your attendance to at least 75%.")
    if category == 'Needs Improvement':
        recommendations.append("Schedule a 1-on-1 counseling session with your faculty mentor for personalized subject guidance.")
        recommendations.append("Join peer study groups in library Block B every Tuesday and Thursday.")
    elif category == 'Average Performance':
        recommendations.append("Focus on improving internal test scores in subjects where your score is below 70%.")
        recommendations.append("Solve previous question papers to raise your GPA towards Good Performance.")
    else:
        recommendations.append("Outstanding performance! You are eligible to apply for Academic Honors and Department Research fellowships.")

    return render_template(
        'student/dashboard.html',
        student=student,
        att_stats=att_stats,
        subject_attendance=subject_attendance,
        academic_marks=academic_marks,
        absence_history=absence_history,
        notifications=notifications,
        prediction=prediction,
        recommendations=recommendations
    )

@student_bp.route('/attendance')
def attendance():
    student = get_current_student()
    student_id = student['id']

    att_stats = AttendanceService.calculate_student_attendance(student_id)
    subject_attendance = AttendanceService.get_subject_wise_attendance(student_id)
    all_absences = AttendanceService.get_student_absence_history(student_id, limit=100)

    # Full attendance log for transparency
    attendance_log = db.query("""
        SELECT a.*, s.subject_code, s.subject_name, u.full_name as faculty_name
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.id
        JOIN faculty f ON a.faculty_id = f.id
        JOIN users u ON f.user_id = u.id
        WHERE a.student_id = %s
        ORDER BY a.attendance_date DESC, a.recorded_at DESC
        LIMIT 60
    """, (student_id,))

    return render_template(
        'student/attendance.html',
        student=student,
        att_stats=att_stats,
        subject_attendance=subject_attendance,
        all_absences=all_absences,
        attendance_log=attendance_log
    )

@student_bp.route('/marks')
def marks():
    student = get_current_student()
    student_id = student['id']

    all_marks = db.query("""
        SELECT m.*, s.subject_code, s.subject_name, s.credits, u.full_name as faculty_name
        FROM academic_marks m
        JOIN subjects s ON m.subject_id = s.id
        JOIN faculty f ON m.entered_by = f.id
        JOIN users u ON f.user_id = u.id
        WHERE m.student_id = %s
        ORDER BY s.subject_code, m.exam_type
    """, (student_id,))

    # Calculate average marks percentage
    avg_marks = 0.0
    if all_marks:
        avg_marks = round(sum((m['marks_obtained'] / m['max_marks']) * 100 for m in all_marks) / len(all_marks), 1)

    return render_template('student/marks.html', student=student, all_marks=all_marks, avg_marks=avg_marks)

@student_bp.route('/notifications')
def notifications():
    student = get_current_student()
    notifs = Notification.get_for_user(student['user_id'], limit=50)
    return render_template('student/notifications.html', student=student, notifications=notifs)

@student_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
def mark_notification_read(notif_id):
    user_id = session.get('user_id')
    Notification.mark_as_read(notif_id, user_id=user_id)
    return jsonify({'success': True})

@student_bp.route('/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    user_id = session.get('user_id')
    Notification.mark_all_as_read(user_id=user_id)
    flash("All notifications marked as read.", "success")
    return redirect(url_for('student.notifications'))

# =====================================================================
# FEATURE 1: SMART ATTENDANCE RECOVERY SIMULATOR
# =====================================================================
@student_bp.route('/recovery-planner')
def recovery_planner():
    student = get_current_student()
    student_id = student['id']
    att_stats = AttendanceService.calculate_student_attendance(student_id)

    curr_pct = att_stats['attendance_percentage']
    attended = att_stats['attended_count']
    total = att_stats['total_conducted']

    # Pre-calculate targets: 75%, 80%, 85%, 90%
    targets = [75, 80, 85, 90]
    recovery_cards = []

    for t_pct in targets:
        t_decimal = t_pct / 100.0
        if total == 0:
            req = 0
            is_met = False
        elif curr_pct >= t_pct:
            req = 0
            is_met = True
        else:
            # Formula: (Target percentage × Total classes - Classes attended) / (1 - Target percentage)
            numerator = (t_decimal * total) - attended
            denominator = 1.0 - t_decimal
            req = max(0, math.ceil(numerator / denominator))
            is_met = False

        recovery_cards.append({
            'target_pct': t_pct,
            'is_met': is_met,
            'required_classes': req,
            'new_total_classes': total + req,
            'new_attended_classes': attended + req
        })

    return render_template(
        'student/recovery_planner.html',
        student=student,
        att_stats=att_stats,
        attended=attended,
        total=total,
        curr_pct=curr_pct,
        recovery_cards=recovery_cards
    )

@student_bp.route('/api/simulate-recovery', methods=['POST'])
def api_simulate_recovery():
    """Interactive JSON API for client-side Attendance Recovery graph projection."""
    student = get_current_student()
    student_id = student['id']
    att_stats = AttendanceService.calculate_student_attendance(student_id)

    data = request.get_json() or {}
    try:
        target_pct = float(data.get('target_pct', 75))
    except (ValueError, TypeError):
        target_pct = 75.0

    target_pct = max(50.0, min(99.0, target_pct))
    t_decimal = target_pct / 100.0

    attended = att_stats['attended_count']
    total = att_stats['total_conducted']
    curr_pct = att_stats['attendance_percentage']

    if total == 0:
        req = 0
    elif curr_pct >= target_pct:
        req = 0
    else:
        req = max(0, math.ceil(((t_decimal * total) - attended) / (1.0 - t_decimal)))

    # Generate simulation trajectory data points
    labels = ["Current"]
    percentages = [curr_pct]
    target_line = [target_pct]

    sim_attended = attended
    sim_total = total
    buffer_steps = max(req + 3, 5)

    for step in range(1, buffer_steps + 1):
        sim_attended += 1
        sim_total += 1
        proj_pct = round((sim_attended / sim_total) * 100, 2)
        labels.append(f"+{step} Class" if step == 1 else f"+{step} Classes")
        percentages.append(proj_pct)
        target_line.append(target_pct)

    return jsonify({
        'status': 'success',
        'current_pct': curr_pct,
        'target_pct': target_pct,
        'classes_attended': attended,
        'total_classes': total,
        'required_consecutive_classes': req,
        'already_met': curr_pct >= target_pct,
        'trajectory': {
            'labels': labels,
            'percentages': percentages,
            'target_line': target_line
        }
    })

# =====================================================================
# FEATURE 2: AI PERSONALIZED ACADEMIC IMPROVEMENT PLANNER
# =====================================================================
@student_bp.route('/improvement-plan')
def improvement_plan():
    student = get_current_student()
    student_id = student['id']

    # Gather comprehensive metrics
    att_stats = AttendanceService.calculate_student_attendance(student_id)
    marks_list = db.query("""
        SELECT m.*, s.subject_code, s.subject_name
        FROM academic_marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = %s
        ORDER BY m.exam_date DESC
    """, (student_id,))

    prediction = PredictionService.get_latest_student_prediction(student_id)

    # Generate tailored, grounded improvement plan
    plan = AcademicImprovementService.generate_plan(student_id, att_stats, marks_list, prediction)

    # Active weekly student improvement goals
    student_goals = StudentImprovementGoal.get_for_student(student_id)

    # Faculty mentoring interventions assigned to this student
    assigned_interventions = FacultyIntervention.get_for_student(student_id)

    return render_template(
        'student/improvement_plan.html',
        student=student,
        att_stats=att_stats,
        prediction=prediction,
        plan=plan,
        student_goals=student_goals,
        assigned_interventions=assigned_interventions
    )

@student_bp.route('/api/goals/toggle/<int:goal_id>', methods=['POST'])
def toggle_goal(goal_id):
    student = get_current_student()
    new_status = StudentImprovementGoal.toggle_completion(goal_id, student_id=student['id'])
    if new_status is None:
        return jsonify({'status': 'error', 'message': 'Goal not found'}), 404
    return jsonify({'status': 'success', 'is_completed': new_status})

@student_bp.route('/api/goals/add', methods=['POST'])
def add_goal():
    student = get_current_student()
    title = request.form.get('goal_title', '').strip()
    category = request.form.get('goal_category', 'Study Routine')
    target_date = request.form.get('target_date')

    if not title:
        flash("Goal title cannot be empty.", "warning")
        return redirect(url_for('student.improvement_plan'))

    StudentImprovementGoal.create(student['id'], title, category, target_date or None)
    flash("New academic goal added successfully!", "success")
    return redirect(url_for('student.improvement_plan'))

@student_bp.route('/api/goals/delete/<int:goal_id>', methods=['POST'])
def delete_goal(goal_id):
    student = get_current_student()
    StudentImprovementGoal.delete(goal_id, student_id=student['id'])
    flash("Goal removed.", "info")
    return redirect(url_for('student.improvement_plan'))

# =====================================================================
# FEATURE 4: ACADEMIC PERFORMANCE TREND ANALYTICS
# =====================================================================
@student_bp.route('/performance-journey')
def performance_journey():
    student = get_current_student()
    student_id = student['id']

    # 1. Subject marks breakdown for charts
    marks = db.query("""
        SELECT m.exam_type, m.marks_obtained, m.max_marks, m.exam_date,
               s.subject_code, s.subject_name
        FROM academic_marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = %s
        ORDER BY s.subject_code, m.exam_date ASC
    """, (student_id,))

    # Organize marks by subject and exam type
    subjects_map = {}
    for m in marks:
        code = m['subject_code']
        if code not in subjects_map:
            subjects_map[code] = {
                'subject_name': m['subject_name'],
                'Internal 1': None,
                'Internal 2': None,
                'Assignment': None,
                'Final Exam': None
            }
        score_pct = round((m['marks_obtained'] / m['max_marks']) * 100, 1) if m['max_marks'] > 0 else 0
        subjects_map[code][m['exam_type']] = score_pct

    # 2. Cumulative attendance progression over dates
    attendance_records = db.query("""
        SELECT attendance_date, status
        FROM attendance
        WHERE student_id = %s
        ORDER BY attendance_date ASC
    """, (student_id,))

    att_timeline = []
    running_present = 0
    running_total = 0
    for r in attendance_records:
        running_total += 1
        if r['status'] in ('Present', 'On Duty'):
            running_present += 1
        pct = round((running_present / running_total) * 100, 1)
        att_timeline.append({
            'date': str(r['attendance_date']),
            'percentage': pct,
            'status': r['status']
        })

    # Sample only up to 20 representative timeline points for clean rendering
    if len(att_timeline) > 20:
        step = len(att_timeline) // 20
        att_timeline_sampled = att_timeline[::step]
        if att_timeline[-1] not in att_timeline_sampled:
            att_timeline_sampled.append(att_timeline[-1])
    else:
        att_timeline_sampled = att_timeline

    # Overall current stats
    att_stats = AttendanceService.calculate_student_attendance(student_id)
    prediction = PredictionService.get_latest_student_prediction(student_id)

    # Has sufficient data check
    has_sufficient_marks = len(marks) >= 2
    has_sufficient_attendance = len(attendance_records) >= 3

    return render_template(
        'student/performance_journey.html',
        student=student,
        subjects_map=subjects_map,
        att_timeline=att_timeline_sampled,
        att_stats=att_stats,
        prediction=prediction,
        has_sufficient_marks=has_sufficient_marks,
        has_sufficient_attendance=has_sufficient_attendance
    )

# =====================================================================
# FEATURE 5: SMART ACADEMIC NOTIFICATION CENTER
# =====================================================================
@student_bp.route('/notification-center')
def notification_center():
    student = get_current_student()
    
    # Run background check to generate any missing contextual notifications
    NotificationService.check_and_generate_automated_alerts()

    # Fetch notifications categorized
    all_notifs = Notification.get_for_user(student['user_id'], limit=100)
    
    # Filter by category tabs
    attendance_notifs = [n for n in all_notifs if n['category'] in ('Absence Alert', 'Low Attendance Warning', 'Approaching Threshold')]
    academic_notifs = [n for n in all_notifs if n['category'] in ('Academic Risk', 'Declining Marks')]
    task_notifs = [n for n in all_notifs if n['category'] in ('Intervention Task', 'Mentoring Completed')]
    milestone_notifs = [n for n in all_notifs if n['category'] in ('Academic Milestone', 'General Notice')]

    unread_count = sum(1 for n in all_notifs if not n['is_read'])

    return render_template(
        'student/notification_center.html',
        student=student,
        all_notifs=all_notifs,
        attendance_notifs=attendance_notifs,
        academic_notifs=academic_notifs,
        task_notifs=task_notifs,
        milestone_notifs=milestone_notifs,
        unread_count=unread_count
    )

