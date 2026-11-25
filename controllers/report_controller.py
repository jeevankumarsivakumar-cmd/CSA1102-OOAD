from flask import Blueprint, render_template, request, Response, send_file, flash, redirect, url_for
from services.report_service import ReportService
from database.db import db
from models.classroom import ClassRoom, Subject
from controllers.auth_controller import login_required, role_required
import io

report_bp = Blueprint('report', __name__, url_prefix='/reports')

@report_bp.before_request
@login_required
@role_required(['admin', 'faculty'])
def check_report_access():
    pass

@report_bp.route('/', methods=['GET'])
def index():
    report_type = request.args.get('report_type', 'daily_attendance')
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    student_id = request.args.get('student_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    headers, rows, title = ReportService.get_report_data(
        report_type=report_type,
        class_id=int(class_id) if class_id else None,
        subject_id=int(subject_id) if subject_id else None,
        student_id=int(student_id) if student_id else None,
        start_date=start_date,
        end_date=end_date
    )

    classes = ClassRoom.get_all()
    subjects = Subject.get_all()
    students = db.query("SELECT s.id, s.student_id, u.full_name FROM students s JOIN users u ON s.user_id = u.id ORDER BY u.full_name")

    return render_template(
        'reports/index.html',
        report_type=report_type,
        class_id=int(class_id) if class_id else None,
        subject_id=int(subject_id) if subject_id else None,
        student_id=int(student_id) if student_id else None,
        start_date=start_date,
        end_date=end_date,
        title=title,
        headers=headers,
        rows=rows,
        classes=classes,
        subjects=subjects,
        students=students
    )

@report_bp.route('/export/csv', methods=['GET'])
def export_csv():
    report_type = request.args.get('report_type', 'daily_attendance')
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    student_id = request.args.get('student_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    headers, rows, title = ReportService.get_report_data(
        report_type=report_type,
        class_id=int(class_id) if class_id else None,
        subject_id=int(subject_id) if subject_id else None,
        student_id=int(student_id) if student_id else None,
        start_date=start_date,
        end_date=end_date
    )

    csv_data = ReportService.export_csv(headers, rows)
    filename = f"{report_type}_{title.replace(' ', '_').lower()}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@report_bp.route('/export/pdf', methods=['GET'])
def export_pdf():
    report_type = request.args.get('report_type', 'daily_attendance')
    class_id = request.args.get('class_id')
    subject_id = request.args.get('subject_id')
    student_id = request.args.get('student_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    headers, rows, title = ReportService.get_report_data(
        report_type=report_type,
        class_id=int(class_id) if class_id else None,
        subject_id=int(subject_id) if subject_id else None,
        student_id=int(student_id) if student_id else None,
        start_date=start_date,
        end_date=end_date
    )

    pdf_bytes = ReportService.export_pdf(title, headers, rows)
    filename = f"{report_type}_report.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )
