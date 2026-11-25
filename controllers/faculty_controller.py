from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from database.db import db
from models.classroom import ClassRoom, Subject
from models.timetable import TimetableEntry
from models.intervention import FacultyIntervention
from models.notification import Notification
from services.attendance_service import AttendanceService
from services.prediction_service import PredictionService
from services.notification_service import NotificationService
from controllers.auth_controller import login_required, role_required

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.before_request
@login_required
@role_required(['faculty'])
def check_faculty_access():
    pass

def get_current_faculty():
    user_id = session.get('user_id')
    f_row = db.query("SELECT * FROM faculty WHERE user_id = %s", (user_id,), fetchone=True)
    return f_row

@faculty_bp.route('/dashboard')
def dashboard():
    faculty = get_current_faculty()
    if not faculty:
        flash("Faculty profile not found.", "danger")
        return redirect(url_for('auth.login'))

    faculty_id = faculty['id']
    today_str = date.today().strftime('%A')
    today_date = str(date.today())

    # 1. Assigned classes & subjects
    assigned_classes = db.query("""
        SELECT DISTINCT c.id, c.class_code, c.department, c.semester, c.section,
               COUNT(DISTINCT s.id) as student_count
        FROM timetable t
        JOIN classes c ON t.class_id = c.id
        LEFT JOIN students s ON c.id = s.class_id
        WHERE t.faculty_id = %s
        GROUP BY c.id, c.class_code, c.department, c.semester, c.section
    """, (faculty_id,))

    # 2. Today's timetable
    today_schedule = TimetableEntry.get_faculty_schedule(faculty_id, day_of_week=today_str)

    # 3. Total students taught
    tot_students = db.query("""
        SELECT COUNT(DISTINCT s.id) as count
        FROM timetable t
        JOIN students s ON t.class_id = s.class_id
        WHERE t.faculty_id = %s
    """, (faculty_id,), fetchone=True)['count']

    # 4. Attendance recorded today
    recorded_today = db.query("""
        SELECT COUNT(DISTINCT subject_id) as count
        FROM attendance
        WHERE faculty_id = %s AND attendance_date = %s
    """, (faculty_id, today_date), fetchone=True)['count']

    # 5. Students absent today in faculty's sessions
    absent_today = db.query("""
        SELECT a.*, st.student_id as student_code, u.full_name, c.class_code, s.subject_code
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        JOIN classes c ON a.class_id = c.id
        JOIN subjects s ON a.subject_id = s.id
        WHERE a.faculty_id = %s AND a.attendance_date = %s AND a.status = 'Absent'
    """, (faculty_id, today_date))

    # 6. Low attendance alerts (< 75%) among students taught by this faculty
    low_attendance_students = db.query("""
        SELECT s.id, s.student_id, u.full_name, c.class_code,
               COUNT(a.id) as total_conducted,
               SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as attended,
               ROUND((SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1.0 ELSE 0.0 END) / COUNT(a.id)) * 100, 1) as percentage
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN classes c ON s.class_id = c.id
        JOIN attendance a ON s.id = a.student_id
        WHERE a.faculty_id = %s
        GROUP BY s.id, s.student_id, u.full_name, c.class_code
        HAVING percentage < 75.0
        ORDER BY percentage ASC
        LIMIT 8
    """, (faculty_id,))

    return render_template(
        'faculty/dashboard.html',
        faculty=faculty,
        assigned_classes=assigned_classes,
        today_schedule=today_schedule,
        today_day=today_str,
        today_date=today_date,
        tot_students=tot_students,
        recorded_today=recorded_today,
        absent_today=absent_today,
        low_attendance_students=low_attendance_students
    )

