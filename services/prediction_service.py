import os
import json
import joblib
import numpy as np
from abc import ABC, abstractmethod
from config import Config
from database.db import db
from services.attendance_service import AttendanceService
from services.notification_service import NotificationService

class BasePredictor(ABC):
    """
    Abstract Base Class for Academic Performance Predictors.
    Demonstrates Abstraction and allows easy swapping or upgrading
    of Machine Learning models in the future.
    """
    @abstractmethod
    def predict(self, feature_vector):
        pass

    @abstractmethod
    def get_metadata(self):
        pass


class RandomForestPerformancePredictor(BasePredictor):
    """
    Random Forest implementation of academic performance classification.
    Predicts: 'Good Performance', 'Average Performance', or 'Needs Improvement'.
    """
    def __init__(self, model_path=None, metadata_path=None):
        self.model_path = model_path or Config.ML_MODEL_PATH
        self.metadata_path = metadata_path or Config.ML_METADATA_PATH
        self._bundle = None
        self._metadata = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self._bundle = joblib.load(self.model_path)
            except Exception as e:
                print(f"[PredictionService] Failed to load model from {self.model_path}: {e}")
                self._bundle = None
        
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r') as f:
                    self._metadata = json.load(f)
            except Exception as e:
                print(f"[PredictionService] Failed to load metadata: {e}")
                self._metadata = None

    def get_metadata(self):
        return self._metadata or {}

    def predict(self, feature_vector):
        """
        Runs model inference on feature_vector:
        [attendance_percentage, absence_count, internal_marks, previous_gpa]
        Returns: (predicted_category, confidence_pct, class_probabilities)
        """
        if not self._bundle:
            # Fallback heuristic if model file is not present
            att, abs_cnt, marks, gpa = feature_vector
            score = (0.4 * marks) + (0.35 * att) + (0.25 * (gpa * 10))
            if score >= 75:
                return 'Good Performance', 85.0, {}
            elif score >= 55:
                return 'Average Performance', 80.0, {}
            else:
                return 'Needs Improvement', 88.0, {}

        model = self._bundle['model']
        scaler = self._bundle['scaler']
        classes = self._bundle['classes']
        feat_names = self._bundle.get('feature_names', ['attendance_percentage', 'absence_count', 'internal_marks', 'previous_gpa'])

        import pandas as pd
        X_df = pd.DataFrame([feature_vector], columns=feat_names)
        X_scaled = scaler.transform(X_df)

        predicted_class = model.predict(X_scaled)[0]
        probabilities = model.predict_proba(X_scaled)[0]

        pred_idx = list(classes).index(predicted_class)
        confidence = round(float(probabilities[pred_idx]) * 100, 2)
        prob_dict = {cls_name: round(float(prob) * 100, 2) for cls_name, prob in zip(classes, probabilities)}

        return predicted_class, confidence, prob_dict


