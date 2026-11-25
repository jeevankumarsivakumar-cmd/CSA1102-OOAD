-- =====================================================================
-- AI-POWERED STUDENT ATTENDANCE AND ACADEMIC ANALYTICS SYSTEM
-- Database Schema for MySQL 8.0 / MariaDB
-- Demonstrating 3NF Normalization, Referential Integrity & Indexing
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `student_analytics_db` 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `student_analytics_db`;

-- Drop existing tables in reverse dependency order
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `prediction_results`;
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `academic_marks`;
DROP TABLE IF EXISTS `attendance`;
DROP TABLE IF EXISTS `timetable`;
DROP TABLE IF EXISTS `subjects`;
DROP TABLE IF EXISTS `students`;
DROP TABLE IF EXISTS `faculty`;
DROP TABLE IF EXISTS `classes`;
DROP TABLE IF EXISTS `users`;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. USERS TABLE (Authentication & Base Role entity)
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `username` VARCHAR(60) NOT NULL UNIQUE,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'faculty', 'student') NOT NULL,
    `full_name` VARCHAR(120) NOT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `avatar` VARCHAR(255) DEFAULT NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_users_role` (`role`),
    INDEX `idx_users_email` (`email`)
) ENGINE=InnoDB;

-- 2. CLASSES TABLE
CREATE TABLE `classes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `class_code` VARCHAR(30) NOT NULL UNIQUE,  -- e.g., 'CSE-4A', 'ECE-3B'
    `department` VARCHAR(60) NOT NULL,        -- e.g., 'Computer Science & Engineering'
    `semester` INT NOT NULL,                  -- 1 to 8
    `academic_year` VARCHAR(20) NOT NULL,     -- e.g., '2025-2026'
    `section` VARCHAR(10) NOT NULL,           -- e.g., 'A', 'B'
    `room_number` VARCHAR(30) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_classes_dept` (`department`, `semester`)
) ENGINE=InnoDB;

-- 3. FACULTY TABLE
CREATE TABLE `faculty` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `employee_id` VARCHAR(30) NOT NULL UNIQUE, -- e.g., 'FAC202401'
    `department` VARCHAR(60) NOT NULL,
    `designation` VARCHAR(60) NOT NULL,        -- 'Professor', 'Associate Professor', 'Assistant Professor'
    `qualification` VARCHAR(100) DEFAULT NULL,
    `specialization` VARCHAR(120) DEFAULT NULL,
    `joining_date` DATE DEFAULT NULL,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_faculty_dept` (`department`)
) ENGINE=InnoDB;

-- 4. STUDENTS TABLE
CREATE TABLE `students` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `student_id` VARCHAR(30) NOT NULL UNIQUE, -- e.g., 'STU2026001'
    `class_id` INT NOT NULL,
    `department` VARCHAR(60) NOT NULL,
    `academic_year` VARCHAR(20) NOT NULL,
    `contact_phone` VARCHAR(20) DEFAULT NULL,
    `emergency_contact` VARCHAR(20) DEFAULT NULL,
    `address` TEXT DEFAULT NULL,
    `date_of_birth` DATE DEFAULT NULL,
    `enrollment_status` ENUM('Active', 'Suspended', 'Graduated', 'Withdrawn') DEFAULT 'Active',
    `previous_gpa` DECIMAL(4,2) DEFAULT 7.50,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`class_id`) REFERENCES `classes`(`id`) ON DELETE RESTRICT,
    INDEX `idx_students_class` (`class_id`),
    INDEX `idx_students_dept` (`department`)
) ENGINE=InnoDB;

-- 5. SUBJECTS TABLE
CREATE TABLE `subjects` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `subject_code` VARCHAR(20) NOT NULL UNIQUE, -- e.g., 'CS401'
    `subject_name` VARCHAR(120) NOT NULL,       -- e.g., 'Object Oriented Analysis & Design'
    `department` VARCHAR(60) NOT NULL,
    `credits` INT NOT NULL DEFAULT 3,
    `semester` INT NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_subjects_dept` (`department`, `semester`)
) ENGINE=InnoDB;

-- 6. TIMETABLE TABLE
CREATE TABLE `timetable` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `class_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `faculty_id` INT NOT NULL,
    `day_of_week` ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday') NOT NULL,
    `start_time` TIME NOT NULL,
    `end_time` TIME NOT NULL,
    `room_number` VARCHAR(30) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`class_id`) REFERENCES `classes`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`faculty_id`) REFERENCES `faculty`(`id`) ON DELETE CASCADE,
    INDEX `idx_timetable_lookup` (`class_id`, `day_of_week`),
    INDEX `idx_timetable_faculty` (`faculty_id`, `day_of_week`)
) ENGINE=InnoDB;

