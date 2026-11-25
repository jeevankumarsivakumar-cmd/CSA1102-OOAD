from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from services.prediction_service import PredictionService
from controllers.auth_controller import login_required, role_required
from database.db import db

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.before_request
@login_required
@role_required(['admin', 'faculty'])
def check_analytics_access():
    pass

@analytics_bp.route('/ai')
def ai_dashboard():
    # Gather comprehensive AI analytics bundle
    dashboard_data = PredictionService.get_ai_analytics_dashboard_data()
    classes = db.query("SELECT id, class_code, department FROM classes ORDER BY class_code")

    # Subject performance overview
    subject_perf = db.query("""
        SELECT s.subject_code, s.subject_name,
               COUNT(m.id) as tests_recorded,
               ROUND(AVG((m.marks_obtained / m.max_marks) * 100), 1) as avg_score_pct
        FROM subjects s
        LEFT JOIN academic_marks m ON s.id = m.subject_id
        GROUP BY s.id, s.subject_code, s.subject_name
        ORDER BY s.subject_code
    """)

    return render_template(
        'analytics/ai_insights.html',
        data=dashboard_data,
        classes=classes,
        subject_perf=subject_perf
    )

@analytics_bp.route('/ai/recompute-all', methods=['POST'])
def recompute_all():
    results = PredictionService.run_batch_predictions_for_all()
    flash(f"AI performance prediction models recomputed for {len(results)} students successfully!", "success")
    return redirect(url_for('analytics.ai_dashboard'))

@analytics_bp.route('/api/predict/<int:student_id>', methods=['GET'])
def api_predict_student(student_id):
    """REST API endpoint returning ML inference payload."""
    try:
        res = PredictionService.predict_student(student_id, trigger_alert=False)
        return jsonify({
            'status': 'success',
            'data': res
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
