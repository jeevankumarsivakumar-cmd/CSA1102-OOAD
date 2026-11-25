import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'student_performance_data.csv')
MODEL_FILE = os.path.join(BASE_DIR, 'student_risk_model.pkl')
METADATA_FILE = os.path.join(BASE_DIR, 'model_metadata.json')

def generate_synthetic_dataset(n_samples=1200, random_state=42):
    """
    Generates realistic student attendance and academic dataset for training.
    Simulates real-world correlation between attendance, internal marks, previous GPA,
    and actual academic outcome categories.
    """
    np.random.seed(random_state)

    # 1. Attendance percentage (normal distribution centered around 76%, bounded 40% to 100%)
    attendance = np.clip(np.random.normal(76, 14, n_samples), 35.0, 100.0)
    
    # 2. Total absences correlated inversely with attendance
    # Assuming ~60 conducted classes in a semester
    total_classes = 60
    absences = np.clip(np.round((100 - attendance) / 100.0 * total_classes + np.random.normal(0, 1.5, n_samples)), 0, 45).astype(int)

    # 3. Previous GPA (0 to 10.0 scale, average ~7.4)
    previous_gpa = np.clip(np.random.normal(7.4, 1.3, n_samples), 4.0, 10.0)

    # 4. Internal Examination Marks (out of 50, correlated with attendance and GPA)
    internal_marks = np.clip(
        (0.40 * (attendance / 100.0 * 50)) + 
        (0.50 * (previous_gpa / 10.0 * 50)) + 
        np.random.normal(0, 3.5, n_samples),
        8.0, 50.0
    )

    # 5. Determine Ground Truth Performance Category
    # Score composite: 40% internal marks (scaled to 100) + 35% attendance + 25% previous GPA (scaled to 100)
    composite_score = (
        0.40 * (internal_marks / 50.0 * 100) +
        0.35 * attendance +
        0.25 * (previous_gpa / 10.0 * 100) +
        np.random.normal(0, 3, n_samples)
    )

    labels = []
    for score in composite_score:
        if score >= 75.0:
            labels.append('Good Performance')
        elif score >= 55.0:
            labels.append('Average Performance')
        else:
            labels.append('Needs Improvement')

    df = pd.DataFrame({
        'attendance_percentage': np.round(attendance, 2),
        'absence_count': absences,
        'internal_marks': np.round(internal_marks, 2),
        'previous_gpa': np.round(previous_gpa, 2),
        'performance_category': labels
    })

    return df

def train_and_evaluate():
    print("Generating representative student academic dataset...")
    df = generate_synthetic_dataset(n_samples=1500)
    df.to_csv(DATA_FILE, index=False)
    print(f"Dataset created with {len(df)} records -> {DATA_FILE}")

    # Feature matrix X and Target vector y
    # NOTE: Student ID is strictly NOT used as a feature per requirements!
    feature_cols = ['attendance_percentage', 'absence_count', 'internal_marks', 'previous_gpa']
    X = df[feature_cols]
    y = df['performance_category']

    # Train / Test split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"Train set: {len(X_train)} samples | Test set: {len(X_test)} samples")

    # Feature standardizer
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train Random Forest Classifier
    rf_model = RandomForestClassifier(
        n_estimators=120,
        max_depth=7,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42
    )
    rf_model.fit(X_train_scaled, y_train)

    # Predictions on unseen test set
    y_pred = rf_model.predict(X_test_scaled)
    y_pred_proba = rf_model.predict_proba(X_test_scaled)

    # Real Evaluation Metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    report = classification_report(y_test, y_pred, output_dict=True)
    conf_mat = confusion_matrix(y_test, y_pred, labels=rf_model.classes_).tolist()

    feature_importances = dict(zip(feature_cols, [float(v) for v in rf_model.feature_importances_]))

    print(f"\n--- Model Evaluation Results ---")
    print(f"Test Accuracy: {accuracy * 100:.2f}%")
    print(f"Classes: {list(rf_model.classes_)}")
    print(f"Feature Importances: {feature_importances}")

    # Save model artifact bundle
    bundle = {
        'model': rf_model,
        'scaler': scaler,
        'feature_names': feature_cols,
        'classes': list(rf_model.classes_)
    }
    joblib.dump(bundle, MODEL_FILE)
    print(f"Trained model artifact saved -> {MODEL_FILE}")

    # Save metadata for evaluation display on UI
    metadata = {
        'model_name': 'Random Forest Classifier',
        'version': '1.0.0',
        'dataset_size': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': feature_cols,
        'accuracy': round(accuracy * 100, 2),
        'precision_macro': round(report['macro avg']['precision'] * 100, 2),
        'recall_macro': round(report['macro avg']['recall'] * 100, 2),
        'f1_macro': round(report['macro avg']['f1-score'] * 100, 2),
        'per_class_metrics': {
            cls: {
                'precision': round(report[cls]['precision'] * 100, 2),
                'recall': round(report[cls]['recall'] * 100, 2),
                'f1_score': round(report[cls]['f1-score'] * 100, 2),
                'support': int(report[cls]['support'])
            } for cls in rf_model.classes_
        },
        'feature_importance': {k: round(v * 100, 2) for k, v in feature_importances.items()},
        'confusion_matrix': conf_mat,
        'classes': list(rf_model.classes_)
    }

    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Model evaluation metadata saved -> {METADATA_FILE}")

    return metadata

if __name__ == '__main__':
    train_and_evaluate()
