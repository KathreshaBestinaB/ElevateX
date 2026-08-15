"""
Spark ETL Job: Silver → Gold

Reads the Silver patient_outcomes fact table (data/silver/) and computes
Gold-layer analytical aggregations (data/gold/):

  - gold/cohort_stats.parquet      — per-cohort response rates, outcome deltas
  - gold/drug_effectiveness.parquet— per-drug response rates by phase
  - gold/trial_kpis.parquet        — per-trial KPIs (enrollment, response, AE rate)
  - gold/population_kpis.parquet   — top-level dashboard KPIs (total patients, etc.)

Usage:
    python spark/jobs/silver_to_gold.py [--input data/silver] [--output data/gold]
"""
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

RESPONSE_STATUSES_POSITIVE = {"Strong Response", "Moderate Response"}


def run_gold_etl(silver_dir: Path, gold_dir: Path):
    """Build Gold analytics layer from Silver fact tables using pandas."""
    import numpy as np
    import pandas as pd

    gold_dir.mkdir(parents=True, exist_ok=True)

    # ── Load Silver fact table ───────────────────────────────────────────────
    fact_path = silver_dir / "patient_outcomes.parquet"
    if not fact_path.exists():
        # Try individual silver tables
        outcomes_path = silver_dir / "outcomes.parquet"
        if outcomes_path.exists():
            fact = pd.read_parquet(outcomes_path)
        else:
            # Last resort: raw CSVs
            raw_dir = silver_dir.parent / "raw"
            fact = pd.read_csv(raw_dir / "outcomes.csv", low_memory=False)
            patients = pd.read_csv(raw_dir / "patients.csv", low_memory=False)
            fact = fact.merge(patients[["patient_id", "gender", "age", "conditions"]],
                              on="patient_id", how="left")
    else:
        fact = pd.read_parquet(fact_path)

    logger.info("Loaded fact table: %d rows, %d columns", len(fact), len(fact.columns))

    # Ensure types
    numeric_cols = ["baseline_value", "followup_value", "change", "change_pct", "age"]
    for c in numeric_cols:
        if c in fact.columns:
            fact[c] = pd.to_numeric(fact[c], errors="coerce")

    fact["responded"] = fact["response_status"].isin(RESPONSE_STATUSES_POSITIVE)

    # ── Gold 1: Population KPIs ──────────────────────────────────────────────
    logger.info("Building Gold: population_kpis...")

    # Load other tables
    silver_patients = silver_dir / "patients.parquet"
    silver_trials   = silver_dir / "trials.parquet"
    raw_dir = silver_dir.parent / "raw"

    total_patients = (
        pd.read_parquet(silver_patients)["patient_id"].nunique()
        if silver_patients.exists()
        else fact["patient_id"].nunique()
    )
    total_trials = (
        pd.read_parquet(silver_trials)["trial_id"].nunique()
        if silver_trials.exists()
        else fact["trial_id"].nunique()
    )

    response_dist = fact.groupby("response_status")["patient_id"].count().to_dict()
    responded = int(fact["responded"].sum())
    total = len(fact)
    overall_response_rate = round(responded / total, 4) if total > 0 else 0.0

    # Adverse events
    ae_col = "adverse_events" if "adverse_events" in fact.columns else None
    ae_rate = 0.0
    if ae_col:
        fact["_has_ae"] = fact[ae_col].astype(str).str.strip().replace({"nan": "", "[]": ""}).str.len() > 0
        ae_rate = round(fact["_has_ae"].mean(), 4)

    pop_kpis = pd.DataFrame([{
        "metric": "total_patients",          "value": total_patients,
    }, {
        "metric": "total_trials",            "value": total_trials,
    }, {
        "metric": "total_outcomes",          "value": total,
    }, {
        "metric": "overall_response_rate",   "value": overall_response_rate,
    }, {
        "metric": "adverse_event_rate",      "value": ae_rate,
    }, {
        "metric": "avg_age",                 "value": round(fact["age"].mean(), 1) if "age" in fact.columns else None,
    }])
    pop_kpis_path = gold_dir / "population_kpis.parquet"
    pop_kpis.to_parquet(pop_kpis_path, index=False)
    logger.info("  ✓ population_kpis: %d metrics", len(pop_kpis))

    # ── Gold 2: Drug Effectiveness ───────────────────────────────────────────
    logger.info("Building Gold: drug_effectiveness...")
    med_col = "medication_name" if "medication_name" in fact.columns else None

    if med_col:
        drug_eff = (
            fact.groupby(med_col)
            .agg(
                total_patients=("patient_id", "nunique"),
                positive_responses=("responded", "sum"),
                avg_change=("change", "mean"),
                avg_change_pct=("change_pct", "mean"),
            )
            .reset_index()
        )
        drug_eff["response_rate"] = (drug_eff["positive_responses"] / drug_eff["total_patients"]).round(4)
        drug_eff = drug_eff.sort_values("response_rate", ascending=False)
        drug_eff_path = gold_dir / "drug_effectiveness.parquet"
        drug_eff.to_parquet(drug_eff_path, index=False)
        logger.info("  ✓ drug_effectiveness: %d drugs", len(drug_eff))
    else:
        logger.warning("  SKIP drug_effectiveness: medication_name not in fact table")

    # ── Gold 3: Trial KPIs ───────────────────────────────────────────────────
    logger.info("Building Gold: trial_kpis...")
    trial_kpis = (
        fact.groupby("trial_id")
        .agg(
            total_enrolled=("patient_id", "nunique"),
            positive_responses=("responded", "sum"),
            avg_outcome_change=("change", "mean"),
            avg_change_pct=("change_pct", "mean"),
        )
        .reset_index()
    )
    trial_kpis["response_rate"] = (trial_kpis["positive_responses"] / trial_kpis["total_enrolled"]).round(4)

    if "title" in fact.columns:
        titles = fact.drop_duplicates("trial_id")[["trial_id", "title"]]
        trial_kpis = trial_kpis.merge(titles, on="trial_id", how="left")

    trial_kpis_path = gold_dir / "trial_kpis.parquet"
    trial_kpis.to_parquet(trial_kpis_path, index=False)
    logger.info("  ✓ trial_kpis: %d trials", len(trial_kpis))

    # ── Gold 4: Cohort Stats ─────────────────────────────────────────────────
    logger.info("Building Gold: cohort_stats...")

    # Segment by condition combinations
    def assign_cohort(row):
        conds = str(row.get("conditions", "")).lower()
        responded = row.get("responded", False)
        if "diabetes" in conds and not responded:
            return "Treatment-Resistant Diabetic"
        elif "diabetes" in conds and responded:
            return "Responsive Diabetic"
        elif "hypertension" in conds and "diabetes" not in conds:
            return "Hypertension-Only"
        elif "obesity" in conds and "diabetes" not in conds:
            return "Obesity-Only"
        else:
            return "Mixed Comorbidities"

    if "conditions" in fact.columns:
        fact["cohort_label"] = fact.apply(assign_cohort, axis=1)
        cohort_stats = (
            fact.groupby("cohort_label")
            .agg(
                cohort_size=("patient_id", "nunique"),
                positive_responses=("responded", "sum"),
                avg_age=("age", "mean"),
                avg_outcome_change=("change", "mean"),
            )
            .reset_index()
        )
        cohort_stats["positive_response_rate"] = (
            cohort_stats["positive_responses"] / cohort_stats["cohort_size"]
        ).round(4)
        cohort_stats["avg_age"] = cohort_stats["avg_age"].round(1)
        cohort_stats["avg_outcome_change"] = cohort_stats["avg_outcome_change"].round(3)
        cohort_stats_path = gold_dir / "cohort_stats.parquet"
        cohort_stats.to_parquet(cohort_stats_path, index=False)
        logger.info("  ✓ cohort_stats: %d cohorts", len(cohort_stats))

    logger.info("Gold ETL complete: %d files in %s", len(list(gold_dir.glob("*.parquet"))), gold_dir)


def main():
    parser = argparse.ArgumentParser(description="ClinicalAI Silver→Gold ETL")
    parser.add_argument("--input",  default="data/silver", help="Silver Parquet directory")
    parser.add_argument("--output", default="data/gold",   help="Gold Parquet output directory")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    silver_dir = project_root / args.input
    gold_dir   = project_root / args.output

    logger.info("ClinicalAI Silver→Gold ETL")
    logger.info("  Silver: %s", silver_dir)
    logger.info("  Gold:   %s", gold_dir)

    run_gold_etl(silver_dir, gold_dir)


if __name__ == "__main__":
    main()
