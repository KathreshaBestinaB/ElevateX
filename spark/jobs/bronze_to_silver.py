"""
Spark ETL Job: Bronze → Silver

This job reads raw CSV files (data/raw/) and writes them as Parquet (data/bronze/).
Then it joins and enriches them into a Silver patient-outcome fact table (data/silver/).

Usage:
    python spark/jobs/bronze_to_silver.py [--input data/raw] [--output-bronze data/bronze] [--output-silver data/silver]

Note: For the hackathon, this runs WITHOUT a Spark cluster (uses pandas under the hood
via PySpark local mode fallback). The API's /api/analytics/spark-status endpoint will
report these layer counts.
"""
import argparse
import logging
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


def run_with_pandas(raw_dir: Path, bronze_dir: Path, silver_dir: Path):
    """
    Fallback ETL using pandas + PyArrow (no Spark cluster needed).
    Converts raw CSVs → Parquet (bronze), then builds joined fact table (silver).
    """
    import pandas as pd

    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)

    tables = {}
    csv_files = ["patients", "trials", "enrollments", "outcomes", "medications"]

    # ── Stage 1: CSV → Bronze Parquet ────────────────────────────────────────
    logger.info("Stage 1: Reading raw CSVs and writing Bronze Parquet...")
    for name in csv_files:
        src = raw_dir / f"{name}.csv"
        if not src.exists():
            logger.warning("  SKIP %s (not found)", src)
            continue
        df = pd.read_csv(src, low_memory=False)
        out_path = bronze_dir / f"{name}.parquet"
        df.to_parquet(out_path, index=False, engine="pyarrow")
        tables[name] = df
        logger.info("  ✓ %s → %s (%d rows)", src.name, out_path.name, len(df))

    # ── Stage 2: Join → Silver fact table ────────────────────────────────────
    logger.info("Stage 2: Building Silver patient_outcomes fact table...")

    if "outcomes" not in tables or "patients" not in tables:
        logger.error("Cannot build silver layer: outcomes or patients table missing.")
        return

    outcomes = tables["outcomes"].copy()
    patients = tables["patients"].copy()
    trials   = tables.get("trials", pd.DataFrame())
    meds     = tables.get("medications", pd.DataFrame())

    # Join outcomes ← patients
    patient_cols = ["patient_id", "gender", "age", "conditions"]
    patient_cols = [c for c in patient_cols if c in patients.columns]
    fact = outcomes.merge(patients[patient_cols], on="patient_id", how="left", suffixes=("", "_pt"))

    # Join outcomes ← trials
    if not trials.empty:
        trial_cols = ["trial_id", "title", "phase", "condition", "sponsor"]
        trial_cols = [c for c in trial_cols if c in trials.columns]
        fact = fact.merge(trials[trial_cols], on="trial_id", how="left", suffixes=("", "_tr"))

    # Attach first medication per patient-trial (most recent investigational drug)
    if not meds.empty:
        inv_meds = meds[meds.get("is_investigational", pd.Series(False, index=meds.index)) == True]
        first_med = (
            inv_meds.sort_values("start_date")
            .groupby(["patient_id", "trial_id"])
            .first()
            .reset_index()[["patient_id", "trial_id", "medication_name", "drug_class", "dose"]]
        )
        fact = fact.merge(first_med, on=["patient_id", "trial_id"], how="left", suffixes=("", "_med"))

    # ── Feature engineering ──────────────────────────────────────────────────
    if "change_pct" in fact.columns:
        fact["change_pct"] = pd.to_numeric(fact["change_pct"], errors="coerce")

    if "age" in fact.columns:
        fact["age_group"] = pd.cut(
            pd.to_numeric(fact["age"], errors="coerce"),
            bins=[0, 30, 45, 60, 75, 120],
            labels=["<30", "30-44", "45-59", "60-74", "75+"],
        )

    if "conditions" in fact.columns:
        fact["has_diabetes"]     = fact["conditions"].str.contains("Diabetes",     case=False, na=False)
        fact["has_hypertension"] = fact["conditions"].str.contains("Hypertension", case=False, na=False)
        fact["has_obesity"]      = fact["conditions"].str.contains("Obesity",      case=False, na=False)

    if "response_status" in fact.columns:
        fact["responded"] = fact["response_status"].isin(["Strong Response", "Moderate Response"])

    # ── Write Silver Parquet ─────────────────────────────────────────────────
    silver_path = silver_dir / "patient_outcomes.parquet"
    fact.to_parquet(silver_path, index=False, engine="pyarrow")
    logger.info("  ✓ Silver fact table → %s (%d rows, %d cols)", silver_path.name, len(fact), len(fact.columns))

    # Also write individual silver tables for quick lookup
    for name, df in tables.items():
        out_path = silver_dir / f"{name}.parquet"
        df.to_parquet(out_path, index=False, engine="pyarrow")
        logger.info("  ✓ Silver passthrough: %s (%d rows)", out_path.name, len(df))

    logger.info("ETL complete: Bronze=%d files, Silver=%d files",
                len(list(bronze_dir.glob("*.parquet"))),
                len(list(silver_dir.glob("*.parquet"))))


