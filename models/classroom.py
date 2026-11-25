from database.db import db

class Subject:
    """Represents a curriculum Subject/Course."""
    def __init__(self, id=None, subject_code="", subject_name="", department="", credits=3, semester=1, **kwargs):
        self.id = id
        self.subject_code = subject_code
        self.subject_name = subject_name
        self.department = department
        self.credits = credits
        self.semester = semester
        self.extra = kwargs

    def to_dict(self):
        return {
            'id': self.id,
            'subject_code': self.subject_code,
            'subject_name': self.subject_name,
            'department': self.department,
            'credits': self.credits,
            'semester': self.semester
        }

    @staticmethod
    def get_all():
        rows = db.query("SELECT * FROM subjects ORDER BY department, semester, subject_code")
        return [Subject(**r) for r in rows]

    @staticmethod
    def get_by_id(sub_id):
        r = db.query("SELECT * FROM subjects WHERE id = %s", (sub_id,), fetchone=True)
        return Subject(**r) if r else None


class ClassRoom:
    """
    Represents an Academic Class / Section.
    Demonstrates Aggregation (contains students) and Association with Subjects.
    """
    def __init__(self, id=None, class_code="", department="", semester=1, 
                 academic_year="", section="", room_number="", **kwargs):
        self.id = id
        self.class_code = class_code
        self.department = department
        self.semester = semester
        self.academic_year = academic_year
        self.section = section
        self.room_number = room_number
        self.extra = kwargs

    def get_students(self):
        """Retrieve all enrolled students (Aggregation)."""
        sql = """
            SELECT s.*, u.full_name, u.email, u.phone
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.class_id = %s
            ORDER BY u.full_name ASC
        """
        return db.query(sql, (self.id,))

    def get_student_count(self):
        r = db.query("SELECT COUNT(*) as count FROM students WHERE class_id = %s", (self.id,), fetchone=True)
        return r['count'] if r else 0

    def to_dict(self):
        return {
            'id': self.id,
            'class_code': self.class_code,
            'department': self.department,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'section': self.section,
            'room_number': self.room_number,
            'student_count': self.get_student_count()
        }

    @staticmethod
    def get_all():
        rows = db.query("SELECT * FROM classes ORDER BY department, semester, section")
        return [ClassRoom(**r) for r in rows]

    @staticmethod
    def get_by_id(cls_id):
        r = db.query("SELECT * FROM classes WHERE id = %s", (cls_id,), fetchone=True)
        return ClassRoom(**r) if r else None
