import sqlite3
from datetime import date, timedelta
from config import Config

def run_additive_migrations(db_instance):
    """
    Non-destructive additive migrations for the 5 advanced innovative features:
    1. Smart Attendance Recovery Simulator
    2. AI Academic Improvement Planner (Goals & Milestones)
    3. Smart Faculty Intervention Center (Mentoring & Tasks)
    4. Performance Journey Analytics
    5. Smart Notification Center
    
    Safe to run repeatedly; uses IF NOT EXISTS and preserves all existing tables and data.
    """
    engine = db_instance.get_engine_name()
    print(f"[Migrations] Running additive migrations on active engine: {engine}...")

    if engine == 'SQLITE':
        conn = sqlite3.connect(Config.SQLITE_PATH)
        cursor = conn.cursor()

        # 1. Faculty Interventions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty_interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            risk_category TEXT NOT NULL,
            attendance_at_intervention REAL NOT NULL,
            marks_at_intervention REAL NOT NULL,
            mentoring_notes TEXT NOT NULL,
            assigned_tasks TEXT,
            mentoring_date DATE NOT NULL,
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Completed')),
            outcome_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)

        # 2. Student Improvement Goals Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_improvement_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            goal_title TEXT NOT NULL,
            goal_category TEXT NOT NULL,
            target_date DATE,
            is_completed INTEGER DEFAULT 0,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );
        """)

        conn.commit()

        # Check if initial intervention seed is needed
        cursor.execute("SELECT COUNT(*) FROM faculty_interventions")
        if cursor.fetchone()[0] == 0:
            today = date.today()
            # Sample interventions for demonstration
            # Faculty 1 (Dr. Rajesh Sharma) mentoring student 2 (Rohan Mehta, low attendance) and student 4 (Kabir Sharma)
            interventions_seed = [
                (
                    1, 2, 'Needs Improvement', 68.75, 52.0,
                    'Conducted 1-on-1 counseling regarding frequent Monday morning absences. Student indicated transportation issues.',
                    '1. Attend all remaining classes in CS401.\n2. Submit handwritten notes for missed OOAD Unit 2 lectures.\n3. Meet mentor every Friday afternoon.',
                    str(today - timedelta(days=7)),
                    'In Progress',
                    'Student showed marked improvement in attendance over the past week (attended 5/5 sessions).'
                ),
                (
                    1, 4, 'Needs Improvement', 68.75, 54.0,
                    'Reviewed low internal test scores in Data Structures. Advised focused algorithm problem solving.',
                    '1. Complete practice problem set on Binary Search Trees.\n2. Attend peer study group at Library Block B on Thursday.',
                    str(today - timedelta(days=12)),
                    'Completed',
                    'Student submitted all practice exercises and scored 42/50 on subsequent diagnostic quiz.'
                ),
                (
                    2, 5, 'Average Performance', 75.00, 64.0,
                    'Discussed time management for balancing semester assignments with exam preparation.',
                    '1. Create weekly study schedule.\n2. Submit Software Engineering assignment 2 days prior to deadline.',
                    str(today - timedelta(days=4)),
                    'Pending',
                    'Awaiting midterm assignment submission.'
                )
            ]
            cursor.executemany("""
                INSERT INTO faculty_interventions 
                (faculty_id, student_id, risk_category, attendance_at_intervention, marks_at_intervention,
                 mentoring_notes, assigned_tasks, mentoring_date, status, outcome_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, interventions_seed)

        # Check if initial student goals seed is needed
        cursor.execute("SELECT COUNT(*) FROM student_improvement_goals")
        if cursor.fetchone()[0] == 0:
            today = date.today()
            goals_seed = [
                (1, 'Maintain 100% attendance in OOAD for the next 2 weeks', 'Attendance', str(today + timedelta(days=14)), 1, str(today - timedelta(days=2))),
                (1, 'Complete mock exam paper for Software Engineering', 'Exam Prep', str(today + timedelta(days=7)), 0, None),
                (1, 'Revise Unit 3 Database Design ERDs', 'Assignment', str(today + timedelta(days=5)), 1, str(today - timedelta(days=1))),
                (2, 'Attend all 8 scheduled classes next week to reach 75% attendance', 'Attendance', str(today + timedelta(days=7)), 0, None),
                (2, 'Submit Unit 2 remedial assignment notes to Dr. Rajesh', 'Mentoring', str(today + timedelta(days=3)), 1, str(today - timedelta(days=1))),
                (2, 'Solve 10 practice problems in Object-Oriented Modeling', 'Exam Prep', str(today + timedelta(days=10)), 0, None)
            ]
            cursor.executemany("""
                INSERT INTO student_improvement_goals
                (student_id, goal_title, goal_category, target_date, is_completed, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, goals_seed)

        conn.commit()
        conn.close()
        print("[Migrations] SQLite additive tables and baseline records verified.")

    else:
        # MySQL implementation
        try:
            db_instance.execute("""
            CREATE TABLE IF NOT EXISTS `faculty_interventions` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `faculty_id` INT NOT NULL,
                `student_id` INT NOT NULL,
                `risk_category` VARCHAR(50) NOT NULL,
                `attendance_at_intervention` DECIMAL(5,2) NOT NULL,
                `marks_at_intervention` DECIMAL(5,2) NOT NULL,
                `mentoring_notes` TEXT NOT NULL,
                `assigned_tasks` TEXT,
                `mentoring_date` DATE NOT NULL,
                `status` ENUM('Pending', 'In Progress', 'Completed') DEFAULT 'Pending',
                `outcome_notes` TEXT,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (`faculty_id`) REFERENCES `faculty`(`id`) ON DELETE CASCADE,
                FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE CASCADE,
                INDEX `idx_intervention_faculty` (`faculty_id`),
                INDEX `idx_intervention_student` (`student_id`),
                INDEX `idx_intervention_status` (`status`)
            ) ENGINE=InnoDB;
            """)

            db_instance.execute("""
            CREATE TABLE IF NOT EXISTS `student_improvement_goals` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `student_id` INT NOT NULL,
                `goal_title` VARCHAR(255) NOT NULL,
                `goal_category` VARCHAR(50) NOT NULL,
                `target_date` DATE,
                `is_completed` BOOLEAN DEFAULT FALSE,
                `completed_at` TIMESTAMP NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE CASCADE,
                INDEX `idx_goals_student` (`student_id`)
            ) ENGINE=InnoDB;
            """)
            print("[Migrations] MySQL additive tables verified.")
        except Exception as e:
            print(f"[Migrations] MySQL migration note: {e}")
