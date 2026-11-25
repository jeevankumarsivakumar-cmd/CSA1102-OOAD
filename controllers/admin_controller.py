from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash
from database.db import db
from models.user import User, Admin, Faculty, Student
from models.classroom import ClassRoom, Subject
from models.timetable import TimetableEntry
from models.intervention import FacultyIntervention
from models.notification import Notification
from services.attendance_service import AttendanceService
from services.prediction_service import PredictionService
from services.notification_service import NotificationService
from controllers.auth_controller import login_required, role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
@role_required(['admin'])
def check_admin_access():
    pass

@admin_bp.route('/dashboard')
def dashboard():
    # 1. Total counts
    tot_students = db.query("SELECT COUNT(*) as cnt FROM students WHERE enrollment_status = 'Active'", fetchone=True)['cnt']
    tot_faculty = db.query("SELECT COUNT(*) as cnt FROM faculty", fetchone=True)['cnt']
    tot_classes = db.query("SELECT COUNT(*) as cnt FROM classes", fetchone=True)['cnt']
    tot_subjects = db.query("SELECT COUNT(*) as cnt FROM subjects", fetchone=True)['cnt']

    # 2. Today's attendance percentage
    today_att = db.query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE attendance_date = DATE('now')
    """, fetchone=True)
    if db.get_engine_name() == 'MYSQL':
        today_att = db.query("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as present
            FROM attendance
            WHERE attendance_date = CURDATE()
        """, fetchone=True)
    
    tot_today = today_att['total'] if today_att else 0
    pres_today = today_att['present'] or 0 if today_att else 0
    today_pct = round((pres_today / tot_today) * 100, 1) if tot_today > 0 else 0.0

    # 3. Students with low attendance (< 75%)
    low_att_students = db.query("""
        SELECT s.id, s.student_id, u.full_name, c.class_code, s.department,
               COUNT(a.id) as total_conducted,
               SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as attended,
               ROUND((SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1.0 ELSE 0.0 END) / COUNT(a.id)) * 100, 1) as percentage
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN classes c ON s.class_id = c.id
        JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id, s.student_id, u.full_name, c.class_code, s.department
        HAVING percentage < 75.0
        ORDER BY percentage ASC
        LIMIT 10
    """)

    # 4. Department-wise student distribution
    dept_dist = db.query("""
        SELECT department, COUNT(*) as count 
        FROM students 
        WHERE enrollment_status = 'Active' 
        GROUP BY department
    """)

    # 5. Attendance trend (last 14 days)
    attendance_trends = AttendanceService.get_attendance_trend(days=14)

    # 6. Overall academic prediction distribution
    ai_summary = PredictionService.get_ai_analytics_dashboard_data()

    # 7. Recent activities
    recent_activities = db.query("""
        SELECT a.attendance_date, a.status, u.full_name as student_name, s.subject_code, c.class_code, a.recorded_at
        FROM attendance a
        JOIN students st ON a.student_id = st.id
        JOIN users u ON st.user_id = u.id
        JOIN subjects s ON a.subject_id = s.id
        JOIN classes c ON a.class_id = c.id
        ORDER BY a.recorded_at DESC
        LIMIT 8
    """)

    return render_template(
        'admin/dashboard.html',
        tot_students=tot_students,
        tot_faculty=tot_faculty,
        tot_classes=tot_classes,
        tot_subjects=tot_subjects,
        today_pct=today_pct,
        tot_today=tot_today,
        low_att_students=low_att_students,
        dept_dist=dept_dist,
        attendance_trends=attendance_trends,
        ai_summary=ai_summary,
        recent_activities=recent_activities
    )

