"""
Spark ETL Job: Silver Layer (Bronze Parquet → Enriched Parquet)
===============================================================
Reads bronze Parquet, applies:
  - Feature engineering (age buckets, comorbidity counts, etc.)
  - Denormalization (join patients ↔ enrollments ↔ outcomes)
  - Aggregates for the analytics API

Run:
    python spark/jobs/02_bronze_to_silver.py

Requires bronze layer to exist (run 01_raw_to_bronze.py first).
"""
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"
SILVER_DIR.mkdir(parents=True, exist_ok=True)


def read_bronze(dataset: str) -> pd.DataFrame:
    path = BRONZE_DIR / f"{dataset}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Bronze file missing: {path}. Run 01_raw_to_bronze.py first.")
    return pq.read_table(path).to_pandas()


def write_silver(name: str, df: pd.DataFrame) -> Path:
    out = SILVER_DIR / f"{name}.parquet"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out, compression="snappy")
    return out


# ---------------------------------------------------------------------------
# Transformation functions
# ---------------------------------------------------------------------------

def transform_patients(patients: pd.DataFrame) -> pd.DataFrame:
    """Add computed patient features."""
    df = patients.copy()

    # Age bucket
    bins = [0, 18, 30, 45, 60, 75, 200]
    labels = ["<18", "18-30", "31-45", "46-60", "61-75", "75+"]
    df["age_bucket"] = pd.cut(df["age"].astype("float"), bins=bins, labels=labels, right=False)
    df["age_bucket"] = df["age_bucket"].astype(str)

    # Comorbidity count (pipe-delimited conditions column)
    df["comorbidity_count"] = df["conditions"].apply(
        lambda x: len([c for c in str(x).split("|") if c.strip()]) if pd.notna(x) else 0
    )

    # Polypharmacy flag (≥5 medications)
    df["medication_count"] = df["medications"].apply(
        lambda x: len([m for m in str(x).split("|") if m.strip()]) if pd.notna(x) else 0
    )
    df["polypharmacy"] = df["medication_count"] >= 5

    # Has diabetes flag
    df["has_diabetes"] = df["conditions"].str.contains("Diabetes|diabetes", na=False)

    df["_transformed_at"] = pd.Timestamp.utcnow().isoformat()
    return df


def build_patient_outcomes_fact(
    patients: pd.DataFrame,
    enrollments: pd.DataFrame,
    outcomes: pd.DataFrame,
    medications: pd.DataFrame,
) -> pd.DataFrame:
    """
    Denormalized fact table joining patients + enrollments + outcomes.
    One row per patient-trial outcome observation.
    """
    # Join outcomes → enrollments
    fact = outcomes.merge(
        enrollments[["patient_id", "trial_id", "arm", "enrollment_date", "status"]],
        on=["patient_id", "trial_id"],
        how="left",
        suffixes=("", "_enroll"),
    )

    # Join → patients (bring in age, gender, comorbidities)
    enriched_patients = patients[["patient_id", "age", "gender", "comorbidity_count", "medication_count", "has_diabetes"]].copy() if "comorbidity_count" in patients.columns else patients[["patient_id", "age", "gender"]].copy()
    fact = fact.merge(enriched_patients, on="patient_id", how="left")

    # Response binary
    positive = {"Strong Response", "Moderate Response"}
    fact["response_positive"] = fact["response_status"].isin(positive).astype(int)

    fact["_transformed_at"] = pd.Timestamp.utcnow().isoformat()
    return fact


def build_drug_effectiveness(outcomes: pd.DataFrame, medications: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate drug effectiveness: mean outcome change + response rate per drug.
    """
    med_out = outcomes.merge(
        medications[["patient_id", "trial_id", "medication_name", "drug_class"]],
        on=["patient_id", "trial_id"],
        how="left",
    )
    positive = {"Strong Response", "Moderate Response"}
    med_out["response_positive"] = med_out["response_status"].isin(positive).astype(int)

    agg = med_out.groupby("medication_name").agg(
        drug_class=("drug_class", "first"),
        patient_count=("patient_id", "nunique"),
        mean_change=("change", "mean"),
        response_rate=("response_positive", "mean"),
        adverse_event_count=("adverse_events", lambda x: x.notna().sum()),
    ).reset_index()
    agg = agg.sort_values("response_rate", ascending=False)
    return agg


def build_trial_summary(
    outcomes: pd.DataFrame,
    enrollments: pd.DataFrame,
    trials: pd.DataFrame,
) -> pd.DataFrame:
    """Per-trial aggregate: response rate, mean change, etc."""
    positive = {"Strong Response", "Moderate Response"}
    outcomes = outcomes.copy()
    outcomes["response_positive"] = outcomes["response_status"].isin(positive).astype(int)

    agg = outcomes.groupby("trial_id").agg(
        outcome_count=("outcome_id", "count"),
        mean_change=("change", "mean"),
        response_rate=("response_positive", "mean"),
    ).reset_index()

    enroll_counts = enrollments.groupby("trial_id").agg(
        enrolled_count=("patient_id", "count"),
    ).reset_index()

    agg = agg.merge(enroll_counts, on="trial_id", how="left")
    if "trial_id" in trials.columns and "title" in trials.columns:
        agg = agg.merge(trials[["trial_id", "title", "phase", "condition"]], on="trial_id", how="left")

    return agg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Spark-style ETL: BRONZE → SILVER")
    print("=" * 60)

    print("\n📖 Loading bronze tables…")
    patients = read_bronze("patients")
    enrollments = read_bronze("enrollments")
    outcomes = read_bronze("outcomes")
    medications = read_bronze("medications")
    trials = read_bronze("trials")

    # --- Silver: enriched patients ---
    print("\n🔧 Transforming patients…")
    silver_patients = transform_patients(patients)
    path = write_silver("patients", silver_patients)
    print(f"  ✅ patients → {path.name} ({len(silver_patients):,} rows)")

    # --- Silver: patient-outcomes fact table ---
    print("\n🔧 Building patient_outcomes fact table…")
    fact = build_patient_outcomes_fact(silver_patients, enrollments, outcomes, medications)
    path = write_silver("patient_outcomes_fact", fact)
    print(f"  ✅ patient_outcomes_fact → {path.name} ({len(fact):,} rows)")

    # --- Silver: drug effectiveness ---
    print("\n🔧 Computing drug effectiveness…")
    drug_eff = build_drug_effectiveness(outcomes, medications)
    path = write_silver("drug_effectiveness", drug_eff)
    print(f"  ✅ drug_effectiveness → {path.name} ({len(drug_eff):,} rows)")

    # --- Silver: trial summary ---
    print("\n🔧 Computing trial summaries…")
    trial_summary = build_trial_summary(outcomes, enrollments, trials)
    path = write_silver("trial_summary", trial_summary)
    print(f"  ✅ trial_summary → {path.name} ({len(trial_summary):,} rows)")

    print("\n✅ Silver layer complete.")


if __name__ == "__main__":
    main()
