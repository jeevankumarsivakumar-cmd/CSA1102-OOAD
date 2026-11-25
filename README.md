# AI-Powered Student Attendance and Academic Analytics System
### College-Level Object-Oriented Analysis & Design (OOAD) Capstone Project

![System Architecture](https://img.shields.io/badge/Architecture-Modular%20MVC%20%2B%20OOAD-indigo)
![Python](https://img.shields.io/badge/Backend-Python%203.10%20%2F%20Flask-blue)
![Database](https://img.shields.io/badge/Database-MySQL%208.0%20%2F%20SQLite%20Dual-success)
![Machine Learning](https://img.shields.io/badge/AI%20Model-Random%20Forest%2086%25%20Accuracy-violet)
![Frontend](https://img.shields.io/badge/UI-Bootstrap%205%20%2B%20Chart.js-purple)
![Tests](https://img.shields.io/badge/Tests-16%20Passed%20(100%25)-brightgreen)
![Deployment](https://img.shields.io/badge/Deployment-Render%20%2F%20Gunicorn-success)

---

## 1. Project Overview
The **AI-Powered Student Attendance and Academic Analytics System** is an intelligent university-level web platform designed to automate attendance management, monitor longitudinal attendance patterns, track internal examination marks, dispatch automated absence alerts, and identify potential academic risks using Machine Learning.

Developed following strict **Object-Oriented Analysis and Design (OOAD)** principles and **3NF relational database normalization**, the system replaces disconnected spreadsheets and static dashboards with an enterprise-ready predictive analytics hub.

---

## 2. OOAD Architectural Principles

The application strictly implements core Object-Oriented paradigms:

1. **Encapsulation**: Domain models (`User`, `Student`, `Faculty`, `AttendanceRecord`, `ClassRoom`, `FacultyIntervention`, `StudentImprovementGoal`) encapsulate internal state and provide safe business methods (`calculate_student_attendance()`, `to_dict()`, `toggle_completion()`).
2. **Inheritance**: Base `User` class is extended by specialized role classes: `Admin`, `Faculty`, and `Student`.
3. **Polymorphism**: The `User` hierarchy overrides role-based permissions and routes, dynamically dispatching role-appropriate dashboards and data scopes.
4. **Abstraction**: The `DatabaseManager` pattern abstracts away database engine differences, enabling seamless execution across both MySQL 8.0 and SQLite. The `PredictionService` decouples the application from the underlying machine learning algorithm.
5. **Association**: `Faculty` is associated with `Subject` and `ClassRoom` via the `Timetable` schedule.
6. **Aggregation**: `ClassRoom` maintains an aggregation of `Student` objects; removing a student does not destroy the class section.
7. **Composition**: `AttendanceSession` composes multiple `AttendanceRecord` entities; individual attendance records exist strictly in the context of a recorded session.

---

## 3. Technology Stack

- **Backend Framework**: Python 3.10+, Flask 3.0 (Modular Blueprints MVC)
- **Production WSGI Server**: Gunicorn 21.2+
- **Database Engine**: Dual-Engine Architecture (MySQL 8.0 with automated zero-downtime SQLite fallback)
- **Machine Learning**: `scikit-learn`, `pandas`, `numpy`, `joblib`
- **Frontend & UI/UX**: HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js 4.4
- **Reporting Engine**: `reportlab` (PDF generation), standard `csv`
- **Security**: `Werkzeug` secure PBKDF2 with SHA-256 password hashing, parameterized SQL queries, session RBAC.

---

## 4. Database Design (12 Normalized Tables in 3NF)

The database schema conforms to Third Normal Form (3NF) with referential integrity, cascading rules, and unique constraints:

| Table | Description | Key Constraints |
|---|---|---|
| `users` | Base authentication table for all system actors | `id` PK, `username` UNIQUE, `email` UNIQUE |
| `classes` | Academic sections, departments, and semesters | `id` PK, `class_code` UNIQUE |
| `faculty` | Faculty employee records, designation, qualification | `id` PK, `user_id` FK (users), `employee_id` UNIQUE |
| `students` | Student demographic records, class mapping, GPA | `id` PK, `user_id` FK (users), `class_id` FK (classes), `student_id` UNIQUE |
| `subjects` | Course catalog, credit weights, semester mapping | `id` PK, `subject_code` UNIQUE |
| `timetable` | Scheduling matrix associating class, subject, faculty | `id` PK, FKs to `classes`, `subjects`, `faculty` |
| `attendance` | Daily attendance records (`Present`, `Absent`, `On Duty`) | `id` PK, `UNIQUE(student_id, subject_id, attendance_date)` |
| `academic_marks` | Internal tests, assignments, and exam scores | `id` PK, `UNIQUE(student_id, subject_id, exam_type)` |
| `notifications` | In-app alerts, absence notices, and delivery tracking | `id` PK, `user_id` FK, `student_id` FK |
| `prediction_results` | ML inference outputs, confidence %, and risk factors | `id` PK, `student_id` FK |
| `faculty_interventions` | Mentoring sessions, assigned tasks, and recovery tracking | `id` PK, `faculty_id` FK, `student_id` FK |
| `student_improvement_goals` | Actionable weekly goals, milestones, and task completion | `id` PK, `student_id` FK |

---

## 5. Five Advanced Innovative Features

1. **Smart Attendance Recovery Simulator ("Attendance Recovery Planner")**:
   - Accurately calculates required consecutive classes to reach target attendance percentages (75%, 80%, 85%, 90%):
     $$\text{Required Classes} = \left\lceil \frac{\text{Target \%} \times \text{Total Conducted} - \text{Classes Attended}}{1 - \text{Target \%}} \right\rceil$$
   - Interactive slider and Chart.js projection trajectory curve.
   - Simulation-only mode ensuring historical records are never altered.

2. **AI-Powered Personalized Academic Improvement Planner ("My Academic Improvement Plan")**:
   - Synthesizes attendance, Internal 1 vs Internal 2 mark trajectories, assignment scores, and ML risk classification.
   - Generates grounded, data-backed diagnostic summaries and multi-phase action plans.
   - Interactive weekly goal checklist with real-time completion tracking.

3. **Smart Faculty Intervention Management ("Student Intervention Center")**:
   - Empowers faculty to identify students categorized as *Needs Improvement* or below 75% attendance.
   - Log 1-on-1 counseling notes, assign actionable remedial tasks, and record mentoring dates.
   - Automatically tracks student attendance recovery deltas (e.g., `+4.5% Improved`) post-intervention.
   - Institutional oversight dashboard for Admin.

4. **Academic Performance Trend Analytics ("My Performance Journey")**:
   - Multidimensional interactive visual analytics rendered via Chart.js.
   - Grouped bar comparisons (Test 1 vs Test 2 vs Assignment scores across subjects).
   - Longitudinal attendance timeline with reference cutoff line.
   - Subject competency radar diagram.

5. **Smart Academic Notification Center**:
   - Dedicated notification hubs for Students, Faculty, and Administrators.
   - Automated detection of critical attendance drops (<75%), approaching threshold watch zones (75%–78%), and declining marks.
   - Built-in deduplication engine preventing notification spam within 48-hour windows.

---

## 6. Machine Learning Pipeline & Evaluation

### Empirical Evaluation Metrics:
- **Model**: `RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42)`
- **Dataset Size**: 1,500 representative student profiles (1,200 Train / 300 Test)
- **Test Accuracy**: **86.00%**
- **Target Categories**: *Good Performance*, *Average Performance*, *Needs Improvement*
- **Ethical AI Guardrail**: Student ID and demographic identifiers are strictly excluded from predictive features.

---

## 7. User Roles & Demonstration Credentials

For quick evaluation, click the preset buttons on the login screen or use:

| Role | Username | Password | Purpose & Capabilities |
|---|---|---|---|
| **Admin (Dean)** | `admin` | `admin123` | Full university oversight, student/faculty/class CRUD, timetable scheduler, campus alert logs, intervention monitoring, reports. |
| **Faculty (HOD)** | `faculty1` | `faculty123` | Assigned classes, daily timetable, attendance marking, marks entry, student intervention center, class alerts. |
| **Student (Good)** | `student1` | `student123` | Aarav Patel: >95% attendance, top internal scores, 'Good Performance' AI badge, performance journey charts. |
| **Student (At Risk)** | `student3` | `student123` | Rohan Mehta: <60% attendance, <75% warning, 'Needs Improvement' advisory, attendance recovery simulator. |

---

## 8. Installation, Local Execution & Cloud Deployment

### Local Execution:
```bash
# 1. Clone repository
git clone https://github.com/jeevankumarsivakumar-cmd/CSA1102-OOAD.git
cd CSA1102-OOAD

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run automated tests (16/16 test suites)
python test_system.py

# 4. Start local development server
python app.py
```

### Production Deployment (Render / Cloud WSGI):
The repository is pre-configured with `Procfile` and `render.yaml`:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
- **Environment Variables**:
  - `PYTHON_VERSION`: `3.10.11`
  - `DB_ENGINE`: `auto` (or `mysql` if connecting to managed MySQL)
  - `FLASK_DEBUG`: `false`

---

## 9. Automated Test Verification
Run the 16-suite automated test matrix:
```bash
python test_system.py
```
- `test_01`: Tri-role authentication & session access control
- `test_02`: Student registration & auto-ID generation
- `test_03`: Timetable retrieval & faculty schedule mapping
- `test_04`: Bulk class attendance recording & database persistence
- `test_05`: Attendance percentage mathematical calculation
- `test_06`: Strict duplicate attendance prevention
- `test_07`: Automated absence alerts & 75% low attendance warning triggers
- `test_08`: Internal exam marks entry & validation
- `test_09`: Random Forest ML model inference & confidence evaluation (86.0%)
- `test_10`: PDF and CSV report generation
- `test_11`: Database relational integrity & 3NF cascading constraints
- `test_12`: Smart Attendance Recovery Simulator calculation & zero-mutation safety
- `test_13`: Personalized Academic Improvement Plan & interactive goal lifecycle
- `test_14`: Faculty Student Intervention Center, task assignments & status transitions
- `test_15`: Performance Journey multi-axis analytics & Chart.js data pipelines
- `test_16`: Smart Notification Center, automated scanning & deduplication engine
