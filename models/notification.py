from database.db import db

class Notification:
    """
    Smart Notification entity for tracking alerts, delivery status, and read states.
    """
    CATEGORIES = (
        'Absence Alert', 'Low Attendance Warning', 'Academic Risk', 'General Notice',
        'Approaching Threshold', 'Declining Marks', 'Intervention Task',
        'Mentoring Completed', 'Academic Milestone'
    )
    PRIORITIES = ('High', 'Medium', 'Low')

    def __init__(self, id=None, user_id=None, student_id=None, title="", message="",
                 category="General Notice", priority="Medium", is_read=False,
                 delivery_status="Delivered", created_at=None, **kwargs):
        self.id = id
        self.user_id = user_id
        self.student_id = student_id
        self.title = title
        self.message = message
        self.category = category if category in self.CATEGORIES else 'General Notice'
        self.priority = priority if priority in self.PRIORITIES else 'Medium'
        self.is_read = bool(is_read)
        self.delivery_status = delivery_status
        self.created_at = created_at
        self.extra = kwargs

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'student_id': self.student_id,
            'title': self.title,
            'message': self.message,
            'category': self.category,
            'priority': self.priority,
            'is_read': self.is_read,
            'delivery_status': self.delivery_status,
            'created_at': str(self.created_at) if self.created_at else None
        }

    @staticmethod
    def create(user_id, title, message, category="General Notice", priority="Medium", student_id=None):
        sql = """
            INSERT INTO notifications (user_id, student_id, title, message, category, priority, is_read, delivery_status)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 'Delivered')
        """
        return db.execute(sql, (user_id, student_id, title, message, category, priority))

    @staticmethod
    def has_recent_notification(user_id, category, title, hours=48):
        """Prevents duplicate notification spam within the specified lookback window."""
        sql = """
            SELECT COUNT(*) as cnt FROM notifications 
            WHERE user_id = %s AND category = %s AND title = %s
            AND created_at >= datetime('now', '-' || %s || ' hours')
        """
        if db.get_engine_name() == 'MYSQL':
            sql = """
                SELECT COUNT(*) as cnt FROM notifications 
                WHERE user_id = %s AND category = %s AND title = %s
                AND created_at >= NOW() - INTERVAL %s HOUR
            """
        try:
            r = db.query(sql, (user_id, category, title, hours), fetchone=True)
            return (r['cnt'] > 0) if r else False
        except Exception:
            return False

    @staticmethod
    def get_for_user(user_id, limit=30):
        sql = """
            SELECT * FROM notifications 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        """
        return db.query(sql, (user_id, limit))

    @staticmethod
    def get_unread_count(user_id):
        sql = "SELECT COUNT(*) as unread_count FROM notifications WHERE user_id = %s AND is_read = 0"
        r = db.query(sql, (user_id,), fetchone=True)
        return r['unread_count'] if r else 0

    @staticmethod
    def mark_as_read(notif_id, user_id=None):
        if user_id:
            sql = "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s"
            db.execute(sql, (notif_id, user_id))
        else:
            sql = "UPDATE notifications SET is_read = 1 WHERE id = %s"
            db.execute(sql, (notif_id,))

    @staticmethod
    def mark_all_as_read(user_id):
        sql = "UPDATE notifications SET is_read = 1 WHERE user_id = %s"
        db.execute(sql, (user_id,))
