"""
Database Module for Student Attendance Management System
Supports MySQL (Primary Database) with pure Python PyMySQL connector.
Includes automatic fallback to SQLite so the application functions reliably in any environment.
"""

import os
import time
import socket
import sqlite3
import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import Config

# Global variable to track active engine and health
CURRENT_ENGINE = 'mysql'
LAST_ERROR = None
_LAST_MYSQL_CHECK_TIME = 0
_LAST_MYSQL_STATUS = False
_LAST_MYSQL_MSG = ""

def is_mysql_port_open(host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, timeout=0.15):
    """Quick socket check to avoid long connection timeout when MySQL service is stopped."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def check_mysql_availability(force=False):
    """Check if the MySQL server is currently reachable (cached for 3 seconds)."""
    global _LAST_MYSQL_CHECK_TIME, _LAST_MYSQL_STATUS, _LAST_MYSQL_MSG
    now = time.time()
    if not force and (now - _LAST_MYSQL_CHECK_TIME) < 3.0:
        return _LAST_MYSQL_STATUS, _LAST_MYSQL_MSG
        
    _LAST_MYSQL_CHECK_TIME = now
    if not is_mysql_port_open():
        _LAST_MYSQL_STATUS = False
        _LAST_MYSQL_MSG = f"MySQL Port {Config.MYSQL_PORT} on {Config.MYSQL_HOST} is not reachable. (Start MySQL in XAMPP or service)"
        return _LAST_MYSQL_STATUS, _LAST_MYSQL_MSG

    try:
        conn = get_mysql_connection(include_db=False)
        conn.close()
        _LAST_MYSQL_STATUS = True
        _LAST_MYSQL_MSG = "MySQL Server is connected and active"
        return True, _LAST_MYSQL_MSG
    except Exception as e:
        _LAST_MYSQL_STATUS = False
        _LAST_MYSQL_MSG = f"MySQL connection failed: {str(e)}"
        return False, _LAST_MYSQL_MSG

def get_mysql_connection(include_db=True):
    """Attempt to establish a MySQL connection using PyMySQL."""
    kwargs = {
        'host': Config.MYSQL_HOST,
        'port': Config.MYSQL_PORT,
        'user': Config.MYSQL_USER,
        'password': Config.MYSQL_PASSWORD,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor,
        'connect_timeout': 1,
        'autocommit': True
    }
    if include_db:
        kwargs['database'] = Config.MYSQL_DB
    
    return pymysql.connect(**kwargs)

def get_sqlite_connection():
    """Establish a SQLite connection for local fallback testing."""
    os.makedirs(Config.INSTANCE_PATH, exist_ok=True)
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_connection():
    """
    Returns an active database connection and the engine type ('mysql' or 'sqlite').
    Tries MySQL if available. If unavailable, falls back gracefully to SQLite.
    """
    global CURRENT_ENGINE, LAST_ERROR
    
    is_avail, msg = check_mysql_availability()
    if is_avail:
        try:
            conn = get_mysql_connection(include_db=True)
            CURRENT_ENGINE = 'mysql'
            LAST_ERROR = None
            return conn, 'mysql'
        except Exception as mysql_err:
            LAST_ERROR = str(mysql_err)
            if "Unknown database" in str(mysql_err):
                try:
                    setup_conn = get_mysql_connection(include_db=False)
                    with setup_conn.cursor() as cur:
                        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                    setup_conn.close()
                    conn = get_mysql_connection(include_db=True)
                    CURRENT_ENGINE = 'mysql'
                    LAST_ERROR = None
                    return conn, 'mysql'
                except Exception as e:
                    LAST_ERROR = str(e)
    
    # Fall back to SQLite
    CURRENT_ENGINE = 'sqlite'
    LAST_ERROR = msg
    conn = get_sqlite_connection()
    return conn, 'sqlite'

def init_db():
    """
    Initializes tables and inserts default admin and sample student data
    into both MySQL (if available) and local SQLite.
    """
    global CURRENT_ENGINE, LAST_ERROR
    
    # Check MySQL first
    is_mysql_ok, msg = check_mysql_availability()
    if is_mysql_ok:
        try:
            # 1. Connect without DB and create DB
            root_conn = get_mysql_connection(include_db=False)
            with root_conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            root_conn.close()
            
            # 2. Connect to the database and create tables
            conn = get_mysql_connection(include_db=True)
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS admin (
                    admin_id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """)
                
                cur.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id INT AUTO_INCREMENT PRIMARY KEY,
                    roll_number VARCHAR(30) NOT NULL UNIQUE,
                    name VARCHAR(100) NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    year INT NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """)
                
                cur.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    attendance_date DATE NOT NULL,
                    status ENUM('Present', 'Absent') NOT NULL DEFAULT 'Present',
                    remarks VARCHAR(255) DEFAULT '',
                    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    CONSTRAINT fk_attendance_student 
                        FOREIGN KEY (student_id) REFERENCES students(student_id) 
                        ON DELETE CASCADE 
                        ON UPDATE CASCADE,
                    CONSTRAINT uq_student_date 
                        UNIQUE (student_id, attendance_date)
                ) ENGINE=InnoDB;
                """)
                
                # Check for admin
                cur.execute("SELECT COUNT(*) AS count FROM admin WHERE username = 'admin'")
                row = cur.fetchone()
                if row['count'] == 0:
                    pw_hash = generate_password_hash('admin123')
                    cur.execute("""
                    INSERT INTO admin (username, password_hash, full_name, email)
                    VALUES (%s, %s, %s, %s)
                    """, ('admin', pw_hash, 'Head Administrator', 'admin@college.edu'))
                
                # Check for sample students
                cur.execute("SELECT COUNT(*) AS count FROM students")
                row = cur.fetchone()
                if row['count'] == 0:
                    sample_students = [
                        ('24CS101', 'Aarav Sharma', 'Computer Science', 2, 'aarav.sharma@college.edu'),
                        ('24CS102', 'Diya Patel', 'Computer Science', 2, 'diya.patel@college.edu'),
                        ('24CS103', 'Rohan Verma', 'Computer Science', 2, 'rohan.verma@college.edu'),
                        ('24CS104', 'Ananya Iyer', 'Computer Science', 2, 'ananya.iyer@college.edu'),
                        ('24CS105', 'Vikram Singh', 'Computer Science', 2, 'vikram.singh@college.edu'),
                        ('24IT201', 'Pooja Nair', 'Information Technology', 2, 'pooja.nair@college.edu'),
                        ('24IT202', 'Rahul Deshmukh', 'Information Technology', 2, 'rahul.deshmukh@college.edu'),
                        ('24CS106', 'Sneha Kulkarni', 'Computer Science', 3, 'sneha.kulkarni@college.edu'),
                        ('24CS107', 'Aditya Joshi', 'Computer Science', 3, 'aditya.joshi@college.edu'),
                        ('24AI301', 'Tanvi Mehta', 'Artificial Intelligence', 2, 'tanvi.mehta@college.edu')
                    ]
                    for s in sample_students:
                        cur.execute("""
                        INSERT INTO students (roll_number, name, department, year, email)
                        VALUES (%s, %s, %s, %s, %s)
                        """, s)
                    
                    # Seed sample attendance for 3 dates
                    dates = ['2026-10-26', '2026-10-27', '2026-10-28']
                    cur.execute("SELECT student_id FROM students ORDER BY student_id")
                    st_ids = [r['student_id'] for r in cur.fetchall()]
                    
                    for d_idx, dt in enumerate(dates):
                        for s_idx, sid in enumerate(st_ids):
                            # realistic mix of present and absent
                            status = 'Absent' if (s_idx + d_idx) % 5 == 2 else 'Present'
                            remarks = 'Medical' if status == 'Absent' else 'Regular session'
                            cur.execute("""
                            INSERT INTO attendance (student_id, attendance_date, status, remarks)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE status = VALUES(status)
                            """, (sid, dt, status, remarks))
            
            conn.close()
            CURRENT_ENGINE = 'mysql'
            print("[DB INFO] MySQL database initialized successfully.")
        except Exception as e:
            print(f"[DB WARN] MySQL init failed ({e}), initializing SQLite fallback...")
            CURRENT_ENGINE = 'sqlite'
    
    # Always also ensure SQLite fallback schema is ready
    init_sqlite()