# --- STUDENT MANAGEMENT ---
@admin_bp.route('/students', methods=['GET', 'POST'])
def students():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            full_name = request.form.get('full_name', '').strip()
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', 'student123')
            class_id = request.form.get('class_id')
            department = request.form.get('department', '').strip()
            phone = request.form.get('phone', '').strip()
            emergency = request.form.get('emergency_contact', '').strip()
            gpa = float(request.form.get('previous_gpa', 7.5))

            # Auto-generate unique Student ID: STU2026XXX
            last_st = db.query("SELECT student_id FROM students ORDER BY id DESC LIMIT 1", fetchone=True)
            if last_st and last_st['student_id'].startswith('STU2026'):
                num = int(last_st['student_id'].replace('STU2026', '')) + 1
            else:
                num = 1
            student_id = f"STU2026{num:03d}"

            # Check duplicate username/email
            if db.query("SELECT id FROM users WHERE username = %s OR email = %s", (username, email), fetchone=True):
                flash("Username or email already exists.", "danger")
                return redirect(url_for('admin.students'))

            pwd_hash = generate_password_hash(password)
            uid = db.execute(
                """
                INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active)
                VALUES (%s, %s, %s, 'student', %s, %s, 1)
                """,
                (username, email, pwd_hash, full_name, phone)
            )
            db.execute(
                """
                INSERT INTO students (user_id, student_id, class_id, department, academic_year, contact_phone, emergency_contact, previous_gpa)
                VALUES (%s, %s, %s, %s, '2025-2026', %s, %s, %s)
                """,
                (uid, student_id, class_id, department, phone, emergency, gpa)
            )
            flash(f"Student '{full_name}' successfully enrolled with ID {student_id}!", "success")
            return redirect(url_for('admin.students'))

        elif action == 'edit':
            st_table_id = request.form.get('student_table_id')
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            class_id = request.form.get('class_id')
            phone = request.form.get('phone', '').strip()
            gpa = float(request.form.get('previous_gpa', 7.5))
            status = request.form.get('enrollment_status', 'Active')

            st_row = db.query("SELECT user_id FROM students WHERE id = %s", (st_table_id,), fetchone=True)
            if st_row:
                db.execute(
                    "UPDATE users SET full_name = %s, email = %s, phone = %s WHERE id = %s",
                    (full_name, email, phone, st_row['user_id'])
                )
                db.execute(
                    "UPDATE students SET class_id = %s, contact_phone = %s, previous_gpa = %s, enrollment_status = %s WHERE id = %s",
                    (class_id, phone, gpa, status, st_table_id)
                )
                flash(f"Student details updated successfully.", "success")
            return redirect(url_for('admin.students'))

        elif action == 'delete':
            st_table_id = request.form.get('student_table_id')
            st_row = db.query("SELECT user_id, full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s", (st_table_id,), fetchone=True)
            if st_row:
                # Deleting user will cascade to student, attendance, marks, etc.
                db.execute("DELETE FROM users WHERE id = %s", (st_row['user_id'],))
                flash(f"Student '{st_row['full_name']}' deleted.", "info")
            return redirect(url_for('admin.students'))

    # GET: Search & filter
    q = request.args.get('q', '').strip()
    filter_class = request.args.get('class_id', '')
    filter_dept = request.args.get('department', '')

    sql = """
        SELECT s.*, u.full_name, u.email, u.phone, u.username, c.class_code
        FROM students s
        JOIN users u ON s.user_id = u.id
        JOIN classes c ON s.class_id = c.id
        WHERE 1=1
    """
    params = []
    if q:
        sql += " AND (u.full_name LIKE %s OR s.student_id LIKE %s OR u.email LIKE %s)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if filter_class:
        sql += " AND s.class_id = %s"
        params.append(filter_class)
    if filter_dept:
        sql += " AND s.department = %s"
        params.append(filter_dept)

    sql += " ORDER BY u.full_name ASC"
    students_list = db.query(sql, tuple(params))
    
    # Calculate real-time attendance for each student
    for st in students_list:
        att = AttendanceService.calculate_student_attendance(st['id'])
        st['attendance_percentage'] = att['attendance_percentage']
        st['absent_count'] = att['absent_count']

    classes_list = ClassRoom.get_all()
    departments = db.query("SELECT DISTINCT department FROM classes ORDER BY department")

    return render_template(
        'admin/students.html',
        students=students_list,
        classes=classes_list,
        departments=[d['department'] for d in departments],
        q=q,
        selected_class=filter_class,
        selected_dept=filter_dept
    )

