from database.db import db

class ExamMark:
    """Encapsulates a single internal/final examination mark entry."""
    def __init__(self, id=None, student_id=None, subject_id=None, exam_type="Internal 1",
                 marks_obtained=0.0, max_marks=50.0, exam_date=None, entered_by=None,
                 remarks=None, recorded_at=None, **kwargs):
        self.id = id
        self.student_id = student_id
        self.subject_id = subject_id
        self.exam_type = exam_type
        self.marks_obtained = float(marks_obtained)
        self.max_marks = float(max_marks)
        self.exam_date = exam_date
        self.entered_by = entered_by
        self.remarks = remarks
        self.recorded_at = recorded_at
        self.extra = kwargs

    @property
    def percentage(self):
        if self.max_marks <= 0:
            return 0.0
        return round((self.marks_obtained / self.max_marks) * 100, 2)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'exam_type': self.exam_type,
            'marks_obtained': self.marks_obtained,
            'max_marks': self.max_marks,
            'percentage': self.percentage,
            'exam_date': str(self.exam_date) if self.exam_date else None,
            'remarks': self.remarks
        }


class AcademicRecord:
    """
    Aggregation Class: Aggregates all marks, subject-wise scores and GPA for a student.
    Provides academic performance analysis methods.
    """
    def __init__(self, student_id):
        self.student_id = student_id

    def get_all_marks(self):
        sql = """
            SELECT m.*, s.subject_code, s.subject_name, s.credits, u.full_name as faculty_name
            FROM academic_marks m
            JOIN subjects s ON m.subject_id = s.id
            JOIN faculty f ON m.entered_by = f.id
            JOIN users u ON f.user_id = u.id
            WHERE m.student_id = %s
            ORDER BY m.exam_date DESC, s.subject_code
        """
        return db.query(sql, (self.student_id,))

    def get_average_percentage(self):
        sql = """
            SELECT AVG((marks_obtained / max_marks) * 100) as avg_pct
            FROM academic_marks
            WHERE student_id = %s
        """
        r = db.query(sql, (self.student_id,), fetchone=True)
        return round(r['avg_pct'], 2) if r and r['avg_pct'] is not None else 0.0

    def get_subject_averages(self):
        sql = """
            SELECT s.id as subject_id, s.subject_code, s.subject_name,
                   AVG((m.marks_obtained / m.max_marks) * 100) as avg_marks,
                   COUNT(m.id) as tests_count
            FROM academic_marks m
            JOIN subjects s ON m.subject_id = s.id
            WHERE m.student_id = %s
            GROUP BY s.id, s.subject_code, s.subject_name
        """
        return db.query(sql, (self.student_id,))