def init_sqlite():
    """Initializes SQLite schema as fallback or local testing."""
    os.makedirs(Config.INSTANCE_PATH, exist_ok=True)
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_number TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        year INTEGER NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
        remarks TEXT DEFAULT '',
        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        UNIQUE (student_id, attendance_date)
    );
    """)
    
    # Default Admin
    cur.execute("SELECT COUNT(*) FROM admin WHERE username = 'admin'")
    if cur.fetchone()[0] == 0:
        pw_hash = generate_password_hash('admin123')
        cur.execute("""
        INSERT INTO admin (username, password_hash, full_name, email)
        VALUES (?, ?, ?, ?)
        """, ('admin', pw_hash, 'Head Administrator', 'admin@college.edu'))
    
    # Sample Students
    cur.execute("SELECT COUNT(*) FROM students")
    if cur.fetchone()[0] == 0:
        sample_students = [
            ('24CS101', 'Aarav Sharma', 'Computer Science', 2, 'aarav.sharma@college.edu'),
            ('24CS102', 'Diya Patel', 'Computer Science', 2, 'diya.patel@college.edu'),
            ('24CS103', 'Rohan Verma', 'Computer Science', 2, 'rohan.verma@college.edu'),
            ('24CS104', 'Ananya Iyer', 'Computer Science', 2, 'ananya.iyer@college.edu'),
            ('24CS105', 'Vikram Singh', 'Computer Science', 2, 'vikram.singh@college.edu'),
            ('24IT201', 'Pooja Nair', 'Information Technology', 2, 'pooja.nair@college.edu'),
            ('24IT202', 'Rahul Deshmukh', 'Information Technology', 2, 'rahul.deshmukh@college.edu'),
            ('24CS106', 'Sneha Kulkarni', 'Computer Science', 3, 'sneha.kulkarni@college.edu'),
            ('24CS107', 'Aditya Joshi', 'Computer Science', 3, 'aditya.joshi@college.edu'),
            ('24AI301', 'Tanvi Mehta', 'Artificial Intelligence', 2, 'tanvi.mehta@college.edu')
        ]
        for s in sample_students:
            cur.execute("""
            INSERT INTO students (roll_number, name, department, year, email)
            VALUES (?, ?, ?, ?, ?)
            """, s)
        
        # Seed sample attendance
        dates = ['2026-10-26', '2026-10-27', '2026-10-28']
        cur.execute("SELECT student_id FROM students ORDER BY student_id")
        st_ids = [r[0] for r in cur.fetchall()]
        for d_idx, dt in enumerate(dates):
            for s_idx, sid in enumerate(st_ids):
                status = 'Absent' if (s_idx + d_idx) % 5 == 2 else 'Present'
                remarks = 'Medical' if status == 'Absent' else 'Regular session'
                cur.execute("""
                INSERT OR REPLACE INTO attendance (student_id, attendance_date, status, remarks)
                VALUES (?, ?, ?, ?)
                """, (sid, dt, status, remarks))
                
    conn.commit()
    conn.close()

def execute_query(query, params=None, fetchone=False, fetchall=False, commit=False):
    """
    Unified query runner that handles both MySQL (%s parameter placeholder)
    and SQLite (? parameter placeholder) transparently.
    """
    conn, engine = get_connection()
    try:
        if engine == 'mysql':
            # PyMySQL uses %s placeholders
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                if commit:
                    conn.commit()
                if fetchone:
                    return cur.fetchone()
                if fetchall:
                    return cur.fetchall()
                return cur.lastrowid
        else:
            # SQLite uses ? placeholders, convert %s to ?
            sqlite_query = query.replace('%s', '?')
            cur = conn.cursor()
            cur.execute(sqlite_query, params or ())
            if commit:
                conn.commit()
            if fetchone:
                row = cur.fetchone()
                return dict(row) if row else None
            if fetchall:
                rows = cur.fetchall()
                return [dict(r) for r in rows]
            return cur.lastrowid
    finally:
        conn.close()

# ====================================================================
# ADMIN AUTHENTICATION
# ====================================================================

def authenticate_admin(username, password):
    """Verify administrator login credentials."""
    admin = execute_query(
        "SELECT * FROM admin WHERE username = %s",
        (username,),
        fetchone=True
    )
    if not admin:
        return None
    
    # Check password hash (also supports simple fallback for student testing)
    pw_hash = admin['password_hash']
    if check_password_hash(pw_hash, password) or pw_hash == password:
        return admin
    return None

def get_admin_by_id(admin_id):
    """Retrieve administrator details by ID."""
    return execute_query(
        "SELECT admin_id, username, full_name, email, created_at FROM admin WHERE admin_id = %s",
        (admin_id,),
        fetchone=True
    )

# ====================================================================
# DASHBOARD MODULE QUERIES
# ====================================================================

def get_dashboard_metrics(target_date):
    """
    Retrieves real-time dashboard statistics using SQL aggregation:
    - Total registered students
    - Present students on date
    - Absent students on date
    - Unmarked students
    - Department-wise student breakdown
    - System-wide average attendance percentage
    """
    # 1. Total registered students
    total_students_res = execute_query("SELECT COUNT(*) AS total FROM students", fetchone=True)
    total_students = total_students_res['total'] if total_students_res else 0
    
    # 2. Present count on selected date
    present_res = execute_query(
        "SELECT COUNT(*) AS count FROM attendance WHERE attendance_date = %s AND status = 'Present'",
        (target_date,),
        fetchone=True
    )
    present_today = present_res['count'] if present_res else 0
    
    # 3. Absent count on selected date
    absent_res = execute_query(
        "SELECT COUNT(*) AS count FROM attendance WHERE attendance_date = %s AND status = 'Absent'",
        (target_date,),
        fetchone=True
    )
    absent_today = absent_res['count'] if absent_res else 0
    
    unmarked_today = max(0, total_students - (present_today + absent_today))
    
    # 4. Overall average attendance percentage across all dates
    overall_avg_res = execute_query("""
        SELECT 
            COUNT(attendance_id) AS total_records,
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS total_present
        FROM attendance
    """, fetchone=True)
    
    overall_percentage = 0.0
    if overall_avg_res and overall_avg_res['total_records'] and overall_avg_res['total_records'] > 0:
        overall_percentage = round((overall_avg_res['total_present'] * 100.0) / overall_avg_res['total_records'], 1)
        
    # 5. Department Breakdown
    dept_breakdown = execute_query("""
        SELECT 
            department, 
            COUNT(student_id) AS student_count 
        FROM students 
        GROUP BY department 
        ORDER BY student_count DESC
    """, fetchall=True) or []
    
    # 6. Recent Attendance activity records
    recent_activity = execute_query("""
        SELECT 
            a.attendance_date,
            COUNT(a.attendance_id) AS total_marked,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count
        FROM attendance a
        GROUP BY a.attendance_date
        ORDER BY a.attendance_date DESC
        LIMIT 5
    """, fetchall=True) or []
    
    return {
        'total_students': total_students,
        'present_today': present_today,
        'absent_today': absent_today,
        'unmarked_today': unmarked_today,
        'overall_percentage': overall_percentage,
        'dept_breakdown': dept_breakdown,
        'recent_activity': recent_activity
    }

# ====================================================================
# STUDENT MANAGEMENT MODULE (CRUD)
# ====================================================================

def get_all_students(search=None, department=None, year=None):
    """Retrieve students with optional search query and filters."""
    conditions = []
    params = []
    
    if search:
        search_pattern = f"%{search}%"
        conditions.append("(name LIKE %s OR roll_number LIKE %s OR email LIKE %s)")
        params.extend([search_pattern, search_pattern, search_pattern])
        
    if department and department != 'All':
        conditions.append("department = %s")
        params.append(department)
        
    if year and year != 'All':
        conditions.append("year = %s")
        params.append(int(year))
        
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT 
            student_id, 
            roll_number, 
            name, 
            department, 
            year, 
            email, 
            created_at
        FROM students
        {where_clause}
        ORDER BY roll_number ASC
    """
    return execute_query(query, tuple(params), fetchall=True) or []