# --- FACULTY MANAGEMENT ---
@admin_bp.route('/faculty', methods=['GET', 'POST'])
def faculty():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            full_name = request.form.get('full_name', '').strip()
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', 'faculty123')
            department = request.form.get('department', '').strip()
            designation = request.form.get('designation', 'Assistant Professor')
            qualification = request.form.get('qualification', '')
            specialization = request.form.get('specialization', '')
            phone = request.form.get('phone', '')

            # Auto employee ID
            last_f = db.query("SELECT employee_id FROM faculty ORDER BY id DESC LIMIT 1", fetchone=True)
            if last_f and last_f['employee_id'].startswith('FAC2024'):
                num = int(last_f['employee_id'].replace('FAC2024', '')) + 1
            else:
                num = 1
            empid = f"FAC2024{num:02d}"

            pwd_hash = generate_password_hash(password)
            uid = db.execute(
                """
                INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active)
                VALUES (%s, %s, %s, 'faculty', %s, %s, 1)
                """,
                (username, email, pwd_hash, full_name, phone)
            )
            db.execute(
                """
                INSERT INTO faculty (user_id, employee_id, department, designation, qualification, specialization, joining_date)
                VALUES (%s, %s, %s, %s, %s, %s, DATE('now'))
                """,
                (uid, empid, department, designation, qualification, specialization)
            )
            flash(f"Faculty member '{full_name}' added successfully!", "success")
            return redirect(url_for('admin.faculty'))

        elif action == 'delete':
            fid = request.form.get('faculty_table_id')
            f_row = db.query("SELECT user_id, full_name FROM faculty f JOIN users u ON f.user_id = u.id WHERE f.id = %s", (fid,), fetchone=True)
            if f_row:
                db.execute("DELETE FROM users WHERE id = %s", (f_row['user_id'],))
                flash(f"Faculty '{f_row['full_name']}' removed.", "info")
            return redirect(url_for('admin.faculty'))

    faculty_list = db.query("""
        SELECT f.*, u.full_name, u.email, u.phone, u.username
        FROM faculty f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.department, u.full_name
    """)
    departments = db.query("SELECT DISTINCT department FROM classes ORDER BY department")
    return render_template('admin/faculty.html', faculty=faculty_list, departments=[d['department'] for d in departments])

# --- CLASSES & SUBJECTS MANAGEMENT ---
@admin_bp.route('/classes', methods=['GET', 'POST'])
def classes():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create_class':
            class_code = request.form.get('class_code', '').strip().upper()
            dept = request.form.get('department', '').strip()
            sem = int(request.form.get('semester', 1))
            sec = request.form.get('section', 'A').strip().upper()
            room = request.form.get('room_number', '').strip()
            ay = request.form.get('academic_year', '2025-2026').strip()

            db.execute(
                """
                INSERT INTO classes (class_code, department, semester, academic_year, section, room_number)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (class_code, dept, sem, ay, sec, room)
            )
            flash(f"Class '{class_code}' created successfully!", "success")
            return redirect(url_for('admin.classes'))

        elif action == 'create_subject':
            scode = request.form.get('subject_code', '').strip().upper()
            sname = request.form.get('subject_name', '').strip()
            dept = request.form.get('department', '').strip()
            cred = int(request.form.get('credits', 3))
            sem = int(request.form.get('semester', 1))

            db.execute(
                """
                INSERT INTO subjects (subject_code, subject_name, department, credits, semester)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (scode, sname, dept, cred, sem)
            )
            flash(f"Subject '{scode} - {sname}' created successfully!", "success")
            return redirect(url_for('admin.classes'))

    classes_list = ClassRoom.get_all()
    subjects_list = Subject.get_all()
    return render_template('admin/classes.html', classes=classes_list, subjects=subjects_list)