-- 7. ATTENDANCE TABLE (Strict uniqueness to prevent duplicate records)
CREATE TABLE `attendance` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `class_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `faculty_id` INT NOT NULL,
    `attendance_date` DATE NOT NULL,
    `status` ENUM('Present', 'Absent', 'On Duty') NOT NULL,
    `remarks` VARCHAR(255) DEFAULT NULL,
    `recorded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`class_id`) REFERENCES `classes`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`faculty_id`) REFERENCES `faculty`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `unique_student_subject_date` (`student_id`, `subject_id`, `attendance_date`),
    INDEX `idx_att_date_class` (`attendance_date`, `class_id`),
    INDEX `idx_att_student_stats` (`student_id`, `status`)
) ENGINE=InnoDB;

-- 8. ACADEMIC MARKS TABLE
CREATE TABLE `academic_marks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `subject_id` INT NOT NULL,
    `exam_type` ENUM('Internal 1', 'Internal 2', 'Assignment', 'Lab Assessment', 'Final Exam') NOT NULL,
    `marks_obtained` DECIMAL(5,2) NOT NULL,
    `max_marks` DECIMAL(5,2) NOT NULL DEFAULT 50.00,
    `exam_date` DATE NOT NULL,
    `entered_by` INT NOT NULL,
    `remarks` VARCHAR(255) DEFAULT NULL,
    `recorded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`subject_id`) REFERENCES `subjects`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`entered_by`) REFERENCES `faculty`(`id`) ON DELETE CASCADE,
    UNIQUE KEY `unique_student_subject_exam` (`student_id`, `subject_id`, `exam_type`),
    INDEX `idx_marks_student` (`student_id`)
) ENGINE=InnoDB;

-- 9. NOTIFICATIONS TABLE
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,                      -- Recipient user ID
    `student_id` INT DEFAULT NULL,               -- Related student entity (if applicable)
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `category` ENUM('Absence Alert', 'Low Attendance Warning', 'Academic Risk', 'General Notice') NOT NULL,
    `priority` ENUM('High', 'Medium', 'Low') DEFAULT 'Medium',
    `is_read` BOOLEAN DEFAULT FALSE,
    `delivery_status` ENUM('Delivered', 'Pending', 'Failed') DEFAULT 'Delivered',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE SET NULL,
    INDEX `idx_notifications_user_read` (`user_id`, `is_read`),
    INDEX `idx_notifications_category` (`category`)
) ENGINE=InnoDB;

-- 10. PREDICTION RESULTS TABLE (ML AI Risk Output)
CREATE TABLE `prediction_results` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `attendance_percentage` DECIMAL(5,2) NOT NULL,
    `total_absences` INT NOT NULL,
    `avg_internal_marks` DECIMAL(5,2) NOT NULL,
    `previous_gpa` DECIMAL(4,2) NOT NULL,
    `risk_category` ENUM('Good Performance', 'Average Performance', 'Needs Improvement') NOT NULL,
    `confidence_score` DECIMAL(5,2) NOT NULL,   -- e.g., 91.50%
    `risk_factors` TEXT DEFAULT NULL,           -- JSON or text summary of factors
    `model_version` VARCHAR(30) DEFAULT 'v1.0-RF',
    `predicted_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`student_id`) REFERENCES `students`(`id`) ON DELETE CASCADE,
    INDEX `idx_predictions_student` (`student_id`),
    INDEX `idx_predictions_category` (`risk_category`)
) ENGINE=InnoDB;

-- =====================================================================
-- ADDITIVE CAPSTONE EXTENSION: ADVANCED INNOVATION MODULES
-- =====================================================================

-- 11. FACULTY INTERVENTIONS TABLE (Smart Faculty Mentoring & Student Support)
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

-- 12. STUDENT IMPROVEMENT GOALS TABLE (Personalized Action Planner & Tracking)
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

