-- AcadBot Database Schema
-- Creates all required tables for AcadBot

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    branch VARCHAR(50) NOT NULL,
    batch_year INT NOT NULL,
    email VARCHAR(100)
);

-- Subjects table
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subject_code VARCHAR(20) UNIQUE NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    credits INT NOT NULL,
    semester INT NOT NULL,
    branch VARCHAR(50) NOT NULL
);

-- Results table with auto-computed grade and grade_points
CREATE TABLE IF NOT EXISTS results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20) NOT NULL,
    subject_code VARCHAR(20) NOT NULL,
    semester INT NOT NULL,
    academic_year VARCHAR(10) NOT NULL,
    internal_marks FLOAT DEFAULT 0,
    external_marks FLOAT DEFAULT 0,
    total_marks FLOAT GENERATED ALWAYS AS (internal_marks + external_marks) STORED,
    grade VARCHAR(2) GENERATED ALWAYS AS (
        CASE
            WHEN (internal_marks + external_marks) >= 90 THEN 'O'
            WHEN (internal_marks + external_marks) >= 80 THEN 'A+'
            WHEN (internal_marks + external_marks) >= 70 THEN 'A'
            WHEN (internal_marks + external_marks) >= 60 THEN 'B+'
            WHEN (internal_marks + external_marks) >= 50 THEN 'B'
            WHEN (internal_marks + external_marks) >= 40 THEN 'C'
            ELSE 'F'
        END
    ) STORED,
    grade_points FLOAT GENERATED ALWAYS AS (
        CASE
            WHEN (internal_marks + external_marks) >= 90 THEN 10
            WHEN (internal_marks + external_marks) >= 80 THEN 9
            WHEN (internal_marks + external_marks) >= 70 THEN 8
            WHEN (internal_marks + external_marks) >= 60 THEN 7
            WHEN (internal_marks + external_marks) >= 50 THEN 6
            WHEN (internal_marks + external_marks) >= 40 THEN 5
            ELSE 0
        END
    ) STORED,
    FOREIGN KEY (roll_number) REFERENCES students(roll_number),
    FOREIGN KEY (subject_code) REFERENCES subjects(subject_code),
    UNIQUE KEY unique_result (roll_number, subject_code, semester)
);

-- Attendance table with auto-computed percentage and status
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20) NOT NULL,
    subject_code VARCHAR(20) NOT NULL,
    semester INT NOT NULL,
    academic_year VARCHAR(10) NOT NULL,
    total_classes INT NOT NULL DEFAULT 0,
    attended_classes INT NOT NULL DEFAULT 0,
    attendance_percent FLOAT GENERATED ALWAYS AS (
        CASE WHEN total_classes = 0 THEN 0
        ELSE ROUND((attended_classes / total_classes) * 100, 2)
        END
    ) STORED,
    status VARCHAR(20) GENERATED ALWAYS AS (
        CASE
            WHEN total_classes = 0 THEN 'No Data'
            WHEN (attended_classes / total_classes) * 100 >= 75 THEN 'Safe'
            WHEN (attended_classes / total_classes) * 100 >= 65 THEN 'Warning'
            ELSE 'Detained Risk'
        END
    ) STORED,
    FOREIGN KEY (roll_number) REFERENCES students(roll_number),
    FOREIGN KEY (subject_code) REFERENCES subjects(subject_code),
    UNIQUE KEY unique_attendance (roll_number, subject_code, semester)
);

-- SGPA Summary table (real data from college Excel)
CREATE TABLE IF NOT EXISTS sgpa_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    roll_number VARCHAR(20) NOT NULL,
    semester INT NOT NULL,
    sgpa FLOAT DEFAULT NULL,
    has_backlogs TINYINT(1) DEFAULT 0,
    backlog_count INT DEFAULT 0,
    status VARCHAR(30) DEFAULT 'Clear',
    FOREIGN KEY (roll_number) REFERENCES students(roll_number),
    UNIQUE KEY unique_roll_sem (roll_number, semester)
);
