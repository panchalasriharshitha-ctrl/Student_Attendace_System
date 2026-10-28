-- ====================================================================
-- DATABASE CREATION SCRIPT: Student Attendance Management System
-- DBMS Mini Project - BTech Computer Science & Engineering
-- ====================================================================

-- 1. Create Database if it does not already exist
CREATE DATABASE IF NOT EXISTS student_attendance 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE student_attendance;

-- ====================================================================
-- 2. TABLE DEFINITIONS
-- ====================================================================

-- A. Admin Table
-- Stores administrator / faculty credentials for portal access
CREATE TABLE IF NOT EXISTS admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- B. Students Table
-- Stores student demographic and academic records
CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50) NOT NULL,
    year INT NOT NULL CHECK (year BETWEEN 1 AND 4),
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_department (department),
    INDEX idx_roll_number (roll_number)
) ENGINE=InnoDB;

-- C. Attendance Table
-- Records daily attendance for each student
-- Enforces:
-- 1. FOREIGN KEY to students table with ON DELETE CASCADE
-- 2. UNIQUE constraint on (student_id, attendance_date) to prevent duplicate entries on the same day
-- 3. ENUM status ('Present', 'Absent')
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
        UNIQUE (student_id, attendance_date),
    INDEX idx_attendance_date (attendance_date),
    INDEX idx_student_status (student_id, status)
) ENGINE=InnoDB;

-- ====================================================================
-- 3. SAMPLE DATA INSERTION (FOR TESTING AND VIVA DEMONSTRATION)
-- ====================================================================

-- Default Admin Account:
-- Username: admin
-- Password: password123 (hashed using Werkzeug scrypt or sha256 compatible format)
-- Plaintext for manual testing: 'admin123'
INSERT INTO admin (username, password_hash, full_name, email)
VALUES (
    'admin', 
    'scrypt:32768:8:1$uH37sA72R1Z1zM2H$3f24bfd27bf9e9c8fa72911b3bc5928d150b07f66a2b89d81dbe59bf7a7f459c5bfca7d424b94f6e1f0e44795e1ee728bfdd2199b457a419c8fbc4cbb0f6d396', 
    'System Administrator', 
    'admin@college.edu'
)
ON DUPLICATE KEY UPDATE full_name = VALUES(full_name);

-- Sample Students (Computer Science & Information Technology BTech)
INSERT INTO students (roll_number, name, department, year, email)
VALUES 
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
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Sample Attendance Data for past dates
-- Date 1: 2026-10-26
INSERT INTO attendance (student_id, attendance_date, status, remarks)
VALUES 
    (1, '2026-10-26', 'Present', 'Regular session'),
    (2, '2026-10-26', 'Present', 'Regular session'),
    (3, '2026-10-26', 'Absent', 'Medical leave'),
    (4, '2026-10-26', 'Present', 'Regular session'),
    (5, '2026-10-26', 'Present', 'Regular session'),
    (6, '2026-10-26', 'Present', 'Regular session'),
    (7, '2026-10-26', 'Absent', 'Unexcused'),
    (8, '2026-10-26', 'Present', 'Regular session'),
    (9, '2026-10-26', 'Present', 'Regular session'),
    (10, '2026-10-26', 'Present', 'Regular session')
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- Date 2: 2026-10-27
INSERT INTO attendance (student_id, attendance_date, status, remarks)
VALUES 
    (1, '2026-10-27', 'Present', 'Lab session'),
    (2, '2026-10-27', 'Absent', 'Sports tournament'),
    (3, '2026-10-27', 'Present', 'Lab session'),
    (4, '2026-10-27', 'Present', 'Lab session'),
    (5, '2026-10-27', 'Absent', 'Sick'),
    (6, '2026-10-27', 'Present', 'Lab session'),
    (7, '2026-10-27', 'Present', 'Lab session'),
    (8, '2026-10-27', 'Present', 'Lab session'),
    (9, '2026-10-27', 'Absent', 'Family function'),
    (10, '2026-10-27', 'Present', 'Lab session')
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- Date 3: 2026-10-28 (Today)
INSERT INTO attendance (student_id, attendance_date, status, remarks)
VALUES 
    (1, '2026-10-28', 'Present', 'On time'),
    (2, '2026-10-28', 'Present', 'On time'),
    (3, '2026-10-28', 'Present', 'On time'),
    (4, '2026-10-28', 'Present', 'On time'),
    (5, '2026-10-28', 'Present', 'On time'),
    (6, '2026-10-28', 'Absent', 'Informed'),
    (7, '2026-10-28', 'Present', 'On time'),
    (8, '2026-10-28', 'Present', 'On time'),
    (9, '2026-10-28', 'Present', 'On time'),
    (10, '2026-10-28', 'Absent', 'Sick')
ON DUPLICATE KEY UPDATE status = VALUES(status);

-- ====================================================================
-- 4. IMPORTANT SQL QUERIES (FOR DBMS PROJECT VIVA & REPORTING)
-- ====================================================================

-- Query 1: Calculate Overall Attendance Percentage for all students
-- SELECT 
--     s.student_id,
--     s.roll_number,
--     s.name,
--     s.department,
--     s.year,
--     COUNT(a.attendance_id) AS total_classes,
--     SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
--     SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
--     ROUND(
--         (SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) * 100.0) / 
--         NULLIF(COUNT(a.attendance_id), 0), 2
--     ) AS attendance_percentage
-- FROM students s
-- LEFT JOIN attendance a ON s.student_id = a.student_id
-- GROUP BY s.student_id, s.roll_number, s.name, s.department, s.year
-- ORDER BY s.roll_number ASC;

-- Query 2: Daily Attendance Summary for Dashboard
-- SELECT 
--     COUNT(s.student_id) AS total_registered,
--     SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS total_present,
--     SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS total_absent,
--     COUNT(s.student_id) - COUNT(a.attendance_id) AS unmarked
-- FROM students s
-- LEFT JOIN attendance a ON s.student_id = a.student_id AND a.attendance_date = CURRENT_DATE();
