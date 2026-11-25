from datetime import datetime
from database.db import db
from config import Config

class AttendanceRecord:
    """
    Encapsulates a single attendance record.
    Implements business rules regarding attendance statuses and timestamps.
    """
    VALID_STATUSES = ('Present', 'Absent', 'On Duty')

    def __init__(self, id=None, student_id=None, class_id=None, subject_id=None,
                 faculty_id=None, attendance_date=None, status='Present', remarks=None,
                 recorded_at=None, **kwargs):
        self.id = id
        self.student_id = student_id
        self.class_id = class_id
        self.subject_id = subject_id
        self.faculty_id = faculty_id
        self.attendance_date = str(attendance_date) if attendance_date else str(datetime.now().date())
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid attendance status: {status}. Allowed: {self.VALID_STATUSES}")
        self.status = status
        self.remarks = remarks
        self.recorded_at = recorded_at
        self.extra = kwargs

    def is_present(self):
        # Present and On Duty are considered present for academic purposes
        return self.status in ('Present', 'On Duty')

    def is_absent(self):
        return self.status == 'Absent'

    def is_on_duty(self):
        return self.status == 'On Duty'

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'class_id': self.class_id,
            'subject_id': self.subject_id,
            'faculty_id': self.faculty_id,
            'attendance_date': self.attendance_date,
            'status': self.status,
            'remarks': self.remarks,
            'recorded_at': str(self.recorded_at) if self.recorded_at else None
        }


class AttendanceSession:
    """
    Composition Class: Manages a batch of AttendanceRecord objects for a whole class,
    date, and subject. Enforces duplicate prevention and atomic batch saving.
    """
    def __init__(self, class_id, subject_id, faculty_id, attendance_date):
        self.class_id = class_id
        self.subject_id = subject_id
        self.faculty_id = faculty_id
        self.attendance_date = attendance_date
        self.records = []

    def add_record(self, student_id, status, remarks=None):
        record = AttendanceRecord(
            student_id=student_id,
            class_id=self.class_id,
            subject_id=self.subject_id,
            faculty_id=self.faculty_id,
            attendance_date=self.attendance_date,
            status=status,
            remarks=remarks
        )
        self.records.append(record)

    def is_already_recorded(self):
        """Check if attendance has already been recorded for this class, subject, and date."""
        sql = """
            SELECT COUNT(*) as count FROM attendance 
            WHERE class_id = %s AND subject_id = %s AND attendance_date = %s
        """
        res = db.query(sql, (self.class_id, self.subject_id, self.attendance_date), fetchone=True)
        return (res['count'] if res else 0) > 0

    def save(self, allow_update=False):
        """
        Persist session records to database with duplicate prevention.
        Returns tuple: (saved_count, absent_student_ids)
        """
        if self.is_already_recorded() and not allow_update:
            raise ValueError(f"Attendance for Subject ID {self.subject_id} on {self.attendance_date} has already been recorded.")

        absent_student_ids = []
        for rec in self.records:
            if rec.status == 'Absent':
                absent_student_ids.append(rec.student_id)

            # Insert or Update on duplicate
            if db.get_engine_name() == 'MYSQL':
                sql = """
                    INSERT INTO attendance (student_id, class_id, subject_id, faculty_id, attendance_date, status, remarks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE status = VALUES(status), remarks = VALUES(remarks), faculty_id = VALUES(faculty_id)
                """
                db.execute(sql, (rec.student_id, rec.class_id, rec.subject_id, rec.faculty_id, rec.attendance_date, rec.status, rec.remarks))
            else:
                # SQLite INSERT OR REPLACE
                sql = """
                    INSERT INTO attendance (student_id, class_id, subject_id, faculty_id, attendance_date, status, remarks)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(student_id, subject_id, attendance_date) 
                    DO UPDATE SET status=excluded.status, remarks=excluded.remarks, faculty_id=excluded.faculty_id
                """
                db.execute(sql, (rec.student_id, rec.class_id, rec.subject_id, rec.faculty_id, rec.attendance_date, rec.status, rec.remarks))

        return len(self.records), absent_student_ids
