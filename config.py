import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-attendance-capstone-secret-key-2026')
    
    # MySQL Database Configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'student_analytics_db')
    
    # SQLite Fallback Configuration (Guarantees zero-friction execution if MySQL is offline)
    SQLITE_PATH = os.path.join(BASE_DIR, 'database', 'student_analytics.db')
    
    # Preferred DB engine: 'mysql' or 'sqlite' or 'auto' (tries MySQL, falls back to SQLite)
    DB_ENGINE = os.environ.get('DB_ENGINE', 'auto')
    
    # ML Model Configuration
    ML_MODEL_PATH = os.path.join(BASE_DIR, 'ml', 'student_risk_model.pkl')
    ML_METADATA_PATH = os.path.join(BASE_DIR, 'ml', 'model_metadata.json')
    
    # Reports output
    REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
    
    # Application Constants
    ATTENDANCE_WARNING_THRESHOLD = 75.0  # Percentage below which alert is triggered
    ITEMS_PER_PAGE = 20
