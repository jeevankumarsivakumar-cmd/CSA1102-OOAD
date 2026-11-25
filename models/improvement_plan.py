from datetime import date, datetime
from database.db import db

class StudentImprovementGoal:
    """
    OOAD Entity representing an actionable weekly academic milestone or task.
    """
    CATEGORIES = ('Attendance', 'Exam Prep', 'Assignment', 'Mentoring', 'Study Routine')

    def __init__(self, id=None, student_id=None, goal_title="", goal_category="Attendance",
                 target_date=None, is_completed=0, completed_at=None, created_at=None, **kwargs):
        self.id = id
        self.student_id = student_id
        self.goal_title = goal_title
        self.goal_category = goal_category
        self.target_date = str(target_date) if target_date else None
        self.is_completed = bool(is_completed)
        self.completed_at = completed_at
        self.created_at = created_at
        self.extra = kwargs

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'goal_title': self.goal_title,
            'goal_category': self.goal_category,
            'target_date': self.target_date,
            'is_completed': self.is_completed,
            'completed_at': str(self.completed_at) if self.completed_at else None,
            'created_at': str(self.created_at) if self.created_at else None
        }

    @staticmethod
    def create(student_id, goal_title, goal_category="Attendance", target_date=None):
        sql = """
            INSERT INTO student_improvement_goals (student_id, goal_title, goal_category, target_date, is_completed)
            VALUES (%s, %s, %s, %s, 0)
        """
        return db.execute(sql, (student_id, goal_title, goal_category, target_date))

    @staticmethod
    def toggle_completion(goal_id, student_id=None):
        if student_id:
            goal = db.query("SELECT * FROM student_improvement_goals WHERE id = %s AND student_id = %s", (goal_id, student_id), fetchone=True)
        else:
            goal = db.query("SELECT * FROM student_improvement_goals WHERE id = %s", (goal_id,), fetchone=True)
        
        if not goal:
            return None

        new_status = 0 if goal['is_completed'] else 1
        comp_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if new_status == 1 else None
        
        if student_id:
            sql = "UPDATE student_improvement_goals SET is_completed = %s, completed_at = %s WHERE id = %s AND student_id = %s"
            db.execute(sql, (new_status, comp_time, goal_id, student_id))
        else:
            sql = "UPDATE student_improvement_goals SET is_completed = %s, completed_at = %s WHERE id = %s"
            db.execute(sql, (new_status, comp_time, goal_id))
        
        return new_status

    @staticmethod
    def get_for_student(student_id):
        sql = """
            SELECT * FROM student_improvement_goals 
            WHERE student_id = %s 
            ORDER BY is_completed ASC, target_date ASC, created_at DESC
        """
        rows = db.query(sql, (student_id,))
        return [dict(r) for r in rows]

    @staticmethod
    def delete(goal_id, student_id=None):
        if student_id:
            sql = "DELETE FROM student_improvement_goals WHERE id = %s AND student_id = %s"
            return db.execute(sql, (goal_id, student_id))
        else:
            sql = "DELETE FROM student_improvement_goals WHERE id = %s"
            return db.execute(sql, (goal_id,))


