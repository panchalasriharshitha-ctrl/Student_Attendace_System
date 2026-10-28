"""
Student Attendance Management System
BTech 2nd Year Computer Science & Engineering - DBMS Mini Project
Flask Backend Application
"""

import os
from datetime import date, datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, jsonify
)
from db_config import Config
import database

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)

# Ensure instance folder exists
os.makedirs(app.instance_path, exist_ok=True)

# Initialize database schema and initial data
with app.app_context():
    database.init_db()

# ====================================================================
# AUTHENTICATION HELPERS
# ====================================================================

def login_required(f):
    """Decorator to protect routes requiring admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash("Please sign in to access this portal.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_data():
    """Injects system status and current date into all Jinja templates."""
    status = database.get_system_status()
    today_str = date.today().strftime('%Y-%m-%d')
    current_admin = None
    if 'admin_id' in session:
        current_admin = {
            'username': session.get('username'),
            'full_name': session.get('full_name')
        }
    return dict(
        db_status=status,
        today=today_str,
        current_admin=current_admin
    )

# ====================================================================
# AUTHENTICATION ROUTES
# ====================================================================

@app.route('/')
def index():
    """Redirect to dashboard if logged in, else to login page."""
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page and verification."""
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template('login.html')
            
        admin = database.authenticate_admin(username, password)
        if admin:
            session['admin_id'] = admin['admin_id']
            session['username'] = admin['username']
            session['full_name'] = admin['full_name']
            flash(f"Welcome back, {admin['full_name']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid administrator credentials. Please check your username and password.", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Log out administrator and clear session."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('login'))

# ====================================================================
# DASHBOARD MODULE
# ====================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard displaying live statistics, attendance metrics,
    department distribution, and quick action shortcuts.
    """
    target_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    metrics = database.get_dashboard_metrics(target_date)
    departments = database.get_distinct_departments()
    
    return render_template(
        'dashboard.html',
        metrics=metrics,
        selected_date=target_date,
        departments=departments
    )

# ====================================================================
# STUDENT MANAGEMENT MODULE (CRUD)
# ====================================================================

@app.route('/students')
@login_required
def students():
    """Display student list with search and filters."""
    search = request.args.get('search', '').strip()
    department = request.args.get('department', 'All')
    year = request.args.get('year', 'All')
    
    student_list = database.get_all_students(search=search, department=department, year=year)
    departments = database.get_distinct_departments()
    
    return render_template(
        'students.html',
        students=student_list,
        departments=departments,
        selected_dept=department,
        selected_year=year,
        search_query=search
    )

@app.route('/students/add', methods=['POST'])
@login_required
def add_student_route():
    """Add a new student record to the database."""
    name = request.form.get('name', '').strip()
    roll_number = request.form.get('roll_number', '').strip()
    department = request.form.get('department', '').strip()
    year = request.form.get('year', '').strip()
    email = request.form.get('email', '').strip()
    
    if not all([name, roll_number, department, year, email]):
        flash("All fields are mandatory to register a student.", "danger")
        return redirect(url_for('students'))
        
    try:
        year_int = int(year)
        if year_int < 1 or year_int > 4:
            raise ValueError()
    except ValueError:
        flash("Academic Year must be a number between 1 and 4.", "danger")
        return redirect(url_for('students'))
        
    success, message = database.add_student(name, roll_number, department, year_int, email)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for('students'))

@app.route('/students/edit/<int:student_id>', methods=['POST'])
@login_required
def edit_student_route(student_id):
    """Update an existing student's details."""
    name = request.form.get('name', '').strip()
    roll_number = request.form.get('roll_number', '').strip()
    department = request.form.get('department', '').strip()
    year = request.form.get('year', '').strip()
    email = request.form.get('email', '').strip()
    
    if not all([name, roll_number, department, year, email]):
        flash("All fields are mandatory to update a student.", "danger")
        return redirect(url_for('students'))
        
    try:
        year_int = int(year)
        if year_int < 1 or year_int > 4:
            raise ValueError()
    except ValueError:
        flash("Academic Year must be between 1 and 4.", "danger")
        return redirect(url_for('students'))
        
    success, message = database.update_student(student_id, name, roll_number, department, year_int, email)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for('students'))