def run_with_pyspark(raw_dir: Path, bronze_dir: Path, silver_dir: Path):
    """Run ETL with actual PySpark (when available)."""
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F

    spark = (SparkSession.builder
             .appName("ClinicalAI_BronzeToSilver")
             .master("local[*]")
             .config("spark.sql.shuffle.partitions", "4")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")

    bronze_dir.mkdir(parents=True, exist_ok=True)
    silver_dir.mkdir(parents=True, exist_ok=True)

    tables = {}
    for name in ["patients", "trials", "enrollments", "outcomes", "medications"]:
        src = str(raw_dir / f"{name}.csv")
        if not Path(src).exists():
            logger.warning("SKIP %s", src)
            continue
        df = spark.read.csv(src, header=True, inferSchema=True)
        df.write.mode("overwrite").parquet(str(bronze_dir / name))
        tables[name] = df
        logger.info("Bronze: %s (%d rows)", name, df.count())

    # Silver join
    if "outcomes" in tables and "patients" in tables:
        fact = tables["outcomes"].join(tables["patients"].select("patient_id", "gender", "age", "conditions"),
                                       on="patient_id", how="left")
        if "trials" in tables:
            fact = fact.join(tables["trials"].select("trial_id", "title", "phase"),
                             on="trial_id", how="left")
        fact = fact.withColumn("responded",
                               F.col("response_status").isin("Strong Response", "Moderate Response"))
        fact.write.mode("overwrite").parquet(str(silver_dir / "patient_outcomes"))
        logger.info("Silver: patient_outcomes (%d rows)", fact.count())

    spark.stop()


def main():
    parser = argparse.ArgumentParser(description="ClinicalAI Bronze→Silver ETL")
    parser.add_argument("--input",         default="data/raw",    help="Raw CSV directory")
    parser.add_argument("--output-bronze", default="data/bronze", help="Bronze Parquet directory")
    parser.add_argument("--output-silver", default="data/silver", help="Silver Parquet directory")
    parser.add_argument("--engine",        default="pandas",      choices=["pandas", "pyspark"],
                        help="Execution engine (pandas=local, pyspark=cluster)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    raw_dir    = project_root / args.input
    bronze_dir = project_root / args.output_bronze
    silver_dir = project_root / args.output_silver

    logger.info("ClinicalAI Bronze→Silver ETL")
    logger.info("  Raw:    %s", raw_dir)
    logger.info("  Bronze: %s", bronze_dir)
    logger.info("  Silver: %s", silver_dir)
    logger.info("  Engine: %s", args.engine)

    if args.engine == "pyspark":
        try:
            run_with_pyspark(raw_dir, bronze_dir, silver_dir)
        except ImportError:
            logger.warning("PySpark not available, falling back to pandas engine.")
            run_with_pandas(raw_dir, bronze_dir, silver_dir)
    else:
        run_with_pandas(raw_dir, bronze_dir, silver_dir)


if __name__ == "__main__":
    main()
