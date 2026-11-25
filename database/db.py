import os
import sqlite3
import pymysql
import pymysql.cursors
from config import Config

class DatabaseManager:
    """
    Object-Oriented Database Connection Manager.
    Implements a robust adapter pattern:
    - Attempts connection to MySQL Server (per capstone specification)
    - Automatically falls back to SQLite if MySQL is offline or not configured,
      ensuring uninterrupted execution and 100% demo reliability.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._engine_type = None
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        pref = Config.DB_ENGINE.lower()
        if pref in ('mysql', 'auto'):
            try:
                # Test MySQL connection
                conn = pymysql.connect(
                    host=Config.MYSQL_HOST,
                    port=Config.MYSQL_PORT,
                    user=Config.MYSQL_USER,
                    password=Config.MYSQL_PASSWORD,
                    database=Config.MYSQL_DB,
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=2
                )
                conn.close()
                self._engine_type = 'mysql'
                print(f"[DatabaseManager] Successfully connected to MySQL at {Config.MYSQL_HOST}:{Config.MYSQL_PORT}/{Config.MYSQL_DB}")
                return
            except Exception as e:
                if pref == 'mysql':
                    print(f"[DatabaseManager] MySQL connection failed: {e}")
                    raise e
                print(f"[DatabaseManager] MySQL not reachable ({e}). Gracefully falling back to local SQLite engine.")
        
        # SQLite Engine
        self._engine_type = 'sqlite'
        os.makedirs(os.path.dirname(Config.SQLITE_PATH), exist_ok=True)
        self._init_sqlite_schema()
        from database.migrations import run_additive_migrations
        run_additive_migrations(self)
        # Auto-seed demonstration data if database is fresh
        try:
            user_cnt = self.query("SELECT COUNT(*) as cnt FROM users", fetchone=True)
            if not user_cnt or user_cnt['cnt'] == 0:
                print("[DatabaseManager] Fresh database detected. Auto-seeding demonstration dataset...")
                from database.seed_data import seed_database
                seed_database()
        except Exception as e:
            print(f"[DatabaseManager] Note on auto-seeding check: {e}")
        print(f"[DatabaseManager] SQLite database active at: {Config.SQLITE_PATH}")

    def get_connection(self):
        """Returns a database connection based on active engine."""
        if self._engine_type == 'mysql':
            return pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        else:
            conn = sqlite3.connect(Config.SQLITE_PATH)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn

    def get_engine_name(self):
        return self._engine_type.upper()

    def query(self, sql, params=None, fetchone=False):
        """Execute a SELECT query and return rows as dictionaries."""
        conn = self.get_connection()
        try:
            if self._engine_type == 'sqlite':
                # Convert %s placeholder to ? for sqlite if needed
                sql_converted = sql.replace('%s', '?')
                cursor = conn.cursor()
                cursor.execute(sql_converted, params or ())
                if fetchone:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                else:
                    rows = cursor.fetchall()
                    return [dict(r) for r in rows]
            else:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    if fetchone:
                        return cursor.fetchone()
                    return cursor.fetchall()
        finally:
            conn.close()

    def execute(self, sql, params=None):
        """Execute an INSERT/UPDATE/DELETE query and return lastrowid / rowcount."""
        conn = self.get_connection()
        try:
            if self._engine_type == 'sqlite':
                sql_converted = sql.replace('%s', '?')
                cursor = conn.cursor()
                cursor.execute(sql_converted, params or ())
                conn.commit()
                return cursor.lastrowid
            else:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    conn.commit()
                    return cursor.lastrowid
        finally:
            conn.close()

    def execute_many(self, sql, seq_of_params):
        """Execute batch statements."""
        conn = self.get_connection()
        try:
            if self._engine_type == 'sqlite':
                sql_converted = sql.replace('%s', '?')
                cursor = conn.cursor()
                cursor.executemany(sql_converted, seq_of_params)
                conn.commit()
                return cursor.rowcount
            else:
                with conn.cursor() as cursor:
                    cursor.executemany(sql, seq_of_params)
                    conn.commit()
                    return cursor.rowcount
        finally:
            conn.close()

    def _init_sqlite_schema(self):
        """Initializes SQLite schema if not already present."""
        conn = sqlite3.connect(Config.SQLITE_PATH)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'faculty', 'student')),
            full_name TEXT NOT NULL,
            phone TEXT,
            avatar TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_code TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL,
            academic_year TEXT NOT NULL,
            section TEXT NOT NULL,
            room_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            employee_id TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            designation TEXT NOT NULL,
            qualification TEXT,
            specialization TEXT,
            joining_date DATE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            student_id TEXT NOT NULL UNIQUE,
            class_id INTEGER NOT NULL,
            department TEXT NOT NULL,
            academic_year TEXT NOT NULL,
            contact_phone TEXT,
            emergency_contact TEXT,
            address TEXT,
            date_of_birth DATE,
            enrollment_status TEXT DEFAULT 'Active',
            previous_gpa REAL DEFAULT 7.50,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT NOT NULL UNIQUE,
            subject_name TEXT NOT NULL,
            department TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 3,
            semester INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            day_of_week TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            room_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            faculty_id INTEGER NOT NULL,
            attendance_date DATE NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'On Duty')),
            remarks TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
            UNIQUE (student_id, subject_id, attendance_date)
        );

        CREATE TABLE IF NOT EXISTS academic_marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            exam_type TEXT NOT NULL,
            marks_obtained REAL NOT NULL,
            max_marks REAL NOT NULL DEFAULT 50.00,
            exam_date DATE NOT NULL,
            entered_by INTEGER NOT NULL,
            remarks TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (entered_by) REFERENCES faculty(id) ON DELETE CASCADE,
            UNIQUE (student_id, subject_id, exam_type)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            student_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT DEFAULT 'Medium',
            is_read INTEGER DEFAULT 0,
            delivery_status TEXT DEFAULT 'Delivered',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS prediction_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_percentage REAL NOT NULL,
            total_absences INTEGER NOT NULL,
            avg_internal_marks REAL NOT NULL,
            previous_gpa REAL NOT NULL,
            risk_category TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            risk_factors TEXT,
            model_version TEXT DEFAULT 'v1.0-RF',
            predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)
        conn.commit()
        conn.close()

# Singleton helper
db = DatabaseManager()
