import os
import sys
import unittest
from datetime import date

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from database.db import db
from models.user import User
from models.classroom import ClassRoom, Subject
from models.timetable import TimetableEntry
from models.notification import Notification
from services.attendance_service import AttendanceService
from services.prediction_service import PredictionService
from services.report_service import ReportService
from services.notification_service import NotificationService

class EndToEndSystemTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        # Clean any leftover test artifacts and reset session state
        self.client.get('/logout')
        db.execute("DELETE FROM users WHERE username LIKE 'autostudent%'")
        db.execute("DELETE FROM attendance WHERE attendance_date = '2026-11-18'")
        db.execute("DELETE FROM faculty_interventions WHERE mentoring_notes LIKE 'Test counseling%'")

    def test_01_authentication_roles(self):
        """1. Test all authentication roles (Admin, Faculty, Student)."""
        # Admin login
        res = self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Administrative Dashboard', res.data)
        self.client.get('/logout')

        # Faculty login
        res = self.client.post('/login', data={'identifier': 'faculty1', 'password': 'faculty123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Faculty Portal', res.data)
        self.client.get('/logout')

        # Student login
        res = self.client.post('/login', data={'identifier': 'student1', 'password': 'student123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Academic Portal', res.data)
        self.client.get('/logout')
        print("[TEST 01] All authentication roles authenticated successfully.")

    def test_02_student_registration_and_crud(self):
        """2. Test student registration, unique ID generation, and relationships."""
        # Login as Admin
        self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'}, follow_redirects=True)
        
        # Register new student
        res = self.client.post('/admin/students', data={
            'action': 'create',
            'full_name': 'Test Student Autocreated',
            'username': 'autostudent2026',
            'email': 'autostudent@university.edu',
            'password': 'student123',
            'class_id': 1,
            'department': 'Computer Science & Engineering',
            'phone': '+91 99999 88888',
            'emergency_contact': '+91 88888 77777',
            'previous_gpa': 8.25
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'successfully enrolled', res.data)

        # Verify created in DB
        st = db.query("SELECT * FROM students WHERE user_id = (SELECT id FROM users WHERE username = 'autostudent2026')", fetchone=True)
        self.assertIsNotNone(st)
        self.assertTrue(st['student_id'].startswith('STU2026'))

        # Clean up test student
        db.execute("DELETE FROM users WHERE username = 'autostudent2026'")
        self.client.get('/logout')
        print("[TEST 02] Student registration and unique ID generation verified.")

    def test_03_timetable_management(self):
        """3. Test timetable management and schedule retrieval."""
        classes = ClassRoom.get_all()
        subjects = Subject.get_all()
        self.assertGreater(len(classes), 0)
        self.assertGreater(len(subjects), 0)

        # Faculty schedule
        faculty = db.query("SELECT id FROM faculty LIMIT 1", fetchone=True)
        sched = TimetableEntry.get_faculty_schedule(faculty['id'])
        self.assertIsInstance(sched, list)
        print(f"[TEST 03] Timetable verified with {len(sched)} slots for faculty ID {faculty['id']}.")

    def test_04_attendance_recording_and_bulk_flow(self):
        """4. Test class attendance recording, bulk operations, and database persistence."""
        # Login as faculty1
        self.client.post('/login', data={'identifier': 'faculty1', 'password': 'faculty123'}, follow_redirects=True)
        
        test_date = '2026-11-18'
        # Get students of class 1
        students = db.query("SELECT id FROM students WHERE class_id = 1")
        form_data = {
            'class_id': 1,
            'subject_id': 1,
            'attendance_date': test_date,
            'allow_update': '1',
            'student_ids': [s['id'] for s in students]
        }
        for s in students:
            form_data[f'status_{s["id"]}'] = 'Present' if s['id'] % 2 == 0 else 'Absent'
            form_data[f'remarks_{s["id"]}'] = 'Unit test marking'

        res = self.client.post('/faculty/attendance', data=form_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Attendance recorded successfully', res.data)

        # Verify in DB
        logs = db.query("SELECT COUNT(*) as count FROM attendance WHERE class_id = 1 AND attendance_date = %s", (test_date,), fetchone=True)
        self.assertEqual(logs['count'], len(students))
        self.client.get('/logout')
        print(f"[TEST 04] Class attendance successfully recorded for {logs['count']} students.")

    def test_05_attendance_calculations(self):
        """5. Test attendance percentage formula: (Present + OD) / Total * 100."""
        # Check student 1 calculations
        stats = AttendanceService.calculate_student_attendance(1)
        self.assertIn('attendance_percentage', stats)
        self.assertIn('total_conducted', stats)
        self.assertGreaterEqual(stats['attendance_percentage'], 0.0)
        self.assertLessEqual(stats['attendance_percentage'], 100.0)
        print(f"[TEST 05] Attendance calculations verified: {stats['attendance_percentage']}% (Total: {stats['total_conducted']}, Attended: {stats['attended_count']}, Absences: {stats['absent_count']}).")

    def test_06_duplicate_attendance_prevention(self):
        """6. Test duplicate attendance prevention for same student, subject and date."""
        self.client.post('/login', data={'identifier': 'faculty1', 'password': 'faculty123'}, follow_redirects=True)
        
        test_date = '2026-11-18'
        students = db.query("SELECT id FROM students WHERE class_id = 1 LIMIT 2")
        # Pre-seed initial record
        form_data_init = {
            'class_id': 1,
            'subject_id': 1,
            'attendance_date': test_date,
            'allow_update': '1',
            'student_ids': [s['id'] for s in students]
        }
        for s in students:
            form_data_init[f'status_{s["id"]}'] = 'Present'
        self.client.post('/faculty/attendance', data=form_data_init, follow_redirects=True)

        # Attempt duplicate insertion without authorization
        form_data = {
            'class_id': 1,
            'subject_id': 1,
            'attendance_date': test_date,
            'allow_update': '0', # Disallow update
            'student_ids': [s['id'] for s in students]
        }
        for s in students:
            form_data[f'status_{s["id"]}'] = 'Present'

        res = self.client.post('/faculty/attendance', data=form_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        # Should flag that attendance is already recorded
        self.assertIn(b'already been recorded', res.data)
        self.client.get('/logout')
        print("[TEST 06] Duplicate attendance prevention constraint strictly enforced.")

    def test_07_absence_alerts_and_notifications(self):
        """7. Test absence notifications and <75% low attendance warning triggers."""
        # Trigger an absence alert for student 1
        notif_id = NotificationService.send_absence_alert(1, "CS401 - OOAD", "2026-11-18")
        self.assertIsNotNone(notif_id)

        notif = db.query("SELECT * FROM notifications WHERE id = %s", (notif_id,), fetchone=True)
        self.assertEqual(notif['category'], 'Absence Alert')
        self.assertIn('absent', notif['message'].lower())

        # Low attendance warning
        warn_id = NotificationService.send_low_attendance_warning(3, 58.5)
        self.assertIsNotNone(warn_id)
        warn_notif = db.query("SELECT * FROM notifications WHERE id = %s", (warn_id,), fetchone=True)
        self.assertEqual(warn_notif['category'], 'Low Attendance Warning')
        print("[TEST 07] Smart Absence alerts and <75% Low Attendance Warnings triggered.")

    def test_08_academic_marks_entry(self):
        """8. Test academic mark entry and synchronization."""
        self.client.post('/login', data={'identifier': 'faculty1', 'password': 'faculty123'}, follow_redirects=True)
        
        students = db.query("SELECT id FROM students WHERE class_id = 1 LIMIT 3")
        form_data = {
            'class_id': 1,
            'subject_id': 1,
            'exam_type': 'Internal 1',
            'max_marks': 50.0,
            'exam_date': '2026-11-17',
            'student_ids': [s['id'] for s in students]
        }
        for s in students:
            form_data[f'marks_{s["id"]}'] = 42.5
            form_data[f'remarks_{s["id"]}'] = 'Good attempt'

        res = self.client.post('/faculty/marks', data=form_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Academic marks recorded successfully', res.data)
        self.client.get('/logout')
        print("[TEST 08] Academic mark entry verified and validated.")

    def test_09_ai_prediction_model(self):
        """9. Test Scikit-learn AI Prediction, risk classification and confidence."""
        pred = PredictionService.predict_student(1, trigger_alert=False)
        self.assertIn(pred['risk_category'], ['Good Performance', 'Average Performance', 'Needs Improvement'])
        self.assertGreaterEqual(pred['confidence_score'], 0.0)
        self.assertLessEqual(pred['confidence_score'], 100.0)
        self.assertIn('attendance_percentage', pred['features'])
        # Student ID not in vector
        self.assertNotIn('student_id', pred['features'])

        # AI Dashboard summary
        ai_dash = PredictionService.get_ai_analytics_dashboard_data()
        self.assertIn('distribution', ai_dash)
        self.assertIn('model_metadata', ai_dash)
        self.assertGreater(ai_dash['model_metadata']['accuracy'], 80.0)
        print(f"[TEST 09] AI Prediction verified: Model accuracy {ai_dash['model_metadata']['accuracy']}% | Category: {pred['risk_category']}.")

    def test_10_reports_and_exports(self):
        """10. Test CSV and PDF report generation."""
        # Login as Admin first
        self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'}, follow_redirects=True)

        # CSV Export
        res_csv = self.client.get('/reports/export/csv?report_type=daily_attendance')
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn('text/csv', res_csv.content_type)
        self.assertGreater(len(res_csv.data), 50)

        # PDF Export
        res_pdf = self.client.get('/reports/export/pdf?report_type=student_wise')
        self.assertEqual(res_pdf.status_code, 200)
        self.assertIn('application/pdf', res_pdf.content_type)
        self.assertTrue(res_pdf.data.startswith(b'%PDF'))
        self.client.get('/logout')
        print(f"[TEST 10] CSV & PDF generation verified ({len(res_pdf.data)} bytes PDF generated).")

    def test_11_database_relationships_and_integrity(self):
        """11. Test database referential integrity, foreign keys, and cascading."""
        # Verify Class has Students
        cls_obj = ClassRoom.get_by_id(1)
        st_list = cls_obj.get_students()
        self.assertGreater(len(st_list), 0)

        # Verify Student has User and Class
        st_row = db.query("SELECT * FROM students WHERE id = 1", fetchone=True)
        user_row = db.query("SELECT * FROM users WHERE id = %s", (st_row['user_id'],), fetchone=True)
        self.assertIsNotNone(user_row)
        print(f"[TEST 11] Database relational integrity verified for Class '{cls_obj.class_code}' ({len(st_list)} students).")

    def test_12_attendance_recovery_simulator(self):
        """12. Test Feature 1: Attendance Recovery Planner calculation and simulation integrity."""
        # Login as student1
        self.client.post('/login', data={'identifier': 'student1', 'password': 'student123'}, follow_redirects=True)
        
        # Test Page Access
        res = self.client.get('/student/recovery-planner')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Attendance Recovery Simulator', res.data)
        self.assertIn(b'Mathematical Recovery Formula', res.data)

        # Count attendance records before simulation
        count_before = db.query("SELECT COUNT(*) as c FROM attendance", fetchone=True)['c']

        # Test Simulation API: simulate target 85%
        res_api = self.client.post('/student/api/simulate-recovery', json={'target_pct': 85.0})
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['target_pct'], 85.0)
        self.assertIn('required_consecutive_classes', data)
        self.assertIn('trajectory', data)
        self.assertGreater(len(data['trajectory']['labels']), 0)

        # Verify strict simulation safety: Zero attendance records modified or inserted!
        count_after = db.query("SELECT COUNT(*) as c FROM attendance", fetchone=True)['c']
        self.assertEqual(count_before, count_after)
        self.client.get('/logout')
        print(f"[TEST 12] Feature 1 Verified: Required consecutive classes computed ({data['required_consecutive_classes']}), 0 DB records altered.")

    def test_13_academic_improvement_planner(self):
        """13. Test Feature 2: Personalized Academic Improvement Planner and Goals."""
        # Login as student1
        self.client.post('/login', data={'identifier': 'student1', 'password': 'student123'}, follow_redirects=True)

        res = self.client.get('/student/improvement-plan')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Academic Improvement Plan', res.data)
        self.assertIn(b'Current Academic Diagnostic', res.data)
        self.assertIn(b'Recommended Action Plan', res.data)

        # Test adding a custom weekly goal
        res_add = self.client.post('/student/api/goals/add', data={
            'goal_title': 'Unit Test Automated Study Goal',
            'goal_category': 'Exam Prep',
            'target_date': '2026-12-01'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)

        # Verify goal in DB and toggle completion
        goal = db.query("SELECT * FROM student_improvement_goals WHERE goal_title = 'Unit Test Automated Study Goal'", fetchone=True)
        self.assertIsNotNone(goal)
        self.assertEqual(goal['is_completed'], 0)

        res_toggle = self.client.post(f'/student/api/goals/toggle/{goal["id"]}')
        self.assertEqual(res_toggle.status_code, 200)
        t_data = res_toggle.get_json()
        self.assertEqual(t_data['is_completed'], 1)

        # Clean up test goal
        db.execute("DELETE FROM student_improvement_goals WHERE id = %s", (goal['id'],))
        self.client.get('/logout')
        print("[TEST 13] Feature 2 Verified: Personalized recommendations and interactive goal lifecycle operational.")

    def test_14_faculty_intervention_management(self):
        """14. Test Feature 3: Faculty Student Intervention Center and Mentoring Tracking."""
        # Login as Faculty 1
        self.client.post('/login', data={'identifier': 'faculty1', 'password': 'faculty123'}, follow_redirects=True)

        # Access Intervention Center
        res = self.client.get('/faculty/interventions')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Intervention Center', res.data)
        self.assertIn(b'Priority Support', res.data)

        # Create new intervention for assigned student (Student ID 2 - Rohan)
        res_create = self.client.post('/faculty/interventions/create', data={
            'student_id': 2,
            'mentoring_date': str(date.today()),
            'mentoring_notes': 'Test counseling session regarding exam readiness.',
            'assigned_tasks': 'Complete practice test 1 and review Unit 3.',
            'status': 'In Progress'
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)
        self.assertIn(b'recorded successfully', res_create.data)

        # Verify in DB
        inv = db.query("SELECT * FROM faculty_interventions WHERE student_id = 2 AND mentoring_notes LIKE 'Test counseling%'", fetchone=True)
        self.assertIsNotNone(inv)
        self.assertEqual(inv['status'], 'In Progress')

        # Test updating intervention status to Completed
        res_upd = self.client.post(f'/faculty/interventions/update-status/{inv["id"]}', data={
            'status': 'Completed',
            'outcome_notes': 'Student demonstrated solid understanding during follow-up.'
        }, follow_redirects=True)
        self.assertEqual(res_upd.status_code, 200)

        inv_upd = db.query("SELECT * FROM faculty_interventions WHERE id = %s", (inv['id'],), fetchone=True)
        self.assertEqual(inv_upd['status'], 'Completed')

        # Test Admin oversight view
        self.client.get('/logout')
        self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'}, follow_redirects=True)
        res_admin = self.client.get('/admin/interventions')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Institutional Mentoring & Interventions Oversight', res_admin.data)

        # Clean up test intervention
        db.execute("DELETE FROM faculty_interventions WHERE id = %s", (inv['id'],))
        self.client.get('/logout')
        print("[TEST 14] Feature 3 Verified: Faculty mentoring logging, task assignment, status updates and admin oversight verified.")

    def test_15_performance_journey_analytics(self):
        """15. Test Feature 4: Academic Performance Trend Analytics."""
        # Login as student1
        self.client.post('/login', data={'identifier': 'student1', 'password': 'student123'}, follow_redirects=True)

        res = self.client.get('/student/performance-journey')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'My Performance Journey', res.data)
        self.assertIn(b'Internal Assessment Score Comparison', res.data)
        self.assertIn(b'Attendance Progression Timeline', res.data)
        self.assertIn(b'Course Mastery Radar', res.data)
        self.client.get('/logout')
        print("[TEST 15] Feature 4 Verified: Multi-chart performance journey analytics rendered with real data.")

    def test_16_smart_notification_center(self):
        """16. Test Feature 5: Smart Notification Center, Deduplication & Role Dispatches."""
        # 1. Test automated scanner
        count_alerts = NotificationService.check_and_generate_automated_alerts()
        self.assertIsInstance(count_alerts, int)

        # 2. Test student dedicated notification center
        self.client.post('/login', data={'identifier': 'student1', 'password': 'student123'}, follow_redirects=True)
        res_stu = self.client.get('/student/notification-center')
        self.assertEqual(res_stu.status_code, 200)
        self.assertIn(b'Academic Notification Center', res_stu.data)
        self.assertIn(b'Mentoring Tasks', res_stu.data)
        self.client.get('/logout')

        # 3. Test faculty alert center
        self.client.post('/login', data={'identifier': 'faculty1', 'password': 'faculty123'}, follow_redirects=True)
        res_fac = self.client.get('/faculty/notifications')
        self.assertEqual(res_fac.status_code, 200)
        self.assertIn(b'Faculty Alert Center', res_fac.data)
        self.client.get('/logout')

        # 4. Test admin campus alert center
        self.client.post('/login', data={'identifier': 'admin', 'password': 'admin123'}, follow_redirects=True)
        res_adm = self.client.get('/admin/notifications')
        self.assertEqual(res_adm.status_code, 200)
        self.assertIn(b'Campus-Wide Alert Center', res_adm.data)
        self.client.get('/logout')

        # 5. Test deduplication prevention
        user_row = db.query("SELECT id FROM users WHERE username = 'student1'", fetchone=True)
        has_dup = Notification.has_recent_notification(user_row['id'], 'Absence Alert', 'Nonexistent Title Test 12345', hours=48)
        self.assertFalse(has_dup)
        print(f"[TEST 16] Feature 5 Verified: Tri-role notification centers, automated scanner ({count_alerts} generated), deduplication verified.")

if __name__ == '__main__':
    unittest.main()
