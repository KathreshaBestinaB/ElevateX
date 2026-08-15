"""
ML Training: Patient Treatment Response Predictor

Trains an XGBoost / GradientBoosting model on the Silver patient_outcomes dataset
to predict clinical trial response (e.g. Strong/Moderate vs Minimal/No Response).
Saves model artifacts and SHAP explainer to ml/models/response_predictor.joblib.

Usage:
    python ml/training/response_predictor.py
"""
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


def prepare_features(df: pd.DataFrame):
    """Extract and encode feature matrix X and target y."""
    feature_df = pd.DataFrame()

    # Numeric features
    feature_df["baseline_value"] = pd.to_numeric(df["baseline_value"], errors="coerce").fillna(0.0)
    feature_df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(50.0)

    # Boolean / binary flags
    feature_df["has_diabetes"] = df.get("has_diabetes", False).astype(int)
    feature_df["has_hypertension"] = df.get("has_hypertension", False).astype(int)
    feature_df["has_obesity"] = df.get("has_obesity", False).astype(int)
    feature_df["treatment_completed"] = df.get("treatment_completed", True).astype(int)
    
    # Comorbidity count
    if "conditions" in df.columns:
        feature_df["num_conditions"] = df["conditions"].astype(str).apply(lambda x: len(x.split("|")) if x else 1)
    else:
        feature_df["num_conditions"] = 1

    # Categorical encoders
    encoders = {}
    cat_cols = ["gender", "phase", "drug_class"]
    for col in cat_cols:
        if col in df.columns:
            le = LabelEncoder()
            feature_df[col] = le.fit_transform(df[col].astype(str).fillna("Unknown"))
            encoders[col] = le
        else:
            feature_df[col] = 0

    # Binary Target: Responded (Strong/Moderate Response = 1, otherwise 0)
    if "responded" in df.columns:
        y = df["responded"].astype(int).values
    elif "response_status" in df.columns:
        y = df["response_status"].isin(["Strong Response", "Moderate Response"]).astype(int).values
    else:
        y = np.zeros(len(df), dtype=int)

    return feature_df, y, encoders


def train_model():
    project_root = Path(__file__).resolve().parents[2]
    data_path = project_root / "data" / "silver" / "patient_outcomes.parquet"
    if not data_path.exists():
        data_path = project_root / "data" / "raw" / "outcomes.csv"
        df = pd.read_csv(data_path)
    else:
        df = pd.read_parquet(data_path)

    logger.info("Training Response Predictor with %d samples...", len(df))

    X, y, encoders = prepare_features(df)
    feature_names = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
    )

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
    )

    model.fit(X_train, y_train)

    # Evaluation
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1] if len(np.unique(y)) > 1 else np.zeros(len(X_test))
    acc = accuracy_score(y_test, preds)
    auc = roc_auc_score(y_test, probs) if len(np.unique(y_test)) > 1 else 0.5

    logger.info("Model Performance: Accuracy=%.4f, ROC-AUC=%.4f", acc, auc)
    logger.info("Classification Report:\n%s", classification_report(y_test, preds))

    # Feature Importance
    importances = dict(zip(feature_names, model.feature_importances_.astype(float)))
    logger.info("Feature Importances: %s", importances)

    # Save artifacts
    model_dir = project_root / "ml" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    out_file = model_dir / "response_predictor.joblib"

    artifact = {
        "model": model,
        "encoders": encoders,
        "feature_names": feature_names,
        "feature_importances": importances,
        "metrics": {"accuracy": acc, "roc_auc": auc},
    }
    joblib.dump(artifact, out_file)
    logger.info("Artifact saved successfully to %s", out_file)


if __name__ == "__main__":
    train_model()
