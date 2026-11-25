import os
import sys
import random

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash
from database.db import db
from services.prediction_service import PredictionService

def seed_database():
    print("[SeedData] Starting rich dataset generation for college demonstration...")

    # Clear existing demo records
    try:
        db.execute("DELETE FROM prediction_results")
        db.execute("DELETE FROM notifications")
        db.execute("DELETE FROM academic_marks")
        db.execute("DELETE FROM attendance")
        db.execute("DELETE FROM timetable")
        db.execute("DELETE FROM subjects")
        db.execute("DELETE FROM students")
        db.execute("DELETE FROM faculty")
        db.execute("DELETE FROM classes")
        db.execute("DELETE FROM users")
    except Exception as e:
        print(f"[SeedData] Table clear warning: {e}")

    default_pwd_hash = generate_password_hash("password123")
    admin_pwd_hash = generate_password_hash("admin123")
    faculty_pwd_hash = generate_password_hash("faculty123")
    student_pwd_hash = generate_password_hash("student123")

    # 1. Create ADMIN user
    admin_user_id = db.execute(
        """
        INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, 1)
        """,
        ('admin', 'admin@university.edu', admin_pwd_hash, 'admin', 'Dr. Ramesh Kumar (Dean Academic)', '+91 98765 43210')
    )

    # 2. Create CLASSES
    classes_data = [
        ('CSE-4A', 'Computer Science & Engineering', 4, '2025-2026', 'A', 'CS-Lab 201'),
        ('CSE-4B', 'Computer Science & Engineering', 4, '2025-2026', 'B', 'CS-Lab 202'),
        ('AIML-4A', 'Artificial Intelligence & ML', 4, '2025-2026', 'A', 'AI-Lab 301'),
        ('ECE-3A', 'Electronics & Communication', 3, '2025-2026', 'A', 'EC-Lab 105')
    ]
    class_ids = {}
    for code, dept, sem, yr, sec, room in classes_data:
        cid = db.execute(
            """
            INSERT INTO classes (class_code, department, semester, academic_year, section, room_number)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (code, dept, sem, yr, sec, room)
        )
        class_ids[code] = cid

    # 3. Create FACULTY users & profile
    faculty_data = [
        ('faculty1', 'anita.sharma@university.edu', 'Dr. Anita Sharma', 'FAC202401', 'Computer Science & Engineering', 'Professor & HOD', 'Ph.D in AI & Software Engineering', 'Machine Learning & OOAD'),
        ('faculty2', 'rajesh.verma@university.edu', 'Prof. Rajesh Verma', 'FAC202402', 'Computer Science & Engineering', 'Associate Professor', 'M.Tech, Ph.D (Pursuing)', 'Database Systems & Cloud Computing'),
        ('faculty3', 'priya.nair@university.edu', 'Dr. Priya Nair', 'FAC202403', 'Artificial Intelligence & ML', 'Assistant Professor', 'Ph.D in Data Science', 'Deep Learning & Pattern Recognition')
    ]
    faculty_table_ids = {}
    for uname, email, fname, empid, dept, desig, qual, spec in faculty_data:
        uid = db.execute(
            """
            INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            """,
            (uname, email, faculty_pwd_hash, 'faculty', fname, '+91 98123 45678')
        )
        fid = db.execute(
            """
            INSERT INTO faculty (user_id, employee_id, department, designation, qualification, specialization, joining_date)
            VALUES (%s, %s, %s, %s, %s, %s, '2021-07-15')
            """,
            (uid, empid, dept, desig, qual, spec)
        )
        faculty_table_ids[uname] = fid

    # 4. Create SUBJECTS
    subjects_data = [
        ('CS401', 'Object Oriented Analysis & Design', 'Computer Science & Engineering', 4, 4),
        ('CS402', 'Database Management Systems', 'Computer Science & Engineering', 4, 4),
        ('CS403', 'Machine Learning Foundations', 'Computer Science & Engineering', 4, 4),
        ('CS404', 'Computer Networks & Security', 'Computer Science & Engineering', 3, 4),
        ('CS405', 'Software Engineering Principles', 'Computer Science & Engineering', 3, 4)
    ]
    subject_ids = {}
    for scode, sname, dept, cred, sem in subjects_data:
        sid = db.execute(
            """
            INSERT INTO subjects (subject_code, subject_name, department, credits, semester)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (scode, sname, dept, cred, sem)
        )
        subject_ids[scode] = sid

    # 5. Create TIMETABLE entries
    timetable_data = [
        ('CSE-4A', 'CS401', 'faculty1', 'Monday', '09:00:00', '10:00:00', 'CS-Lab 201'),
        ('CSE-4A', 'CS402', 'faculty2', 'Monday', '10:15:00', '11:15:00', 'CS-Lab 201'),
        ('CSE-4A', 'CS403', 'faculty3', 'Monday', '11:30:00', '12:30:00', 'AI-Lab 301'),
        ('CSE-4A', 'CS404', 'faculty2', 'Tuesday', '09:00:00', '10:00:00', 'CS-Lab 201'),
        ('CSE-4A', 'CS401', 'faculty1', 'Tuesday', '10:15:00', '11:15:00', 'CS-Lab 201'),
        ('CSE-4A', 'CS405', 'faculty1', 'Wednesday', '09:00:00', '10:00:00', 'CS-Lab 201'),
        ('CSE-4A', 'CS403', 'faculty3', 'Wednesday', '10:15:00', '11:15:00', 'AI-Lab 301'),
        ('CSE-4A', 'CS402', 'faculty2', 'Thursday', '09:00:00', '10:00:00', 'CS-Lab 201'),
        ('CSE-4A', 'CS401', 'faculty1', 'Friday', '09:00:00', '10:00:00', 'CS-Lab 201'),
        ('CSE-4B', 'CS401', 'faculty1', 'Monday', '14:00:00', '15:00:00', 'CS-Lab 202'),
        ('CSE-4B', 'CS402', 'faculty2', 'Tuesday', '14:00:00', '15:00:00', 'CS-Lab 202')
    ]
    for ccode, scode, fname, dow, st, et, rm in timetable_data:
        db.execute(
            """
            INSERT INTO timetable (class_id, subject_id, faculty_id, day_of_week, start_time, end_time, room_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (class_ids[ccode], subject_ids[scode], faculty_table_ids[fname], dow, st, et, rm)
        )

    # 6. Create STUDENTS
    # Let's seed 15 students in CSE-4A, 5 in CSE-4B
    students_raw = [
        # (username, email, name, student_id, class_code, dept, prev_gpa, target_profile)
        # target_profile: 'high' (good att, high marks), 'mid' (avg att, mid marks), 'low' (low att, low marks/risk)
        ('student1', 'aarav.patel@student.edu', 'Aarav Patel', 'STU2026001', 'CSE-4A', 'Computer Science & Engineering', 8.90, 'high'),
        ('student2', 'diya.sengupta@student.edu', 'Diya Sengupta', 'STU2026002', 'CSE-4A', 'Computer Science & Engineering', 9.15, 'high'),
        ('student3', 'rohan.mehta@student.edu', 'Rohan Mehta', 'STU2026003', 'CSE-4A', 'Computer Science & Engineering', 6.20, 'low'), # At risk
        ('student4', 'ananya.iyer@student.edu', 'Ananya Iyer', 'STU2026004', 'CSE-4A', 'Computer Science & Engineering', 7.80, 'mid'),
        ('student5', 'vikram.singh@student.edu', 'Vikram Singh', 'STU2026005', 'CSE-4A', 'Computer Science & Engineering', 5.90, 'low'), # At risk
        ('student6', 'sneha.reddy@student.edu', 'Sneha Reddy', 'STU2026006', 'CSE-4A', 'Computer Science & Engineering', 8.45, 'high'),
        ('student7', 'kabir.sharma@student.edu', 'Kabir Sharma', 'STU2026007', 'CSE-4A', 'Computer Science & Engineering', 7.10, 'mid'),
        ('student8', 'tanya.deshmukh@student.edu', 'Tanya Deshmukh', 'STU2026008', 'CSE-4A', 'Computer Science & Engineering', 8.20, 'high'),
        ('student9', 'aditya.joshi@student.edu', 'Aditya Joshi', 'STU2026009', 'CSE-4A', 'Computer Science & Engineering', 6.40, 'low'), # At risk
        ('student10', 'meera.krishnan@student.edu', 'Meera Krishnan', 'STU2026010', 'CSE-4A', 'Computer Science & Engineering', 7.50, 'mid'),
        ('student11', 'rahul.kapoor@student.edu', 'Rahul Kapoor', 'STU2026011', 'CSE-4A', 'Computer Science & Engineering', 8.00, 'mid'),
        ('student12', 'pooja.verma@student.edu', 'Pooja Verma', 'STU2026012', 'CSE-4A', 'Computer Science & Engineering', 7.30, 'mid'),
        ('student13', 'karan.malhotra@student.edu', 'Karan Malhotra', 'STU2026013', 'CSE-4A', 'Computer Science & Engineering', 5.50, 'low'), # At risk
        ('student14', 'ishita.banerjee@student.edu', 'Ishita Banerjee', 'STU2026014', 'CSE-4A', 'Computer Science & Engineering', 9.30, 'high'),
        ('student15', 'manish.rao@student.edu', 'Manish Rao', 'STU2026015', 'CSE-4A', 'Computer Science & Engineering', 7.70, 'mid'),
        ('student16', 'siddharth.nair@student.edu', 'Siddharth Nair', 'STU2026016', 'CSE-4B', 'Computer Science & Engineering', 8.50, 'high'),
        ('student17', 'neha.gupta@student.edu', 'Neha Gupta', 'STU2026017', 'CSE-4B', 'Computer Science & Engineering', 6.10, 'low'),
        ('student18', 'varun.chawla@student.edu', 'Varun Chawla', 'STU2026018', 'CSE-4B', 'Computer Science & Engineering', 7.40, 'mid'),
        ('student19', 'ritu.agrawal@student.edu', 'Ritu Agrawal', 'STU2026019', 'CSE-4B', 'Computer Science & Engineering', 8.70, 'high'),
        ('student20', 'harsh.vardhan@student.edu', 'Harsh Vardhan', 'STU2026020', 'CSE-4B', 'Computer Science & Engineering', 6.80, 'mid')
    ]

    student_records = []
    for uname, email, sname, sid_code, ccode, dept, prev_gpa, profile in students_raw:
        uid = db.execute(
            """
            INSERT INTO users (username, email, password_hash, role, full_name, phone, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 1)
            """,
            (uname, email, student_pwd_hash, 'student', sname, '+91 97654 32100')
        )
        st_id = db.execute(
            """
            INSERT INTO students (user_id, student_id, class_id, department, academic_year, contact_phone, emergency_contact, address, date_of_birth, enrollment_status, previous_gpa)
            VALUES (%s, %s, %s, %s, '2025-2026', '+91 97654 32100', '+91 98989 89898', 'College Campus Hostel, Block C', '2004-05-14', 'Active', %s)
            """,
            (uid, sid_code, class_ids[ccode], dept, prev_gpa)
        )
        student_records.append({
            'id': st_id,
            'user_id': uid,
            'student_id': sid_code,
            'name': sname,
            'class_id': class_ids[ccode],
            'class_code': ccode,
            'profile': profile,
            'prev_gpa': prev_gpa
        })

    # 7. Generate 16 days of ATTENDANCE logs (across 5 subjects for CSE-4A)
    # Using dates over past 3 weeks
    today = date.today()
    past_dates = []
    d = today - timedelta(days=24)
    while len(past_dates) < 16:
        if d.weekday() < 5: # Monday to Friday
            past_dates.append(d)
        d += timedelta(days=1)

    cse4a_subs = [subject_ids['CS401'], subject_ids['CS402'], subject_ids['CS403'], subject_ids['CS404'], subject_ids['CS405']]
    faculty_list = [faculty_table_ids['faculty1'], faculty_table_ids['faculty2'], faculty_table_ids['faculty3']]

    for day_idx, att_date in enumerate(past_dates):
        # 2 subjects per day
        subs_today = [cse4a_subs[day_idx % len(cse4a_subs)], cse4a_subs[(day_idx + 1) % len(cse4a_subs)]]
        
        for sub_id in subs_today:
            fac_id = faculty_list[sub_id % len(faculty_list)]
            
            for st in student_records:
                if st['class_code'] != 'CSE-4A':
                    continue

                # Probability based on profile
                if st['profile'] == 'high':
                    # 94% present, 4% on duty, 2% absent
                    p = random.random()
                    status = 'Present' if p < 0.94 else ('On Duty' if p < 0.98 else 'Absent')
                elif st['profile'] == 'mid':
                    # 78% present, 5% on duty, 17% absent
                    p = random.random()
                    status = 'Present' if p < 0.78 else ('On Duty' if p < 0.83 else 'Absent')
                else:
                    # 'low' profile: 60% present, 2% on duty, 38% absent (Clearly <75% low attendance)
                    p = random.random()
                    status = 'Present' if p < 0.60 else ('On Duty' if p < 0.62 else 'Absent')

                remarks = "Official Sports Meet" if status == 'On Duty' else ("Medical leave" if status == 'Absent' and random.random() < 0.3 else None)

                try:
                    db.execute(
                        """
                        INSERT INTO attendance (student_id, class_id, subject_id, faculty_id, attendance_date, status, remarks)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (st['id'], st['class_id'], sub_id, fac_id, str(att_date), status, remarks)
                    )
                except Exception:
                    pass

    # 8. Generate ACADEMIC MARKS
    exam_types = [
        ('Internal 1', 50.0, date.today() - timedelta(days=15)),
        ('Internal 2', 50.0, date.today() - timedelta(days=5)),
        ('Assignment', 25.0, date.today() - timedelta(days=2))
    ]

    for st in student_records:
        if st['class_code'] != 'CSE-4A':
            continue

        for sub_code, sub_id in subject_ids.items():
            fac_id = faculty_table_ids['faculty1'] if 'CS401' in sub_code else faculty_table_ids['faculty2']
            
            for etype, max_m, edate in exam_types:
                if st['profile'] == 'high':
                    marks = round(random.uniform(0.78, 0.96) * max_m, 1)
                elif st['profile'] == 'mid':
                    marks = round(random.uniform(0.60, 0.76) * max_m, 1)
                else: # low
                    marks = round(random.uniform(0.35, 0.58) * max_m, 1)

                try:
                    db.execute(
                        """
                        INSERT INTO academic_marks (student_id, subject_id, exam_type, marks_obtained, max_marks, exam_date, entered_by, remarks)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (st['id'], sub_id, etype, marks, max_m, str(edate), fac_id, "Evaluated")
                    )
                except Exception:
                    pass

    # 9. Run AI Predictions for all students
    print("[SeedData] Running AI Predictions for all students...")
    PredictionService.run_batch_predictions_for_all()

    # 10. Generate Notifications
    # Sample notifications for demo
    for st in student_records:
        if st['profile'] == 'low':
            db.execute(
                """
                INSERT INTO notifications (user_id, student_id, title, message, category, priority, is_read, delivery_status)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 'Delivered')
                """,
                (
                    st['user_id'],
                    st['id'],
                    "CRITICAL: Low Attendance Warning (<75%)",
                    f"Dear {st['name']}, your attendance has fallen below 75%. You are at risk of debarment. Please meet your HOD.",
                    "Low Attendance Warning",
                    "High"
                )
            )
            db.execute(
                """
                INSERT INTO notifications (user_id, student_id, title, message, category, priority, is_read, delivery_status)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 'Delivered')
                """,
                (
                    st['user_id'],
                    st['id'],
                    "AI Academic Risk Advisory",
                    f"AI Analytics has categorized your profile as 'Needs Improvement'. Free remedial tutoring is scheduled this Thursday.",
                    "Academic Risk",
                    "High"
                )
            )
        else:
            db.execute(
                """
                INSERT INTO notifications (user_id, student_id, title, message, category, priority, is_read, delivery_status)
                VALUES (%s, %s, %s, %s, %s, %s, 1, 'Delivered')
                """,
                (
                    st['user_id'],
                    st['id'],
                    "Semester Timetable Updated",
                    "The timetable for Semester 4 has been finalized. Please check your schedule.",
                    "General Notice",
                    "Low"
                )
            )

    print("[SeedData] Seeding complete! 1 Admin, 3 Faculty, 20 Students, 5 Subjects, 4 Classes, 500+ Attendance records, Marks, and AI predictions ready.")

if __name__ == '__main__':
    seed_database()