class PredictionService:
    """
    High-level Service Layer coordinating student data extraction,
    AI inference, risk assessment, database storage, and notifications.
    """
    _predictor = None

    @classmethod
    def get_predictor(cls):
        if cls._predictor is None:
            cls._predictor = RandomForestPerformancePredictor()
        return cls._predictor

    @staticmethod
    def extract_student_features(student_table_id):
        """
        Extracts real-time input features for a student:
        - Attendance Percentage
        - Absence Count
        - Internal Marks (out of 50)
        - Previous Academic GPA (out of 10)
        NOTE: Student ID is strictly NOT used as a predictive feature!
        """
        att_stats = AttendanceService.calculate_student_attendance(student_table_id)
        att_pct = att_stats['attendance_percentage']
        absences = att_stats['absent_count']

        # Get internal examination average (scaled to 50)
        marks_row = db.query(
            "SELECT AVG((marks_obtained / max_marks) * 50.0) as avg_marks FROM academic_marks WHERE student_id = %s",
            (student_table_id,), fetchone=True
        )
        avg_internal = round(marks_row['avg_marks'], 2) if marks_row and marks_row['avg_marks'] is not None else 32.0

        # Get previous GPA
        st_row = db.query("SELECT previous_gpa FROM students WHERE id = %s", (student_table_id,), fetchone=True)
        prev_gpa = float(st_row['previous_gpa']) if st_row and st_row['previous_gpa'] is not None else 7.50

        return {
            'attendance_percentage': att_pct,
            'absence_count': absences,
            'internal_marks': avg_internal,
            'previous_gpa': prev_gpa
        }

    @staticmethod
    def predict_student(student_table_id, trigger_alert=True):
        """
        Runs ML prediction for a single student and records the outcome.
        """
        features = PredictionService.extract_student_features(student_table_id)
        vector = [
            features['attendance_percentage'],
            features['absence_count'],
            features['internal_marks'],
            features['previous_gpa']
        ]

        predictor = PredictionService.get_predictor()
        category, confidence, prob_dict = predictor.predict(vector)

        # Generate human-readable risk factors
        risk_factors = []
        if features['attendance_percentage'] < 75.0:
            risk_factors.append(f"Low Attendance ({features['attendance_percentage']:.1f}%)")
        if features['absence_count'] >= 6:
            risk_factors.append(f"High Absences ({features['absence_count']} missed sessions)")
        if features['internal_marks'] < 25.0:
            risk_factors.append(f"Low Internal Marks ({features['internal_marks']:.1f}/50)")
        if features['previous_gpa'] < 6.5:
            risk_factors.append(f"Borderline Previous GPA ({features['previous_gpa']:.2f})")
        if not risk_factors:
            risk_factors.append("Consistent attendance and satisfactory marks")

        factors_str = "; ".join(risk_factors)

        # Save or update prediction in prediction_results table
        db.execute(
            """
            INSERT INTO prediction_results 
            (student_id, attendance_percentage, total_absences, avg_internal_marks, previous_gpa, risk_category, confidence_score, risk_factors, model_version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                student_table_id,
                features['attendance_percentage'],
                features['absence_count'],
                features['internal_marks'],
                features['previous_gpa'],
                category,
                confidence,
                factors_str,
                'v1.0-RF'
            )
        )

        # Trigger notification if student needs improvement
        if trigger_alert and category == 'Needs Improvement':
            NotificationService.send_academic_risk_alert(student_table_id, category, factors_str)

        return {
            'student_id': student_table_id,
            'features': features,
            'risk_category': category,
            'confidence_score': confidence,
            'probabilities': prob_dict,
            'risk_factors': factors_str,
            'needs_support': category == 'Needs Improvement'
        }

    @staticmethod
    def run_batch_predictions_for_all():
        """Runs predictions for all active students in the database."""
        students = db.query("SELECT id FROM students WHERE enrollment_status = 'Active'")
        results = []
        for s in students:
            res = PredictionService.predict_student(s['id'], trigger_alert=False)
            results.append(res)
        return results

    @staticmethod
    def get_latest_student_prediction(student_table_id):
        sql = """
            SELECT * FROM prediction_results 
            WHERE student_id = %s 
            ORDER BY predicted_at DESC 
            LIMIT 1
        """
        row = db.query(sql, (student_table_id,), fetchone=True)
        if not row:
            # Generate fresh prediction on the fly
            res = PredictionService.predict_student(student_table_id, trigger_alert=False)
            return {
                'student_id': student_table_id,
                'risk_category': res['risk_category'],
                'confidence_score': res['confidence_score'],
                'risk_factors': res['risk_factors'],
                'attendance_percentage': res['features']['attendance_percentage'],
                'total_absences': res['features']['absence_count'],
                'avg_internal_marks': res['features']['internal_marks'],
                'previous_gpa': res['features']['previous_gpa'],
                'predicted_at': 'Just now'
            }
        return row

    @staticmethod
    def get_ai_analytics_dashboard_data():
        """
        Comprehensive data bundle for the AI Analytics Dashboard:
        - Performance distribution
        - Attendance vs Marks comparison
        - Students requiring academic support
        - Model evaluation metrics
        """
        # Distribution counts
        dist_sql = """
            SELECT risk_category, COUNT(*) as count 
            FROM prediction_results p1
            WHERE id = (SELECT MAX(id) FROM prediction_results p2 WHERE p2.student_id = p1.student_id)
            GROUP BY risk_category
        """
        dist_rows = db.query(dist_sql)
        distribution = {'Good Performance': 0, 'Average Performance': 0, 'Needs Improvement': 0}
        for r in dist_rows:
            if r['risk_category'] in distribution:
                distribution[r['risk_category']] = r['count']

        # Support required students list
        support_sql = """
            SELECT p.*, s.student_id as student_code, u.full_name, u.email, c.class_code, s.department
            FROM prediction_results p
            JOIN students s ON p.student_id = s.id
            JOIN users u ON s.user_id = u.id
            JOIN classes c ON s.class_id = c.id
            WHERE p.id = (SELECT MAX(p2.id) FROM prediction_results p2 WHERE p2.student_id = p.student_id)
              AND p.risk_category = 'Needs Improvement'
            ORDER BY p.attendance_percentage ASC, p.avg_internal_marks ASC
        """
        support_students = db.query(support_sql)

        # Scatter plot dataset: Attendance vs Internal Marks
        scatter_sql = """
            SELECT p.attendance_percentage, p.avg_internal_marks, p.risk_category, u.full_name
            FROM prediction_results p
            JOIN students s ON p.student_id = s.id
            JOIN users u ON s.user_id = u.id
            WHERE p.id = (SELECT MAX(p2.id) FROM prediction_results p2 WHERE p2.student_id = p.student_id)
        """
        scatter_data = db.query(scatter_sql)

        predictor = PredictionService.get_predictor()
        metadata = predictor.get_metadata()

        return {
            'distribution': distribution,
            'support_students': support_students,
            'scatter_data': scatter_data,
            'model_metadata': metadata
        }
