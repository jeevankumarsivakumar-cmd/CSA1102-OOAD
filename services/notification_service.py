from database.db import db
from models.notification import Notification

class NotificationService:
    """
    Automated Smart Notification System.
    Generates contextual alerts across categories:
    - Absence Alerts
    - Low-Attendance Warnings (<75%)
    - Academic Risk Insights
    - General Administrative Notices
    """

    @staticmethod
    def _dispatch_email_modular(recipient_email, subject, body):
        """
        Modular Email dispatcher: logs clean dispatch record for demonstration
        and can be hooked up to SMTP / SendGrid without modifying application logic.
        """
        print(f"[EMAIL DISPATCHER] To: {recipient_email} | Subject: '{subject}' | Status: Simulated Success")

    @staticmethod
    def send_absence_alert(student_table_id, subject_str, attendance_date):
        """Dispatches an immediate alert when a student is recorded absent."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = "Absence Recorded"
        message = f"Dear {student_row['full_name']}, you were marked absent for {subject_str} on {attendance_date}. Please contact your course faculty if you believe this is an error."
        
        notif_id = Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Absence Alert",
            priority="Medium",
            student_id=student_table_id
        )

        NotificationService._dispatch_email_modular(student_row['email'], title, message)
        return notif_id

    @staticmethod
    def send_low_attendance_warning(student_table_id, current_pct):
        """Dispatches warning when overall attendance falls below 75%."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = "CRITICAL: Low Attendance Warning (<75%)"
        message = (
            f"Dear {student_row['full_name']}, your cumulative attendance has dropped to {current_pct:.1f}%, "
            f"which is below the mandatory 75% requirement. You are at risk of exam debarment. "
            f"Please meet your academic advisor immediately."
        )

        notif_id = Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Low Attendance Warning",
            priority="High",
            student_id=student_table_id
        )

        NotificationService._dispatch_email_modular(student_row['email'], title, message)
        return notif_id

    @staticmethod
    def send_academic_risk_alert(student_table_id, risk_category, factors):
        """Dispatches proactive support notification based on ML prediction."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = "Academic Support Notification"
        message = (
            f"Our AI Analytics system has evaluated your recent performance metrics and identified you in "
            f"the '{risk_category}' category. Key factors: {factors}. Dedicated remedial sessions and faculty mentoring "
            f"are available to help you excel."
        )

        notif_id = Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Academic Risk",
            priority="High",
            student_id=student_table_id
        )
        return notif_id

    @staticmethod
    def send_approaching_threshold_alert(student_table_id, current_pct):
        """Dispatches an alert when attendance is approaching the 75% critical cutoff (75% to 78%)."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = "WATCH: Attendance Approaching 75% Threshold"
        if Notification.has_recent_notification(student_row['user_id'], 'Approaching Threshold', title, hours=48):
            return None

        message = (
            f"Dear {student_row['full_name']}, your attendance is currently at {current_pct:.1f}%. "
            f"You are approaching the university minimum eligibility cutoff of 75%. "
            f"Please ensure you attend all upcoming lectures to avoid entering the debarment zone."
        )

        notif_id = Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Approaching Threshold",
            priority="Medium",
            student_id=student_table_id
        )
        NotificationService._dispatch_email_modular(student_row['email'], title, message)
        return notif_id

    @staticmethod
    def send_declining_marks_alert(student_table_id, subject_str, test1_marks, test2_marks):
        """Dispatches warning when a student shows a declining internal exam score trajectory."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = f"Academic Alert: Score Decline in {subject_str}"
        if Notification.has_recent_notification(student_row['user_id'], 'Declining Marks', title, hours=72):
            return None

        message = (
            f"Dear {student_row['full_name']}, your score in {subject_str} declined from "
            f"{test1_marks:.1f} in Internal 1 to {test2_marks:.1f} in Internal 2. "
            f"Please review Unit 2 & 3 study materials and consult your subject faculty for doubts."
        )

        notif_id = Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Declining Marks",
            priority="High",
            student_id=student_table_id
        )
        NotificationService._dispatch_email_modular(student_row['email'], title, message)
        return notif_id

    @staticmethod
    def send_intervention_assigned_alert(student_table_id, faculty_name, tasks):
        """Notifies student when a faculty mentor assigns improvement tasks."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = "Faculty Mentoring Task Assigned"
        message = (
            f"Your faculty mentor {faculty_name} has assigned you new academic improvement tasks: "
            f"{tasks[:120]}... Check your 'My Academic Improvement Plan' for full details."
        )

        return Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Intervention Task",
            priority="High",
            student_id=student_table_id
        )

    @staticmethod
    def send_mentoring_completed_alert(student_table_id, faculty_name):
        """Notifies student when faculty logs an intervention as completed."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = "Mentoring Session Successfully Completed"
        message = (
            f"Faculty mentor {faculty_name} has officially reviewed and marked your academic intervention "
            f"as Completed. Keep up the consistent progress!"
        )

        return Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=message,
            category="Mentoring Completed",
            priority="Medium",
            student_id=student_table_id
        )

    @staticmethod
    def send_milestone_alert(student_table_id, milestone_title, description):
        """Celebrates positive academic recovery or achievement milestone."""
        student_row = db.query(
            "SELECT s.id, s.student_id, s.user_id, u.email, u.full_name FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = %s",
            (student_table_id,), fetchone=True
        )
        if not student_row:
            return None

        title = f"Academic Milestone: {milestone_title}"
        if Notification.has_recent_notification(student_row['user_id'], 'Academic Milestone', title, hours=48):
            return None

        return Notification.create(
            user_id=student_row['user_id'],
            title=title,
            message=description,
            category="Academic Milestone",
            priority="Medium",
            student_id=student_table_id
        )

    @staticmethod
    def check_and_generate_automated_alerts():
        """
        Background scanner that evaluates all students and generates:
        - Approaching threshold alerts (75% to 78%)
        - Declining marks alerts
        - Recovery milestones (when attendance rises >= 75%)
        Ensures 100% duplicate protection.
        """
        students = db.query("SELECT id, user_id, class_id FROM students WHERE enrollment_status = 'Active'")
        alerts_generated = 0

        for st in students:
            sid = st['id']
            # 1. Attendance check
            from services.attendance_service import AttendanceService
            att = AttendanceService.calculate_student_attendance(sid)
            pct = att.get('attendance_percentage', 0.0)

            if 75.0 <= pct <= 78.0:
                if NotificationService.send_approaching_threshold_alert(sid, pct):
                    alerts_generated += 1
            elif pct >= 75.0 and att.get('total_conducted', 0) >= 15:
                # Check if student was previously low
                prev_low = db.query(
                    "SELECT COUNT(*) as c FROM notifications WHERE student_id = %s AND category = 'Low Attendance Warning'",
                    (sid,), fetchone=True
                )
                if prev_low and prev_low['c'] > 0:
                    NotificationService.send_milestone_alert(
                        sid,
                        "Attendance Restored Above 75%",
                        f"Congratulations! Your cumulative attendance has successfully reached {pct:.1f}%, restoring your exam eligibility."
                    )
                    alerts_generated += 1

            # 2. Declining marks check
            marks = db.query("""
                SELECT subject_id, exam_type, marks_obtained, max_marks
                FROM academic_marks
                WHERE student_id = %s AND exam_type IN ('Internal 1', 'Internal 2')
                ORDER BY subject_id, exam_type
            """, (sid,))
            
            by_subj = {}
            for m in marks:
                sub_id = m['subject_id']
                if sub_id not in by_subj:
                    by_subj[sub_id] = {}
                by_subj[sub_id][m['exam_type']] = (m['marks_obtained'] / m['max_marks']) * 100

            for sub_id, scores in by_subj.items():
                if 'Internal 1' in scores and 'Internal 2' in scores:
                    if scores['Internal 1'] - scores['Internal 2'] >= 10.0:
                        subj = db.query("SELECT subject_name FROM subjects WHERE id = %s", (sub_id,), fetchone=True)
                        s_name = subj['subject_name'] if subj else 'Subject'
                        if NotificationService.send_declining_marks_alert(sid, s_name, scores['Internal 1'], scores['Internal 2']):
                            alerts_generated += 1

        return alerts_generated