# --- ATTENDANCE RECORDING ---
@faculty_bp.route('/attendance', methods=['GET', 'POST'])
def attendance():
    faculty = get_current_faculty()
    faculty_id = faculty['id']

    # Handle POST submission of marked attendance
    if request.method == 'POST':
        class_id = request.form.get('class_id')
        subject_id = request.form.get('subject_id')
        att_date = request.form.get('attendance_date')
        allow_update = request.form.get('allow_update') == '1'

        student_ids = request.form.getlist('student_ids')
        if not student_ids:
            flash("No students found in the selected class.", "warning")
            return redirect(url_for('faculty.attendance'))

        attendance_data = []
        for sid in student_ids:
            status = request.form.get(f'status_{sid}', 'Present')
            remarks = request.form.get(f'remarks_{sid}', '').strip()
            attendance_data.append({
                'student_id': int(sid),
                'status': status,
                'remarks': remarks or None
            })

        try:
            saved_count, absent_count = AttendanceService.record_class_attendance(
                class_id=int(class_id),
                subject_id=int(subject_id),
                faculty_id=faculty_id,
                attendance_date=att_date,
                attendance_data=attendance_data,
                allow_update=allow_update
            )
            flash(f"Attendance recorded successfully for {saved_count} students! ({absent_count} marked Absent, automated alerts sent)", "success")
            return redirect(url_for('faculty.attendance', class_id=class_id, subject_id=subject_id, date=att_date))
        except ValueError as ve:
            flash(f"{ve} Check 'Update Existing Record' if you have authorization to modify.", "danger")
            return redirect(url_for('faculty.attendance', class_id=class_id, subject_id=subject_id, date=att_date, exists=1))

    # GET: Load class roster & existing attendance if any
    selected_class_id = request.args.get('class_id')
    selected_subject_id = request.args.get('subject_id')
    selected_date = request.args.get('date', str(date.today()))
    exists_flag = request.args.get('exists') == '1'

    # Faculty's scheduled classes and subjects
    classes = db.query("""
        SELECT DISTINCT c.id, c.class_code, c.department, c.semester, c.section
        FROM timetable t
        JOIN classes c ON t.class_id = c.id
        WHERE t.faculty_id = %s
        ORDER BY c.class_code
    """, (faculty_id,))

    subjects = db.query("""
        SELECT DISTINCT s.id, s.subject_code, s.subject_name
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.faculty_id = %s
        ORDER BY s.subject_code
    """, (faculty_id,))

    students_roster = []
    already_recorded = False

    if selected_class_id and selected_subject_id:
        # Check if already recorded on this date
        existing_records = db.query("""
            SELECT student_id, status, remarks 
            FROM attendance 
            WHERE class_id = %s AND subject_id = %s AND attendance_date = %s
        """, (selected_class_id, selected_subject_id, selected_date))

        existing_map = {r['student_id']: r for r in existing_records}
        already_recorded = len(existing_records) > 0

        # Load enrolled students
        students = db.query("""
            SELECT s.id, s.student_id, u.full_name, u.email
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.class_id = %s AND s.enrollment_status = 'Active'
            ORDER BY s.student_id ASC
        """, (selected_class_id,))

        for st in students:
            # Calculate cumulative attendance stats
            stats = AttendanceService.calculate_student_attendance(st['id'])
            st['overall_pct'] = stats['attendance_percentage']
            st['is_low'] = stats['is_low_attendance']

            if st['id'] in existing_map:
                st['current_status'] = existing_map[st['id']]['status']
                st['current_remarks'] = existing_map[st['id']]['remarks'] or ''
            else:
                st['current_status'] = 'Present'  # Default
                st['current_remarks'] = ''
            students_roster.append(st)

    return render_template(
        'faculty/attendance.html',
        classes=classes,
        subjects=subjects,
        selected_class_id=int(selected_class_id) if selected_class_id else None,
        selected_subject_id=int(selected_subject_id) if selected_subject_id else None,
        selected_date=selected_date,
        students=students_roster,
        already_recorded=already_recorded,
        exists_flag=exists_flag
    )

