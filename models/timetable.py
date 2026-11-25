from database.db import db

class TimetableEntry:
    """
    Timetable entity demonstrating Association between ClassRoom, Subject and Faculty.
    """
    def __init__(self, id=None, class_id=None, subject_id=None, faculty_id=None,
                 day_of_week="", start_time="", end_time="", room_number="", **kwargs):
        self.id = id
        self.class_id = class_id
        self.subject_id = subject_id
        self.faculty_id = faculty_id
        self.day_of_week = day_of_week
        self.start_time = str(start_time)
        self.end_time = str(end_time)
        self.room_number = room_number
        self.extra = kwargs

    @staticmethod
    def get_faculty_schedule(faculty_table_id, day_of_week=None):
        sql = """
            SELECT t.*, c.class_code, c.department, s.subject_name, s.subject_code,
                   u.full_name as faculty_name
            FROM timetable t
            JOIN classes c ON t.class_id = c.id
            JOIN subjects s ON t.subject_id = s.id
            JOIN faculty f ON t.faculty_id = f.id
            JOIN users u ON f.user_id = u.id
            WHERE t.faculty_id = %s
        """
        params = [faculty_table_id]
        if day_of_week:
            sql += " AND t.day_of_week = %s"
            params.append(day_of_week)
        sql += " ORDER BY t.day_of_week, t.start_time"
        return db.query(sql, tuple(params))

    @staticmethod
    def get_class_schedule(class_id, day_of_week=None):
        sql = """
            SELECT t.*, c.class_code, s.subject_name, s.subject_code,
                   u.full_name as faculty_name, f.designation
            FROM timetable t
            JOIN classes c ON t.class_id = c.id
            JOIN subjects s ON t.subject_id = s.id
            JOIN faculty f ON t.faculty_id = f.id
            JOIN users u ON f.user_id = u.id
            WHERE t.class_id = %s
        """
        params = [class_id]
        if day_of_week:
            sql += " AND t.day_of_week = %s"
            params.append(day_of_week)
        sql += " ORDER BY t.day_of_week, t.start_time"
        return db.query(sql, tuple(params))

    @staticmethod
    def get_all():
        sql = """
            SELECT t.*, c.class_code, s.subject_name, s.subject_code,
                   u.full_name as faculty_name
            FROM timetable t
            JOIN classes c ON t.class_id = c.id
            JOIN subjects s ON t.subject_id = s.id
            JOIN faculty f ON t.faculty_id = f.id
            JOIN users u ON f.user_id = u.id
            ORDER BY c.class_code, t.day_of_week, t.start_time
        """
        return db.query(sql)