# --- TIMETABLE MANAGEMENT ---
@admin_bp.route('/timetable', methods=['GET', 'POST'])
def timetable():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            class_id = request.form.get('class_id')
            subject_id = request.form.get('subject_id')
            faculty_id = request.form.get('faculty_id')
            dow = request.form.get('day_of_week')
            start_t = request.form.get('start_time')
            end_t = request.form.get('end_time')
            room = request.form.get('room_number')

            db.execute(
                """
                INSERT INTO timetable (class_id, subject_id, faculty_id, day_of_week, start_time, end_time, room_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (class_id, subject_id, faculty_id, dow, start_t, end_t, room)
            )
            flash("Timetable slot scheduled successfully!", "success")
            return redirect(url_for('admin.timetable'))

        elif action == 'delete':
            slot_id = request.form.get('slot_id')
            db.execute("DELETE FROM timetable WHERE id = %s", (slot_id,))
            flash("Timetable slot removed.", "info")
            return redirect(url_for('admin.timetable'))

    selected_class = request.args.get('class_id')
    if selected_class:
        schedule = TimetableEntry.get_class_schedule(selected_class)
    else:
        schedule = TimetableEntry.get_all()

    classes_list = ClassRoom.get_all()
    subjects_list = Subject.get_all()
    faculty_list = db.query("SELECT f.id, u.full_name, f.department FROM faculty f JOIN users u ON f.user_id = u.id ORDER BY u.full_name")

    return render_template(
        'admin/timetable.html',
        schedule=schedule,
        classes=classes_list,
        subjects=subjects_list,
        faculty=faculty_list,
        selected_class=selected_class
    )

# =====================================================================
# FEATURE 3: ADMIN INSTITUTIONAL INTERVENTION OVERSIGHT
# =====================================================================
@admin_bp.route('/interventions')
def interventions():
    status_filter = request.args.get('status')
    all_interventions = FacultyIntervention.get_all(status_filter=status_filter, limit=100)

    # Summary metrics
    tot_interventions = len(all_interventions)
    pending_count = sum(1 for i in all_interventions if i['status'] == 'Pending')
    in_progress_count = sum(1 for i in all_interventions if i['status'] == 'In Progress')
    completed_count = sum(1 for i in all_interventions if i['status'] == 'Completed')

    # Department breakdown
    dept_counts = {}
    for i in all_interventions:
        dept = i.get('department', 'General')
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    return render_template(
        'admin/interventions.html',
        interventions=all_interventions,
        tot_interventions=tot_interventions,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        completed_count=completed_count,
        dept_counts=dept_counts,
        status_filter=status_filter
    )

# =====================================================================
# FEATURE 5: ADMIN CAMPUS-WIDE NOTIFICATIONS CENTER
# =====================================================================
@admin_bp.route('/notifications')
def notifications():
    # Automated scan for fresh alerts
    NotificationService.check_and_generate_automated_alerts()

    category_filter = request.args.get('category')
    sql = """
        SELECT n.*, u.full_name as user_name, u.role, st.student_id as student_code, c.class_code
        FROM notifications n
        JOIN users u ON n.user_id = u.id
        LEFT JOIN students st ON n.student_id = st.id
        LEFT JOIN classes c ON st.class_id = c.id
    """
    params = []
    if category_filter:
        sql += " WHERE n.category = %s"
        params.append(category_filter)
    sql += " ORDER BY n.created_at DESC LIMIT 100"

    all_campus_alerts = db.query(sql, tuple(params) if params else None)

    # Category counts
    counts = db.query("""
        SELECT category, COUNT(*) as cnt 
        FROM notifications 
        GROUP BY category
    """)
    category_counts = {c['category']: c['cnt'] for c in counts}

    return render_template(
        'admin/notifications.html',
        alerts=all_campus_alerts,
        category_counts=category_counts,
        selected_category=category_filter
    )