def get_student_by_id(student_id):
    """Retrieve a single student record by primary key."""
    return execute_query(
        "SELECT * FROM students WHERE student_id = %s",
        (student_id,),
        fetchone=True
    )

def add_student(name, roll_number, department, year, email):
    """
    Insert a new student into the database.
    Checks for roll_number and email uniqueness beforehand.
    """
    # Validation checks
    existing_roll = execute_query("SELECT student_id FROM students WHERE roll_number = %s", (roll_number,), fetchone=True)
    if existing_roll:
        return False, f"Roll Number '{roll_number}' is already registered."
        
    existing_email = execute_query("SELECT student_id FROM students WHERE email = %s", (email,), fetchone=True)
    if existing_email:
        return False, f"Email address '{email}' is already in use."
        
    try:
        execute_query("""
            INSERT INTO students (name, roll_number, department, year, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (name.strip(), roll_number.strip().upper(), department.strip(), int(year), email.strip().lower()), commit=True)
        return True, "Student added successfully."
    except Exception as e:
        return False, f"Database Error: {str(e)}"

def update_student(student_id, name, roll_number, department, year, email):
    """
    Update student information.
    Ensures unique constraints are not violated by other records.
    """
    existing_roll = execute_query(
        "SELECT student_id FROM students WHERE roll_number = %s AND student_id != %s", 
        (roll_number, student_id), 
        fetchone=True
    )
    if existing_roll:
        return False, f"Roll Number '{roll_number}' is already registered to another student."
        
    existing_email = execute_query(
        "SELECT student_id FROM students WHERE email = %s AND student_id != %s", 
        (email, student_id), 
        fetchone=True
    )
    if existing_email:
        return False, f"Email address '{email}' is already registered to another student."
        
    try:
        execute_query("""
            UPDATE students 
            SET name = %s, roll_number = %s, department = %s, year = %s, email = %s
            WHERE student_id = %s
        """, (name.strip(), roll_number.strip().upper(), department.strip(), int(year), email.strip().lower(), student_id), commit=True)
        return True, "Student details updated successfully."
    except Exception as e:
        return False, f"Database Error: {str(e)}"

def delete_student(student_id):
    """
    Delete a student record.
    Foreign key ON DELETE CASCADE automatically removes associated attendance records.
    """
    try:
        execute_query("DELETE FROM students WHERE student_id = %s", (student_id,), commit=True)
        return True, "Student and corresponding attendance records deleted successfully."
    except Exception as e:
        return False, f"Database Error: {str(e)}"

def get_distinct_departments():
    """Returns list of all distinct departments present in the database."""
    res = execute_query("SELECT DISTINCT department FROM students ORDER BY department ASC", fetchall=True) or []
    return [r['department'] for r in res]

# ====================================================================
# ATTENDANCE MANAGEMENT MODULE
# ====================================================================

def get_attendance_sheet(target_date, department=None, year=None):
    """
    Retrieves all students joined with their attendance status for a given date.
    Uses LEFT JOIN so students with no record for that date still appear.
    """
    conditions = []
    params = [target_date]
    
    if department and department != 'All':
        conditions.append("s.department = %s")
        params.append(department)
        
    if year and year != 'All':
        conditions.append("s.year = %s")
        params.append(int(year))
        
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    query = f"""
        SELECT 
            s.student_id,
            s.roll_number,
            s.name,
            s.department,
            s.year,
            a.attendance_id,
            a.status,
            a.remarks
        FROM students s
        LEFT JOIN attendance a 
            ON s.student_id = a.student_id AND a.attendance_date = %s
        {where_clause}
        ORDER BY s.roll_number ASC
    """
    return execute_query(query, tuple(params), fetchall=True) or []

def save_attendance_batch(target_date, records):
    """
    Saves or updates attendance for multiple students for a specific date.
    Prevents duplicate attendance records by enforcing the UNIQUE constraint on (student_id, attendance_date).
    Uses transactional execution.
    """
    conn, engine = get_connection()
    try:
        if engine == 'mysql':
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO attendance (student_id, attendance_date, status, remarks)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        status = VALUES(status), 
                        remarks = VALUES(remarks)
                """
                for rec in records:
                    cur.execute(sql, (
                        rec['student_id'],
                        target_date,
                        rec['status'],
                        rec.get('remarks', '')
                    ))
            conn.commit()
        else:
            cur = conn.cursor()
            sql = """
                INSERT INTO attendance (student_id, attendance_date, status, remarks)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(student_id, attendance_date) DO UPDATE SET 
                    status = excluded.status, 
                    remarks = excluded.remarks
            """
            for rec in records:
                cur.execute(sql, (
                    rec['student_id'],
                    target_date,
                    rec['status'],
                    rec.get('remarks', '')
                ))
            conn.commit()
            
        return True, f"Successfully saved attendance for {len(records)} students on {target_date}."
    except Exception as e:
        if engine == 'mysql':
            conn.rollback()
        return False, f"Failed to record attendance: {str(e)}"
    finally:
        conn.close()

# ====================================================================
# ATTENDANCE REPORTS MODULE (SQL AGGREGATIONS)
# ====================================================================

def get_attendance_reports(student_id=None, department=None, year=None, start_date=None, end_date=None):
    """
    Computes attendance summary and percentage for students using SQL aggregation.
    SQL calculation:
    attendance_percentage = (present_days * 100.0) / total_classes
    """
    # Build filter conditions
    join_conditions = []
    join_params = []
    
    if start_date:
        join_conditions.append("a.attendance_date >= %s")
        join_params.append(start_date)
    if end_date:
        join_conditions.append("a.attendance_date <= %s")
        join_params.append(end_date)
        
    date_join_sql = f"AND {' AND '.join(join_conditions)}" if join_conditions else ""
    
    where_conditions = []
    where_params = []
    
    if student_id and student_id != 'All':
        where_conditions.append("s.student_id = %s")
        where_params.append(int(student_id))
    if department and department != 'All':
        where_conditions.append("s.department = %s")
        where_params.append(department)
    if year and year != 'All':
        where_conditions.append("s.year = %s")
        where_params.append(int(year))
        
    where_sql = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    
    all_params = tuple(join_params + where_params)
    
    query = f"""
        SELECT 
            s.student_id,
            s.roll_number,
            s.name,
            s.department,
            s.year,
            s.email,
            COUNT(a.attendance_id) AS total_classes,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
            CASE 
                WHEN COUNT(a.attendance_id) = 0 THEN 0.0
                ELSE ROUND((SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) * 100.0) / COUNT(a.attendance_id), 2)
            END AS attendance_percentage
        FROM students s
        LEFT JOIN attendance a 
            ON s.student_id = a.student_id {date_join_sql}
        {where_sql}
        GROUP BY s.student_id, s.roll_number, s.name, s.department, s.year, s.email
        ORDER BY s.roll_number ASC
    """
    
    return execute_query(query, all_params, fetchall=True) or []

def get_student_history(student_id, start_date=None, end_date=None):
    """
    Fetches chronological attendance records for an individual student.
    """
    conditions = ["student_id = %s"]
    params = [student_id]
    
    if start_date:
        conditions.append("attendance_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("attendance_date <= %s")
        params.append(end_date)
        
    where_sql = f"WHERE {' AND '.join(conditions)}"
    
    query = f"""
        SELECT 
            attendance_id,
            attendance_date,
            status,
            remarks,
            marked_at
        FROM attendance
        {where_sql}
        ORDER BY attendance_date DESC
    """
    return execute_query(query, tuple(params), fetchall=True) or []

def get_system_status():
    """Returns database connection diagnostics for the UI status badge."""
    global CURRENT_ENGINE, LAST_ERROR
    is_mysql_ok, msg = check_mysql_availability()
    
    return {
        'active_engine': CURRENT_ENGINE,
        'mysql_online': is_mysql_ok,
        'mysql_message': msg,
        'mysql_host': Config.MYSQL_HOST,
        'mysql_port': Config.MYSQL_PORT,
        'mysql_user': Config.MYSQL_USER,
        'mysql_db': Config.MYSQL_DB,
        'last_error': LAST_ERROR
    }