@app.route('/students/delete/<int:student_id>', methods=['POST'])
@login_required
def delete_student_route(student_id):
    """Delete a student and cascade delete associated attendance records."""
    success, message = database.delete_student(student_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")
        
    return redirect(url_for('students'))

# ====================================================================
# ATTENDANCE MANAGEMENT MODULE
# ====================================================================

@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    """
    Attendance recording interface:
    - View student roster for selected date
    - Mark Present/Absent
    - Save batch attendance into MySQL with duplicate prevention
    """
    if request.method == 'POST':
        target_date = request.form.get('attendance_date')
        if not target_date:
            flash("Attendance date is required.", "danger")
            return redirect(url_for('attendance'))
            
        # Collect marked attendance from form submissions
        # Form inputs: status_<student_id>, remarks_<student_id>
        records = []
        for key, val in request.form.items():
            if key.startswith('status_'):
                student_id = int(key.replace('status_', ''))
                status = val
                remarks = request.form.get(f'remarks_{student_id}', '').strip()
                records.append({
                    'student_id': student_id,
                    'status': status,
                    'remarks': remarks
                })
                
        if not records:
            flash("No student attendance records were submitted.", "warning")
            return redirect(url_for('attendance', date=target_date))
            
        success, message = database.save_attendance_batch(target_date, records)
        if success:
            flash(message, "success")
        else:
            flash(message, "danger")
            
        department = request.form.get('department', 'All')
        year = request.form.get('year', 'All')
        return redirect(url_for('attendance', date=target_date, department=department, year=year))
        
    # GET request: load sheet for selected date and filters
    target_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    department = request.args.get('department', 'All')
    year = request.args.get('year', 'All')
    
    sheet = database.get_attendance_sheet(target_date, department=department, year=year)
    departments = database.get_distinct_departments()
    
    # Check if attendance has already been marked for this date
    marked_count = sum(1 for s in sheet if s['status'] is not None)
    
    return render_template(
        'attendance.html',
        sheet=sheet,
        selected_date=target_date,
        selected_dept=department,
        selected_year=year,
        departments=departments,
        marked_count=marked_count,
        total_students=len(sheet)
    )

# ====================================================================
# ATTENDANCE REPORTS MODULE
# ====================================================================

@app.route('/reports')
@login_required
def reports():
    """
    Attendance reports computed via SQL aggregation.
    Displays percentage, total classes, present, absent counts,
    and eligibility badge.
    """
    student_id = request.args.get('student_id', 'All')
    department = request.args.get('department', 'All')
    year = request.args.get('year', 'All')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    report_data = database.get_attendance_reports(
        student_id=student_id,
        department=department,
        year=year,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None
    )
    
    all_students = database.get_all_students()
    departments = database.get_distinct_departments()
    
    return render_template(
        'reports.html',
        reports=report_data,
        all_students=all_students,
        departments=departments,
        selected_student=student_id,
        selected_dept=department,
        selected_year=year,
        start_date=start_date,
        end_date=end_date
    )

@app.route('/api/student-history/<int:student_id>')
@login_required
def student_history_api(student_id):
    """JSON API endpoint returning chronological attendance log for an individual student."""
    student = database.get_student_by_id(student_id)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
        
    history = database.get_student_history(student_id)
    return jsonify({
        'student': student,
        'history': history
    })

# ====================================================================
# SYSTEM & DATABASE STATUS
# ====================================================================

@app.route('/db-status')
@login_required
def db_status_page():
    """Information page detailing MySQL connection status and schema info."""
    status = database.get_system_status()
    return render_template('db_status.html', status=status)

# ====================================================================
# APPLICATION ENTRYPOINT
# ====================================================================

if __name__ == '__main__':
    print("=" * 65)
    print("🎓 Student Attendance Management System - Flask Server Starting")
    print(f"📡 Access URL: http://127.0.0.1:5000")
    print(f"🔑 Default Admin Credentials: Username: admin | Password: admin123")
    print("=" * 65)
    app.run(host='0.0.0.0', port=5000, debug=True)
