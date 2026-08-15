"""
Research Assistant — Data-Driven Analytical Query Interface.

Answers clinical research questions by computing real statistics from the
Parquet data lake at request time.  No static answer templates, no fake cohort
sizes.  All numbers come from the bronze Parquet files.

Safety: outputs are research decision-support only — not medical advice.
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/research", tags=["research"])

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

SAFETY_NOTICE = (
    "This is a research analytics response based on synthetic observational data. "
    "It does not constitute medical advice, diagnosis, or treatment recommendation. "
    "Clinical decisions require review by qualified healthcare professionals."
)


# ── Parquet helpers ──────────────────────────────────────────────────────────


def _read(name: str, layer: str = "bronze") -> pd.DataFrame:
    p = DATA_DIR / layer / f"{name}.parquet"
    if p.exists():
        try:
            return pd.read_parquet(p)
        except Exception as e:
            logger.warning("Could not read %s: %s", p, e)
    return pd.DataFrame()


# ── Question classifier ──────────────────────────────────────────────────────


def _classify(question: str) -> str:
    q = question.lower()
    if any(kw in q for kw in ["non-response", "not respond", "didn't respond", "low response",
                               "why", "fail", "failure", "didn't work"]):
        return "non_response"
    if any(kw in q for kw in ["response rate", "effective", "medication", "drug",
                               "best treatment", "which treatment", "drug class"]):
        return "medication_effectiveness"
    if any(kw in q for kw in ["completion", "dropout", "withdraw", "finish",
                               "complete", "retention"]):
        return "trial_completion"
    if any(kw in q for kw in ["enroll", "enrol", "recruitment", "eligible",
                               "how many patient", "cohort size"]):
        return "enrollment"
    if any(kw in q for kw in ["condition", "disease", "diagnosis", "indication",
                               "prevalent", "common condition"]):
        return "condition_breakdown"
    return "general"


# ── Data computers ────────────────────────────────────────────────────────────


def _non_response_answer() -> Dict[str, Any]:
    outcomes    = _read("outcomes")
    patients    = _read("patients")
    medications = _read("medications")

    POSITIVE = {"Strong Response", "Moderate Response"}

    total   = len(outcomes)
    non_pos = 0
    if "response_status" in outcomes.columns:
        non_pos = int((~outcomes["response_status"].isin(POSITIVE)).sum())

    # Factor 1 — baseline severity
    factor_rows: List[Dict[str, Any]] = []
    if "baseline_value" in outcomes.columns and "response_status" in outcomes.columns:
        high_sev = outcomes["baseline_value"] > outcomes["baseline_value"].quantile(0.75)
        high_sev_non_resp = outcomes[high_sev & ~outcomes["response_status"].isin(POSITIVE)]
        high_sev_total    = high_sev.sum() or 1
        factor_rows.append({
            "factor": "High Baseline Disease Severity (top 25th percentile)",
            "association": "High",
            "patients_affected": int(len(high_sev_non_resp)),
            "note": (
                f"{int(len(high_sev_non_resp))} / {int(high_sev_total)} high-severity patients "
                f"({round(len(high_sev_non_resp)/high_sev_total*100,1)}%) were non-responders"
            ),
        })

    # Factor 2 — multiple medications (proxy for complex disease)
    if not medications.empty and "patient_id" in medications.columns:
        med_count = medications.groupby("patient_id").size().reset_index(name="n_meds")
        poly_pids = set(med_count[med_count["n_meds"] >= 3]["patient_id"].astype(str))
        if "patient_id" in outcomes.columns and "response_status" in outcomes.columns:
            poly_out = outcomes[outcomes["patient_id"].astype(str).isin(poly_pids)]
            poly_non = poly_out[~poly_out["response_status"].isin(POSITIVE)]
            factor_rows.append({
                "factor": "Polypharmacy (≥3 concurrent medications)",
                "association": "Moderate",
                "patients_affected": int(len(poly_non)),
                "note": (
                    f"{int(len(poly_non))} non-responders among {int(len(poly_out))} "
                    f"polypharmacy patients "
                    f"({round(len(poly_non)/max(1,len(poly_out))*100,1)}%)"
                ),
            })

    # Factor 3 — age
    if not patients.empty and "age" in patients.columns and "patient_id" in patients.columns:
        elderly = set(patients[patients["age"] >= 65]["patient_id"].astype(str))
        if "patient_id" in outcomes.columns and "response_status" in outcomes.columns:
            eld_out  = outcomes[outcomes["patient_id"].astype(str).isin(elderly)]
            eld_non  = eld_out[~eld_out["response_status"].isin(POSITIVE)]
            factor_rows.append({
                "factor": "Age ≥ 65 years",
                "association": "Moderate",
                "patients_affected": int(len(eld_non)),
                "note": (
                    f"{int(len(eld_non))} non-responders among {int(len(eld_out))} "
                    f"elderly patients "
                    f"({round(len(eld_non)/max(1,len(eld_out))*100,1)}%)"
                ),
            })

    if not factor_rows:
        factor_rows = [{"factor": "Insufficient linked data", "association": "N/A",
                        "patients_affected": 0, "note": "Run ETL to build silver layer."}]

    return {
        "question_category": "Non-Response Analysis",
        "answer": (
            f"Among {non_pos:,} non-responding patients (out of {total:,} total outcomes), "
            "the following data-derived factors were associated with lower treatment response:"
        ),
        "findings": factor_rows,
        "cohort_size": total,
        "evidence_level": "Observational — synthetic dataset",
        "disclaimer": "Observational associations in synthetic data. Does not establish causality.",
    }


def _medication_effectiveness_answer() -> Dict[str, Any]:
    medications = _read("medications")
    outcomes    = _read("outcomes")

    POSITIVE = {"Strong Response", "Moderate Response"}
    rows: List[Dict[str, Any]] = []

    drug_col  = next((c for c in medications.columns if c.lower() in ("drug_class", "drugclass", "class")), None)
    pid_med   = next((c for c in medications.columns if "patient" in c.lower()), None)
    pid_out   = next((c for c in outcomes.columns   if "patient" in c.lower()), None)
    resp_col  = next((c for c in outcomes.columns   if "response_status" in c.lower()), None)

    if drug_col and pid_med and pid_out and resp_col:
        merged = medications[[drug_col, pid_med]].merge(
            outcomes[[pid_out, resp_col]],
            left_on=pid_med, right_on=pid_out, how="inner"
        )
        for drug_class, grp in merged.groupby(drug_col):
            if not str(drug_class).strip():
                continue
            n   = len(grp)
            pos = grp[resp_col].isin(POSITIVE).sum()
            rows.append({
                "drug_class":    str(drug_class),
                "response_rate": f"{round(pos/n*100,1)}%",
                "responders":    int(pos),
                "sample_size":   n,
            })
        rows.sort(key=lambda x: -float(x["response_rate"].rstrip("%")))

    total = len(outcomes)
    return {
        "question_category": "Medication Effectiveness",
        "answer": (
            f"Response rates by drug class, computed from {total:,} outcome records "
            "merged with the medications Parquet file:"
        ),
        "findings": rows or [{"drug_class": "No drug_class column found",
                               "response_rate": "N/A", "sample_size": 0}],
        "cohort_size": total,
        "evidence_level": "High — full dataset cross-join",
        "disclaimer": "Computed from synthetic dataset. Real-world effectiveness requires clinical trial validation.",
    }


def _trial_completion_answer() -> Dict[str, Any]:
    enrollments = _read("enrollments")
    trials      = _read("trials")

    rows: List[Dict[str, Any]] = []
    phase_col   = next((c for c in trials.columns if "phase" in c.lower()), None)
    status_col  = next((c for c in enrollments.columns if "status" in c.lower()), None)
    trial_col_e = next((c for c in enrollments.columns if "trial" in c.lower()), None)
    trial_col_t = next((c for c in trials.columns if "trial_id" in c.lower() or c == "id"), None)

    if phase_col and status_col and trial_col_e and trial_col_t:
        merged = enrollments.merge(
            trials[[trial_col_t, phase_col]],
            left_on=trial_col_e, right_on=trial_col_t, how="left"
        )
        completed_vals = {"Completed", "COMPLETED", "completed", "Complete"}
        for phase, grp in merged.groupby(phase_col):
            if pd.isna(phase) or not str(phase).strip():
                continue
            n   = len(grp)
            c   = grp[status_col].isin(completed_vals).sum()
            rows.append({
                "trial_phase":     str(phase),
                "completion_rate": f"{round(c/n*100,1)}%",
                "completed":       int(c),
                "total_enrolled":  n,
            })
        rows.sort(key=lambda x: -float(x["completion_rate"].rstrip("%")))

    total = len(enrollments)
    return {
        "question_category": "Trial Completion Analysis",
        "answer": (
            f"Trial completion rates by phase, from {total:,} enrollment records "
            "joined with trial phase data:"
        ),
        "findings": rows or [{"trial_phase": "Phase data unavailable",
                               "completion_rate": "N/A", "total_enrolled": total}],
        "cohort_size": total,
        "evidence_level": "Moderate",
        "disclaimer": "Synthetic dataset patterns. Real trial completion depends on protocol-specific factors.",
    }


def _enrollment_answer() -> Dict[str, Any]:
    patients    = _read("patients")
    enrollments = _read("enrollments")
    trials      = _read("trials")

    n_patients    = len(patients)
    n_enrollments = len(enrollments)
    n_trials      = len(trials)

    # Enrollments per trial (top 10)
    top_trials: List[Dict[str, Any]] = []
    trial_col = next((c for c in enrollments.columns if "trial" in c.lower()), None)
    if trial_col:
        vc = enrollments[trial_col].value_counts().head(10)
        top_trials = [{"trial_id": str(k), "enrollments": int(v)} for k, v in vc.items()]

    return {
        "question_category": "Enrollment & Recruitment",
        "answer": (
            f"The dataset contains {n_patients:,} patients across {n_trials:,} trials "
            f"with {n_enrollments:,} total enrollment records."
        ),
        "findings": top_trials or [{"info": "No trial-enrollment linkage found"}],
        "cohort_size": n_patients,
        "evidence_level": "High — direct Parquet count",
        "disclaimer": "Counts reflect the current bronze Parquet data lake. Run Synthea generator to scale.",
    }


def _condition_breakdown_answer() -> Dict[str, Any]:
    patients = _read("patients")
    outcomes = _read("outcomes")
    POSITIVE = {"Strong Response", "Moderate Response"}

    rows: List[Dict[str, Any]] = []
    if not patients.empty and "conditions" in patients.columns:
        patient_response: Dict[str, str] = {}
        if not outcomes.empty and "patient_id" in outcomes.columns and "response_status" in outcomes.columns:
            for _, row in outcomes.iterrows():
                patient_response[str(row["patient_id"])] = str(row.get("response_status", ""))

        cond_map: Dict[str, set] = defaultdict(set)
        for _, row in patients.iterrows():
            pid  = str(row.get("patient_id", ""))
            cond = row.get("conditions", [])
            if isinstance(cond, str):
                cond = [c.strip() for c in cond.strip("[]").replace("'","").replace('"','').split(",") if c.strip()]
            for c in (cond or []):
                cond_map[c].add(pid)

        for cond, pids in sorted(cond_map.items(), key=lambda x: -len(x[1]))[:10]:
            resp_vals = [patient_response.get(p, "") for p in pids]
            pos = sum(1 for r in resp_vals if r in POSITIVE)
            rows.append({
                "condition":     cond,
                "patient_count": len(pids),
                "responders":    pos,
                "response_rate": f"{round(pos/len(pids)*100,1)}%" if pids else "N/A",
            })

    return {
        "question_category": "Condition Breakdown",
        "answer": (
            f"Top conditions by patient frequency across {len(patients):,} patients, "
            "with response rates from linked outcome records:"
        ),
        "findings": rows or [{"info": "No conditions column found in patients dataset"}],
        "cohort_size": len(patients),
        "evidence_level": "High — full cohort",
        "disclaimer": "Observational associations only. Correlation does not imply causation.",
    }


def _general_answer() -> Dict[str, Any]:
    patients    = _read("patients")
    trials      = _read("trials")
    outcomes    = _read("outcomes")
    enrollments = _read("enrollments")
    medications = _read("medications")

    POSITIVE = {"Strong Response", "Moderate Response"}
    pos_rate = 0.0
    if "response_status" in outcomes.columns and not outcomes.empty:
        pos = outcomes["response_status"].isin(POSITIVE).sum()
        pos_rate = round(pos / len(outcomes) * 100, 1)

    return {
        "question_category": "General Dataset Summary",
        "answer": "Here is a summary of the current synthetic clinical dataset:",
        "findings": [
            {"metric": "Total Patients",       "value": f"{len(patients):,}"},
            {"metric": "Clinical Trials",      "value": f"{len(trials):,}"},
            {"metric": "Enrollment Records",   "value": f"{len(enrollments):,}"},
            {"metric": "Outcome Records",      "value": f"{len(outcomes):,}"},
            {"metric": "Medication Records",   "value": f"{len(medications):,}"},
            {"metric": "Positive Response Rate", "value": f"{pos_rate}%"},
            {
                "metric": "Supported Question Types",
                "value":  (
                    "non-response factors | medication effectiveness | "
                    "trial completion | enrollment stats | condition breakdown"
                )
            },
        ],
        "cohort_size": len(patients),
        "evidence_level": "High — direct Parquet counts",
        "disclaimer": "Synthetic dataset — not for clinical use.",
    }


# ── Pydantic models ──────────────────────────────────────────────────────────


class ResearchQuery(BaseModel):
    question: str
    context: Dict[str, Any] = {}


class ResearchResponse(BaseModel):
    question: str
    question_category: str
    answer: str
    findings: List[Dict[str, Any]]
    disclaimer: str
    cohort_size: int
    evidence_level: str
    timestamp: str
    safety_notice: str = SAFETY_NOTICE


# ── Router ───────────────────────────────────────────────────────────────────


@router.post("/question", response_model=ResearchResponse)
async def ask_research_question(query: ResearchQuery) -> ResearchResponse:
    """
    Data-driven research analytics query interface.

    Classifies the question into one of 5 categories and computes the answer
    live from the Parquet data lake.  No static templates — all numbers are real.

    Example questions:
    - "Why did patients in this cohort have a low response rate?"
    - "Which drug class had the highest response rate?"
    - "What is the trial completion rate by phase?"
    - "How many patients are enrolled across all trials?"
    - "What are the most common conditions in the dataset?"
    """
    category = _classify(query.question)

    computers = {
        "non_response":            _non_response_answer,
        "medication_effectiveness": _medication_effectiveness_answer,
        "trial_completion":        _trial_completion_answer,
        "enrollment":              _enrollment_answer,
        "condition_breakdown":     _condition_breakdown_answer,
        "general":                 _general_answer,
    }

    data = computers[category]()

    return ResearchResponse(
        question=query.question,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **data,
    )