# --- INTERNAL EXAMINATION MARKS ENTRY ---
@faculty_bp.route('/marks', methods=['GET', 'POST'])
def marks():
    faculty = get_current_faculty()
    faculty_id = faculty['id']

    if request.method == 'POST':
        class_id = request.form.get('class_id')
        subject_id = request.form.get('subject_id')
        exam_type = request.form.get('exam_type', 'Internal 1')
        max_marks = float(request.form.get('max_marks', 50.0))
        exam_date = request.form.get('exam_date', str(date.today()))

        student_ids = request.form.getlist('student_ids')
        saved_count = 0
        for sid in student_ids:
            marks_val = request.form.get(f'marks_{sid}')
            remarks = request.form.get(f'remarks_{sid}', '').strip()
            if marks_val is not None and marks_val != '':
                m_float = float(marks_val)
                # Cap marks at max_marks
                m_float = min(m_float, max_marks)

                if db.get_engine_name() == 'MYSQL':
                    sql = """
                        INSERT INTO academic_marks (student_id, subject_id, exam_type, marks_obtained, max_marks, exam_date, entered_by, remarks)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE marks_obtained = VALUES(marks_obtained), max_marks = VALUES(max_marks), entered_by = VALUES(entered_by), remarks = VALUES(remarks)
                    """
                    db.execute(sql, (sid, subject_id, exam_type, m_float, max_marks, exam_date, faculty_id, remarks))
                else:
                    sql = """
                        INSERT INTO academic_marks (student_id, subject_id, exam_type, marks_obtained, max_marks, exam_date, entered_by, remarks)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT(student_id, subject_id, exam_type)
                        DO UPDATE SET marks_obtained=excluded.marks_obtained, max_marks=excluded.max_marks, entered_by=excluded.entered_by, remarks=excluded.remarks
                    """
                    db.execute(sql, (sid, subject_id, exam_type, m_float, max_marks, exam_date, faculty_id, remarks))
                
                # Refresh AI prediction for this student in background
                PredictionService.predict_student(int(sid), trigger_alert=True)
                saved_count += 1

        flash(f"Academic marks recorded successfully for {saved_count} students! AI risk models updated.", "success")
        return redirect(url_for('faculty.marks', class_id=class_id, subject_id=subject_id, exam_type=exam_type))

    # GET Roster & Marks
    selected_class_id = request.args.get('class_id')
    selected_subject_id = request.args.get('subject_id')
    selected_exam = request.args.get('exam_type', 'Internal 1')

    classes = db.query("""
        SELECT DISTINCT c.id, c.class_code, c.department
        FROM timetable t
        JOIN classes c ON t.class_id = c.id
        WHERE t.faculty_id = %s
        ORDER BY c.class_code
    """, (faculty_id,))

    subjects = db.query("""
        SELECT DISTINCT s.id, s.subject_code, s.subject_name
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.id
        WHERE t.faculty_id = %s
        ORDER BY s.subject_code
    """, (faculty_id,))

    roster = []
    if selected_class_id and selected_subject_id:
        existing_marks = db.query("""
            SELECT student_id, marks_obtained, max_marks, remarks
            FROM academic_marks
            WHERE subject_id = %s AND exam_type = %s
        """, (selected_subject_id, selected_exam))
        marks_map = {m['student_id']: m for m in existing_marks}

        students = db.query("""
            SELECT s.id, s.student_id, u.full_name
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.class_id = %s AND s.enrollment_status = 'Active'
            ORDER BY s.student_id
        """, (selected_class_id,))

        for st in students:
            if st['id'] in marks_map:
                st['marks_obtained'] = marks_map[st['id']]['marks_obtained']
                st['max_marks'] = marks_map[st['id']]['max_marks']
                st['remarks'] = marks_map[st['id']]['remarks'] or ''
            else:
                st['marks_obtained'] = ''
                st['max_marks'] = 50.0
                st['remarks'] = ''
            roster.append(st)

    return render_template(
        'faculty/marks.html',
        classes=classes,
        subjects=subjects,
        selected_class_id=int(selected_class_id) if selected_class_id else None,
        selected_subject_id=int(selected_subject_id) if selected_subject_id else None,
        selected_exam=selected_exam,
        students=roster
    )

# --- FACULTY ANALYTICS ---
@faculty_bp.route('/analytics')
def analytics():
    faculty = get_current_faculty()
    faculty_id = faculty['id']

    # Performance per subject taught by faculty
    subject_stats = db.query("""
        SELECT s.id, s.subject_code, s.subject_name,
               COUNT(a.id) as total_attendance_logs,
               ROUND(AVG(CASE WHEN a.status IN ('Present', 'On Duty') THEN 100.0 ELSE 0.0 END), 1) as avg_attendance_pct,
               (SELECT ROUND(AVG((m.marks_obtained / m.max_marks) * 100), 1) 
                FROM academic_marks m WHERE m.subject_id = s.id AND m.entered_by = %s) as avg_marks_pct
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.id
        LEFT JOIN attendance a ON s.id = a.subject_id AND a.faculty_id = %s
        WHERE t.faculty_id = %s
        GROUP BY s.id, s.subject_code, s.subject_name
    """, (faculty_id, faculty_id, faculty_id))

    # At-risk students in faculty's classes
    risk_students = db.query("""
        SELECT p.*, s.student_id as student_code, u.full_name, c.class_code
        FROM prediction_results p
        JOIN students s ON p.student_id = s.id
        JOIN users u ON s.user_id = u.id
        JOIN classes c ON s.class_id = c.id
        WHERE s.class_id IN (SELECT DISTINCT class_id FROM timetable WHERE faculty_id = %s)
          AND p.id = (SELECT MAX(p2.id) FROM prediction_results p2 WHERE p2.student_id = p.student_id)
          AND p.risk_category = 'Needs Improvement'
        ORDER BY p.attendance_percentage ASC
    """, (faculty_id,))

    return render_template('faculty/analytics.html', subject_stats=subject_stats, risk_students=risk_students)

