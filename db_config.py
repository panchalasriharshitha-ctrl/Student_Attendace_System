import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

class Config:
    """Database and Application Configuration"""
    # Flask Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'btech_dbms_mini_project_secret_key_2026')
    
    # MySQL Database Connection Settings
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')  # Default empty password in XAMPP
    MYSQL_DB = os.environ.get('MYSQL_DB', 'student_attendance')
    
    # Connection timeouts
    MYSQL_CONNECT_TIMEOUT = 3
    
    # SQLite fallback directory for testing when MySQL is not running
    INSTANCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    SQLITE_DB_PATH = os.path.join(INSTANCE_PATH, 'attendance_local.db')
