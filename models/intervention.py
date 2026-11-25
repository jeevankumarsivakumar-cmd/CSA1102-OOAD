from datetime import date
from database.db import db

class FacultyIntervention:
    """
    OOAD Entity representing a Faculty Mentoring Intervention session.
    Encapsulates intervention state, task assignments, and outcome tracking.
    """
    STATUSES = ('Pending', 'In Progress', 'Completed')

    def __init__(self, id=None, faculty_id=None, student_id=None, risk_category="",
                 attendance_at_intervention=0.0, marks_at_intervention=0.0,
                 mentoring_notes="", assigned_tasks="", mentoring_date=None,
                 status="Pending", outcome_notes="", created_at=None, updated_at=None, **kwargs):
        self.id = id
        self.faculty_id = faculty_id
        self.student_id = student_id
        self.risk_category = risk_category
        self.attendance_at_intervention = float(attendance_at_intervention or 0.0)
        self.marks_at_intervention = float(marks_at_intervention or 0.0)
        self.mentoring_notes = mentoring_notes or ""
        self.assigned_tasks = assigned_tasks or ""
        self.mentoring_date = str(mentoring_date) if mentoring_date else str(date.today())
        self.status = status if status in self.STATUSES else "Pending"
        self.outcome_notes = outcome_notes or ""
        self.created_at = created_at
        self.updated_at = updated_at
        self.extra = kwargs

    def to_dict(self):
        return {
            'id': self.id,
            'faculty_id': self.faculty_id,
            'student_id': self.student_id,
            'risk_category': self.risk_category,
            'attendance_at_intervention': self.attendance_at_intervention,
            'marks_at_intervention': self.marks_at_intervention,
            'mentoring_notes': self.mentoring_notes,
            'assigned_tasks': self.assigned_tasks,
            'mentoring_date': self.mentoring_date,
            'status': self.status,
            'outcome_notes': self.outcome_notes,
            'created_at': str(self.created_at) if self.created_at else None,
            'updated_at': str(self.updated_at) if self.updated_at else None,
            **self.extra
        }

    @staticmethod
    def create(faculty_id, student_id, risk_category, attendance_at_intervention,
               marks_at_intervention, mentoring_notes, assigned_tasks="",
               mentoring_date=None, status="Pending"):
        m_date = mentoring_date or str(date.today())
        sql = """
            INSERT INTO faculty_interventions 
            (faculty_id, student_id, risk_category, attendance_at_intervention,
             marks_at_intervention, mentoring_notes, assigned_tasks, mentoring_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return db.execute(sql, (
            faculty_id, student_id, risk_category, attendance_at_intervention,
            marks_at_intervention, mentoring_notes, assigned_tasks, m_date, status
        ))

    @staticmethod
    def update_status(intervention_id, status, outcome_notes=None):
        if outcome_notes:
            sql = "UPDATE faculty_interventions SET status = %s, outcome_notes = %s WHERE id = %s"
            db.execute(sql, (status, outcome_notes, intervention_id))
        else:
            sql = "UPDATE faculty_interventions SET status = %s WHERE id = %s"
            db.execute(sql, (status, intervention_id))

    @staticmethod
    def get_by_id(intervention_id):
        sql = """
            SELECT fi.*, u.full_name as student_name, st.student_id as student_code,
                   fu.full_name as faculty_name, c.class_code
            FROM faculty_interventions fi
            JOIN students st ON fi.student_id = st.id
            JOIN users u ON st.user_id = u.id
            JOIN classes c ON st.class_id = c.id
            JOIN faculty f ON fi.faculty_id = f.id
            JOIN users fu ON f.user_id = fu.id
            WHERE fi.id = %s
        """
        row = db.query(sql, (intervention_id,), fetchone=True)
        return FacultyIntervention(**row) if row else None

    @staticmethod
    def get_for_faculty(faculty_id, status_filter=None):
        sql = """
            SELECT fi.*, u.full_name as student_name, st.student_id as student_code,
                   c.class_code, u.email as student_email
            FROM faculty_interventions fi
            JOIN students st ON fi.student_id = st.id
            JOIN users u ON st.user_id = u.id
            JOIN classes c ON st.class_id = c.id
            WHERE fi.faculty_id = %s
        """
        params = [faculty_id]
        if status_filter:
            sql += " AND fi.status = %s"
            params.append(status_filter)
        sql += " ORDER BY fi.mentoring_date DESC, fi.created_at DESC"
        rows = db.query(sql, tuple(params))
        return [dict(r) for r in rows]

    @staticmethod
    def get_for_student(student_id):
        sql = """
            SELECT fi.*, fu.full_name as faculty_name, f.designation, f.department
            FROM faculty_interventions fi
            JOIN faculty f ON fi.faculty_id = f.id
            JOIN users fu ON f.user_id = fu.id
            WHERE fi.student_id = %s
            ORDER BY fi.mentoring_date DESC
        """
        rows = db.query(sql, (student_id,))
        return [dict(r) for r in rows]

    @staticmethod
    def get_all(status_filter=None, limit=100):
        sql = """
            SELECT fi.*, u.full_name as student_name, st.student_id as student_code,
                   fu.full_name as faculty_name, c.class_code, c.department
            FROM faculty_interventions fi
            JOIN students st ON fi.student_id = st.id
            JOIN users u ON st.user_id = u.id
            JOIN classes c ON st.class_id = c.id
            JOIN faculty f ON fi.faculty_id = f.id
            JOIN users fu ON f.user_id = fu.id
        """
        params = []
        if status_filter:
            sql += " WHERE fi.status = %s"
            params.append(status_filter)
        sql += " ORDER BY fi.mentoring_date DESC LIMIT %s"
        params.append(limit)
        rows = db.query(sql, tuple(params))
        return [dict(r) for r in rows]
