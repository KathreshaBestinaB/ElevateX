"""
Verifies the API degrades gracefully when Firebase isn't configured — a real
(non-faked) repository should surface as a clean 503, not an unhandled 500.
This complements test_patients.py/test_trials.py, which use fake repositories
and don't exercise the real Firestore-backed path at all.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_patients_returns_503_when_firebase_unconfigured():
    # No dependency override here — uses the real PatientRepository, which
    # hits Firestore. In this test/dev env Firebase isn't configured.
    response = client.get("/api/patients")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_list_trials_returns_503_when_firebase_unconfigured():
    response = client.get("/api/trials")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()
