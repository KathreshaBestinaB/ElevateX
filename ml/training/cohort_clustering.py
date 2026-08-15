"""
ML Training: Patient Cohort Clustering & Discovery

Applies unsupervised K-Means clustering to patient clinical profiles to discover
sub-phenotypes and research cohorts. Generates cluster profiles and characteristics.
Saves model artifacts to ml/models/cohort_clustering.joblib.

Usage:
    python ml/training/cohort_clustering.py
"""
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


def train_cohort_clustering():
    project_root = Path(__file__).resolve().parents[2]
    data_path = project_root / "data" / "silver" / "patient_outcomes.parquet"
    if not data_path.exists():
        data_path = project_root / "data" / "raw" / "outcomes.csv"
        df = pd.read_csv(data_path)
    else:
        df = pd.read_parquet(data_path)

    logger.info("Training Cohort Clustering with %d samples...", len(df))

    # Feature matrix for clustering
    features = pd.DataFrame()
    features["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(50.0)
    features["baseline_value"] = pd.to_numeric(df["baseline_value"], errors="coerce").fillna(0.0)
    features["change_pct"] = pd.to_numeric(df.get("change_pct", 0.0), errors="coerce").fillna(0.0)
    features["has_diabetes"] = df.get("has_diabetes", False).astype(int)
    features["has_hypertension"] = df.get("has_hypertension", False).astype(int)
    features["has_obesity"] = df.get("has_obesity", False).astype(int)
    features["responded"] = df.get("responded", False).astype(int)

    feature_names = list(features.columns)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    # 5 Research Cohorts
    k = 5
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)
    df["cluster"] = cluster_labels

    # Build cohort profiles
    cohort_profiles = {}
    cohort_names = [
        "Treatment-Resistant Diabetic Cohort",
        "High-Responder Metabolic Cohort",
        "Early-Stage Hypertensive Cohort",
        "Complex Multi-Comorbidity Cohort",
        "Standard Maintenance Cohort"
    ]

    for cluster_id in range(k):
        sub = df[df["cluster"] == cluster_id]
        cname = cohort_names[cluster_id] if cluster_id < len(cohort_names) else f"Cohort {cluster_id+1}"
        cohort_profiles[cluster_id] = {
            "cohort_id": f"C{cluster_id+1:03d}",
            "name": cname,
            "size": len(sub),
            "avg_age": round(float(sub["age"].mean()), 1) if "age" in sub else 0,
            "response_rate": round(float(sub["responded"].mean()), 4) if "responded" in sub else 0,
            "avg_baseline": round(float(sub["baseline_value"].mean()), 2) if "baseline_value" in sub else 0,
            "avg_change_pct": round(float(sub["change_pct"].mean()), 2) if "change_pct" in sub else 0,
        }
        logger.info("  Cluster %d: %s | Size: %d | Response Rate: %.2f%%",
                    cluster_id, cname, len(sub), cohort_profiles[cluster_id]["response_rate"] * 100)

    # Save artifacts
    model_dir = project_root / "ml" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    out_file = model_dir / "cohort_clustering.joblib"

    artifact = {
        "kmeans": kmeans,
        "scaler": scaler,
        "feature_names": feature_names,
        "cohort_profiles": cohort_profiles,
        "n_clusters": k,
    }
    joblib.dump(artifact, out_file)
    logger.info("Cohort Clustering artifact saved to %s", out_file)


if __name__ == "__main__":
    train_cohort_clustering()
