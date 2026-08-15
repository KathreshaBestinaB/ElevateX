"""
Spark ETL Job: Bronze Layer (Raw CSV → Parquet)
================================================
Reads raw CSV files from data/raw/, applies minimal validation and type casting,
and writes them as Parquet to data/bronze/.

Run:
    python spark/jobs/01_raw_to_bronze.py

NOTE: This job uses pandas + pyarrow for portability (no Spark cluster needed
for the hackathon demo). The logic is identical to what a PySpark job would do;
swapping pandas for pyspark.sql is a one-line change per read/write.
"""
import os
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
BRONZE_DIR = PROJECT_ROOT / "data" / "bronze"
BRONZE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Schema definitions (maps CSV columns → clean Parquet types)
# ---------------------------------------------------------------------------
SCHEMAS: dict = {
    "patients": {
        "dtypes": {
            "patient_id": "str",
            "external_id": "str",
            "gender": "str",
            "age": "Int64",
            "birth_date": "str",
            "conditions": "str",        # pipe-delimited
            "medications": "str",       # pipe-delimited
            "allergies": "str",
            "source": "str",
        },
        "required_cols": ["patient_id", "gender", "age"],
    },
    "trials": {
        "dtypes": {
            "trial_id": "str",
            "nct_id": "str",
            "title": "str",
            "phase": "str",
            "condition": "str",
            "drug_class": "str",
            "status": "str",
            "enrollment_target": "Int64",
            "sponsor": "str",
            "min_age": "Int64",
            "max_age": "Int64",
            "gender": "str",
        },
        "required_cols": ["trial_id", "title"],
    },
    "enrollments": {
        "dtypes": {
            "enrollment_id": "str",
            "patient_id": "str",
            "trial_id": "str",
            "arm": "str",
            "enrollment_date": "str",
            "status": "str",
            "withdrawal_reason": "str",
        },
        "required_cols": ["enrollment_id", "patient_id", "trial_id"],
    },
    "outcomes": {
        "dtypes": {
            "outcome_id": "str",
            "patient_id": "str",
            "trial_id": "str",
            "outcome_type": "str",
            "unit": "str",
            "baseline_value": "float64",
            "followup_value": "float64",
            "change": "float64",
            "change_pct": "float64",
            "measurement_date": "str",
            "response_status": "str",
            "adverse_events": "str",
            "treatment_completed": "bool",
        },
        "required_cols": ["outcome_id", "patient_id", "trial_id", "outcome_type"],
    },
    "medications": {
        "dtypes": {
            "medication_id": "str",
            "patient_id": "str",
            "trial_id": "str",
            "medication_name": "str",
            "drug_class": "str",
            "dose": "str",
            "route": "str",
            "frequency": "str",
            "start_date": "str",
            "end_date": "str",
            "duration_weeks": "Int64",
            "is_investigational": "bool",
            "combination_with": "str",
        },
        "required_cols": ["medication_id", "patient_id", "trial_id", "medication_name"],
    },
}


def load_and_validate(dataset: str) -> pd.DataFrame:
    """Load a CSV, apply type coercions, drop rows missing required columns."""
    csv_path = RAW_DIR / f"{dataset}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {csv_path}")

    schema_info = SCHEMAS[dataset]
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    # Apply type coercions safely
    for col, dtype in schema_info["dtypes"].items():
        if col not in df.columns:
            df[col] = None
        if dtype == "Int64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        elif dtype == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif dtype == "bool":
            df[col] = df[col].str.lower().map({"true": True, "1": True, "false": False, "0": False})

    # Drop rows missing required columns
    required = schema_info["required_cols"]
    before = len(df)
    df = df.dropna(subset=required)
    dropped = before - len(df)
    if dropped:
        print(f"  ⚠  Dropped {dropped} rows with null required fields in {dataset}")

    # Add ingestion metadata
    df["_ingested_at"] = pd.Timestamp.utcnow().isoformat()
    df["_source_file"] = str(csv_path)

    return df


def write_bronze(dataset: str, df: pd.DataFrame) -> Path:
    """Write DataFrame to bronze as Parquet (snappy compressed)."""
    out_path = BRONZE_DIR / f"{dataset}.parquet"
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(table, out_path, compression="snappy")
    return out_path


def main():
    print("=" * 60)
    print("  Spark-style ETL: RAW → BRONZE")
    print("=" * 60)

    for dataset in SCHEMAS:
        print(f"\n📦 Processing: {dataset}")
        try:
            df = load_and_validate(dataset)
            out_path = write_bronze(dataset, df)
            print(f"  ✅ {len(df):,} rows → {out_path.name} ({out_path.stat().st_size / 1024:.1f} KB)")
        except FileNotFoundError as e:
            print(f"  ⏭  Skipping (not found): {e}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            raise

    print("\n✅ Bronze layer complete.")


if __name__ == "__main__":
    main()