# =====================================================================
# FEATURE 3: SMART FACULTY INTERVENTION CENTER
# =====================================================================
@faculty_bp.route('/interventions')
def interventions():
    faculty = get_current_faculty()
    faculty_id = faculty['id']

    # 1. Fetch all students in classes assigned to this faculty member
    assigned_students = db.query("""
        SELECT DISTINCT s.id, s.student_id, u.full_name, u.email, c.class_code, c.department
        FROM timetable t
        JOIN classes c ON t.class_id = c.id
        JOIN students s ON c.id = s.class_id
        JOIN users u ON s.user_id = u.id
        WHERE t.faculty_id = %s AND s.enrollment_status = 'Active'
        ORDER BY u.full_name ASC
    """, (faculty_id,))

    # Enrich each student with attendance percentage and latest ML risk prediction
    categorized_students = {
        'Needs Improvement': [],
        'Average Performance': [],
        'Good Performance': []
    }
    low_attendance_list = []

    for st in assigned_students:
        sid = st['id']
        att_stats = AttendanceService.calculate_student_attendance(sid)
        pred = PredictionService.get_latest_student_prediction(sid)

        st['attendance_percentage'] = att_stats['attendance_percentage']
        st['total_absences'] = att_stats['absent_count']
        st['is_low_attendance'] = att_stats['is_low_attendance']
        st['risk_category'] = pred.get('risk_category', 'Average Performance') if pred else 'Average Performance'
        st['confidence_score'] = pred.get('confidence_score', 85.0) if pred else 85.0
        st['risk_factors'] = pred.get('risk_factors', 'Balanced metrics') if pred else 'Balanced metrics'

        cat = st['risk_category']
        if cat in categorized_students:
            categorized_students[cat].append(st)
        else:
            categorized_students['Average Performance'].append(st)

        if st['is_low_attendance']:
            low_attendance_list.append(st)

    # 2. Existing interventions logged by this faculty member
    status_filter = request.args.get('status')
    logged_interventions = FacultyIntervention.get_for_faculty(faculty_id, status_filter=status_filter)

    # Calculate post-intervention recovery impact (check if student's current attendance improved)
    for inv in logged_interventions:
        sid = inv['student_id']
        curr_att = AttendanceService.calculate_student_attendance(sid)
        inv['current_attendance'] = curr_att['attendance_percentage']
        inv['attendance_delta'] = round(curr_att['attendance_percentage'] - inv['attendance_at_intervention'], 1)

    return render_template(
        'faculty/interventions.html',
        faculty=faculty,
        assigned_students=assigned_students,
        categorized_students=categorized_students,
        low_attendance_list=low_attendance_list,
        logged_interventions=logged_interventions,
        status_filter=status_filter
    )

