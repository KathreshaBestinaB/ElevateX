"""
Synthea CSV import & normalization.

Synthea (https://github.com/synthetichealth/synthea) generates synthetic
patient records as a set of CSVs (patients.csv, conditions.csv, etc.) in a
single output directory. This module reads that directory and normalizes
each patient into our internal `PatientCreate` shape — matching exactly
what the matching engine (Phase 6) expects, so nothing downstream needs to
know a record originated from Synthea vs. manual entry.

Deliberately has zero Firestore/Firebase dependency: it's pure parsing, so
it can be unit tested without any credentials, and reused identically by
both the API upload endpoint (app/api/patients.py) and the CLI script
(scripts/import_synthea.py).

Only a handful of Synthea's real columns are used; everything else in a
real Synthea export is safely ignored via DictReader.
"""
import csv
import logging
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.models.patient import Encounter, Observation, PatientCreate, Procedure

logger = logging.getLogger(__name__)


class SyntheaImportError(ValueError):
    """Raised when a Synthea export directory is missing required files or is malformed."""


def _read_csv(path: Path) -> List[dict]:
    # utf-8-sig quietly strips a BOM if the file was exported on Windows.
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _calculate_age(birth_date: str, death_date: Optional[str] = None) -> int:
    born = _parse_date(birth_date)
    if born is None:
        raise SyntheaImportError(f"Unparseable BIRTHDATE: {birth_date!r}")
    reference = _parse_date(death_date) or date.today()
    years = reference.year - born.year - ((reference.month, reference.day) < (born.month, born.day))
    return max(years, 0)


def _normalize_gender(raw: str) -> str:
    mapping = {"M": "male", "F": "female"}
    cleaned = (raw or "").strip().upper()
    return mapping.get(cleaned, (raw or "unknown").strip().lower() or "unknown")


def _safe_float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def load_synthea_directory(directory: Path) -> List[PatientCreate]:
    """
    Parse a Synthea CSV export directory into a list of PatientCreate objects,
    ready to hand to PatientRepository.create(). `directory` must contain at
    least patients.csv; the other CSVs (conditions, medications, observations,
    procedures, allergies, encounters) are all optional — a missing one just
    means "no data in that category" rather than an error.
    """
    directory = Path(directory)
    patients_csv = directory / "patients.csv"
    if not patients_csv.exists():
        raise SyntheaImportError(f"Required file not found: {patients_csv}")

    patient_rows = _read_csv(patients_csv)

    conditions_by_patient: Dict[str, List[str]] = defaultdict(list)
    medications_by_patient: Dict[str, List[str]] = defaultdict(list)
    allergies_by_patient: Dict[str, List[str]] = defaultdict(list)
    observations_by_patient: Dict[str, List[Observation]] = defaultdict(list)
    procedures_by_patient: Dict[str, List[Procedure]] = defaultdict(list)
    encounters_by_patient: Dict[str, List[Encounter]] = defaultdict(list)

    conditions_path = directory / "conditions.csv"
    if conditions_path.exists():
        for row in _read_csv(conditions_path):
            desc = (row.get("DESCRIPTION") or "").strip()
            patient_id = row.get("PATIENT")
            if desc and patient_id:
                conditions_by_patient[patient_id].append(desc)

    medications_path = directory / "medications.csv"
    if medications_path.exists():
        for row in _read_csv(medications_path):
            desc = (row.get("DESCRIPTION") or "").strip()
            patient_id = row.get("PATIENT")
            if desc and patient_id:
                medications_by_patient[patient_id].append(desc)

    allergies_path = directory / "allergies.csv"
    if allergies_path.exists():
        for row in _read_csv(allergies_path):
            desc = (row.get("DESCRIPTION") or "").strip()
            patient_id = row.get("PATIENT")
            if desc and patient_id:
                allergies_by_patient[patient_id].append(desc)

    observations_path = directory / "observations.csv"
    if observations_path.exists():
        skipped_non_numeric = 0
        for row in _read_csv(observations_path):
            patient_id = row.get("PATIENT")
            name = (row.get("DESCRIPTION") or "").strip()
            value = _safe_float(row.get("VALUE"))
            if not patient_id or not name:
                continue
            if value is None:
                # Free-text / categorical observations (e.g. "Normal") aren't
                # usable by the numeric lab-comparison matching engine yet —
                # skip rather than guess a value.
                skipped_non_numeric += 1
                continue
            observations_by_patient[patient_id].append(
                Observation(name=name, value=value, unit=(row.get("UNITS") or None))
            )
        if skipped_non_numeric:
            logger.info("Skipped %d non-numeric observation rows", skipped_non_numeric)

    procedures_path = directory / "procedures.csv"
    if procedures_path.exists():
        for row in _read_csv(procedures_path):
            desc = (row.get("DESCRIPTION") or "").strip()
            patient_id = row.get("PATIENT")
            if desc and patient_id:
                procedures_by_patient[patient_id].append(
                    Procedure(name=desc, date=row.get("DATE") or row.get("START") or None)
                )

    encounters_path = directory / "encounters.csv"
    if encounters_path.exists():
        for row in _read_csv(encounters_path):
            enc_type = (row.get("ENCOUNTERCLASS") or row.get("DESCRIPTION") or "").strip()
            patient_id = row.get("PATIENT")
            if enc_type and patient_id:
                encounters_by_patient[patient_id].append(
                    Encounter(type=enc_type, date=row.get("START") or None)
                )

    patients: List[PatientCreate] = []
    skipped_invalid = 0
    for row in patient_rows:
        patient_id = row.get("Id")
        birth_date = row.get("BIRTHDATE")
        if not patient_id or not birth_date:
            skipped_invalid += 1
            continue

        try:
            age = _calculate_age(birth_date, death_date=row.get("DEATHDATE") or None)
        except SyntheaImportError:
            skipped_invalid += 1
            continue

        patients.append(
            PatientCreate(
                gender=_normalize_gender(row.get("GENDER", "")),
                birth_date=birth_date,
                age=age,
                conditions=sorted(set(conditions_by_patient.get(patient_id, []))),
                medications=sorted(set(medications_by_patient.get(patient_id, []))),
                allergies=sorted(set(allergies_by_patient.get(patient_id, []))),
                observations=observations_by_patient.get(patient_id, []),
                procedures=procedures_by_patient.get(patient_id, []),
                encounters=encounters_by_patient.get(patient_id, []),
                source="synthea",
                external_id=patient_id,
            )
        )

    if skipped_invalid:
        logger.warning("Skipped %d Synthea patient rows missing/unparseable Id or BIRTHDATE", skipped_invalid)

    logger.info("Normalized %d patients from Synthea directory %s", len(patients), directory)
    return patients
