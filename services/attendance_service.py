from datetime import datetime, date, timedelta
from database.db import db
from models.attendance import AttendanceSession, AttendanceRecord
from config import Config

class AttendanceService:
    """
    Service Layer: Encapsulates attendance business logic,
    calculations, duplicate prevention, and automatic warning triggers.
    """
    
    @staticmethod
    def calculate_student_attendance(student_id):
        """
        Calculates overall attendance percentage and absence metrics for a student.
        Formula: (Present + On Duty) / Total Conducted * 100
        """
        sql = """
            SELECT 
                COUNT(*) as total_conducted,
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'On Duty' THEN 1 ELSE 0 END) as on_duty_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count
            FROM attendance
            WHERE student_id = %s
        """
        res = db.query(sql, (student_id,), fetchone=True)
        if not res or res['total_conducted'] == 0:
            return {
                'total_conducted': 0,
                'attended_count': 0,
                'present_count': 0,
                'on_duty_count': 0,
                'absent_count': 0,
                'attendance_percentage': 100.0,
                'is_low_attendance': False
            }

        total = res['total_conducted']
        present = res['present_count'] or 0
        on_duty = res['on_duty_count'] or 0
        absent = res['absent_count'] or 0
        attended = present + on_duty
        pct = round((attended / total) * 100, 2)

        return {
            'total_conducted': total,
            'attended_count': attended,
            'present_count': present,
            'on_duty_count': on_duty,
            'absent_count': absent,
            'attendance_percentage': pct,
            'is_low_attendance': pct < Config.ATTENDANCE_WARNING_THRESHOLD
        }

    @staticmethod
    def get_subject_wise_attendance(student_id):
        """
        Returns breakdown of attendance for every enrolled subject.
        """
        sql = """
            SELECT 
                s.id as subject_id,
                s.subject_code,
                s.subject_name,
                COUNT(a.id) as total_classes,
                SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as attended_classes,
                SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent_classes
            FROM subjects s
            LEFT JOIN attendance a ON s.id = a.subject_id AND a.student_id = %s
            GROUP BY s.id, s.subject_code, s.subject_name
            HAVING total_classes > 0
            ORDER BY s.subject_code
        """
        rows = db.query(sql, (student_id,))
        for r in rows:
            tot = r['total_classes']
            att = r['attended_classes'] or 0
            r['percentage'] = round((att / tot) * 100, 2) if tot > 0 else 100.0
            r['is_low'] = r['percentage'] < Config.ATTENDANCE_WARNING_THRESHOLD
        return rows

    @staticmethod
    def get_student_absence_history(student_id, limit=30):
        """Returns detailed absence events for a student."""
        sql = """
            SELECT a.id, a.attendance_date, a.status, a.remarks,
                   s.subject_code, s.subject_name,
                   u.full_name as faculty_name
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            JOIN faculty f ON a.faculty_id = f.id
            JOIN users u ON f.user_id = u.id
            WHERE a.student_id = %s AND a.status = 'Absent'
            ORDER BY a.attendance_date DESC
            LIMIT %s
        """
        return db.query(sql, (student_id, limit))

    @staticmethod
    def record_class_attendance(class_id, subject_id, faculty_id, attendance_date, attendance_data, allow_update=False):
        """
        Records attendance for an entire class and triggers smart notifications.
        attendance_data: list of dicts [{'student_id': 1, 'status': 'Present', 'remarks': ''}]
        """
        from services.notification_service import NotificationService

        session = AttendanceSession(class_id, subject_id, faculty_id, attendance_date)
        for item in attendance_data:
            session.add_record(
                student_id=item['student_id'],
                status=item['status'],
                remarks=item.get('remarks')
            )

        count, absent_ids = session.save(allow_update=allow_update)

        # Subject details for notification context
        sub_info = db.query("SELECT subject_code, subject_name FROM subjects WHERE id = %s", (subject_id,), fetchone=True)
        sub_str = f"{sub_info['subject_code']} - {sub_info['subject_name']}" if sub_info else "Class"

        # Trigger smart absence alerts and check low-attendance status
        for st_id in absent_ids:
            NotificationService.send_absence_alert(st_id, sub_str, attendance_date)
            # Check if student drops below threshold
            stats = AttendanceService.calculate_student_attendance(st_id)
            if stats['is_low_attendance']:
                NotificationService.send_low_attendance_warning(st_id, stats['attendance_percentage'])

        return count, len(absent_ids)

    @staticmethod
    def get_class_attendance_summary(class_id, target_date=None):
        """Class-level metrics for faculty and admin dashboards."""
        if not target_date:
            target_date = str(date.today())

        sql = """
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count
            FROM attendance
            WHERE class_id = %s AND attendance_date = %s
        """
        res = db.query(sql, (class_id, target_date), fetchone=True)
        tot = res['total_records'] if res else 0
        pres = res['present_count'] or 0 if res else 0
        pct = round((pres / tot) * 100, 2) if tot > 0 else 0.0
        return {
            'date': target_date,
            'total_marked': tot,
            'present_count': pres,
            'absent_count': res['absent_count'] or 0 if res else 0,
            'attendance_rate': pct
        }

    @staticmethod
    def get_attendance_trend(days=14):
        """Daily attendance trends over the last N days."""
        sql = """
            SELECT 
                attendance_date,
                COUNT(*) as total_logged,
                SUM(CASE WHEN status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count
            FROM attendance
            WHERE attendance_date >= DATE('now', '-' || %s || ' day')
            GROUP BY attendance_date
            ORDER BY attendance_date ASC
        """
        if db.get_engine_name() == 'MYSQL':
            sql = """
                SELECT 
                    attendance_date,
                    COUNT(*) as total_logged,
                    SUM(CASE WHEN status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as present_count,
                    SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_count
                FROM attendance
                WHERE attendance_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY attendance_date
                ORDER BY attendance_date ASC
            """
        rows = db.query(sql, (days,))
        trend = []
        for r in rows:
            tot = r['total_logged']
            pres = r['present_count'] or 0
            trend.append({
                'date': str(r['attendance_date']),
                'total': tot,
                'present': pres,
                'absent': r['absent_count'] or 0,
                'percentage': round((pres / tot) * 100, 1) if tot > 0 else 0.0
            })
        return trend
