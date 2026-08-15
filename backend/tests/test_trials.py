from typing import Dict, List, Optional

from fastapi.testclient import TestClient

from app.api.trials import get_trial_repository
from app.main import app
from app.models.trial import Trial


class FakeTrialRepository:
    """In-memory stand-in for TrialRepository — same interface, no Firestore required."""

    def __init__(self):
        self._store: Dict[str, dict] = {}

    def create(self, data: dict) -> Trial:
        import uuid

        data = dict(data)
        data["trial_id"] = data.get("trial_id") or str(uuid.uuid4())
        self._store[data["trial_id"]] = data
        return Trial(**data)

    def get(self, trial_id: str) -> Optional[Trial]:
        data = self._store.get(trial_id)
        return Trial(**data) if data else None

    def list(self, limit: int = 100) -> List[Trial]:
        return [Trial(**d) for d in list(self._store.values())[:limit]]


client = TestClient(app)


def _override_repo():
    fake = FakeTrialRepository()
    app.dependency_overrides[get_trial_repository] = lambda: fake
    return fake


def teardown_function():
    app.dependency_overrides.pop(get_trial_repository, None)


def _sample_trial_payload():
    return {
        "nct_id": "NCT00000001",
        "title": "Type 2 Diabetes Metformin Study",
        "brief_summary": "A demo trial for HbA1c-controlled diabetes.",
        "status": "RECRUITING",
        "conditions": ["Type 2 Diabetes"],
        "interventions": ["Metformin"],
        "min_age": 18,
        "max_age": 65,
        "gender": "ALL",
        "eligibility_criteria": [
            {
                "criterion_type": "lab",
                "name": "HbA1c",
                "operator": ">=",
                "value": 7,
                "unit": "%",
                "required": True,
                "source_text": "HbA1c greater than or equal to 7%",
            }
        ],
        "source": "manual",
    }


def test_create_trial_returns_201_with_generated_id():
    _override_repo()
    response = client.post("/api/trials", json=_sample_trial_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["trial_id"]
    assert body["eligibility_criteria"][0]["name"] == "HbA1c"


def test_get_trial_returns_created_trial():
    _override_repo()
    created = client.post("/api/trials", json=_sample_trial_payload()).json()
    response = client.get(f"/api/trials/{created['trial_id']}")
    assert response.status_code == 200
    assert response.json()["trial_id"] == created["trial_id"]


def test_get_missing_trial_returns_404():
    _override_repo()
    response = client.get("/api/trials/does-not-exist")
    assert response.status_code == 404


def test_list_trials_returns_all_created():
    _override_repo()
    client.post("/api/trials", json=_sample_trial_payload())
    client.post("/api/trials", json=_sample_trial_payload())
    response = client.get("/api/trials")
    assert response.status_code == 200
    assert len(response.json()) == 2
