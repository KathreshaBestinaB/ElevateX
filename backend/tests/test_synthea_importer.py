import csv
from pathlib import Path

import pytest

from app.services.synthea_importer import SyntheaImportError, load_synthea_directory

# The importer is pure parsing logic (no Firestore), so these tests build
# small CSVs on disk via tmp_path rather than mocking anything.


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_missing_patients_csv_raises_synthea_import_error(tmp_path):
    with pytest.raises(SyntheaImportError):
        load_synthea_directory(tmp_path)


def test_load_minimal_patients_csv(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "1990-01-01", "DEATHDATE": "", "GENDER": "F"},
    ])

    patients = load_synthea_directory(tmp_path)

    assert len(patients) == 1
    p = patients[0]
    assert p.gender == "female"
    assert p.source == "synthea"
    assert p.external_id == "p-1"
    assert p.conditions == []


def test_age_calculated_from_birthdate(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "2000-01-01", "DEATHDATE": "", "GENDER": "M"},
    ])

    patients = load_synthea_directory(tmp_path)

    # As of "today" in this environment (2026), someone born 2000-01-01 is 26.
    assert patients[0].age >= 25


def test_age_calculated_as_of_deathdate_for_deceased_patients(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "1950-06-01", "DEATHDATE": "2020-06-01", "GENDER": "M"},
    ])

    patients = load_synthea_directory(tmp_path)

    assert patients[0].age == 70


def test_conditions_medications_allergies_joined_by_patient(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "1980-01-01", "DEATHDATE": "", "GENDER": "F"},
    ])
    _write_csv(tmp_path / "conditions.csv", [
        {"PATIENT": "p-1", "DESCRIPTION": "Type 2 Diabetes Mellitus"},
        {"PATIENT": "p-1", "DESCRIPTION": "Type 2 Diabetes Mellitus"},  # duplicate, should dedupe
    ])
    _write_csv(tmp_path / "medications.csv", [
        {"PATIENT": "p-1", "DESCRIPTION": "Metformin 500 MG"},
    ])
    _write_csv(tmp_path / "allergies.csv", [
        {"PATIENT": "p-1", "DESCRIPTION": "Penicillin"},
    ])

    patients = load_synthea_directory(tmp_path)

    assert patients[0].conditions == ["Type 2 Diabetes Mellitus"]
    assert patients[0].medications == ["Metformin 500 MG"]
    assert patients[0].allergies == ["Penicillin"]


def test_numeric_observations_parsed_with_unit(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "1980-01-01", "DEATHDATE": "", "GENDER": "F"},
    ])
    _write_csv(tmp_path / "observations.csv", [
        {"PATIENT": "p-1", "DESCRIPTION": "HbA1c", "VALUE": "8.2", "UNITS": "%"},
    ])

    patients = load_synthea_directory(tmp_path)

    obs = patients[0].observations
    assert len(obs) == 1
    assert obs[0].name == "HbA1c"
    assert obs[0].value == 8.2
    assert obs[0].unit == "%"


def test_non_numeric_observations_are_skipped_not_guessed(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "1980-01-01", "DEATHDATE": "", "GENDER": "F"},
    ])
    _write_csv(tmp_path / "observations.csv", [
        {"PATIENT": "p-1", "DESCRIPTION": "General appearance", "VALUE": "Normal", "UNITS": ""},
    ])

    patients = load_synthea_directory(tmp_path)

    assert patients[0].observations == []


def test_rows_missing_id_or_birthdate_are_skipped(tmp_path):
    _write_csv(tmp_path / "patients.csv", [
        {"Id": "p-1", "BIRTHDATE": "1980-01-01", "DEATHDATE": "", "GENDER": "F"},
        {"Id": "", "BIRTHDATE": "1990-01-01", "DEATHDATE": "", "GENDER": "M"},
        {"Id": "p-3", "BIRTHDATE": "", "DEATHDATE": "", "GENDER": "M"},
    ])

    patients = load_synthea_directory(tmp_path)

    assert len(patients) == 1
    assert patients[0].external_id == "p-1"


def test_gender_normalization():
    from app.services.synthea_importer import _normalize_gender

    assert _normalize_gender("M") == "male"
    assert _normalize_gender("F") == "female"
    assert _normalize_gender("") == "unknown"


def test_bundled_sample_synthea_data_loads_cleanly():
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample_synthea"
    patients = load_synthea_directory(sample_dir)

    assert len(patients) == 8
    diabetic = next(p for p in patients if p.external_id == "p-001")
    assert "Type 2 Diabetes Mellitus" in diabetic.conditions
    assert any(o.name == "HbA1c" and o.value == 8.2 for o in diabetic.observations)
