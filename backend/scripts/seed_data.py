"""
Seed Firestore with demo data for local development and hackathon demos.

Usage:
    python -m scripts.seed_data

Loads:
  1. The bundled sample Synthea CSV export (backend/data/sample_synthea/) —
     8 synthetic patients covering diabetes, hypertension, cancer, kidney
     disease, and a healthy control, sized so screening produces at least
     one ELIGIBLE, one NOT_ELIGIBLE, and one REQUIRES_REVIEW result once
     the matching engine (Phase 6) exists.
  2. Three demo clinical trials (from the project spec's demo-trial list),
     each with structured eligibility_criteria already filled in — no LLM
     extraction needed to try matching against them.

Compliance records aren't seeded yet — the Compliance model lands in
Phase 8; re-run/extend this script once that exists.

Requires Firebase to be configured (.env: FIREBASE_PROJECT_ID,
FIREBASE_CREDENTIALS_PATH).
"""
import logging
from pathlib import Path

from app.core.logging import configure_logging
from app.firebase.client import FirebaseNotConfiguredError
from app.repositories.patient_repository import PatientRepository
from app.repositories.trial_repository import TrialRepository
from app.services.synthea_importer import load_synthea_directory

configure_logging()
logger = logging.getLogger(__name__)

SAMPLE_SYNTHEA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_synthea"

DEMO_TRIALS = [
    {
        "nct_id": "NCT90000001",
        "title": "Metformin Response in Type 2 Diabetes",
        "brief_summary": "Demo trial: adults with Type 2 Diabetes and elevated HbA1c and BMI, no severe kidney disease.",
        "status": "RECRUITING",
        "conditions": ["Type 2 Diabetes Mellitus"],
        "interventions": ["Metformin"],
        "study_type": "Interventional",
        "phase": "Phase 3",
        "min_age": 18,
        "max_age": 65,
        "gender": "ALL",
        "eligibility_criteria": [
            {"criterion_type": "age", "operator": ">=", "value": 18, "required": True, "source_text": "Age 18-65"},
            {"criterion_type": "age", "operator": "<=", "value": 65, "required": True, "source_text": "Age 18-65"},
            {"criterion_type": "condition", "name": "Type 2 Diabetes Mellitus", "required": True, "source_text": "Diagnosed Type 2 Diabetes"},
            {"criterion_type": "lab", "name": "HbA1c", "operator": ">=", "value": 7, "unit": "%", "required": True, "source_text": "HbA1c >= 7%"},
            {"criterion_type": "bmi", "operator": ">=", "value": 25, "required": True, "source_text": "BMI >= 25"},
            {"criterion_type": "condition", "name": "Chronic kidney disease stage 3", "required": False, "source_text": "No severe kidney disease"},
        ],
        "source": "manual",
    },
    {
        "nct_id": "NCT90000002",
        "title": "Lisinopril Titration in Essential Hypertension",
        "brief_summary": "Demo trial: adults 40+ with essential hypertension and elevated systolic blood pressure.",
        "status": "RECRUITING",
        "conditions": ["Essential Hypertension"],
        "interventions": ["Lisinopril"],
        "study_type": "Interventional",
        "phase": "Phase 2",
        "min_age": 40,
        "max_age": None,
        "gender": "ALL",
        "eligibility_criteria": [
            {"criterion_type": "age", "operator": ">=", "value": 40, "required": True, "source_text": "Age >= 40"},
            {"criterion_type": "condition", "name": "Essential Hypertension", "required": True, "source_text": "Diagnosed essential hypertension"},
            {"criterion_type": "lab", "name": "Systolic Blood Pressure", "operator": ">=", "value": 140, "unit": "mmHg", "required": True, "source_text": "Systolic BP >= 140 mmHg"},
        ],
        "source": "manual",
    },
    {
        "nct_id": "NCT90000003",
        "title": "Tumor Marker-Guided Therapy Trial",
        "brief_summary": "Demo trial: adults 50+ with a malignant neoplastic disease diagnosis and elevated tumor marker level.",
        "status": "RECRUITING",
        "conditions": ["Malignant neoplastic disease"],
        "interventions": ["Investigational agent X"],
        "study_type": "Interventional",
        "phase": "Phase 1",
        "min_age": 50,
        "max_age": None,
        "gender": "ALL",
        "eligibility_criteria": [
            {"criterion_type": "age", "operator": ">=", "value": 50, "required": True, "source_text": "Age >= 50"},
            {"criterion_type": "condition", "name": "Malignant neoplastic disease", "required": True, "source_text": "Diagnosed malignant neoplasm"},
            {"criterion_type": "lab", "name": "Tumor Marker Level", "operator": ">=", "value": 30, "unit": "U/mL", "required": True, "source_text": "Tumor marker level >= 30 U/mL"},
        ],
        "source": "manual",
    },
]


def seed_patients() -> None:
    repo = PatientRepository()
    candidates = load_synthea_directory(SAMPLE_SYNTHEA_DIR)

    created = 0
    skipped_duplicate = 0
    for candidate in candidates:
        if candidate.external_id and repo.find_by_external_id(candidate.external_id):
            skipped_duplicate += 1
            continue
        repo.create(candidate.model_dump())
        created += 1

    logger.info(
        "Seeded patients: %d parsed, %d created, %d already present",
        len(candidates), created, skipped_duplicate,
    )


def seed_trials() -> None:
    repo = TrialRepository()

    created = 0
    skipped_duplicate = 0
    for trial_data in DEMO_TRIALS:
        if repo.find_by_nct_id(trial_data["nct_id"]):
            skipped_duplicate += 1
            continue
        repo.create(dict(trial_data))
        created += 1

    logger.info(
        "Seeded trials: %d defined, %d created, %d already present",
        len(DEMO_TRIALS), created, skipped_duplicate,
    )


def main() -> None:
    logger.info("Seeding demo data...")
    seed_patients()
    seed_trials()
    logger.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except FirebaseNotConfiguredError as exc:
        logger.error(
            "%s\nSet FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS_PATH in .env before running this script.",
            exc,
        )