@faculty_bp.route('/interventions/create', methods=['POST'])
def create_intervention():
    faculty = get_current_faculty()
    faculty_id = faculty['id']

    student_id = int(request.form.get('student_id'))
    mentoring_date = request.form.get('mentoring_date', str(date.today()))
    mentoring_notes = request.form.get('mentoring_notes', '').strip()
    assigned_tasks = request.form.get('assigned_tasks', '').strip()
    status = request.form.get('status', 'Pending')

    if not mentoring_notes:
        flash("Mentoring notes are required.", "warning")
        return redirect(url_for('faculty.interventions'))

    # Verify authorization: student must be in faculty's assigned classes
    auth_check = db.query("""
        SELECT COUNT(*) as cnt
        FROM timetable t
        JOIN students s ON t.class_id = s.class_id
        WHERE t.faculty_id = %s AND s.id = %s
    """, (faculty_id, student_id), fetchone=True)

    if not auth_check or auth_check['cnt'] == 0:
        flash("Unauthorized: You can only mentor students enrolled in your assigned classes.", "danger")
        return redirect(url_for('faculty.interventions'))

    # Fetch current metrics at point of intervention
    att_stats = AttendanceService.calculate_student_attendance(student_id)
    pred = PredictionService.get_latest_student_prediction(student_id)
    risk_cat = pred.get('risk_category', 'Needs Improvement') if pred else 'Needs Improvement'

    avg_marks_row = db.query("""
        SELECT AVG((marks_obtained / max_marks) * 100) as avg_score
        FROM academic_marks WHERE student_id = %s
    """, (student_id,), fetchone=True)
    avg_marks = round(avg_marks_row['avg_score'] or 60.0, 1)

    # Save intervention record
    inv_id = FacultyIntervention.create(
        faculty_id=faculty_id,
        student_id=student_id,
        risk_category=risk_cat,
        attendance_at_intervention=att_stats['attendance_percentage'],
        marks_at_intervention=avg_marks,
        mentoring_notes=mentoring_notes,
        assigned_tasks=assigned_tasks,
        mentoring_date=mentoring_date,
        status=status
    )

    # Dispatch notification to student
    faculty_user = db.query("SELECT full_name FROM users WHERE id = %s", (faculty['user_id'],), fetchone=True)
    f_name = faculty_user['full_name'] if faculty_user else 'Your Faculty Mentor'
    if assigned_tasks:
        NotificationService.send_intervention_assigned_alert(student_id, f_name, assigned_tasks)

    flash("Mentoring intervention and student action tasks recorded successfully!", "success")
    return redirect(url_for('faculty.interventions'))

@faculty_bp.route('/interventions/update-status/<int:intervention_id>', methods=['POST'])
def update_intervention_status(intervention_id):
    faculty = get_current_faculty()
    inv = FacultyIntervention.get_by_id(intervention_id)

    if not inv or inv.faculty_id != faculty['id']:
        flash("Intervention record not found or unauthorized.", "danger")
        return redirect(url_for('faculty.interventions'))

    status = request.form.get('status', 'In Progress')
    outcome_notes = request.form.get('outcome_notes', '').strip()

    FacultyIntervention.update_status(intervention_id, status, outcome_notes=outcome_notes)

    # If marked completed, notify student
    if status == 'Completed':
        faculty_user = db.query("SELECT full_name FROM users WHERE id = %s", (faculty['user_id'],), fetchone=True)
        f_name = faculty_user['full_name'] if faculty_user else 'Your Faculty Mentor'
        NotificationService.send_mentoring_completed_alert(inv.student_id, f_name)

    flash(f"Intervention status updated to '{status}' successfully!", "success")
    return redirect(url_for('faculty.interventions'))

# =====================================================================
# FEATURE 5: FACULTY NOTIFICATION & ALERTS CENTER
# =====================================================================
@faculty_bp.route('/notifications')
def notifications():
    faculty = get_current_faculty()
    faculty_id = faculty['id']

    # Automated scan for student alerts
    NotificationService.check_and_generate_automated_alerts()

    # Alerts specifically relevant to faculty's students
    student_alerts = db.query("""
        SELECT n.*, u.full_name as student_name, st.student_id as student_code, c.class_code
        FROM notifications n
        JOIN students st ON n.student_id = st.id
        JOIN users u ON st.user_id = u.id
        JOIN classes c ON st.class_id = c.id
        WHERE c.id IN (SELECT DISTINCT class_id FROM timetable WHERE faculty_id = %s)
          AND n.category IN ('Low Attendance Warning', 'Approaching Threshold', 'Declining Marks', 'Academic Risk')
        ORDER BY n.created_at DESC
        LIMIT 60
    """, (faculty_id,))

    # Faculty personal notices
    personal_notifs = Notification.get_for_user(faculty['user_id'], limit=30)

    return render_template(
        'faculty/notifications.html',
        faculty=faculty,
        student_alerts=student_alerts,
        personal_notifs=personal_notifs
    )