class AcademicImprovementService:
    """
    Intelligent Service that synthesizes student attendance, internal exam scores,
    assignment marks, and Random Forest risk categorization to generate a
    personalized, non-speculative, data-grounded Academic Improvement Plan.
    """

    @staticmethod
    def generate_plan(student_id, att_stats, marks_list, prediction):
        """
        Builds a comprehensive personalized improvement plan based on actual records.
        """
        att_pct = att_stats.get('attendance_percentage', 0.0)
        total_absences = att_stats.get('absent_count', 0)
        risk_category = prediction.get('risk_category', 'Average Performance') if prediction else 'Average Performance'
        
        # Calculate subject-wise performance and mark trends
        subjects_weak = []
        subjects_strong = []
        marks_trend = "Stable"
        
        it1_scores = []
        it2_scores = []
        assignment_scores = []

        for m in marks_list:
            score_pct = (float(m['marks_obtained']) / float(m['max_marks'])) * 100.0 if m['max_marks'] > 0 else 0
            subj_name = m.get('subject_name', m.get('subject_code', 'Subject'))
            
            if m.get('exam_type') == 'Internal 1':
                it1_scores.append(score_pct)
            elif m.get('exam_type') == 'Internal 2':
                it2_scores.append(score_pct)
            elif m.get('exam_type') == 'Assignment':
                assignment_scores.append(score_pct)

            if score_pct < 60.0:
                subjects_weak.append({'subject': subj_name, 'score': score_pct, 'exam': m.get('exam_type')})
            elif score_pct >= 80.0:
                subjects_strong.append({'subject': subj_name, 'score': score_pct, 'exam': m.get('exam_type')})

        # Detect mark trajectory
        avg_it1 = sum(it1_scores) / len(it1_scores) if it1_scores else 0
        avg_it2 = sum(it2_scores) / len(it2_scores) if it2_scores else 0
        
        if avg_it1 > 0 and avg_it2 > 0:
            diff = avg_it2 - avg_it1
            if diff > 5.0:
                marks_trend = "Improving (+{:.1f}%)".format(diff)
            elif diff < -5.0:
                marks_trend = "Declining ({:.1f}%)".format(diff)
            else:
                marks_trend = "Consistent"

        # Diagnostic Status Evaluation
        status_color = "success"
        status_headline = "On Track with Strong Momentum"
        if risk_category == 'Needs Improvement' or att_pct < 75.0:
            status_color = "danger"
            status_headline = "Academic Priority Support Required"
        elif risk_category == 'Average Performance' or att_pct < 80.0:
            status_color = "warning"
            status_headline = "Moderate Academic Performance with Growth Potential"

        # Areas Requiring Improvement
        areas = []
        if att_pct < 75.0:
            areas.append({
                'title': f'Critical Attendance Shortfall ({att_pct:.1f}% vs 75% Cutoff)',
                'severity': 'Critical',
                'description': f'You have accumulated {total_absences} absences. Reaching 75% is legally required for semester examination eligibility.',
                'metric': f'{att_pct:.1f}%'
            })
        elif att_pct < 80.0:
            areas.append({
                'title': f'Attendance in Watch Zone ({att_pct:.1f}%)',
                'severity': 'Moderate',
                'description': 'Your attendance is above 75% but within the sensitive threshold. A few missed classes could trigger examination debarment.',
                'metric': f'{att_pct:.1f}%'
            })

        if "Declining" in marks_trend:
            areas.append({
                'title': 'Downward Internal Test Trajectory',
                'severity': 'High',
                'description': f'Your Internal Test 2 average ({avg_it2:.1f}%) dropped compared to Internal Test 1 ({avg_it1:.1f}%). Focus on revision is recommended.',
                'metric': f'{avg_it2 - avg_it1:.1f}%'
            })

        if subjects_weak:
            weak_names = ", ".join(list({w['subject'] for w in subjects_weak}))
            areas.append({
                'title': 'Subject Comprehension Gaps',
                'severity': 'High',
                'description': f'Scores below 60% observed in: {weak_names}. Targeted review of core concepts is recommended.',
                'metric': f'{len(subjects_weak)} assessments'
            })

        if not areas:
            areas.append({
                'title': 'No Immediate Critical Academic Risks',
                'severity': 'Low',
                'description': 'Both your attendance and examination metrics comply comfortably with department excellence benchmarks.',
                'metric': '100% On Track'
            })

        # Actionable Recommendations
        actions = []
        if att_pct < 75.0:
            actions.append({
                'phase': 'Immediate (Week 1)',
                'icon': 'bi-calendar-check',
                'title': 'Mandatory Class Attendance Lock',
                'detail': 'Attend 100% of all lectures across every scheduled subject over the next 3 weeks. Use the Attendance Recovery Simulator to calculate your target milestones.'
            })
            actions.append({
                'phase': 'Mentoring',
                'icon': 'bi-person-raised-hand',
                'title': 'Schedule Faculty Counseling',
                'detail': 'Consult with your class faculty advisor to officially log reasons for absences and obtain guidance on remedial coursework.'
            })

        if subjects_weak or "Declining" in marks_trend:
            actions.append({
                'phase': 'Mid-Term Revision',
                'icon': 'bi-journal-code',
                'title': 'Targeted Problem-Solving Sessions',
                'detail': 'Dedicate 45 minutes daily to previous semester university question papers in subjects with lower internal scores.'
            })
            actions.append({
                'phase': 'Peer Learning',
                'icon': 'bi-people',
                'title': 'Join Department Study Cohort',
                'detail': 'Collaborate with peer study groups in library Block B every Tuesday and Thursday afternoon.'
            })

        if not actions:
            actions.append({
                'phase': 'Advanced Enrichment',
                'icon': 'bi-award',
                'title': 'Pursue Academic Honors & Mini-Projects',
                'detail': 'Consult your faculty guide regarding undergraduate research publications or technical paper presentations in OOAD conferences.'
            })

        # Suggested Weekly Milestones
        weekly_goals = [
            {'week': 'Week 1', 'target': 'Zero Absences Across All Lectures', 'focus': 'Attendance'},
            {'week': 'Week 2', 'target': 'Complete Unit Revision & Lab Exercises', 'focus': 'Exam Prep'},
            {'week': 'Week 3', 'target': 'Solve 2 Previous Question Papers', 'focus': 'Self-Study'},
            {'week': 'Week 4', 'target': 'Review Progress With Faculty Mentor', 'focus': 'Mentoring'}
        ]

        return {
            'status_color': status_color,
            'status_headline': status_headline,
            'att_pct': att_pct,
            'risk_category': risk_category,
            'marks_trend': marks_trend,
            'avg_it1': round(avg_it1, 1),
            'avg_it2': round(avg_it2, 1),
            'areas': areas,
            'actions': actions,
            'weekly_goals': weekly_goals,
            'subjects_weak': subjects_weak,
            'subjects_strong': subjects_strong
        }
