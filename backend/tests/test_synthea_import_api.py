import io
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from fastapi.testclient import TestClient

from app.api.patients import get_patient_repository
from app.main import app
from app.models.patient import Patient

SAMPLE_SYNTHEA_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_synthea"


class FakePatientRepository:
    """Same fake used in test_patients.py, plus find_by_external_id for dedup testing."""

    def __init__(self):
        self._store: Dict[str, dict] = {}

    def create(self, data: dict) -> Patient:
        import uuid

        data = dict(data)
        data["patient_id"] = data.get("patient_id") or str(uuid.uuid4())
        self._store[data["patient_id"]] = data
        return Patient(**data)

    def get(self, patient_id: str) -> Optional[Patient]:
        data = self._store.get(patient_id)
        return Patient(**data) if data else None

    def list(self, limit: int = 100) -> List[Patient]:
        return [Patient(**d) for d in list(self._store.values())[:limit]]

    def find_by_external_id(self, external_id: str) -> Optional[Patient]:
        for data in self._store.values():
            if data.get("external_id") == external_id:
                return Patient(**data)
        return None


client = TestClient(app)


def _override_repo():
    fake = FakePatientRepository()
    app.dependency_overrides[get_patient_repository] = lambda: fake
    return fake


def teardown_function():
    app.dependency_overrides.pop(get_patient_repository, None)


def _zip_sample_synthea_dir() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for csv_file in SAMPLE_SYNTHEA_DIR.glob("*.csv"):
            zf.write(csv_file, arcname=csv_file.name)
    return buffer.getvalue()


def test_import_synthea_creates_all_sample_patients():
    _override_repo()
    zip_bytes = _zip_sample_synthea_dir()

    response = client.post(
        "/api/patients/import/synthea",
        files={"file": ("synthea_export.zip", zip_bytes, "application/zip")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["total_parsed"] == 8
    assert body["created"] == 8
    assert body["skipped_duplicate"] == 0


def test_import_synthea_is_idempotent_on_reimport():
    _override_repo()
    zip_bytes = _zip_sample_synthea_dir()

    first = client.post(
        "/api/patients/import/synthea",
        files={"file": ("synthea_export.zip", zip_bytes, "application/zip")},
    )
    assert first.json()["created"] == 8

    second = client.post(
        "/api/patients/import/synthea",
        files={"file": ("synthea_export.zip", zip_bytes, "application/zip")},
    )
    body = second.json()
    assert body["created"] == 0
    assert body["skipped_duplicate"] == 8


def test_import_synthea_rejects_non_zip_file():
    _override_repo()
    response = client.post(
        "/api/patients/import/synthea",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_import_synthea_rejects_zip_without_patients_csv():
    _override_repo()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("conditions.csv", "PATIENT,DESCRIPTION\np-1,Asthma\n")

    response = client.post(
        "/api/patients/import/synthea",
        files={"file": ("bad_export.zip", buffer.getvalue(), "application/zip")},
    )
    assert response.status_code == 400
