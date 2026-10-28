from app import app
import database

client = app.test_client()

# Admin Login
res = client.post('/login', data={'username': 'admin', 'password': 'admin123'})
assert res.status_code == 302 or res.status_code == 200

# 1. Test Add Student
res = client.post('/students/add', data={
    'name': 'Test Candidate',
    'roll_number': '24CS999',
    'department': 'Computer Science',
    'year': '2',
    'email': 'candidate999@college.edu'
}, follow_redirects=True)
assert res.status_code == 200
assert b'Student added successfully' in res.data
print('[PASS] 1. Add Student')

# Verify student exists in DB
student = database.execute_query('SELECT * FROM students WHERE roll_number = %s', ('24CS999',), fetchone=True)
assert student is not None
student_id = student['student_id']
print(f'[PASS] 2. Student verified in DB (ID: {student_id})')

# 2. Test Duplicate Roll Number Prevention
res = client.post('/students/add', data={
    'name': 'Duplicate Candidate',
    'roll_number': '24CS999',
    'department': 'Computer Science',
    'year': '2',
    'email': 'other@college.edu'
}, follow_redirects=True)
assert b'already registered' in res.data
print('[PASS] 3. Duplicate Roll Number Rejected')

# 3. Test Edit Student
res = client.post(f'/students/edit/{student_id}', data={
    'name': 'Updated Candidate',
    'roll_number': '24CS999',
    'department': 'Information Technology',
    'year': '3',
    'email': 'candidate999@college.edu'
}, follow_redirects=True)
assert b'Student details updated successfully' in res.data
updated_student = database.get_student_by_id(student_id)
assert updated_student['name'] == 'Updated Candidate'
assert updated_student['department'] == 'Information Technology'
assert updated_student['year'] == 3
print('[PASS] 4. Edit Student')

# 4. Test Mark Attendance Batch
res = client.post('/attendance', data={
    'attendance_date': '2026-10-29',
    'department': 'All',
    'year': 'All',
    f'status_{student_id}': 'Present',
    f'remarks_{student_id}': 'First class on new date'
}, follow_redirects=True)
assert b'Successfully saved attendance' in res.data
print('[PASS] 5. Mark Attendance Batch')

# Verify attendance in DB
att = database.execute_query('SELECT * FROM attendance WHERE student_id = %s AND attendance_date = %s', (student_id, '2026-10-29'), fetchone=True)
assert att is not None and att['status'] == 'Present'
print('[PASS] 6. Attendance verified in DB')

# 5. Test Attendance Reports SQL Aggregation
report = database.get_attendance_reports(student_id=student_id)
assert len(report) == 1
assert report[0]['total_classes'] == 1
assert report[0]['present_count'] == 1
assert report[0]['attendance_percentage'] == 100.0
pct = report[0]['attendance_percentage']
print(f'[PASS] 7. SQL Percentage Calculation: {pct}%')

# 6. Test Delete Student (Foreign Key CASCADE)
res = client.post(f'/students/delete/{student_id}', follow_redirects=True)
assert b'Student and corresponding attendance records deleted successfully' in res.data
deleted_student = database.get_student_by_id(student_id)
assert deleted_student is None
# Verify cascaded attendance is also deleted
att_check = database.execute_query('SELECT * FROM attendance WHERE student_id = %s', (student_id,), fetchall=True)
assert len(att_check) == 0
print('[PASS] 8. Delete Student with Foreign Key ON DELETE CASCADE verified')

print('\n' + '='*60)
print('ALL DBMS Mini Project Verification Tests Passed (8/8)!')
print('='*60)

