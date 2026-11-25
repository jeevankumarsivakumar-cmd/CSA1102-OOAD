from abc import ABC, abstractmethod
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db

class User:
    """
    Base User class representing an authenticated identity in the system.
    Demonstrates Encapsulation and Polymorphism.
    """
    def __init__(self, id=None, username="", email="", role="", full_name="", phone="", 
                 avatar=None, is_active=True, created_at=None, password_hash=None):
        self._id = id
        self._username = username
        self._email = email
        self._role = role
        self._full_name = full_name
        self._phone = phone
        self._avatar = avatar
        self._is_active = bool(is_active)
        self._created_at = created_at
        self._password_hash = password_hash

    # Getters & Properties
    @property
    def id(self): return self._id
    @property
    def username(self): return self._username
    @property
    def email(self): return self._email
    @property
    def role(self): return self._role
    @property
    def full_name(self): return self._full_name
    @property
    def phone(self): return self._phone
    @property
    def avatar(self): return self._avatar or "default-avatar.png"
    @property
    def is_active(self): return self._is_active

    def set_password(self, plain_password):
        """Encapsulate password hashing."""
        self._password_hash = generate_password_hash(plain_password)

    def verify_password(self, plain_password):
        """Verify candidate password against hash."""
        if not self._password_hash:
            return False
        return check_password_hash(self._password_hash, plain_password)

    def get_dashboard_route(self):
        """Polymorphic dashboard resolution."""
        return "auth.login"

    def get_permissions(self):
        """Return permission set based on role."""
        return []

    def to_dict(self):
        return {
            'id': self._id,
            'username': self._username,
            'email': self._email,
            'role': self._role,
            'full_name': self._full_name,
            'phone': self._phone,
            'avatar': self.avatar,
            'is_active': self._is_active
        }

    @staticmethod
    def get_by_id(user_id):
        row = db.query("SELECT * FROM users WHERE id = %s", (user_id,), fetchone=True)
        if not row:
            return None
        return User.create_from_row(row)

    @staticmethod
    def get_by_username_or_email(identifier):
        row = db.query(
            "SELECT * FROM users WHERE username = %s OR email = %s", 
            (identifier, identifier), 
            fetchone=True
        )
        if not row:
            return None
        return User.create_from_row(row)

    @classmethod
    def create_from_row(cls, row):
        role = row.get('role')
        if role == 'admin':
            return Admin(
                id=row['id'], username=row['username'], email=row['email'],
                role='admin', full_name=row['full_name'], phone=row.get('phone'),
                avatar=row.get('avatar'), is_active=row.get('is_active', 1),
                created_at=row.get('created_at'), password_hash=row.get('password_hash')
            )
        elif role == 'faculty':
            f_row = db.query("SELECT * FROM faculty WHERE user_id = %s", (row['id'],), fetchone=True)
            return Faculty(
                id=row['id'], username=row['username'], email=row['email'],
                role='faculty', full_name=row['full_name'], phone=row.get('phone'),
                avatar=row.get('avatar'), is_active=row.get('is_active', 1),
                created_at=row.get('created_at'), password_hash=row.get('password_hash'),
                faculty_table_id=f_row['id'] if f_row else None,
                employee_id=f_row['employee_id'] if f_row else None,
                department=f_row['department'] if f_row else None,
                designation=f_row['designation'] if f_row else None,
                qualification=f_row.get('qualification') if f_row else None,
                specialization=f_row.get('specialization') if f_row else None
            )
        elif role == 'student':
            s_row = db.query("SELECT * FROM students WHERE user_id = %s", (row['id'],), fetchone=True)
            return Student(
                id=row['id'], username=row['username'], email=row['email'],
                role='student', full_name=row['full_name'], phone=row.get('phone'),
                avatar=row.get('avatar'), is_active=row.get('is_active', 1),
                created_at=row.get('created_at'), password_hash=row.get('password_hash'),
                student_table_id=s_row['id'] if s_row else None,
                student_id=s_row['student_id'] if s_row else None,
                class_id=s_row['class_id'] if s_row else None,
                department=s_row['department'] if s_row else None,
                academic_year=s_row['academic_year'] if s_row else None,
                contact_phone=s_row.get('contact_phone') if s_row else None,
                emergency_contact=s_row.get('emergency_contact') if s_row else None,
                address=s_row.get('address') if s_row else None,
                previous_gpa=float(s_row.get('previous_gpa', 7.5)) if s_row else 7.5
            )
        return cls(
            id=row['id'], username=row['username'], email=row['email'],
            role=row['role'], full_name=row['full_name'], phone=row.get('phone'),
            avatar=row.get('avatar'), is_active=row.get('is_active', 1),
            created_at=row.get('created_at'), password_hash=row.get('password_hash')
        )


class Admin(User):
    """Admin role demonstrating Inheritance and Specialized Permissions."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._role = 'admin'

    def get_dashboard_route(self):
        return "admin.dashboard"

    def get_permissions(self):
        return ['manage_students', 'manage_faculty', 'manage_classes', 'manage_timetable', 'view_reports', 'manage_system']


class Faculty(User):
    """Faculty role demonstrating Inheritance & Subject Association."""
    def __init__(self, faculty_table_id=None, employee_id=None, department=None,
                 designation=None, qualification=None, specialization=None, **kwargs):
        super().__init__(**kwargs)
        self._role = 'faculty'
        self.faculty_table_id = faculty_table_id
        self.employee_id = employee_id
        self.department = department
        self.designation = designation
        self.qualification = qualification
        self.specialization = specialization

    def get_dashboard_route(self):
        return "faculty.dashboard"

    def get_permissions(self):
        return ['mark_attendance', 'edit_attendance', 'enter_marks', 'view_class_analytics', 'view_assigned_timetable']

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'faculty_table_id': self.faculty_table_id,
            'employee_id': self.employee_id,
            'department': self.department,
            'designation': self.designation,
            'qualification': self.qualification,
            'specialization': self.specialization
        })
        return d


class Student(User):
    """Student role demonstrating Inheritance, Class Association & Performance Tracking."""
    def __init__(self, student_table_id=None, student_id=None, class_id=None, department=None,
                 academic_year=None, contact_phone=None, emergency_contact=None,
                 address=None, previous_gpa=7.50, **kwargs):
        super().__init__(**kwargs)
        self._role = 'student'
        self.student_table_id = student_table_id
        self.student_id = student_id
        self.class_id = class_id
        self.department = department
        self.academic_year = academic_year
        self.contact_phone = contact_phone
        self.emergency_contact = emergency_contact
        self.address = address
        self.previous_gpa = previous_gpa

    def get_dashboard_route(self):
        return "student.dashboard"

    def get_permissions(self):
        return ['view_own_attendance', 'view_own_marks', 'view_own_notifications', 'view_ai_insights']

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'student_table_id': self.student_table_id,
            'student_id': self.student_id,
            'class_id': self.class_id,
            'department': self.department,
            'academic_year': self.academic_year,
            'contact_phone': self.contact_phone,
            'emergency_contact': self.emergency_contact,
            'address': self.address,
            'previous_gpa': self.previous_gpa
        })
        return d
