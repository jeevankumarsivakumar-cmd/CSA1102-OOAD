import os
import csv
import io
from datetime import datetime, date
from database.db import db
from config import Config
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ReportService:
    """
    Comprehensive reporting engine providing tabular aggregations,
    CSV exports, and clean PDF report generation.
    """

    @staticmethod
    def get_report_data(report_type, class_id=None, subject_id=None, student_id=None, start_date=None, end_date=None):
        """
        Gathers structured tabular data based on the requested report type and filters.
        """
        params = []
        
        if report_type == 'daily_attendance':
            target_date = start_date or str(date.today())
            sql = """
                SELECT a.attendance_date, c.class_code, s.subject_code, s.subject_name,
                       u.full_name as student_name, st.student_id as student_code,
                       a.status, a.remarks, uf.full_name as faculty_name
                FROM attendance a
                JOIN students st ON a.student_id = st.id
                JOIN users u ON st.user_id = u.id
                JOIN classes c ON a.class_id = c.id
                JOIN subjects s ON a.subject_id = s.id
                JOIN faculty f ON a.faculty_id = f.id
                JOIN users uf ON f.user_id = uf.id
                WHERE a.attendance_date = %s
            """
            params.append(target_date)
            if class_id:
                sql += " AND a.class_id = %s"
                params.append(class_id)
            sql += " ORDER BY c.class_code, u.full_name"
            headers = ['Date', 'Class', 'Subject Code', 'Subject Name', 'Student Name', 'Student ID', 'Status', 'Remarks', 'Faculty']
            rows = db.query(sql, tuple(params))
            return headers, rows, f"Daily Attendance Report ({target_date})"

        elif report_type == 'monthly_attendance':
            s_date = start_date or str(date.today().replace(day=1))
            e_date = end_date or str(date.today())
            sql = """
                SELECT c.class_code, st.student_id as student_code, u.full_name as student_name,
                       COUNT(a.id) as total_sessions,
                       SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1 ELSE 0 END) as attended,
                       SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent,
                       ROUND((SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1.0 ELSE 0.0 END) / COUNT(a.id)) * 100, 2) as attendance_percentage
                FROM attendance a
                JOIN students st ON a.student_id = st.id
                JOIN users u ON st.user_id = u.id
                JOIN classes c ON a.class_id = c.id
                WHERE a.attendance_date BETWEEN %s AND %s
            """
            params.extend([s_date, e_date])
            if class_id:
                sql += " AND a.class_id = %s"
                params.append(class_id)
            sql += " GROUP BY c.class_code, st.student_id, u.full_name ORDER BY c.class_code, u.full_name"
            headers = ['Class', 'Student ID', 'Student Name', 'Total Sessions', 'Attended', 'Absent', 'Attendance %']
            rows = db.query(sql, tuple(params))
            return headers, rows, f"Monthly Attendance Report ({s_date} to {e_date})"

        elif report_type == 'student_wise':
            sql = """
                SELECT st.student_id as student_code, u.full_name as student_name, c.class_code, st.department,
                       COUNT(a.id) as total_classes,
                       SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) as present,
                       SUM(CASE WHEN a.status = 'On Duty' THEN 1 ELSE 0 END) as on_duty,
                       SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) as absent,
                       ROUND((SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1.0 ELSE 0.0 END) / COUNT(a.id)) * 100, 2) as attendance_pct
                FROM students st
                JOIN users u ON st.user_id = u.id
                JOIN classes c ON st.class_id = c.id
                LEFT JOIN attendance a ON st.id = a.student_id
                WHERE 1=1
            """
            if student_id:
                sql += " AND st.id = %s"
                params.append(student_id)
            if class_id:
                sql += " AND st.class_id = %s"
                params.append(class_id)
            sql += " GROUP BY st.id, st.student_id, u.full_name, c.class_code, st.department ORDER BY attendance_pct ASC"
            headers = ['Student ID', 'Student Name', 'Class', 'Department', 'Total Classes', 'Present', 'On Duty', 'Absent', 'Attendance %']
            rows = db.query(sql, tuple(params))
            return headers, rows, "Student-Wise Attendance Report"

        elif report_type == 'class_wise':
            sql = """
                SELECT c.class_code, c.department, c.semester, c.section,
                       COUNT(DISTINCT st.id) as enrolled_students,
                       COUNT(a.id) as total_attendance_entries,
                       ROUND(AVG(CASE WHEN a.status IN ('Present', 'On Duty') THEN 100.0 ELSE 0.0 END), 2) as avg_attendance_rate
                FROM classes c
                LEFT JOIN students st ON c.id = st.class_id
                LEFT JOIN attendance a ON c.id = a.class_id
                GROUP BY c.id, c.class_code, c.department, c.semester, c.section
                ORDER BY c.class_code
            """
            headers = ['Class Code', 'Department', 'Semester', 'Section', 'Enrolled Students', 'Total Entries', 'Avg Attendance %']
            rows = db.query(sql)
            return headers, rows, "Class-Wise Attendance Summary"

        elif report_type == 'subject_wise':
            sql = """
                SELECT s.subject_code, s.subject_name, s.department, s.credits,
                       COUNT(a.id) as total_sessions_conducted,
                       ROUND(AVG(CASE WHEN a.status IN ('Present', 'On Duty') THEN 100.0 ELSE 0.0 END), 2) as avg_attendance_pct
                FROM subjects s
                LEFT JOIN attendance a ON s.id = a.subject_id
                GROUP BY s.id, s.subject_code, s.subject_name, s.department, s.credits
                ORDER BY s.subject_code
            """
            headers = ['Subject Code', 'Subject Name', 'Department', 'Credits', 'Conducted Sessions', 'Avg Attendance %']
            rows = db.query(sql)
            return headers, rows, "Subject-Wise Attendance Report"

        elif report_type == 'academic_performance':
            sql = """
                SELECT st.student_id as student_code, u.full_name as student_name, c.class_code,
                       s.subject_code, s.subject_name, m.exam_type, m.marks_obtained, m.max_marks,
                       ROUND((m.marks_obtained / m.max_marks) * 100, 2) as percentage
                FROM academic_marks m
                JOIN students st ON m.student_id = st.id
                JOIN users u ON st.user_id = u.id
                JOIN classes c ON st.class_id = c.id
                JOIN subjects s ON m.subject_id = s.id
                WHERE 1=1
            """
            if class_id:
                sql += " AND st.class_id = %s"
                params.append(class_id)
            if subject_id:
                sql += " AND m.subject_id = %s"
                params.append(subject_id)
            sql += " ORDER BY c.class_code, u.full_name, s.subject_code"
            headers = ['Student ID', 'Student Name', 'Class', 'Subject Code', 'Subject Name', 'Exam Type', 'Marks Obtained', 'Max Marks', 'Percentage']
            rows = db.query(sql, tuple(params))
            return headers, rows, "Academic Performance & Marks Report"

        elif report_type == 'ai_prediction':
            sql = """
                SELECT st.student_id as student_code, u.full_name as student_name, c.class_code,
                       p.attendance_percentage, p.total_absences, p.avg_internal_marks, p.previous_gpa,
                       p.risk_category, p.confidence_score, p.risk_factors, p.predicted_at
                FROM prediction_results p
                JOIN students st ON p.student_id = st.id
                JOIN users u ON st.user_id = u.id
                JOIN classes c ON st.class_id = c.id
                WHERE p.id = (SELECT MAX(p2.id) FROM prediction_results p2 WHERE p2.student_id = p.student_id)
            """
            if class_id:
                sql += " AND st.class_id = %s"
                params.append(class_id)
            sql += " ORDER BY p.attendance_percentage ASC, p.avg_internal_marks ASC"
            headers = ['Student ID', 'Student Name', 'Class', 'Attendance %', 'Absences', 'Internal Avg', 'Previous GPA', 'AI Risk Category', 'Confidence %', 'Identified Factors', 'Date']
            rows = db.query(sql, tuple(params))
            return headers, rows, "AI Academic Performance & Risk Classification Report"

        elif report_type == 'absence_summary':
            sql = """
                SELECT st.student_id as student_code, u.full_name as student_name, c.class_code,
                       COUNT(a.id) as total_absences,
                       ROUND((SUM(CASE WHEN a.status IN ('Present', 'On Duty') THEN 1.0 ELSE 0.0 END) / 
                             (SELECT COUNT(*) FROM attendance a2 WHERE a2.student_id = st.id)) * 100, 2) as current_attendance_pct
                FROM attendance a
                JOIN students st ON a.student_id = st.id
                JOIN users u ON st.user_id = u.id
                JOIN classes c ON a.class_id = c.id
                WHERE a.status = 'Absent'
            """
            if class_id:
                sql += " AND a.class_id = %s"
                params.append(class_id)
            sql += " GROUP BY st.id, st.student_id, u.full_name, c.class_code ORDER BY total_absences DESC"
            headers = ['Student ID', 'Student Name', 'Class', 'Total Absences', 'Current Attendance %']
            rows = db.query(sql, tuple(params))
            return headers, rows, "Student Absence Summary Report"

        return [], [], "Unknown Report"

    @staticmethod
    def export_csv(headers, rows, filename="report.csv"):
        """Exports data rows to in-memory CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for r in rows:
            # r can be dict or list
            if isinstance(r, dict):
                writer.writerow(list(r.values()))
            else:
                writer.writerow(r)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def export_pdf(title, headers, rows):
        """Generates a clean PDF document using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1E1B4B'),
            spaceAfter=10
        )
        meta_style = ParagraphStyle(
            'ReportMeta',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#6B7280'),
            spaceAfter=15
        )

        elements.append(Paragraph(f"<b>AI-Powered Student Analytics System</b>", title_style))
        elements.append(Paragraph(f"<b>Report:</b> {title} | <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", meta_style))
        elements.append(Spacer(1, 10))

        # Convert table data
        table_data = [headers]
        for row in rows[:150]:  # Cap at 150 rows for clean PDF rendering
            if isinstance(row, dict):
                table_data.append([str(v or '') for v in row.values()])
            else:
                table_data.append([str(v or '') for v in row])

        if len(table_data) > 1:
            col_count = len(headers)
            t = Table(table_data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366F1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("No records found matching the specified criteria.", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
