from typing import Dict, List, Optional

from fastapi.testclient import TestClient

from app.api.patients import get_patient_repository
from app.main import app
from app.models.patient import Patient


class FakePatientRepository:
    """In-memory stand-in for PatientRepository — same interface, no Firestore required."""

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


client = TestClient(app)


def _override_repo():
    fake = FakePatientRepository()
    app.dependency_overrides[get_patient_repository] = lambda: fake
    return fake


def teardown_function():
    app.dependency_overrides.pop(get_patient_repository, None)


def _sample_patient_payload():
    return {
        "gender": "female",
        "birth_date": "1980-01-01",
        "age": 45,
        "conditions": ["Type 2 Diabetes"],
        "medications": ["Metformin"],
        "allergies": [],
        "observations": [{"name": "HbA1c", "value": 8.2, "unit": "%"}],
        "procedures": [],
        "encounters": [],
        "source": "manual",
    }


def test_create_patient_returns_201_with_generated_id():
    _override_repo()
    response = client.post("/api/patients", json=_sample_patient_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["patient_id"]
    assert body["conditions"] == ["Type 2 Diabetes"]


def test_get_patient_returns_created_patient():
    _override_repo()
    created = client.post("/api/patients", json=_sample_patient_payload()).json()
    response = client.get(f"/api/patients/{created['patient_id']}")
    assert response.status_code == 200
    assert response.json()["patient_id"] == created["patient_id"]


def test_get_missing_patient_returns_404():
    _override_repo()
    response = client.get("/api/patients/does-not-exist")
    assert response.status_code == 404


def test_list_patients_returns_all_created():
    _override_repo()
    client.post("/api/patients", json=_sample_patient_payload())
    client.post("/api/patients", json=_sample_patient_payload())
    response = client.get("/api/patients")
    assert response.status_code == 200
    assert len(response.json()) == 2
